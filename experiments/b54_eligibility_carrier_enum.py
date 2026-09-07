"""B54: enumerate the family-B carriers, where eligibility is what cannot be transferred.

B51 rewrote D30 as a rule about whether a channel exists between two classes.
The commodity is one kind of channel; a checked identity at the point of
consumption is another. B51 named four family-B candidates and recorded that the
enumeration itself had not been done. This is that enumeration.

Pure questions, no data. The output is a screen, not a reading.

The four questions are B51's, unchanged:
    Q0  one commodity          both classes buy the same thing
    Q1  no transfer            the good cannot pass from one class to the other
    Q2  two posted prices      each class has a published price
    Q3  imposed split          a third party draws the line, not the parties

Every answer carries a reason and a checked flag. An answer that has not been
checked against a document does not become a pass and does not become a fail:
it lands in the third state. That rule is criterion B54-4 and it is the point of
the station, because B51's first run mapped unchecked yes to pass and reported
four carriers it had not established.
"""

import json
from pathlib import Path

Y, N, U = "yes", "no", "unknown"

def c(answer, reason):
    """An answer checked against a document or true by definition."""
    return {"answer": answer, "checked": True, "reason": reason}

def u(answer, reason):
    """An answer carried without a document behind it."""
    return {"answer": answer, "checked": False, "reason": reason}

QUESTIONS = ["Q0_one_commodity", "Q1_no_transfer",
             "Q2_two_posted_prices", "Q3_imposed_split"]

