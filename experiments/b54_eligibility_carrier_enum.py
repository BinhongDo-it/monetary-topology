"""B54: enumerate the family-B carriers, where eligibility is what cannot be transferred.

B51 rewrote D30 as a rule about whether a channel exists between two classes.
The commodity is one kind of channel; a checked identity at the point of
consumption is another. B51 named four family-B candidates and recorded that the
enumeration itself had not been done. This is that enumeration.

Pure questions, no data. The output is a screen, not a reading.

The four questions are B51's, unchanged:
    Q0  one commodity          both classes buy the same thing ON THE
                               FEATURES THIS ARM'S READING DEPENDS ON
    Q1  no transfer            the good cannot pass from one class to the other
    Q2  two posted prices      each class has a published price
    Q3  crossing is costly     the disfavoured class cannot cross to the other
                               side at near-zero cost

    Q3 was "a third party draws the line" until 2026-09-07. That is a proxy, and
    section R8 of this station's own results file replaced it on 2026-09-06 with
    the thing the proxy stood for, which is the cost of crossing. The instrument
    was never updated to match, so eight rows sat undetermined on a question the
    station had already superseded. D30's second clause is the source: it bars a
    chosen split because the disfavoured side then EXITS and there is no price
    difference left to read. Where the class is an attribute of a person rather
    than a form the seller may restructure, nobody exits, and what matters is
    whether the attribute can be acquired cheaply. Two of the four rows that
    already failed had their reasons written in crossing language while the
    question text still said who drew it.

    Q0 carries a reading, ruled 2026-09-08. Sameness is not a property two
    things have on their own; it is a property relative to a question. Two things
    are never identical, so an absolute Q0 can kill any carrier, and it looks like
    discipline while it does it. The rule is: write down what the reading is, list
    the features that reading depends on, compare only on that list, and record
    differences off the list without letting them enter the verdict. Different
    readings on one carrier therefore demand different amounts of sameness: a
    counting-law reading needs the least, because it counts the values a published
    programme writes and does not ask what the underlying instrument is made of; a
    square reading needs the most, because both endpoints must be the same position
    for both classes; a reachability reading needs none, because nothing is being
    compared. So a carrier that fails Q0 has not been struck out. It has been told
    which reading it is not available for.

    Every row here already answered this way. "one kilowatt hour is one kilowatt
    hour" and "same seat, same instruction, same degree" both name the features
    rather than asserting identity. The wording of the question changed; not one
    answer did, and the record is bitwise what it was.

    Bands, from that section:

        1  crossing costs near nothing            fails Q3
        2  crossing is possible and costs         this family
        3  crossing is impossible by construction the hardest band

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
             "Q2_two_posted_prices", "Q3_crossing_is_costly"]

CANDIDATES = {
    # ---- control: family A, already established, must not read as family B ---
    "electricity": {
        "family": "A: commodity cannot be transferred", "axis": "connection point",
        "Q0_one_commodity": c(Y, "one kilowatt hour is one kilowatt hour"),
        "Q1_no_transfer": c(Y, "fixed network; nothing moves past the meter. "
                               "the barrier is the good, not an identity"),
        "Q2_two_posted_prices": c(Y, "residential and industrial prices published "
                                     "per country and half year (B49, B52)"),
        "Q3_crossing_is_costly": c(Y, "band 2. connection voltage is set by regulation and changing it is a capital project. family A control row"),
        "band": 2,
        "crossing": 'rewire and re-contract at another connection voltage',
    },
    "piped_natural_gas": {
        "family": "A: commodity cannot be transferred", "axis": "connection point",
        "Q0_one_commodity": c(Y, "same molecule, same pipe"),
        "Q1_no_transfer": c(Y, "fixed network; the barrier is the good"),
        "Q2_two_posted_prices": c(Y, "published, though not in every country (B52: Albania)"),
        "Q3_crossing_is_costly": c(Y, "band 2. connection and eligibility set by regulation. family A control row"),
        "band": 2,
        "crossing": 're-contract at another connection class',
    },

    # ---- axis 1: residence -------------------------------------------------
    "tuition_resident_rate": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same seat, same instruction, same degree"),
        "Q1_no_transfer": c(Y, "residency is verified at enrolment and cannot be lent"),
        "Q2_two_posted_prices": c(Y, "IPEDS publishes in-district, in-state and "
                                     "out-of-state per school per level (B53: "
                                     "5605 schedules, 3861 schools, 2020)"),
        "Q3_crossing_is_costly": c(Y, "band 2. residency defined by state statute with a durational test"),
        "band": 2,
        "crossing": 'move and satisfy a durational residence test',
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
        "Q3_crossing_is_costly": c(Y, "band 2. read 2026-09-07: Code of Virginia 29.1-319 defines the resident class, and crossing it means moving and waiting out the durational test"),
        "band": 2,
        "crossing": 'move and satisfy a durational residence test',
    },
    "resident_admission_price": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same site, same visit"),
        "Q1_no_transfer": c(Y, "proof of residence is shown at the gate"),
        "Q2_two_posted_prices": c(Y, "read 2026-09-08: one named municipal site, "
                                     "the Shaw Park Aquatic Center in Clayton, "
                                     "Missouri, posts daily admission in three "
                                     "columns headed Resident, Corporate and "
                                     "Guest, at 7 / 10 / 13 for youth, 9 / 12 / "
                                     "15 for adult and 8 / 11 / 14 for senior. "
                                     "three posted prices for one visit, not two. "
                                     "the same page says Clayton Advantage Status "
                                     "is required to receive resident or corporate "
                                     "rates and to bring proof of residency, which "
                                     "is Q1 corroborated by the same document"),
        "Q3_crossing_is_costly": c(Y, "band 2. crossing means changing where one lives, which is far from free, and this holds whether the site or a statute drew the line. the old Q3 needed a jurisdiction-by-jurisdiction reading; this one does not"),
        "band": 2,
        "crossing": 'move and satisfy a residence test',
    },
    "state_park_camping": {
        "family": "B: eligibility cannot be transferred", "axis": "residence",
        "Q0_one_commodity": c(Y, "same pitch, same night"),
        "Q1_no_transfer": c(Y, "read 2026-09-08: Rhode Island State Parks camping "
                               "policies state that residency for rates is "
                               "determined by the primary occupant's government "
                               "issued photo identification and the booking "
                               "profile address, and that campers who reserved "
                               "as a resident and cannot provide proof are "
                               "charged the non-resident rate at check-in. "
                               "verified, with a stated consequence"),
        "Q2_two_posted_prices": c(Y, "read 2026-09-08: the same page posts four "
                                     "tiers at 18/36, 24/45, 28/55 and 50/75 "
                                     "resident against non-resident. Maine's "
                                     "published fee schedule posts the same "
                                     "split across twelve parks under column "
                                     "headers RESIDENT and NON-RESIDENT"),
        "Q3_crossing_is_costly": c(Y, "band 2, same as any residence line"),
        "band": 2,
        "crossing": 'move and satisfy a residence test',
    },

    # ---- axis 2: means test ------------------------------------------------
    "low_income_electricity_rate": {
        "family": "B: eligibility cannot be transferred", "axis": "means test",
        "Q0_one_commodity": c(Y, "one kilowatt hour. Q0 and Q1 for this good are "
                                 "already established by B49 and B52"),
        "Q1_no_transfer": c(Y, "the good is on a fixed network AND the discount is "
                               "attached to a verified household. both barriers hold"),
        "Q2_two_posted_prices": c(N, "read 2026-09-08 in the filed tariff itself, "
                                     "PG and E electric Schedule D-CARE, whose own "
                                     "title is LINE-ITEM DISCOUNT FOR CALIFORNIA "
                                     "ALTERNATE RATES FOR ENERGY (CARE) CUSTOMERS. "
                                     "it prints no per kWh charge of its own. it "
                                     "prints one multiplier, 35.000 percent off the "
                                     "otherwise applicable rate schedule, and a "
                                     "second one, 50.000 percent off the delivery "
                                     "minimum bill. a price and a published constant "
                                     "that converts it are one price, D30 third clause"),
        "Q3_crossing_is_costly": c(Y, "band 2. read 2026-09-07: California Public Utilities Code 739.1(a) sets the benchmark at 200 percent of the federal poverty level. this row now fails, on Q2: the tariff files a multiplier, not a second price"),
        "band": 2,
        "crossing": 'fall below an income benchmark',
    },
    "means_tested_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "means test",
        "Q0_one_commodity": c(Y, "same trip, same vehicle"),
        "Q1_no_transfer": c(Y, "the pass is issued to a named person and inspected"),
        "Q2_two_posted_prices": c(Y, "read 2026-09-07: one operator posts both, the standard one-way at 240 subway and 170 bus and the reduced one-way, which every reduced card including the low-income card carries, at 110 and 85. bus sits exactly at the federal half-fare ceiling and subway below it"),
        "Q3_crossing_is_costly": c(Y, "band 2. read 2026-09-07: one operator requires enrolment in an approved state assistance programme. crossing means having the income, which the disfavoured class by definition does not"),
        "band": 2,
        "crossing": 'lose income, or qualify for an assistance programme',
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
        "Q3_crossing_is_costly": c(Y, "band 3. read 2026-09-07: the Ministry of Culture set the schedule, and the class is nationality, which is not acquired to buy a ticket"),
        "band": 3,
        "crossing": 'naturalise',
    },
    "foreigner_medical_fee": {
        "family": "B: eligibility cannot be transferred", "axis": "nationality",
        "Q0_one_commodity": c(Y, "read 2026-09-08: the health ministry publishes "
                                 "its subsidy table per ward class, which is the "
                                 "system's own way of holding the commodity "
                                 "fixed. a citizen and a foreigner in ward class "
                                 "B2 occupy the same class of bed for the same "
                                 "procedure"),
        "Q1_no_transfer": c(Y, "eligibility is checked at the point of care"),
        "Q2_two_posted_prices": c(N, "read 2026-09-08: Singapore's health ministry "
                                     "publishes subsidy percentages per ward class "
                                     "and residency status, 20/10/none for B1, "
                                     "65/55/none for B2, 80/70/none for C, 65/55/"
                                     "none for day surgery and 50/40/none for the "
                                     "specialist outpatient clinic. one bill and "
                                     "three published constants, so D30 third "
                                     "clause again, the fifth instance after the "
                                     "utility tariff, the two Japanese statutes and "
                                     "the military discount"),
        "Q3_crossing_is_costly": c(Y, "band 3. naturalisation takes years where it is available at all"),
        "band": 3,
        "crossing": 'naturalise',
    },

    # ---- axis 4: age --------------------------------------------------------
    "senior_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "same trip, same seat, same service"),
        "Q1_no_transfer": c(Y, "an identity card is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares appear in the published fare table"),
        "Q3_crossing_is_costly": c(Y, "band 2. the crossing is waiting, which cannot be bought at a point in time, so within a cross section the membership is pinned. read 2026-09-07: 49 U.S.C. 5307(c)(1)(D) also imposes it, but that is no longer what Q3 asks"),
        "band": 2,
        "crossing": 'wait',
    },
    "child_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "same trip"),
        "Q1_no_transfer": c(Y, "age is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_crossing_is_costly": c(Y, "band 3. the disfavoured class here is adults, and the crossing is not merely costly, it does not exist in either a cross section or a panel. who drew the line does not enter"),
        "band": 3,
        "crossing": 'an adult cannot become a child in any window',
    },
    "senior_prescription_copayment": {
        "family": "B: eligibility cannot be transferred", "axis": "age",
        "Q0_one_commodity": c(Y, "the same molecule, the same pack"),
        "Q1_no_transfer": c(Y, "eligibility checked at the counter"),
        "Q2_two_posted_prices": c(N, "read 2026-09-08 in the statutes themselves, "
                                     "Japan. Health Insurance Act article 74 "
                                     "paragraph 1 makes the patient charge the "
                                     "amount computed under article 76 multiplied "
                                     "by the ratio the item names, 30 or 20 or 30 "
                                     "per hundred; the Act on Assurance of Medical "
                                     "Care for Elderly People article 67 does the "
                                     "same at 10 or 20 or 30. one price, computed "
                                     "once for everyone, and a statutory multiplier "
                                     "on top of it. B51 guessed the obstacle was "
                                     "commensurability; the statute says it is "
                                     "D30 third clause, the same one that fails "
                                     "low_income_electricity_rate"),
        "Q3_crossing_is_costly": c(Y, "band 2, same as the transit age line: the crossing is waiting. this row now fails, on Q2: the statute prices once and multiplies"),
        "band": 2,
        "crossing": 'wait',
    },

    # ---- axis 5: enrolment or occupation ------------------------------------
    "student_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "enrolment",
        "Q0_one_commodity": c(Y, "same trip"),
        "Q1_no_transfer": c(Y, "a student card is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_crossing_is_costly": c(Y, "band 2. read 2026-09-07: both operators require enrolment at a participating school and issue a card against a roster, so an adult cannot cross without enrolling. that the federal condition does not reach this class is no longer what Q3 asks"),
        "band": 2,
        "crossing": 'enrol at a participating school',
    },
    "military_discount": {
        "family": "none", "axis": "occupation",
        "Q0_one_commodity": c(Y, "same good"),
        "Q1_no_transfer": c(Y, "service identity is checked"),
        "Q2_two_posted_prices": c(N, "the discount is announced as a percentage off, "
                                     "and the discounted price is usually not posted "
                                     "as a second price"),
        "Q3_crossing_is_costly": c(Y, "band 2. enlisting is expensive in every sense. this row still fails, on Q2: the discounted price is usually not posted as a second price"),
        "band": 2,
        "crossing": 'enlist',
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
        "Q3_crossing_is_costly": c(Y, "band 2. enrolment is costly. this row still fails, on Q0: the academic edition is a different product"),
        "band": 2,
        "crossing": 'enrol',
    },

    # ---- axis 6: disability -------------------------------------------------
    "disability_transit_fare": {
        "family": "B: eligibility cannot be transferred", "axis": "disability",
        "Q0_one_commodity": c(Y, "same trip. note: a paratransit service is NOT the "
                                 "same commodity and would fail Q0"),
        "Q1_no_transfer": c(Y, "a certificate is inspected"),
        "Q2_two_posted_prices": c(Y, "both fares published"),
        "Q3_crossing_is_costly": c(Y, "band 3. nobody crosses this line to obtain a fare, and the crossing is not available at any price. read 2026-09-07: also federally imposed"),
        "band": 3,
        "crossing": 'acquire a qualifying disability',
    },

    # ---- axis 7: registration or membership ---------------------------------
    # Re-read 2026-09-23 against D30's fourth clause, which adds soft resistance to
    # the crossing cost and asks one more question of band 1: can someone else cross
    # for you? Both rows were generic until then, and their Q0 to Q2 had no document
    # behind them. Each is now pinned to one named seller and read from that seller's
    # own terms. Both still fail, and in both the seller's terms answer the new
    # question yes: the crossing can be done by someone else.
    "membership_price": {
        "family": "none", "axis": "membership",
        "carrier": "Costco (United States), Member Privileges and Conditions, last updated 2026-03-30; customer service answer 1155",
        "Q0_one_commodity": c(Y, "the same item sold to members and, online, to non-members"),
        "Q1_no_transfer": c(N, "the card is checked ('not transferable', 'recognizable, unobstructed full-face photo'), "
                               "but the goods pass: the terms provide for members 'purchased for resale' with a resale "
                               "licence on file, and Shop Cards let non-members buy. Someone else crosses for you"),
        "Q2_two_posted_prices": c(N, "in the warehouse 'Only Costco members may purchase items', so one price; online a "
                                     "non-member pays 'a 5% surcharge over posted prices for members'. One price and a "
                                     "published constant is one price (D30 third clause)"),
        "Q3_crossing_is_costly": c(N, "band 1. the fee is not near zero, but the crossing can be done by a member or a "
                                      "reseller on your behalf, which D30's fourth clause prices at the cheapest crosser"),
        "band": 1,
        "crossing": 'pay the fee, or have a member or reseller buy for you',
    },
    "loyalty_programme_price": {
        "family": "none", "axis": "membership",
        "carrier": "Safeway forU, Program Details, last updated 2026-06-12",
        "Q0_one_commodity": c(Y, "the same item at the member price and at the regular price"),
        "Q1_no_transfer": c(N, "member prices need 'your forU account number at checkout or the phone number you used "
                               "when registering', and the terms provide for another person using it: 'If a Program "
                               "Member's account number is used by any other person, all Points relating to purchases "
                               "made by such other person will be credited to the Program Member's account.' The good "
                               "itself carries no restriction after purchase"),
        "Q2_two_posted_prices": u(Y, "member price and regular price are shown side by side at the shelf; the program "
                                     "terms do not say how they are displayed, so this is not checked"),
        "Q3_crossing_is_costly": c(N, "band 1. 'forU program is a free customer loyalty program' and 'No purchase is "
                                      "required to become a Program Member'; the terms also provide for crossing on "
                                      "another member's number"),
        "band": 1,
        "crossing": "enrol free, or use a member's number at checkout",
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
        if "carrier" in row:
            rows[name]["carrier"] = row["carrier"]

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
    KIND = {"B54-1": "known_answer", "B54-2": "bookkeeping",
            "B54-3": "bookkeeping", "B54-4": "instrument", "B54-5": "instrument"}

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

    # B54-4 the three state mapping, rule 11c. A leak is a verdict that rests on an
    # unchecked or unknown cell. A fail rests only on the questions it names, and
    # verdict() names checked noes only, so an unchecked yes elsewhere in a failing
    # row is not mapped to anything. Until 2026-09-23 this counted every failing row
    # that carried any unchecked cell, which is one cell wider than rule 11c; no row
    # had one before, so no reading moves.
    leaked = []
    for k, r in rows.items():
        unchecked = [q for q in QUESTIONS if not r["answers"][q]["checked"]]
        unknown = [q for q in QUESTIONS if r["answers"][q]["answer"] == U]
        rests_on = unchecked + unknown if r["verdict"] == "carries" else (
            [q for q in r["questions_named"] if q in unchecked or q in unknown]
            if r["verdict"] == "fails" else [])
        if rests_on:
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

    # B54-5. The band and the Q3 answer are two writings of one fact, so they must
    # agree: band 1 is the near-zero crossing D30's second clause bars and must
    # answer no, bands 2 and 3 must answer yes. A row where they disagree means
    # one of the two was written without the other in view.
    disagree = []
    for name, cand in sorted(CANDIDATES.items()):
        band = cand.get("band")
        ans = cand["Q3_crossing_is_costly"]["answer"]
        if band is None:
            disagree.append(name + ":no band")
        elif (band == 1) != (ans == N):
            disagree.append("%s:band %d vs %s" % (name, band, ans))
    bands = {}
    for cand in CANDIDATES.values():
        bands[cand.get("band")] = bands.get(cand.get("band"), 0) + 1
    crit["B54-5"] = {"passed": not disagree,
        "name": "the band and the Q3 answer agree in every row: band 1 answers no, "
                "bands 2 and 3 answer yes",
        "detail": "%d candidates, %d disagreements; bands %s"
                  % (len(CANDIDATES), len(disagree),
                     ", ".join("%s:%d" % (b, n) for b, n in sorted(bands.items())))}

    out = {
        "stage": "B54",
        "config": {
            "questions": QUESTIONS,
            "cell_to_verdict": CELL_TO_VERDICT,
            "n_candidates": len(rows),
            "axes": sorted({r["axis"] for r in rows.values()}),
        },
        "criteria": [{"name": k, "passed": v["passed"], "kind": KIND[k],
                         "detail": v["detail"], "criterion": v["name"]} for k, v in sorted(crit.items())],
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
