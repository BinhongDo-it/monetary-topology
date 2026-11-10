"""B143: where a statute draws the line of a price regulation, and which side of it gets a written price.

A good can change hands after it is delivered, so a third party can close a loop through it and the
cheapest crosser holds its price. A delivered service cannot change hands. The only loop that can hold its
price is the buyer's own, between two offers the buyer can compare before buying. Where the buyer has no such
comparison (the buyer did not consent, hailed in the street, was in an emergency, never chose a tariff),
nothing in the market holds the price, and the seller alone writes it.

This station reads statutes and rules that regulate the price of part of one line of business and say, in
their own words, where the regulated part ends. For each provision it records the dividing words, the side
whose price an authority writes, and what kind of thing the dividing words name:

    buyer_act        something the buyer did or could do at this transaction: consent, prior arrangement,
                     a hail, choosing a tariff, renewing
    emergency        an emergency, of the buyer or declared by a government
    good_or_seller   an attribute of the good, the service or the seller: the cargo, the kind of service,
                     the seller's size

Nothing is estimated and nothing is fitted. The corpus is small and printed in full, including the rows whose
line follows the seller or the good. Which transactions a legislature regulates is a choice made by people, so
the readings are statements that such provisions exist, with printed counts over the rows read, and not laws.

The corpus: the towing provision, read first; two provisions named from memory before they were read (taxi
fares, emergency medical bills); the other price provisions met in the same sections (household goods, air
ambulance); two price rules
this repository already cites from their official texts (the British default tariff cap and the renewal-price
rule for insurance); the debit interchange rule, whose line is drawn on the size of the seller; and one
statute for the emergency cell (California Penal Code 396).

Every fragment below was copied from a page opened for this station, and the record carries which page and
when. A row whose page was not opened is not a reading and leaves every count (rule 11c: the third state maps
to no verdict).

    python experiments/b143_price_control_line.py              # print the rows and write the record
    python experiments/b143_price_control_line.py --selftest   # seeded faults, each must be caught
"""

import argparse
import copy
import json
import sys
from pathlib import Path

KINDS = {
    "buyer_act": "something the buyer did or could do at this transaction: consent, prior arrangement, "
                 "a hail, choosing a tariff, renewing",
    "emergency": "an emergency, of the buyer or declared by a government",
    "good_or_seller": "an attribute of the good, the service or the seller",
}

# A row is read only when its pages were opened and the provision names both sides of its line.
STATE_OF_ROW = {
    "a cited page was not opened for this station": "unopened: not a reading, leaves every count",
    "pages opened, the text does not name the other side of the line": "no_object: printed, not counted",
    "pages opened and both sides named": "read",
}

DIRECTION_OF_ROW = {
    "the authority writes the price on the side the buyer did not act on": "no_choice_side_written",
    "the authority writes the price on the side the buyer acted on": "reversed",
    "the text does not say which side the buyer acted on": "undetermined: no verdict",
}