CANDIDATES = {
    # ---- control: family A, already established, must not read as family B ---
    "electricity": {
        "family": "A: commodity cannot be transferred", "axis": "connection point",
        "Q0_one_commodity": c(Y, "one kilowatt hour is one kilowatt hour"),
        "Q1_no_transfer": c(Y, "fixed network; nothing moves past the meter. "
                               "the barrier is the good, not an identity"),
        "Q2_two_posted_prices": c(Y, "residential and industrial prices published "
                                     "per country and half year (B49, B52)"),
        "Q3_imposed_split": c(Y, "connection voltage and eligibility set by regulation"),
    },
    "piped_natural_gas": {
        "family": "A: commodity cannot be transferred", "axis": "connection point",
        "Q0_one_commodity": c(Y, "same molecule, same pipe"),
        "Q1_no_transfer": c(Y, "fixed network; the barrier is the good"),
        "Q2_two_posted_prices": c(Y, "published, though not in every country (B52: Albania)"),
        "Q3_imposed_split": c(Y, "connection and eligibility set by regulation"),
    },

    # ---- axis 1: residence -------------------------------------------------
    "tuition_resident_rate": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same seat, same instruction, same degree"),
        "Q1_no_transfer": c(Y, "residency is verified at enrolment and cannot be lent"),
        "Q2_two_posted_prices": c(Y, "IPEDS publishes in-district, in-state and "
                                     "out-of-state per school per level (B53: "
                                     "5605 schedules, 3861 schools, 2020)"),
        "Q3_imposed_split": c(Y, "residency defined by state statute, not by the school"),
    },
    "hunting_fishing_licence": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "the same licence conveys the same right to take "
                                 "the same species in the same season"),
        "Q1_no_transfer": c(Y, "the licence is issued to a named person and checked "
                               "in the field; it cannot be handed over"),
        "Q2_two_posted_prices": c(Y, "read 2026-09-07: 4 Va. Admin. Code 15-20-65 "
                                     "carries both, e.g. resident hunting $22.00 "
                                     "against nonresident $110.00, resident "
                                     "freshwater fishing $22.00 against $46.00. the "
                                     "two classes sit in separate subsections of the "
                                     "same filed regulation, which is what Q2 asks: "
                                     "each class has a published price"),
        "Q3_imposed_split": c(Y, "read 2026-09-07: Code of Virginia 29.1-319 sets who "
                                 "is entitled to a resident licence, and it is the "
                                 "legislature that sets it. the Board's authority "
                                 "under 29.1-103 covers the fee, not the residency "
                                 "test, so the operator cannot draw this line"),
    },
    "resident_admission_price": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same site, same visit"),
        "Q1_no_transfer": c(Y, "proof of residence is shown at the gate"),
        "Q2_two_posted_prices": u(Y, "both prices normally appear on the same board"),
        "Q3_imposed_split": u(U, "THIS IS THE ONE TO CHECK: a municipal site may set "
                                 "the resident price itself, which would be a chosen "
                                 "split and fail Q3. a statutory one would pass"),
    },
    "state_park_camping": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same pitch, same night"),
        "Q1_no_transfer": u(Y, "residency checked at booking or at the gate. NOT YET "
                               "READ: whether it is actually verified"),
        "Q2_two_posted_prices": u(Y, "published fee schedules per state park system"),
        "Q3_imposed_split": u(U, "the park agency may set it; same question as above"),
    },

    # ---- axis 2: means test ------------------------------------------------
    "low_income_electricity_rate": {
        "family": "B: eligibility cannot be transferred", "axis": "means test",
        "Q0_one_commodity": c(Y, "one kilowatt hour. Q0 and Q1 for this good are "
                                 "already established by B49 and B52"),
        "Q1_no_transfer": c(Y, "the good is on a fixed network AND the discount is "
                               "attached to a verified household. both barriers hold"),
        "Q2_two_posted_prices": u(Y, "the discounted schedule and the standard "
                                     "schedule are lines on the same filed tariff. "
                                     "NOT YET READ: one filed tariff"),
        "Q3_imposed_split": c(Y, "read 2026-09-07: California Public Utilities Code 739.1(a) sets the eligibility benchmark at 200 percent of the federal poverty guideline and 739.1(c)(1) binds the average effective discount to not less than 30 and not more than 35 percent. the statute draws the line AND brackets the value; the utility does neither"),
    },
    "means_tested_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "means test",
        "Q0_one_commodity": c(Y, "same trip, same vehicle"),
        "Q1_no_transfer": c(Y, "the pass is issued to a named person and inspected"),
        "Q2_two_posted_prices": u(Y, "both fares published in the same fare table"),
        "Q3_imposed_split": u(U, "read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) names seniors, disability and Medicare only. it does NOT reach this class, so the split here is not federally imposed and has to be read jurisdiction by jurisdiction"),
    },

    # ---- axis 3: nationality ------------------------------------------------
    "heritage_site_admission": {
        "family": "B: eligibility cannot be transferred", "axis": "nationality",
        "Q0_one_commodity": c(Y, "the same monument, the same entry, on the same day. "
                                 "Q0 is as strong here as anywhere in the corpus"),
        "Q1_no_transfer": c(Y, "a passport is checked at the counter; a ticket bought "
                               "at the national price cannot be used by a foreigner"),
        "Q2_two_posted_prices": c(Y, "read 2026-09-07: the Ministry of Culture "
                                     "announcement effective 2016-04-01 posts both, "
                                     "world heritage monuments Rs.30 for Indian "
                                     "citizens against Rs.500 for other foreign "
                                     "nationals, other ticketed monuments Rs.15 "
                                     "against Rs.200. ASI's own site refuses "
                                     "automated retrieval by robots rule, so the "
                                     "current rate is recorded as not retrieved "
                                     "rather than absent; it does not bear on Q2"),
        "Q3_imposed_split": c(Y, "read 2026-09-07: the Ministry of Culture set it, "
                                 "not the individual monument. this is the third "
                                 "band, nationality, which no visitor can cross"),
    },
    "foreigner_medical_fee": {
        "family": "B: eligibility cannot be transferred", "axis": "nationality",
        "Q0_one_commodity": u(U, "the same procedure may or may not be the same "
                                 "product once the class differs"),
        "Q1_no_transfer": c(Y, "eligibility is checked at the point of care"),
        "Q2_two_posted_prices": u(U, "what is published is often a reimbursement rate, "
                                     "not a price. the two numbers are then not "
                                     "commensurable (B51 flagged this for copayments)"),
        "Q3_imposed_split": u(Y, "set by health ministry regulation"),
    },

    # ---- axis 4: age --------------------------------------------------------
    "senior_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "same trip, same seat, same service"),
        "Q1_no_transfer": c(Y, "an identity card is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares appear in the published fare table"),
        "Q3_imposed_split": c(Y, "read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) makes it a condition of federal transit assistance that during non-peak hours a fare no greater than 50 percent of the peak fare be charged to seniors, to persons with the listed disabilities, and to Medicare card holders. the class line is drawn by federal statute; the operator picks the value under that ceiling"),
    },
    "child_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "same trip"),
        "Q1_no_transfer": c(Y, "age is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_imposed_split": u(U, "read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) names seniors, disability and Medicare only. it does NOT reach this class, so the split here is not federally imposed and has to be read jurisdiction by jurisdiction"),
    },
    "senior_prescription_copayment": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "the same molecule, the same pack"),
        "Q1_no_transfer": c(Y, "eligibility checked at the counter"),
        "Q2_two_posted_prices": u(U, "B51 already flagged it: what is published may be "
                                     "a reimbursement rate rather than a price, and "
                                     "two such numbers are not commensurable"),
        "Q3_imposed_split": u(Y, "the age threshold is statutory"),
    },

    # ---- axis 5: enrolment or occupation ------------------------------------
    "student_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "enrolment",
        "Q0_one_commodity": c(Y, "same trip"),
        "Q1_no_transfer": c(Y, "a student card is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_imposed_split": u(U, "read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) names seniors, disability and Medicare only. it does NOT reach this class, so the split here is not federally imposed and has to be read jurisdiction by jurisdiction"),
    },
    "military_discount": {
        "family": "none", "axis": "occupation",
        "Q0_one_commodity": c(Y, "same good"),
        "Q1_no_transfer": c(Y, "service identity is checked"),
        "Q2_two_posted_prices": c(N, "the discount is announced as a percentage off, "
                                     "and the discounted price is usually not posted "
                                     "as a second price"),
        "Q3_imposed_split": c(N, "the merchant chooses to offer it. no statute "
                                 "requires it"),
    },
    "student_software_licence": {
        "family": "none", "axis": "enrolment",
        "Q0_one_commodity": c(N, "the academic edition is commonly a different "
                                 "product: restricted licence terms, no commercial "
                                 "use, sometimes fewer features. the gap carries "
                                 "product specification, which is exactly what Q0 "
                                 "was written to catch (B51 on broadband and cable)"),
        "Q1_no_transfer": c(Y, "enrolment is verified"),
        "Q2_two_posted_prices": c(Y, "both prices posted"),
        "Q3_imposed_split": c(N, "the vendor defines the academic class itself"),
    },

    # ---- axis 6: disability -------------------------------------------------
    "disability_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "disability",
        "Q0_one_commodity": c(Y, "same trip. note: a paratransit service is NOT the "
                                 "same commodity and would fail Q0"),
        "Q1_no_transfer": c(Y, "a certificate is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_imposed_split": c(Y, "read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) makes it a condition of federal transit assistance that during non-peak hours a fare no greater than 50 percent of the peak fare be charged to seniors, to persons with the listed disabilities, and to Medicare card holders. the class line is drawn by federal statute; the operator picks the value under that ceiling"),
    },

    # ---- axis 7: registration or membership ---------------------------------
    "membership_price": {
        "family": "none", "axis": "membership",
        "Q0_one_commodity": c(Y, "same good"),
        "Q1_no_transfer": c(Y, "the card is checked"),
        "Q2_two_posted_prices": c(Y, "member and non-member prices both posted"),
        "Q3_imposed_split": c(N, "the seller draws the line and anyone may cross it "
                                 "by paying the membership. the split is chosen by "
                                 "the parties, which is what D30 second clause bars"),
    },
    "loyalty_programme_price": {
        "family": "none", "axis": "membership",
        "Q0_one_commodity": c(Y, "same good"),
        "Q1_no_transfer": c(Y, "the account is identified at checkout"),
        "Q2_two_posted_prices": c(Y, "shelf price and member price both shown"),
        "Q3_imposed_split": c(N, "the seller draws the line; enrolment is free and open"),
    },
}