SOURCES = {
    "usc49_14501": {
        "what": "49 U.S.C. 14501, with its amendment notes",
        "url": "https://www.law.cornell.edu/uscode/text/49/14501",
        "publisher": "Legal Information Institute, reproducing the current United States Code",
        "opened": ["2026-10-08", "2026-10-09"]},
    "usc42_300gg131": {
        "what": "42 U.S.C. 300gg-131, balance billing in cases of emergency services",
        "url": "https://www.law.cornell.edu/uscode/text/42/300gg-131",
        "publisher": "Legal Information Institute, reproducing the current United States Code",
        "opened": ["2026-10-09"]},
    "usc42_300gg132": {
        "what": "42 U.S.C. 300gg-132, balance billing for non-emergency services by nonparticipating "
                "providers at participating facilities",
        "url": "https://www.law.cornell.edu/uscode/text/42/300gg-132",
        "publisher": "Legal Information Institute, reproducing the current United States Code",
        "opened": ["2026-10-09"]},
    "usc42_300gg135": {
        "what": "42 U.S.C. 300gg-135, air ambulance services",
        "url": "https://www.law.cornell.edu/uscode/text/42/300gg-135",
        "publisher": "Legal Information Institute, reproducing the current United States Code",
        "opened": ["2026-10-09"]},
    "usc15_1693o2": {
        "what": "15 U.S.C. 1693o-2, reasonable fees and rules for payment card transactions",
        "url": "https://www.law.cornell.edu/uscode/text/15/1693o-2",
        "publisher": "Legal Information Institute, reproducing the current United States Code",
        "opened": ["2026-10-09"]},
    "nyc_admin_19_5": {
        "what": "New York City Administrative Code, title 19 chapter 5, sections 19-502, 19-504 and 19-507",
        "url": "https://nycadmincode.readthedocs.io/t19/c05/",
        "publisher": "an unofficial mirror of the Administrative Code; read to character 100,000 of 211,207, "
                     "which ends after section 19-507.1",
        "opened": ["2026-10-09"]},
    "tlc_ch58": {
        "what": "Rules of the New York City Taxi and Limousine Commission, chapter 58, 108 pages, "
                "'Updated February 27, 2026'; section 58-26 on pages 58 and 59; a copy is kept at "
                "data/raw/b143/tlc/ with its hash in the manifest there",
        "url": "https://www.nyc.gov/assets/tlc/downloads/pdf/rule_book_current_chapter_58.pdf",
        "publisher": "the Commission's own file",
        "opened": ["2026-10-09"]},
    "tlc_ch59": {
        "what": "Rules of the New York City Taxi and Limousine Commission, chapter 59, 198 pages, "
                "'Updated February 27, 2026'; sections 59A-25, 59B-21 and 59B-23; a copy is kept at "
                "data/raw/b143/tlc/ with its hash in the manifest there",
        "url": "https://www.nyc.gov/assets/tlc/downloads/pdf/rule_book_current_chapter_59.pdf",
        "publisher": "the Commission's own file",
        "opened": ["2026-10-09"]},
    "ca_pen_396": {
        "what": "California Penal Code section 396, 'Current as of January 01, 2026'",
        "url": "https://codes.findlaw.com/ca/penal-code/pen-sect-396/",
        "publisher": "FindLaw, reproducing the code",
        "opened": ["2026-10-09"]},
    "ca_oag_gouging": {
        "what": "the California Attorney General's page on price gouging during disasters",
        "url": "https://oag.ca.gov/consumers/pricegougingduringdisasters",
        "publisher": "the Attorney General's own page; a summary, read beside the code",
        "opened": ["2026-10-09"]},
    "uk_tariff_cap_2018": {
        "what": "Domestic Gas and Electricity (Tariff Cap) Act 2018, text as enacted, sections 1, 3 and 12",
        "url": "https://www.legislation.gov.uk/ukpga/2018/21/enacted",
        "publisher": "legislation.gov.uk, the official publisher",
        "opened": ["2026-10-09"]},
    "fca_icobs_6b2": {
        "what": "FCA Handbook, ICOBS 6B.2 'Setting renewal prices', rule 6B.2.1R, in force 01/01/2022",
        "url": "https://www.handbook.fca.org.uk/handbook/ICOBS/6B/2.html",
        "publisher": "the Financial Conduct Authority's own handbook",
        "opened": ["2026-10-09"]},
}

# Pages opened that gave no row. A page that returned nothing and a page never tried look the same in a
# count, so they are listed.
PAGES_WITHOUT_ROWS = [
    {"url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PEN&sectionNum=396",
     "result": "HTTP 403; the code was read from the FindLaw reproduction instead"},
    {"url": "https://law.justia.com/codes/california/code-pen/part-1/title-10/section-396/",
     "result": "HTTP 403"},
    {"url": "https://nycadmincode.readthedocs.io/t19/c05/",
     "result": "characters 100,000 to 211,207 not read; section 19-516 was not reached and no row rests on it"},
]


def frag(text, cite, source):
    """One fragment copied from a page: its words, where in the provision, and which page."""
    return {"text": text, "cite": cite, "source": source}