def verdict(row):
    """Three states, and the middle one is load bearing.

    B54-4: an unchecked answer does not become a pass and does not become a
    fail. B51's first run had this wrong and reported four carriers it had not
    established. The mapping from cell to verdict is printed, not just the
    verdict, which is rule 11c.
    """
    answers = [row[q] for q in QUESTIONS]
    if any(a["answer"] == N and a["checked"] for a in answers):
        failed = [q for q in QUESTIONS if row[q]["answer"] == N and row[q]["checked"]]
        return "fails", failed
    if any(a["answer"] == U for a in answers):
        unresolved = [q for q in QUESTIONS if row[q]["answer"] == U]
        return "undetermined", unresolved
    if any(not a["checked"] for a in answers):
        uncheckedq = [q for q in QUESTIONS if not row[q]["checked"]]
        return "undetermined", uncheckedq
    return "carries", []


CELL_TO_VERDICT = {
    "a checked no on any question": "fails",
    "any answer is unknown": "undetermined",
    "any answer is yes but unchecked": "undetermined",
    "all four checked yes": "carries",
}


def main():
    rows = {}
    for name, row in sorted(CANDIDATES.items()):
        v, which = verdict(row)
        rows[name] = {
            "family": row["family"], "axis": row["axis"], "verdict": v,
            "questions_named": which,
            "answers": {q: row[q] for q in QUESTIONS},
        }

    carries = sorted(k for k, r in rows.items() if r["verdict"] == "carries")
    undet = sorted(k for k, r in rows.items() if r["verdict"] == "undetermined")
    fails = sorted(k for k, r in rows.items() if r["verdict"] == "fails")

    fam_b = {k: r for k, r in rows.items() if r["family"].startswith("B")}

    crit = {}

    # B54-1 known answer self check
    tui = rows["tuition_resident_rate"]
    ele = rows["electricity"]
    gas = rows["piped_natural_gas"]
    ok1 = (tui["verdict"] == "carries"
           and tui["family"].startswith("B")
           and ele["family"].startswith("A")
           and gas["family"].startswith("A"))
    crit["B54-1"] = {
        "passed": ok1,
        "name": "known answers: tuition carries and is family B; "
                "electricity and piped gas are family A",
        "detail": "tuition %s / %s, electricity %s, gas %s"
                  % (tui["verdict"], tui["family"][:1], ele["family"][:1], gas["family"][:1]),
    }

    # B54-2 every answer carries a reason
    missing = [(k, q) for k, r in rows.items() for q in QUESTIONS
               if not r["answers"][q].get("reason")]
    crit["B54-2"] = {
        "passed": not missing,
        "name": "every one of the four answers carries a reason",
        "detail": "%d candidates x 4 questions = %d answers, %d without a reason"
                  % (len(rows), 4 * len(rows), len(missing)),
    }

    # B54-3 every failure names its question
    unnamed = [k for k, r in rows.items()
               if r["verdict"] == "fails" and not r["questions_named"]]
    crit["B54-3"] = {
        "passed": not unnamed,
        "name": "every failing candidate names the question it fails",
        "detail": "%d fail, %d without a named question" % (len(fails), len(unnamed)),
    }

    # B54-4 the three state mapping, rule 11c
    leaked = []
    for k, r in rows.items():
        unchecked = [q for q in QUESTIONS if not r["answers"][q]["checked"]]
        unknown = [q for q in QUESTIONS if r["answers"][q]["answer"] == U]
        if (unchecked or unknown) and r["verdict"] in ("carries", "fails"):
            leaked.append((k, r["verdict"], unchecked, unknown))
    crit["B54-4"] = {
        "passed": not leaked,
        "name": "rule 11c: no unchecked or unknown answer is mapped to a verdict",
        "detail": "cell to verdict map printed; %d candidates carry an unchecked or "
                  "unknown answer, %d of them leaked into a verdict"
                  % (sum(1 for k, r in rows.items()
                         if any(not r["answers"][q]["checked"]
                                or r["answers"][q]["answer"] == U for q in QUESTIONS)),
                     len(leaked)),
        "leaked": leaked,
    }

    out = {
        "stage": "B54",
        "config": {
            "questions": QUESTIONS,
            "cell_to_verdict": CELL_TO_VERDICT,
            "n_candidates": len(rows),
            "axes": sorted({r["axis"] for r in rows.values()}),
        },
        "criteria": [{"name": k, "passed": v["passed"], "detail": v["detail"],
                      "criterion": v["name"]} for k, v in sorted(crit.items())],
        "counts": {"carries": len(carries), "undetermined": len(undet),
                   "fails": len(fails), "family_B": len(fam_b)},
        "carries": carries, "undetermined": undet, "fails": fails,
        "rows": rows,
    }

    dest = Path(__file__).resolve().parents[1] / "results" / "b54_eligibility_carrier_enum.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    # print the objects, not the counts (rule 11)
    print("cell -> verdict map (rule 11c):")
    for cell, v in CELL_TO_VERDICT.items():
        print("    %-32s -> %s" % (cell, v))
    print()
    print("%-32s %-9s %-14s %s" % ("candidate", "family", "verdict", "questions named"))
    print("-" * 96)
    for k, r in sorted(rows.items(), key=lambda x: (x[1]["verdict"], x[0])):
        print("%-32s %-9s %-14s %s"
              % (k, r["family"][:1], r["verdict"], ", ".join(r["questions_named"]) or "-"))
    print()
    for k, v in sorted(crit.items()):
        print("%-8s %-5s %s" % (k, "PASS" if v["passed"] else "FAIL", v["detail"]))
    print()
    print("carries %d, undetermined %d, fails %d, family B %d of %d"
          % (len(carries), len(undet), len(fails), len(fam_b), len(rows)))
    print("wrote", dest.name)
    return 0 if all(v["passed"] for v in crit.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