# Each row has two sides. `authority_writes` names the side whose price an authority writes or may write.
# `buyer_acted_on` names the side the text describes as consented to, arranged in advance or chosen by the
# buyer; it is None where the dividing words are not about an act of the buyer.
ROWS = [
    {"id": "tow_without_consent",
     "hand": "United States Congress", "provision": "49 U.S.C. 14501(c), amended 2015 by Pub. L. 114-94",
     "line_of_business": "tow trucks, among motor carriers of property",
     "kind": "buyer_act",
     "dividing_words": frag(
         "performed without the prior consent or authorization of the owner or operator of the motor vehicle",
         "49 U.S.C. 14501(c)(2)(C)", "usc49_14501"),
     "side_a": {"what": "tows without the owner's prior consent",
                "price": "a State may regulate them; until 2015 the carve-out named the price itself",
                "text": frag("the price of for-hire motor vehicle transportation by a tow truck, if such "
                             "transportation is",
                             "49 U.S.C. 14501(c)(2)(C) as it stood before Pub. L. 114-94, from the amendment note",
                             "usc49_14501")},
     "side_b": {"what": "tows the owner consented to",
                "price": "no State may regulate the price",
                "text": frag("may not enact or enforce a law, regulation, or other provision having the force "
                             "and effect of law related to a price, route, or service of any motor carrier",
                             "49 U.S.C. 14501(c)(1)", "usc49_14501")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": True,
     "note": "since 2015 the carve-out reads 'the regulation of tow truck operations performed without the "
             "prior consent', which is wider than the price"},

    {"id": "household_goods",
     "hand": "United States Congress", "provision": "49 U.S.C. 14501(c)",
     "line_of_business": "motor carriers of property",
     "kind": "good_or_seller",
     "dividing_words": frag("does not apply to the intrastate transportation of household goods",
                            "49 U.S.C. 14501(c)(2)(B)", "usc49_14501"),
     "side_a": {"what": "intrastate carriage of household goods",
                "price": "a State may regulate price, route and service",
                "text": frag("does not apply to the intrastate transportation of household goods",
                             "49 U.S.C. 14501(c)(2)(B)", "usc49_14501")},
     "side_b": {"what": "carriage of other property",
                "price": "no State may regulate the price",
                "text": frag("related to a price, route, or service of any motor carrier",
                             "49 U.S.C. 14501(c)(1)", "usc49_14501")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": None,
     "same_seller_both_sides": False,
     "note": "the words name the cargo"},

    {"id": "emergency_medical_bill",
     "hand": "United States Congress", "provision": "42 U.S.C. 300gg-131, for plan years from January 1, 2022",
     "line_of_business": "care by providers and facilities outside the patient's plan network",
     "kind": "emergency",
     "dividing_words": frag("emergency services (for which benefits are provided under the plan or coverage) "
                            "with respect to an emergency medical condition",
                            "42 U.S.C. 300gg-131(a)", "usc42_300gg131"),
     "side_a": {"what": "emergency services",
                "price": "the patient may be billed no more than the in-network cost-sharing amount",
                "text": frag("shall not bill, and shall not hold liable, the participant, beneficiary, or "
                             "enrollee for a payment amount for such emergency services so furnished that is "
                             "more than the cost-sharing requirement for such services",
                             "42 U.S.C. 300gg-131(a)(1)", "usc42_300gg131")},
     "side_b": {"what": "services other than emergency services",
                "price": "this section does not reach them; section 300gg-132 treats part of them",
                "text": frag("items or services (other than emergency services to which section 300gg–131 of "
                             "this title applies)",
                             "42 U.S.C. 300gg-132(a)", "usc42_300gg132")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": None,
     "same_seller_both_sides": True,
     "note": "the words name a state of the buyer, not an act"},

    {"id": "medical_bill_without_consent",
     "hand": "United States Congress", "provision": "42 U.S.C. 300gg-132, for plan years from January 1, 2022",
     "line_of_business": "non-emergency care by out-of-network providers at in-network facilities",
     "kind": "buyer_act",
     "dividing_words": frag("if the provider satisfies the notice and consent criteria of subsection (d)",
                            "42 U.S.C. 300gg-132(b)(1)", "usc42_300gg132"),
     "side_a": {"what": "care given without the patient's notice and consent",
                "price": "the patient may be billed no more than the in-network cost-sharing amount",
                "text": frag("such provider shall not bill, and shall not hold liable, such participant, "
                             "beneficiary, or enrollee for a payment amount for such an item or service",
                             "42 U.S.C. 300gg-132(a)", "usc42_300gg132")},
     "side_b": {"what": "care the patient consented to after notice",
                "price": "the limit does not apply",
                "text": frag("Subsection (a) shall not apply with respect to items or services (other than "
                             "ancillary services described in paragraph (2))",
                             "42 U.S.C. 300gg-132(b)(1)", "usc42_300gg132")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": True,
     "note": "consent cannot lift the limit where the patient has nobody else to go to: the ancillary services "
             "that keep the limit include 'items and services provided by a nonparticipating provider if there "
             "is no participating provider who can furnish such item or service at such facility' "
             "(300gg-132(b)(2)(D)); and the notice itself must carry 'a list of any participating providers at "
             "the facility who are able to furnish such items' and say the patient 'may be referred, at their "
             "option, to such a participating provider' (300gg-132(d)(2)(C))"},

    {"id": "air_ambulance",
     "hand": "United States Congress", "provision": "42 U.S.C. 300gg-135, for plan years from January 1, 2022",
     "line_of_business": "care by providers outside the patient's plan network",
     "kind": "good_or_seller",
     "dividing_words": frag("air ambulance services (for which benefits are available under such plan or "
                            "coverage) from a nonparticipating provider",
                            "42 U.S.C. 300gg-135", "usc42_300gg135"),
     "side_a": {"what": "air ambulance services",
                "price": "the patient may be billed no more than the cost-sharing amount",
                "text": frag("such provider shall not bill, and shall not hold liable, such participant, "
                             "beneficiary, or enrollee for a payment amount for such service furnished by such "
                             "provider that is more than the cost-sharing amount for such service",
                             "42 U.S.C. 300gg-135", "usc42_300gg135")},
     "side_b": {"what": "other transport and other services", "price": "not named in the section",
                "text": None},
     "both_sides_in_text": False, "authority_writes": "a", "buyer_acted_on": None,
     "same_seller_both_sides": False,
     "note": "the words name a kind of service; the section does not say what lies on the other side"},

    {"id": "nyc_hail_or_prearranged",
     "hand": "New York City", "provision": "Administrative Code 19-502, 19-504, 19-507; TLC Rules 58-26, "
                                           "59B-21, 59B-23",
     "line_of_business": "passengers carried for hire by car",
     "kind": "buyer_act",
     "dividing_words": frag("shall accept passengers unless the passengers have engaged the use of the "
                            "for-hire vehicle on the basis of telephone contract or prearrangement",
                            "N.Y.C. Admin. Code 19-507(a)(4)", "nyc_admin_19_5"),
     "side_a": {"what": "trips hailed in the street, which only a taxicab may accept",
                "price": "the Commission writes the fare: $3.00 for the first unit, $.70 for each further unit",
                "text": frag("The rate of fare for Taxicabs is as follows, regardless of the number of "
                             "passengers or stops: (i) The charge for the initial unit is $3.00 plus the "
                             "Taxicab Improvement Surcharge of $1.00 (ii) The charge for each additional unit "
                             "is $.70",
                             "TLC Rules 58-26(a)(1)", "tlc_ch58")},
     "side_b": {"what": "trips arranged in advance through a base",
                "price": "the base writes its own fares and files them; it is held to what it filed",
                "text": frag("A Base Owner must not quote or charge a fare that is more than the fare listed "
                             "in the Rate Schedule filed with the Commission.",
                             "TLC Rules 59B-23(a)", "tlc_ch59")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": False,
     "note": "'No motor vehicle other than a duly licensed taxicab shall be permitted to accept hails from "
             "passengers in the street' (Admin. Code 19-504(a)(1)); a taxicab is defined as a vehicle 'duly "
             "licensed as a taxi cab by the commission and permitted to accept hails from passengers in the "
             "street' (19-502(l)); 'A Base Owner must file a Rate Schedule with the Commission' (TLC Rules "
             "59B-21(a)(1))"},

    {"id": "nyc_same_vehicle",
     "hand": "New York City", "provision": "TLC Rules 59B-21, 59B-23",
     "line_of_business": "one licensed vehicle, the Street Hail Livery, taking both kinds of trip",
     "kind": "buyer_act",
     "dividing_words": frag("Fares for Hail Trips in Street Hail Liveries will be as set forth in section "
                            "82-26 of these Rules",
                            "TLC Rules 59B-23(c)", "tlc_ch59"),
     "side_a": {"what": "a trip hailed in the street",
                "price": "the Commission's rule sets the fare",
                "text": frag("Fares for Hail Trips in Street Hail Liveries will be as set forth in section "
                             "82-26 of these Rules",
                             "TLC Rules 59B-23(c)", "tlc_ch59")},
     "side_b": {"what": "a trip in the same vehicle, arranged in advance through its base",
                "price": "the base's own filed rates",
                "text": frag("the Base’s rates for rides dispatched by the Base for Pre-Arranged Trips provided "
                             "by Street Hail Liveries",
                             "TLC Rules 59B-21(a)(1)", "tlc_ch59")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": True,
     "note": "the vehicle, its driver and its base are the same on both sides; what differs is how the "
             "passenger came to be in the car"},

    {"id": "declared_emergency",
     "hand": "California Legislature", "provision": "Penal Code 396",
     "line_of_business": "listed consumer goods and services",
     "kind": "emergency",
     "dividing_words": frag("Upon the proclamation of a state of emergency declared by the President of the "
                            "United States or the Governor, or upon the declaration of a local emergency",
                            "Cal. Penal Code 396(b)", "ca_pen_396"),
     "side_a": {"what": "sales in the thirty days after an emergency is declared",
                "price": "no more than ten percent above the seller's own price just before",
                "text": frag("for a price of more than 10 percent greater than the price charged by that "
                             "person for those goods or services immediately prior to the proclamation or "
                             "declaration of emergency",
                             "Cal. Penal Code 396(b)", "ca_pen_396")},
     "side_b": {"what": "sales under ordinary conditions",
                "price": "left to the market",
                "text": frag("While the pricing of consumer goods and services is generally best left to the "
                             "marketplace under ordinary conditions, when a declared state of emergency or "
                             "local emergency results in abnormal disruptions of the market, the public "
                             "interest requires that excessive and unjustified increases in the prices of "
                             "essential consumer goods and services be prohibited.",
                             "Cal. Penal Code 396(a)", "ca_pen_396")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": None,
     "same_seller_both_sides": True,
     "note": "goods and services alike; the Attorney General's page reads the statute as prohibiting 'raising "
             "the price of many consumer goods and services by more than 10% after an emergency has been "
             "declared'"},

    {"id": "default_energy_tariff",
     "hand": "United Kingdom Parliament",
     "provision": "Domestic Gas and Electricity (Tariff Cap) Act 2018, sections 1 and 3",
     "line_of_business": "gas and electricity supplied to homes",
     "kind": "buyer_act",
     "dividing_words": frag("“default rate” means a rate or amount charged for, or in relation to, "
                            "the supply of gas or electricity under the contract that applies if the customer "
                            "under the contract fails to choose an alternative rate.",
                            "Tariff Cap Act 2018 s.1(4)(b)", "uk_tariff_cap_2018"),
     "side_a": {"what": "standard variable and default rates",
                "price": "capped by the regulator",
                "text": frag("conditions (“tariff cap conditions”) that impose a cap on all standard "
                             "variable and default rates that may be charged by the holders of supply licences",
                             "Tariff Cap Act 2018 s.1(1)", "uk_tariff_cap_2018")},
     "side_b": {"what": "rates fixed for a period named in the contract, and green standard variable rates "
                        "the customer chose",
                "price": "not capped",
                "text": frag("standard variable rates which apply only if chosen by domestic customers",
                             "Tariff Cap Act 2018 s.3(2)(b)", "uk_tariff_cap_2018")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": True,
     "note": "a standard variable rate is one 'that is not fixed for a period specified in the contract' "
             "(s.1(4)(a)); the regulator is to keep 'incentives for domestic customers to switch to different "
             "domestic supply contracts' (s.1(6)(c))"},

    {"id": "insurance_renewal",
     "hand": "Financial Conduct Authority", "provision": "ICOBS 6B.2.1R, in force 1 January 2022",
     "line_of_business": "insurance renewals within ICOBS 6B; the scope provision was not on the page read",
     "kind": "buyer_act",
     "dividing_words": frag("A firm must not set a renewal price that is higher than the equivalent new "
                            "business price.",
                            "ICOBS 6B.2.1R(1)", "fca_icobs_6b2"),
     "side_a": {"what": "the price offered to a customer who renews",
                "price": "no higher than the firm's price for an equivalent new customer",
                "text": frag("A firm must not set a renewal price that is higher than the equivalent new "
                             "business price.",
                             "ICOBS 6B.2.1R(1)", "fca_icobs_6b2")},
     "side_b": {"what": "the price offered to a customer who comes as new business",
                "price": "the firm sets it",
                "text": frag("the equivalent new business price", "ICOBS 6B.2.1R(1)", "fca_icobs_6b2")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": "b",
     "same_seller_both_sides": True,
     "note": "the customer who comes as new business has just chosen this firm; the customer who renews has "
             "not chosen again. The glossary definition of the equivalent new business price was not on the "
             "page"},

    {"id": "debit_interchange_small_issuer",
     "hand": "United States Congress", "provision": "15 U.S.C. 1693o-2(a)",
     "line_of_business": "interchange fees on debit card transactions",
     "kind": "good_or_seller",
     "dividing_words": frag("This subsection shall not apply to any issuer that, together with its "
                            "affiliates, has assets of less than $10,000,000,000",
                            "15 U.S.C. 1693o-2(a)(6)(A)", "usc15_1693o2"),
     "side_a": {"what": "issuers with assets of ten billion dollars or more",
                "price": "the fee must be reasonable and proportional to the issuer's cost",
                "text": frag("The amount of any interchange transaction fee that an issuer may receive or "
                             "charge with respect to an electronic debit transaction shall be reasonable and "
                             "proportional to the cost incurred by the issuer with respect to the transaction.",
                             "15 U.S.C. 1693o-2(a)(2)", "usc15_1693o2")},
     "side_b": {"what": "issuers with assets below ten billion dollars",
                "price": "exempt",
                "text": frag("This subsection shall not apply to any issuer that, together with its "
                             "affiliates, has assets of less than $10,000,000,000",
                             "15 U.S.C. 1693o-2(a)(6)(A)", "usc15_1693o2")},
     "both_sides_in_text": True, "authority_writes": "a", "buyer_acted_on": None,
     "same_seller_both_sides": False,
     "note": "the words name the size of the seller"},
]


def fragments(row):
    """Every fragment a row rests on. A side the text does not name carries none."""
    out = [row["dividing_words"]]
    for side in ("side_a", "side_b"):
        if row[side]["text"] is not None:
            out.append(row[side]["text"])
    return out


def bookkeeping_problems(rows, sources):
    """A fragment without words, without a place in its provision, or resting on a page that is not listed."""
    bad = []
    for row in rows:
        if row["kind"] not in KINDS:
            bad.append(f"{row['id']}: kind {row['kind']!r} is not one of the three")
        for f in fragments(row):
            if not (f.get("text") or "").strip():
                bad.append(f"{row['id']}: a fragment has no words")
            if not (f.get("cite") or "").strip():
                bad.append(f"{row['id']}: a fragment has no place in its provision")
            if f.get("source") not in sources:
                bad.append(f"{row['id']}: page {f.get('source')!r} is not listed")
    return bad


def state_of(row, sources):
    """Three states. Only `read` enters a count."""
    for f in fragments(row):
        src = sources.get(f.get("source"))
        if src is None or not src.get("opened"):
            return "unopened"
    if not row["both_sides_in_text"] or row["side_a"]["text"] is None or row["side_b"]["text"] is None:
        return "no_object"
    return "read"


def direction_of(row):
    """For a row whose line is an act of the buyer: which side has its price written."""
    if row["kind"] != "buyer_act":
        return None
    if row["buyer_acted_on"] not in ("a", "b"):
        return "undetermined"
    return "no_choice_side_written" if row["authority_writes"] != row["buyer_acted_on"] else "reversed"


def read_rows(rows, sources):
    """The rows with their state and direction, and the tallies. Objects first, counts after."""
    table = []
    for row in rows:
        st = state_of(row, sources)
        table.append({"id": row["id"], "hand": row["hand"], "provision": row["provision"],
                      "line_of_business": row["line_of_business"], "kind": row["kind"], "state": st,
                      "direction": direction_of(row) if st == "read" else None,
                      "same_seller_both_sides": row["same_seller_both_sides"],
                      "dividing_words": row["dividing_words"],
                      "side_a": row["side_a"], "side_b": row["side_b"],
                      "authority_writes": row["authority_writes"], "buyer_acted_on": row["buyer_acted_on"],
                      "note": row["note"]})
    read = [r for r in table if r["state"] == "read"]
    by_kind = {k: sorted(r["id"] for r in read if r["kind"] == k) for k in KINDS}
    hands = {k: sorted({r["hand"] for r in read if r["kind"] == k}) for k in KINDS}
    acts = [r for r in read if r["kind"] == "buyer_act"]
    by_direction = {d: sorted(r["id"] for r in acts if r["direction"] == d)
                    for d in ("no_choice_side_written", "reversed", "undetermined")}
    same_seller = sorted(r["id"] for r in read if r["same_seller_both_sides"])
    return {"table": table, "read": sorted(r["id"] for r in read),
            "unopened": sorted(r["id"] for r in table if r["state"] == "unopened"),
            "no_object": sorted(r["id"] for r in table if r["state"] == "no_object"),
            "by_kind": by_kind, "hands": hands, "by_direction": by_direction, "same_seller": same_seller}


def coverage(rows, sources):
    """Which pages were opened and which rows rest on each, a page with no row included."""
    cover = {}
    for sid, src in sorted(sources.items()):
        cites = sorted({row["id"] for row in rows for f in fragments(row) if f.get("source") == sid})
        cover[sid] = {"opened": list(src.get("opened", [])), "rows": cites, "url": src["url"],
                      "what": src["what"], "publisher": src["publisher"]}
    return cover


def build_criteria(rows, sources, checks=None):
    """The five criteria, each flag computed from the rows."""
    bad = bookkeeping_problems(rows, sources)
    got = read_rows(rows, sources)
    cover = coverage(rows, sources)
    n_read = len(got["read"])
    line_on_buyer = got["by_kind"]["buyer_act"] + got["by_kind"]["emergency"]
    line_on_seller = got["by_kind"]["good_or_seller"]
    hands_buyer = sorted(set(got["hands"]["buyer_act"]) | set(got["hands"]["emergency"]))
    d = got["by_direction"]
    has_object = n_read > 0

    if not has_object:
        found, direction = None, None
    else:
        found = len(line_on_buyer) > 0
        if not got["by_kind"]["buyer_act"] or (not d["no_choice_side_written"] and not d["reversed"]):
            direction = None
        else:
            direction = len(d["no_choice_side_written"]) > 0 and len(d["reversed"]) == 0

    unopened_pages = sorted(sid for sid, c in cover.items() if not c["opened"])
    crit = [
        {"name": "B143-1  every fragment carries its words, its place and an opened page",
         "kind": "bookkeeping",
         "passed": len(rows) > 0 and not bad,
         "detail": f"{len(rows)} rows resting on {sum(1 for c in cover.values() if c['rows'])} pages, "
                   f"{len(cover)} pages listed; problems: " + ("none" if not bad else "; ".join(bad))
                   + ". Pages listed and never opened: " + (", ".join(unopened_pages) or "none")
                   + ". Rows left out because a page was not opened: " + (", ".join(got["unopened"]) or "none")
                   + ". Pages opened that gave no row: "
                   + "; ".join(f"{p['url']} ({p['result']})" for p in PAGES_WITHOUT_ROWS)},
        {"name": "B143-2  the provision regulates part of one line of business and names both sides",
         "kind": "premise",
         "passed": has_object,
         "detail": f"{n_read} of {len(rows)} rows name both sides in their own text and are read: "
                   + ", ".join(got["read"]) + ". Printed and not counted, the other side is not named: "
                   + (", ".join(got["no_object"]) or "none")},
        {"name": "B143-3  lines drawn on an act of the buyer or on an emergency exist, in more than one hand",
         "kind": "own_reading",
         "passed": found,
         "detail": (f"of {n_read} rows read, {len(got['by_kind']['buyer_act'])} draw the line on an act of the "
                    f"buyer ({', '.join(got['by_kind']['buyer_act']) or 'none'}), "
                    f"{len(got['by_kind']['emergency'])} on an emergency "
                    f"({', '.join(got['by_kind']['emergency']) or 'none'}) and {len(line_on_seller)} on the "
                    f"good or the seller ({', '.join(line_on_seller) or 'none'}). Hands with a line on the "
                    f"buyer's act or an emergency: {len(hands_buyer)} ({', '.join(hands_buyer) or 'none'}). "
                    f"Rows where the same sellers supply the same thing on both sides of the line: "
                    f"{len(got['same_seller'])} ({', '.join(got['same_seller']) or 'none'}); a reading that "
                    "ties the line to an attribute of the seller or the good fits the rows of that kind and "
                    "has nothing to hold on to in these")
                   if has_object else "no row is read, so there is nothing to count"},
        {"name": "B143-4  where the line is an act of the buyer, the price written is on the side the buyer "
                 "did not act on",
         "kind": "own_reading",
         "passed": direction,
         "detail": (f"rows whose line is an act of the buyer: {len(got['by_kind']['buyer_act'])}; the "
                    f"authority writes the price on the side the buyer did not act on in "
                    f"{len(d['no_choice_side_written'])} ({', '.join(d['no_choice_side_written']) or 'none'}), "
                    f"on the side the buyer acted on in {len(d['reversed'])} "
                    f"({', '.join(d['reversed']) or 'none'}), and the text does not say in "
                    f"{len(d['undetermined'])} ({', '.join(d['undetermined']) or 'none'})")
                   if has_object else "no row is read, so there is nothing to count"},
    ]
    if checks is not None:
        crit.append(
            {"name": "B143-5  the reader of rows, on seeded faults",
             "kind": "instrument",
             "passed": len(checks) > 0 and all(checks.values()),
             "detail": "seeded faults caught: " + ", ".join(f"{k} {v}" for k, v in sorted(checks.items()))})
    return crit, got, cover


def by_name(crit):
    return {c["name"].split()[0]: c for c in crit}


def seeded_faults():
    """Each fault is planted in a copy of the corpus and must move the flag it is aimed at."""
    out = {}

    def run(rows, sources=SOURCES):
        crit, got, _ = build_criteria(rows, sources)
        return by_name(crit), got

    base, base_got = run(ROWS)
    out["the corpus as it stands passes one to four"] = all(
        base[k]["passed"] is True for k in ("B143-1", "B143-2", "B143-3", "B143-4"))

    rows = copy.deepcopy(ROWS)
    rows[0]["dividing_words"]["text"] = "  "
    out["a fragment without words fails one"] = run(rows)[0]["B143-1"]["passed"] is False

    rows = copy.deepcopy(ROWS)
    rows[0]["dividing_words"]["source"] = "a_page_nobody_listed"
    out["a page that is not listed fails one"] = run(rows)[0]["B143-1"]["passed"] is False

    rows = copy.deepcopy(ROWS)
    rows[0]["kind"] = "something_else"
    out["a kind outside the three fails one"] = run(rows)[0]["B143-1"]["passed"] is False

    sources = copy.deepcopy(SOURCES)
    sources["tlc_ch59"]["opened"] = []
    crit, got = run(ROWS, sources)
    out["a row on an unopened page leaves every count"] = (
        "nyc_same_vehicle" in got["unopened"] and "nyc_same_vehicle" not in got["read"]
        and "nyc_same_vehicle" not in got["by_kind"]["buyer_act"]
        and "nyc_same_vehicle" not in got["by_direction"]["no_choice_side_written"])

    rows = copy.deepcopy(ROWS)
    for r in rows:
        r["both_sides_in_text"] = False
    crit, got = run(rows)
    out["no row naming both sides fails two and leaves three and four without a verdict"] = (
        crit["B143-2"]["passed"] is False and crit["B143-3"]["passed"] is None
        and crit["B143-4"]["passed"] is None)

    rows = [r for r in copy.deepcopy(ROWS) if r["kind"] == "good_or_seller"]
    crit, got = run(rows)
    out["a corpus of seller lines alone fails three"] = crit["B143-3"]["passed"] is False

    rows = copy.deepcopy(ROWS)
    flipped = next(r for r in rows if r["id"] == "tow_without_consent")
    flipped["buyer_acted_on"] = flipped["authority_writes"]
    crit, got = run(rows)
    out["one reversed row fails four and is named"] = (
        crit["B143-4"]["passed"] is False and got["by_direction"]["reversed"] == ["tow_without_consent"])

    rows = copy.deepcopy(ROWS)
    for r in rows:
        if r["kind"] == "buyer_act":
            r["buyer_acted_on"] = None
    crit, got = run(rows)
    out["an act of the buyer the text does not place gets no verdict in four"] = (
        crit["B143-4"]["passed"] is None)

    rows = copy.deepcopy(ROWS)
    gone = next(r for r in rows if r["id"] == "air_ambulance")
    out["the row that does not name its other side is printed and not counted"] = (
        state_of(gone, SOURCES) == "no_object" and "air_ambulance" in base_got["no_object"]
        and "air_ambulance" not in base_got["by_kind"]["good_or_seller"])
    return out


def build_record():
    checks = seeded_faults()
    crit, got, cover = build_criteria(ROWS, SOURCES, checks)
    config = {
        "kinds": KINDS,
        "state_of_row": STATE_OF_ROW,
        "direction_of_row": DIRECTION_OF_ROW,
        "corpus": "the towing provision, read first; two provisions named from memory before they were read "
                  "(taxi fares, emergency medical bills); the other price provisions met in the same sections; two price rules already cited from their "
                  "official texts (the British default tariff cap, the insurance renewal rule); the debit "
                  "interchange rule; one statute for the emergency cell",
        "unit_of_hand": "the body that issued the text; several statutes of one legislature are one hand",
        "what_counts_as_written": "an authority sets the price, caps it, or is given the power to regulate it",
    }
    return {"stage": "B143", "config": config, "criteria": crit, "rows": got["table"],
            "tallies": {k: got[k] for k in ("read", "unopened", "no_object", "by_kind", "hands", "by_direction",
                                             "same_seller")},
            "pages": cover, "pages_without_rows": PAGES_WITHOUT_ROWS}


def show(rec):
    out = sys.stdout
    print("state of a row (rule 11c):")
    for cell, st in STATE_OF_ROW.items():
        print(f"    {cell:66s} -> {st}")
    print("direction of a row whose line is an act of the buyer:")
    for cell, st in DIRECTION_OF_ROW.items():
        print(f"    {cell:72s} -> {st}")
    print()
    for r in rec["rows"]:
        print(f"{r['id']}  [{r['kind']}, {r['state']}"
              + (f", {r['direction']}" if r["direction"] else "") + f"]  {r['hand']}")
        print(f"    line:    \"{r['dividing_words']['text']}\"  ({r['dividing_words']['cite']})")
        for side in ("side_a", "side_b"):
            mark = "written" if r["authority_writes"] == side[-1] else "       "
            act = "buyer acted" if r["buyer_acted_on"] == side[-1] else ""
            print(f"    {side[-1]} {mark}  {r[side]['what']}: {r[side]['price']}  {act}")
        print()
    print("pages:")
    for sid, c in rec["pages"].items():
        print(f"    {sid:20s} opened {', '.join(c['opened']) or 'never':24s} rows {len(c['rows'])}")
    for p in rec["pages_without_rows"]:
        print(f"    no row: {p['url']}  ({p['result']})")
    print()
    for c in rec["criteria"]:
        print(f"  {({True: 'PASS', False: 'FAIL', None: 'UNREAD'})[c['passed']]:6s} {c['name']}")
        print(f"         {c['detail']}")
    out.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        checks = seeded_faults()
        for name, ok in sorted(checks.items()):
            print(f"  {'caught' if ok else 'MISSED':7s} {name}")
        return 0 if all(checks.values()) else 1
    rec = build_record()
    show(rec)
    path = Path(__file__).resolve().parents[1] / "results" / "b143_price_control_line.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"\nwrote {path.name}")
    return 0 if all(c["passed"] is not False for c in rec["criteria"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
