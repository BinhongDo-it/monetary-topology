"""B159: Definity takes over Travelers Canada; in Nova Scotia the same policies renew, one by one, into
the acquirer's rating program.

On 2 January 2026 Definity acquired the Canadian operations of Travelers. The Nova Scotia Regulatory and
Appeals Board approved (2026 NSRAB 20, matter M12606, private passenger vehicles; 2026 NSRAB 8, M12629,
commercial vehicles) a plan under which every Travelers Canada policy renews, on its own renewal date from
2026-07-01 to 2027-06-30, into a Definity policy rated by Definity's rates and risk-classification system.
The customers, vehicles and risks are those of the Travelers book; the pricing procedure is Definity's. The
Board writes that the two systems differ and that a straight transfer would move many premiums sharply.

The station reads what the public record carries about that swap: what the procedure change replaces
(class lines), how far it moves prices (the portfolio average only), and where the policy-level
displacement distribution sits in the regulatory process.

Criteria (kind in brackets):
  B159-1 [bookkeeping]  every source file matches its manifest hash; every quote is found in its snapshot
  B159-2 [own_reading]  the swap as the Board writes it, for both rating programs; the conversion window
  B159-3 [own_reading]  commercial vehicles: portfolio change from the swap, uncapped and capped
  B159-4 [own_reading]  private passenger: portfolio or distribution of the change, three states
  B159-5 [own_reading]  CLEAR rate groups of the same vehicles under the two programs' table versions
  B159-6 [own_reading]  class lines keyed on "came from the acquired insurer", in two acquisitions
  B159-7 [instrument]   D53 dose index: versions of the acquirer's program inside the conversion window
  B159-8 [bookkeeping]  every wanted object carries exactly one availability state
  B159-9 [known_answer] the 8% increase M12606 cites for the Travelers side, traced to its decision
  B159-10 [own_reading] same standard risk, two programs, two prices: the square on CARR rating profiles
  B159-11 [own_reading] the swap's displacement at profile resolution, against the caps and the Board's letter
  B159-12 [own_reading] the two programs' territory partitions over the same nine Board territories

B159-10 to B159-12 read the CARR harmonized rating profiles both companies filed in the Board's public
matter files (UARB15): Dominion of Canada (Travelers Canada) in M12284, exhibit T-8, and Definity in M12161,
exhibit D-2. Both use the 2022 version of the profiles, the same drivers, vehicles and coverages, and both
"proposed" columns are the programs in force when the first Travelers policy renewed into Definity
(Dominion from 2025-12-21 renewals, Definity from 2025-11-21 renewals until 2026-10-21).

There is no rival criterion. The risk-pricing reading (one risk, one premium, whoever runs the procedure)
is written into the detail and settled by the readings.

usage:
  python -B experiments/b159_definity_travelers.py              run, write results/b159_definity_travelers.json
  python -B experiments/b159_definity_travelers.py --selftest   planted faults, each flag must flip
  python -B experiments/b159_definity_travelers.py --mutation   deliberate implementation errors, the selftest must catch each
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b159"
MANIFEST = RAW / "b159_manifest.json"
RECORD = ROOT / "results" / "b159_definity_travelers.json"
SESSION = "B159_1029b"
# Manifest status of a file held on disk but withheld from every reading: M12284 T-10 is listed Public while
# its cover reads Confidential. It is renamed with .expired and no code path opens it.
WITHHELD = "withheld_not_read"

TXT = {
    "M12606_AMEND": "txt/M12606_101357_Amending_Order.txt",
    "M12606_LETTER": "txt/M12606_103078_Board_Letter_re_directive.txt",
    "M12803_AMEND": "txt/M12803_103778_Amended_Board_Order.txt",
    "M12161": "txt/M12161_98121_Board_Decision.txt",
    "M12161_AMEND": "txt/M12161_99051_Amended_Order.txt",
    "M12466": "txt/M12466_99287_Board_Decision_Letter.txt",
    "M12466_COVER": "txt/M12466_99256_Cover_Letter.txt",
    "S155G_MINOR": "txt/NSRAB_Section_155G_Prior_Approval_Minor_Revised_2025.txt",
    "M12606": "txt/NSRAB_Board_Decision_-_Definity_Insurance_Company_M12606.txt",
    "M12629": "txt/NSRAB_Board_Decision_-_Definity_Insurance_Company_M12629.txt",
    "M12803": "txt/NSRAB_Board_Decision_-_Definity_Insurance_Company_M12803.txt",
    "M12284": "txt/NSRAB_Decision_Dominion_M12284.txt",
    "M12044": "txt/NSUARB_2025_NSUARB_25_Hartford_M12044.txt",
    "INTACT2023": "txt/NSUARB_2023_NSUARB_11_Intact_Trafalgar_M10813_M10861.txt",
    "S155G": "txt/NSRAB_Section_155G_Prior_Approval_Revised_2025.txt",
    "NBIB2026": "txt/NBIB_2026_07_13_Definity_PPV_RFG-1_Decision_E.txt",
    "DFY_Q2": "txt/Definity_Q2-2026-News-Release.txt",
}
PROFILES = "xlsx/PPV_Rating_Profiles_2026_CARR_NS.xlsx"
APPENDIX_A = "xlsx/S155G_PAMajor_Summ_of_Info_2021.xlsx"
RG_TABS = {2024: "Profile RGs - 2024 (21 year)", 2025: "Profile RGs - 2025 (21 year)",
           2026: "Profile RGs - 2026 (21 year)"}
# The Travelers side (Dominion) adopted the 2025 table, separated version (M12284 [16]-[17]); Definity
# rates on the combined collision-and-DCPD version, 2025 table until its renewals move to the 2026 table
# on 2026-12-30 (M12803 [42], [46]).
B_YEAR = 2025
A_YEARS_ON_RAMP = (2025, 2026)

# CARR harmonized rating profiles from the Board's matter files (UARB15). B = Dominion of Canada (Travelers
# Canada), A = Definity. Both 2022-version workbooks; the "proposed" column of each is the program in force
# when the first Travelers policy renewed into Definity on 2026-07-11.
B_PROFILES = "uarb15/M12284_T-8.xlsx"
A_PROFILES = "uarb15/M12161_D-2_Rating_Profiles.xlsx"
A_NEXT_PROFILES = "uarb15/M12803_D-3_Rating_Profiles.xlsx"   # 2025-version profiles, Definity only
PROFILE_SHEET = re.compile(r"^(Combined )?\d+\.\d+$")
A_NEXT_SHEET = re.compile(r"^Profile \d+$")
COVERAGE_HEAD = ["Bodily Injury*", "Property Damage*", "DCPD*", "Accident Benefits", "Uninsured Auto",
                 "Total Mandatory Coverages", "END 44", "Collision", "Comprehensive", "Total Optional Coverages",
                 "Total of Mandatory and Optional"]
COMPONENTS = (0, 1, 2, 3, 4, 6, 7, 8)   # BI, PD, DCPD, AB, UA, END 44, Collision, Comprehensive
TOTAL = 10
CAP_UP, CAP_DOWN = 0.15, -0.05          # first renewal into Definity, no new claim (quotes ppv_cap_up, ppv_cap_down)

# ---------------------------------------------------------------- quotes

# (id, source, quote). Every quote is searched for in the whitespace-collapsed snapshot with page
# furniture (page markers, running page numbers, document numbers) removed.
QUOTES = [
    # B159-2, private passenger
    ("ppv_acquired", "M12606", "On January 2, 2026, Definity acquired the Canadian operations of The Travelers Companies (Travelers Canada)."),
    ("ppv_renew_into_A", "M12606", "Definity will produce renewal notices for Travelers Canada policies that will have the policy renew, on its renewal date, into a Definity policy."),
    ("ppv_window", "M12606", "The first Travelers Canada policy will renew on July 1, 2026, and by June 30, 2027, all Travelers Canada policies will have been renewed into Definity."),
    ("ppv_differ", "M12606", "Travelers Canada rates and risk-classification systems are different from those used by Definity."),
    ("ppv_large", "M12606", "A straight transfer of the Travelers Canada policies into Definity policies, without any mitigating factors, would result in large premium increases for many customers."),
    ("ppv_manual", "M12606", "Definity proposed no changes to its Automobile Insurance Manual."),
    # B159-2, commercial
    ("cv_renew_into_A", "M12629", "renew existing Travelers’ policies into a Definity policy using Definity’s risk-classification system and rates."),
    ("cv_window", "M12629", "Starting July 1, 2026, Travelers’ policies will renew, on their renewal date, into a Definity policy. By the end of June 30, 2027, all Travelers’ policies will have renewed into Definity."),
    ("cv_differ", "M12629", "Because the rates and risk-classification system for Travelers differ from those used by Definity, a straight renewal of the Travelers’ policies into Definity policies without any mitigating factors would result in many customers seeing large premium changes."),
    ("cv_manual", "M12629", "Definity proposed no changes to its Automobile Insurance Manual in this application."),
    # B159-3
    ("cv_uncapped", "M12629", "Definity notes that renewing the Travelers’ policies into Definity without the capping mechanism would see the Travelers’ portfolio rate increase by 4.2%."),
    ("cv_capped", "M12629", "The application of the proposed cap would see this increase remain at 4.2%."),
    # B159-4
    ("ppv_update", "M12606", "No later than six months from the date of this Order, Definity must provide an update on the impact of the renewals into Definity policies to confirm that the approved Travelers Canada specific capping mechanism meets the Board’s requirement for negative capping."),
    ("conf8", "S155G", "Information on rate dislocation is required in Question CONF-8 of section C-2."),
    ("conf_routine", "S155G", "The confidential sections noted above reflect the Board’s position on the portions of an application which will routinely be kept confidential."),
    ("conf_part2", "S155G", "Part 2: Confidential Information (Format: One PDF File)"),
    ("conf_c2", "S155G", "C-2 Conf. Pages from “S155G PA - Summary of Information – Appendix A.xls”"),
    ("conf_c5", "S155G", "C-5 Final Rates"),
    ("dislocation_merger", "S155G", "though it could relate to acquisition of a portfolio through merger or acquisition."),
    ("nc_part1", "S155G", "Part 1: Non-Confidential Information (Format: One PDF File)"),
    ("nc_n5", "S155G", "N-5 Rating Profiles – Appendix C"),
    ("profiles_current_proposed", "S155G", "Each Company must provide both current and proposed rating criteria for each of the rating examples as required."),
    ("two_cycles", "S155G", "the capping measure only applies for two annual renewal cycles."),
    # B159-5
    ("b_clear_version", "M12284", "The company uses the CLEAR (AB Alberta & Atlantics) - Collison, DCPD and Comprehensive Separated version of the table."),
    ("b_clear_2025", "M12284", "Dominion proposes adoption of the 2025 version of this table"),
    ("a_clear_version", "M12803", "The company uses the CLEAR (AB Alberta & Atlantics) – Collison and DCPD Combined version of the table."),
    ("a_clear_dates", "M12803", "except for the adoption of the 2026 CLEAR table which will be effective October 1, 2026, for new business and December 30, 2026, for renewal business."),
    # B159-6
    ("ppv_cap_up", "M12606", "Definity’s proposed mechanism would cap any premium increase that would arise when a Travelers Canada policy renews into Definity at 15%."),
    ("ppv_cap_claim", "M12606", "the premium increase would be capped at a higher level (i.e., 25%)."),
    ("ppv_cap_down", "M12606", "Definity will also limit any premium decrease a Travelers Canada policy would experience upon renewal into Definity to 5%."),
    ("ppv_cap_differs", "M12606", "Definity proposed a renewal premium dislocation capping mechanism that differs from its own approved mechanism and will only apply to a Travelers Canada policy renewing into Definity."),
    ("ppv_cap_span", "M12606", "Definity’s proposed capping mechanism would apply when a Travelers Canada policy first renews into a Definity policy and for the first renewal as a Definity policy."),
    ("ppv_ccs", "M12606", "Definity proposes to apply a temporary Conversion Credit Score relativity to all Travelers Canada policies renewing into Definity."),
    ("ppv_collector", "M12606", "Definity does not have a collector car rating algorithm."),
    ("cv_cap_up", "M12629", "Definity proposed a mechanism that would cap any premium increase that would arise when a Travelers’ policy renews into Definity at 15%."),
    ("cv_cap_claim", "M12629", "If the policy has a new chargeable claim or conviction during the preceding policy term, the cap will increase to 25%."),
    ("cv_cap_down", "M12629", "Definity will also limit any premium decrease a Travelers’ policy would experience upon renewal into Definity to 5%."),
    ("cv_own_none", "M12629", "Currently, Definity does not apply such a mechanism to its own renewing policies."),
    ("rsa_caps", "INTACT2023", "For clients that Intact gained from the acquisition of RSA, Intact capped renewal premium increases at 5% and capped renewal premium decreases at -14%."),
    ("intact_own_35", "INTACT2023", "Intact and Trafalgar currently apply a 35% premium dislocation cap on premium increases at renewal."),
    ("intact_own_45", "INTACT2023", "the cap increases to 45%"),
    ("rsa_removed", "INTACT2023", "Intact proposed to remove the RSA specific capping and instead apply the proposed Intact capping to those clients."),
    ("rsa_all_renewed", "INTACT2023", "With the RSA clients on the Intact administration system having all renewed to that system, the single capping approach makes sense."),
    # B159-7
    ("a_rates_dates", "M12803", "approves the changes effective July 23, 2026, for new business and October 21, 2026, for renewal business"),
    ("a_rates_overall", "M12803", "The company proposes rate changes that vary by coverage and result in an overall increase of 7%."),
    # B159-8
    ("manual_no_caps", "M12629", "The company does not disclose capping mechanisms, and therefore no change to the Manual is necessary."),
    ("manual_no_renewal_discount", "M12803", "the amount of the Renewal Discount is not displayed in its Manual"),
    ("staff_report", "M12606", "Board staff prepared a report to the Board with recommendations on the application (Staff Report)."),
    ("nb_merger", "NBIB2026", "The Panel confirmed that a merger filing had been submitted and approved in this case,"),
    ("renewal_discount", "M12803", "Definity provides a discount for policies that have been with the company for three or more years."),
    ("dfy_q2_retention", "DFY_Q2", "We are particularly pleased with our customer retention as policies began to renew on Definity systems this quarter."),
    # B159-9
    ("cites_8", "M12606", "including the overall 8% increase approved by the Board in 2025 NSUARB 25."),
    ("m12284_8", "M12284", "The changes result in an overall, all-coverage combined rate level increase of 8.0%."),
    ("m12284_cite", "M12284", "2025 NSRAB 65"),
    ("m12284_ppv", "M12284", "for approval to change its rates and risk-classification system for private passenger vehicles"),
    ("m12044_cite", "M12044", "2025 NSUARB 25"),
    ("m12044_who", "M12044", "HARTFORD FIRE INSURANCE COMPANY applied"),
    ("m12044_what", "M12044", "for commercial vehicles"),
    # 2026-10-29 second pass: the Board's matter files (UARB15)
    ("ppv_window_amended", "M12606_AMEND", "orders that the effective date is changed to July 11, 2026, the date when Travelers Canada policies will first begin renewing into Definity."),
    ("update_received", "M12606_LETTER", "The Board confirms the information was provided within the 6-month limit the Board set in the Order."),
    ("negative_capping_confirmed", "M12606_LETTER", "confirms that the capping mechanism complies with the Board requirement for the use of negative capping (i.e., the premium foregone on the cap on increases exceeds the extra premium collected from the cap on decrease)."),
    ("a_clear_dates_amended", "M12803_AMEND", "orders that the effective dates for the CLEAR table change are revised to October 29, 2026, for new business and January 27, 2027, for renewal business."),
    ("a2025_approved", "M12161", "approves the company’s proposed rates and risk-classification system."),
    ("a2025_territories", "M12161", "Definity proposed no changes to its territories or its territorial differentials."),
    ("a2025_dates", "M12161_AMEND", "orders that the effective dates are changed for private passenger vehicles to September 17, 2025, for new business and November 21, 2025, for renewal business."),
    ("b2025_dates", "M12284", "the changes effective November 18, 2025, for new business and December 21, 2025, for"),
    ("b_theft_dates", "M12466", "The Board approves the revised high theft vehicle list effective November 18, 2025, for new business and December 21, 2025, for renewal business."),
    ("b_filings_confidential", "M12466_COVER", "our rate filings contain confidential and proprietary information."),
    ("minor_no_profiles", "S155G_MINOR", "If the filing does not include any changes to rates, differentials, or rate group tables (i.e., nothing is changing), the Board does not require the company to file new rating profiles."),
]

MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                       "September", "October", "November", "December"], 1)}
DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) "
                     r"(\d{1,2}), (\d{4})")

# Closed set of availability states for B159-8.
STATES = {
    "read": "in hand, read",
    "case_file_not_opened": "in the Board's matter database (UARB15), reachable only through its search form; not opened",
    "confidential_by_rule": "in Part 2 of a filing, which the Board's filing requirements say is routinely kept confidential",
    "not_found_public": "searched for on the public pages, not found",
    "not_in_manual": "the Board's decision says the company's manual does not carry it",
    "not_required_by_rule": "the filing type does not require it, by the Board's filing requirements",
    "matter_listing_absent": "the matter's public document listing in UARB15 was read; the item is not in it",
    "public_marked_confidential": "listed Public in UARB15, marked Confidential by the filer; opened only to identify it, used for no reading",
}

# (object, state, quote ids that support the state, note)
WANTED = [
    ("M12606 decision text (6 pages)", "read", ["ppv_differ"], "the swap, the caps, the credit relativity"),
    ("M12629 decision text, commercial vehicles", "read", ["cv_differ"], "carries the only number for the swap"),
    ("M12803 decision text, Definity's next private passenger program", "read", ["a_rates_dates"], "changes A's program inside the window"),
    ("M12284 decision text, the Travelers side's last private passenger program", "read", ["m12284_8"], "8.0% overall; Optima, credit score, theft table"),
    ("Policy-level displacement distribution, uncapped (CONF-8: 17 percent bins and 17 dollar bins, mandatory and optional coverages)",
     "confidential_by_rule", ["conf8", "conf_routine", "conf_part2", "conf_c2"],
     "the form exists and the filing must fill it; its numbers sit in Part 2"),
    ("Policy-level displacement distribution, capped (CONF-9), and premium foregone against extra premium collected",
     "confidential_by_rule", ["conf_routine", "conf_part2", "conf_c2"], "same Part 2 pages"),
    ("Rating-variable differentials and final rates of either company (C-5)", "confidential_by_rule",
     ["conf_routine", "conf_part2", "conf_c5"], "the relativities that make the two programs' prices"),
    ("Rating profiles in M12606", "not_required_by_rule", ["minor_no_profiles", "ppv_manual"],
     "a simplified filing that changes no rates; its Part 1 (exhibit D-1) is the three certificate pages"),
    ("Rating profiles, Dominion (Travelers Canada), M12284 exhibit T-8, CARR 2022 version", "read",
     ["nc_n5", "profiles_current_proposed", "b2025_dates"], "the B program in force at the swap"),
    ("Rating profiles, Definity, M12161 exhibit D-2, CARR 2022 version", "read",
     ["nc_n5", "a2025_approved", "a2025_dates"], "the A program in force at the swap; same profiles as T-8"),
    ("Rating profiles, Definity, M12803 exhibit D-3, CARR 2025 version", "read", ["a_rates_dates"],
     "A's next program; the Travelers side never filed 2025-version profiles, so it pairs with nothing"),
    ("Dominion exhibit T-10 'Proposed Rating Profiles' (its cover: Confidential, Exhibit Sec C-5.c, base rates "
     "and differentials)", "public_marked_confidential", ["b_filings_confidential"], "not used"),
    ("Staff Report and Information Request responses, M12606", "matter_listing_absent", ["staff_report"],
     "the decision says they exist; the public listing of M12606 has 3 exhibits (D-1 public, D-2 and D-3 "
     "confidential) and 4 Board documents"),
    ("Definity's six-month negative-capping update, M12606", "matter_listing_absent", ["ppv_update", "update_received"],
     "received 2026-08-05 per the Board's letter; the company's correspondence is not in the public listing"),
    ("The Board's letter acknowledging that update, M12606 document 103078", "read", ["negative_capping_confirmed"],
     "states the sign of foregone minus collected premium, not its size"),
    ("Capping values in Definity's Automobile Insurance Manual", "not_in_manual", ["manual_no_caps"], ""),
    ("Renewal discount amount in Definity's Automobile Insurance Manual", "not_in_manual", ["manual_no_renewal_discount"],
     "whether Travelers tenure counts toward Definity's three-year discount is not stated in any decision read"),
    ("Renewal-date distribution of the Nova Scotia Travelers book (maps the D53 dose to the calendar)",
     "not_found_public", [], "not a field of the public filing forms read"),
    ("The 2021 Nova Scotia decision converting RSA policies into Intact", "not_found_public", [],
     "trade press dates it 2021-07-28; the Board's site search and public decision pages did not return it"),
    ("New Brunswick merger filing for the same conversion", "not_found_public", ["nb_merger"],
     "approved, outside the hearing record"),
    ("Definity 2026 Q2 news release", "read", ["dfy_q2_retention"], "national figures, no provincial displacement"),
    ("CLEAR rate groups of the profile vehicles, 2024-2026 tables, separated and combined versions", "read", [],
     "from the Board's profile workbook"),
]

# ---------------------------------------------------------------- text helpers

FURNITURE = [re.compile(r"^=== page \d+ ===$"), re.compile(r"^-\s*\d+\s*-$"), re.compile(r"^Document:\s*\d+$"),
             re.compile(r"^Page \| \d+$"), re.compile(r"^Page \d+$"),
             re.compile(r"^Nova Scotia Regulatory and Appeals Board \(Board\) – Rate Filing Requirements \(Prior Approval\)$"),
             re.compile(r"^Source Document #\d+$"),
             re.compile(r"^Rate Filing Requirements – Published Feb\. 21, 2018 / Effective: June 1, 2018$")]


def normalize(raw: str) -> str:
    keep = []
    for line in raw.splitlines():
        s = line.strip()
        if any(p.match(s) for p in FURNITURE):
            continue
        keep.append(s)
    return re.sub(r"\s+", " ", " ".join(keep)).strip()


def nq(q: str) -> str:
    return re.sub(r"\s+", " ", q).strip()


def load_texts(raw=RAW) -> dict:
    return {k: normalize((raw / v).read_text(encoding="utf-8")) for k, v in TXT.items()}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_date(s: str) -> dt.date:
    m = DATE_RE.search(s)
    return dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))


def all_dates(s: str) -> list:
    return [dt.date(int(y), MONTHS[mo], int(d)) for mo, d, y in DATE_RE.findall(s)]


def pct(s: str, pattern: str):
    m = re.search(pattern, s)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- B159-1

def b159_1(texts, quotes=QUOTES, manifest=None, raw=RAW):
    manifest = manifest if manifest is not None else json.loads(MANIFEST.read_text(encoding="utf-8"))
    files, withheld = [], []
    for e in manifest["files"]:
        p = raw / e["path"]
        if e.get("status") == WITHHELD:
            # Held on disk under a renamed name and never opened, hashed included; only its absence under
            # the readable name is checked, which is a stat, not a read.
            withheld.append({"path": e["path"], "renamed_to": e["renamed_to"], "bytes": e["bytes"],
                             "sha256": e["sha256"], "present_under_readable_name": p.exists()})
            continue
        got = sha(p) if p.exists() else ""
        files.append({"path": e["path"], "bytes": e["bytes"], "sha256": e["sha256"], "match": got == e["sha256"],
                      "url": e.get("url", ""), "derived_from": e.get("derived_from", "")})
    found = [{"id": i, "source": s, "found": nq(q) in texts.get(s, "")} for i, s, q in quotes]
    passed = (bool(files) and all(f["match"] for f in files) and all(q["found"] for q in found)
              and not any(w["present_under_readable_name"] for w in withheld))
    return passed, {"files": files, "withheld": withheld, "quotes": found,
                    "quotes_found": sum(q["found"] for q in found), "quotes_total": len(found),
                    "missing": [q["id"] for q in found if not q["found"]]}


def qfound(texts, qid, quotes=QUOTES) -> bool:
    for i, s, q in quotes:
        if i == qid:
            return nq(q) in texts.get(s, "")
    raise KeyError(qid)


def qtext(qid, quotes=QUOTES) -> str:
    for i, _s, q in quotes:
        if i == qid:
            return q
    raise KeyError(qid)


# ---------------------------------------------------------------- B159-2

PROGRAMS = {
    "private_passenger": {"decision": "M12606", "citation": "2026 NSRAB 20",
                          "elements": ["ppv_renew_into_A", "ppv_window", "ppv_differ", "ppv_large", "ppv_manual"],
                          "window": "ppv_window"},
    "commercial": {"decision": "M12629", "citation": "2026 NSRAB 8",
                   "elements": ["cv_renew_into_A", "cv_window", "cv_differ", "cv_manual"], "window": "cv_window"},
}


def b159_2(texts, quotes=QUOTES):
    out = {}
    ok = True
    for prog, spec in PROGRAMS.items():
        el = {e: qfound(texts, e, quotes) for e in spec["elements"]}
        ds = all_dates(qtext(spec["window"], quotes)) if el[spec["window"]] else []
        start, end = (ds[0], ds[-1]) if len(ds) >= 2 else (None, None)
        start_in_order = start
        # The private passenger start moved from 2026-07-01 to 2026-07-11 by the Amending Order of 2026-03-25.
        if prog == "private_passenger" and start and qfound(texts, "ppv_window_amended", quotes):
            start = all_dates(qtext("ppv_window_amended", quotes))[0]
        out[prog] = {"decision": spec["decision"], "citation": spec["citation"], "elements": el,
                     "window_start_in_order": start_in_order.isoformat() if start_in_order else "",
                     "window_start": start.isoformat() if start else "", "window_end": end.isoformat() if end else "",
                     "window_days": (end - start).days + 1 if start and end else None}
        ok = ok and all(el.values()) and bool(start and end and start < end)
    return ok, out


# ---------------------------------------------------------------- B159-3, B159-4

def magnitude_state(text: str) -> dict:
    """Three states for how far the swap moves prices, read from one decision's text.

    distribution: a sentence counts exposures by range of change
    aggregate:    a sentence about the portfolio (or overall) change on renewal into the acquirer, with a percent
    none:         neither
    """
    sentences = re.split(r"(?<=[.;])\s+(?=[A-Z\[])", text)
    dist = [s for s in sentences if "exposures" in s and re.search(r"\d+(\.\d+)?%\s*to\s*\d", s)]
    agg = [s for s in sentences if "into Definity" in s and re.search(r"\bportfolio\b|\boverall\b", s)
           and re.search(r"\d+(\.\d+)?%", s)]
    uncapped = None
    capped = None
    for s in agg:
        u = pct(s, r"without the capping mechanism[^%]*?([0-9]+(?:\.[0-9]+)?)%")
        uncapped = u if u is not None else uncapped
    capped = pct(text, r"proposed cap would see this increase remain at ([0-9]+(?:\.[0-9]+)?)%")
    state = "distribution" if dist else ("aggregate" if agg else "none")
    return {"state": state, "distribution_sentences": dist, "aggregate_sentences": agg,
            "uncapped_pct": uncapped, "capped_pct": capped}


def b159_3(texts):
    m = magnitude_state(texts["M12629"])
    if m["state"] == "none" or m["uncapped_pct"] is None or m["capped_pct"] is None:
        return None, m
    return m["capped_pct"] <= m["uncapped_pct"], m


def b159_4(texts):
    m = magnitude_state(texts["M12606"])
    m["update_ordered"] = qfound(texts, "ppv_update")
    if m["state"] == "none":
        return None, m
    return True, m


# ---------------------------------------------------------------- B159-5

def read_rate_groups(path=None):
    import openpyxl
    path = path or RAW / PROFILES
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for year, tab in RG_TABS.items():
        rows = list(wb[tab].iter_rows(values_only=True))
        top, head = rows[0], rows[1]
        # D54: the source names its own columns; check them before reading
        names = {"top4": top[4], "top9": top[9], "h4": head[4], "h5": head[5], "h6": head[6], "h9": head[9],
                 "h10": head[10]}
        want = {"top4": "Separate", "top9": "Combined COLL & DCPD", "h4": "COLL", "h5": "COMP", "h6": "DCPD",
                "h9": "COLL", "h10": "COMP"}
        if names != want:
            raise ValueError(f"{tab}: columns are {names}, expected {want}")
        footer = [r[0] for r in rows[2:] if isinstance(r[0], str) and "CLEAR Tables" in r[0]]
        veh = []
        for r in rows[2:]:
            if isinstance(r[0], int):
                veh.append({"profile": r[0], "vehicle": r[1], "code": f"{r[2]}-{r[3]}",
                            "sep_coll": r[4], "sep_comp": r[5], "sep_dcpd": r[6],
                            "comb_coll_dcpd": r[9], "comb_comp": r[10]})
        out[year] = {"tab": tab, "footer": footer[0] if footer else "", "profiles": veh}
    return out


def b159_5(texts, rg):
    versions = {"b_separated": qfound(texts, "b_clear_version"), "b_2025": qfound(texts, "b_clear_2025"),
                "a_combined": qfound(texts, "a_clear_version"), "a_2026_dates": qfound(texts, "a_clear_dates")}
    per_year = {}
    all_between = True
    n = 0
    for year, d in sorted(rg.items()):
        seen = {}
        for v in d["profiles"]:
            seen.setdefault(v["code"], v)
        rows = []
        for code, v in seen.items():
            lo, hi = min(v["sep_coll"], v["sep_dcpd"]), max(v["sep_coll"], v["sep_dcpd"])
            between = lo <= v["comb_coll_dcpd"] <= hi
            all_between = all_between and between
            n += 1
            rows.append({"vehicle": v["vehicle"], "code": code,
                         "B_coll_comp_dcpd": [v["sep_coll"], v["sep_comp"], v["sep_dcpd"]],
                         "A_collDCPD_comp": [v["comb_coll_dcpd"], v["comb_comp"]],
                         "B_distinct_values": len({v["sep_coll"], v["sep_comp"], v["sep_dcpd"]}),
                         "A_distinct_values": len({v["comb_coll_dcpd"], v["comb_comp"]}),
                         "comp_equal": v["sep_comp"] == v["comb_comp"], "merged_between": between})
        per_year[year] = {"tab": d["tab"], "footer": d["footer"], "vehicles": rows,
                          "profiles": len(d["profiles"]), "distinct_vehicles": len(rows),
                          "coll_dcpd_differ_under_B": sum(r["B_coll_comp_dcpd"][0] != r["B_coll_comp_dcpd"][2]
                                                          for r in rows)}
    # The conversion pairing: B rated on the 2025 separated table; A on the combined table, 2025 then 2026.
    ramp = {}
    b = {r["code"]: r for r in per_year[B_YEAR]["vehicles"]}
    for ya in A_YEARS_ON_RAMP:
        lst = []
        for r in per_year[ya]["vehicles"]:
            br = b[r["code"]]
            lst.append({"vehicle": r["vehicle"],
                        "collision": [br["B_coll_comp_dcpd"][0], r["A_collDCPD_comp"][0]],
                        "dcpd": [br["B_coll_comp_dcpd"][2], r["A_collDCPD_comp"][0]],
                        "comprehensive": [br["B_coll_comp_dcpd"][1], r["A_collDCPD_comp"][1]]})
        ramp[f"B{B_YEAR}_separated_to_A{ya}_combined"] = lst
    differ_2026_2025 = sum(
        a["B_coll_comp_dcpd"] != b2["B_coll_comp_dcpd"] or a["A_collDCPD_comp"] != b2["A_collDCPD_comp"]
        for a, b2 in zip(per_year[2026]["vehicles"], per_year[2025]["vehicles"]))
    passed = all(versions.values()) and all_between and n > 0
    return passed, {"versions": versions, "per_year": per_year, "conversion_pairing": ramp,
                    "vehicle_years": n, "tab2026_vehicles_differing_from_tab2025": differ_2026_2025}


# ---------------------------------------------------------------- B159-6

def cap_sets(texts):
    t = texts
    ppv = {"up": pct(t["M12606"], r"renews into Definity at ([0-9]+)%"),
           "up_after_claim": pct(t["M12606"], r"capped at a higher level \(i\.e\., ([0-9]+)%\)"),
           "down": pct(t["M12606"], r"upon renewal into Definity to ([0-9]+)%")}
    cv = {"up": pct(t["M12629"], r"renews into Definity at ([0-9]+)%"),
          "up_after_claim": pct(t["M12629"], r"the cap will increase to ([0-9]+)%"),
          "down": pct(t["M12629"], r"upon renewal into Definity to ([0-9]+)%")}
    rsa = {"up": pct(t["INTACT2023"], r"Intact capped renewal premium increases at ([0-9]+)%"),
           "down": pct(t["INTACT2023"], r"capped renewal premium decreases at -([0-9]+)%")}
    intact = {"up": pct(t["INTACT2023"], r"currently apply a ([0-9]+)% premium dislocation cap"),
              "up_after_conviction": pct(t["INTACT2023"], r"the cap increases to ([0-9]+)%")}
    return ppv, cv, rsa, intact


def as_set(d, down_keys=("down",)):
    return sorted((-v if k in down_keys else v) for k, v in d.items() if v is not None)


def b159_6(texts):
    ppv, cv, rsa, intact = cap_sets(texts)
    events = [
        {"event": "Definity <- Travelers, commercial (M12629)", "provenance": as_set(cv),
         "acquirer_own": [] if qfound(texts, "cv_own_none") else None,
         "own_note": "Definity applies no capping mechanism to its own renewing commercial policies"},
        {"event": "Definity <- Travelers, private passenger (M12606)", "provenance": as_set(ppv),
         "acquirer_own": None,
         "own_note": ("the decision says the mechanism differs from Definity's own approved one"
                      if qfound(texts, "ppv_cap_differs") else "") + "; the own values are not printed"},
        {"event": "Intact <- RSA, private passenger (2023 NSUARB 11 [58])", "provenance": as_set(rsa),
         "acquirer_own": as_set(intact, down_keys=()),
         "own_note": "Intact and Trafalgar as of the application decided 2023-01-24; no cap on decreases",
         "provenance_line_removed": qfound(texts, "rsa_removed") and qfound(texts, "rsa_all_renewed")},
    ]
    extra = {"conversion_credit_score_relativity": qfound(texts, "ppv_ccs"),
             "cap_span_two_renewals": qfound(texts, "ppv_cap_span"),
             "collector_car_no_algorithm": qfound(texts, "ppv_collector")}
    evaluable = []
    for e in events:
        if e["acquirer_own"] is None:
            e["verdict"] = None
            continue
        ok = bool(e["provenance"]) and e["provenance"] != e["acquirer_own"]
        if "provenance_line_removed" in e:
            ok = ok and e["provenance_line_removed"]
        e["verdict"] = ok
        evaluable.append(ok)
    passed = bool(evaluable) and all(evaluable) and bool(events[1]["provenance"])
    return passed, {"events": events, "temporary_lines_private_passenger": extra}


# ---------------------------------------------------------------- B159-7

def b159_7(texts):
    win = all_dates(qtext("ppv_window")) if qfound(texts, "ppv_window") else []
    rates = all_dates(qtext("a_rates_dates")) if qfound(texts, "a_rates_dates") else []
    clear = all_dates(qtext("a_clear_dates")) if qfound(texts, "a_clear_dates") else []
    if len(win) < 2 or len(rates) < 2 or len(clear) < 2:
        return False, {"segments": [], "note": "a date did not parse"}
    start, end = win[0], win[-1]
    cut1, cut2 = rates[1], clear[1]  # renewal-business dates
    amended = {}
    # Two amending orders move two of these dates (2026-03-25 for the start, 2026-10-02 for the CLEAR table).
    if qfound(texts, "ppv_window_amended"):
        amended["start"] = [start.isoformat(), all_dates(qtext("ppv_window_amended"))[0].isoformat()]
        start = all_dates(qtext("ppv_window_amended"))[0]
    if qfound(texts, "a_clear_dates_amended"):
        amended["clear_renewal"] = [cut2.isoformat(), all_dates(qtext("a_clear_dates_amended"))[1].isoformat()]
        cut2 = all_dates(qtext("a_clear_dates_amended"))[1]
    p, r = segments_check(start, end, [cut1, cut2])
    r["amended_dates"] = amended
    return p, r


def segments_check(start, end, cuts):
    bounds = [start] + list(cuts) + [end + dt.timedelta(days=1)]
    labels = ["Definity program of M12161 (2025 NSRAB 38; M12606 changed no rate), 2025 CLEAR combined version",
              "Definity program of M12803 (overall +7%), 2025 CLEAR",
              "Definity program of M12803, 2026 CLEAR"]
    segs = []
    total = (end - start).days + 1
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        segs.append({"from": a.isoformat(), "to_inclusive": (b - dt.timedelta(days=1)).isoformat(),
                     "calendar_days": (b - a).days, "calendar_share": f"{(b - a).days / total:.4f}",
                     "program": labels[i] if i < len(labels) else ""})
    contiguous = all(segs[i]["calendar_days"] > 0 for i in range(len(segs)))
    covered = sum(s["calendar_days"] for s in segs) == total
    ordered = all(bounds[i] < bounds[i + 1] for i in range(len(bounds) - 1))
    return contiguous and covered and ordered, {"window": [start.isoformat(), end.isoformat()],
                                                "window_days": total, "segments": segs,
                                                "note": "calendar shares, not shares of policies: the renewal-date "
                                                        "distribution of the book is not public"}


# ---------------------------------------------------------------- B159-8

def b159_8(texts, wanted=WANTED):
    rows = []
    ok = True
    for obj, state, qids, note in wanted:
        qs = {q: qfound(texts, q) for q in qids}
        good = state in STATES and all(qs.values())
        if state == "confidential_by_rule":
            good = good and any(q.startswith("conf") for q in qids)
        ok = ok and good
        rows.append({"object": obj, "state": state, "state_reads": STATES.get(state, "?"), "quotes": qs,
                     "note": note, "ok": good})
    counts = {s: sum(r["state"] == s for r in rows) for s in STATES}
    return ok and bool(rows), {"objects": rows, "counts": counts}


# ---------------------------------------------------------------- B159-9

def b159_9(texts):
    rep = {k: qfound(texts, k) for k in ("cites_8", "m12284_8", "m12284_cite", "m12284_ppv",
                                          "m12044_cite", "m12044_who", "m12044_what")}
    traced = rep["cites_8"] and rep["m12284_8"] and rep["m12284_cite"] and rep["m12284_ppv"]
    rep["cited_decision_is"] = ("2025 NSUARB 25 is Hartford Fire Insurance Company adopting IAO rates for "
                                "commercial vehicles (M12044)" if rep["m12044_cite"] and rep["m12044_who"] else "")
    return traced, rep


# ---------------------------------------------------------------- B159-10 to B159-12: rating profiles

def read_profiles(path, sheet_re=PROFILE_SHEET) -> dict:
    """Every (profile sheet, territory) block of a CARR rating-profile workbook, current and proposed rows.

    Returns plain JSON types so the selftest can copy and plant faults: cells keyed 'sheet|territory'.
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    meta = {}
    for r in wb["Comp Info"].iter_rows(values_only=True):
        vals = [v for v in r if v is not None]
        if vals and isinstance(vals[0], str):
            key = vals[0].strip()
            if key in ("Company Name", "New Business", "Renewal Business") and len(vals) > 1:
                meta[key] = str(vals[-1])
            if key == "Status of Profiles":
                meta[key] = " ".join(str(v) for v in vals[1:])
            if "harmonized profiles" in key:
                meta["profile_version"] = key
    sheets, cells = {}, {}
    for sh in wb.sheetnames:
        if not sheet_re.match(sh):
            continue
        rows = list(wb[sh].iter_rows(values_only=True))
        head_i = next(i for i, r in enumerate(rows) if r[0] == "Territory")
        head = [str(v).strip() for v in rows[head_i][2:13]]
        if head != COVERAGE_HEAD:   # D54: the source names its own columns; check them before reading
            raise ValueError(f"{path.name if hasattr(path, 'name') else path} {sh}: columns {head}")
        sheets[sh] = [" | ".join(str(v).strip() for v in r if v is not None) for r in rows[5:head_i]]
        for i, r in enumerate(rows):
            if isinstance(r[0], str) and r[1] == "Current" and i + 1 < len(rows) and rows[i + 1][1] == "Proposed":
                cells[f"{sh}|{r[0].strip()}"] = {"current": [float(v or 0) for v in r[2:13]],
                                                 "proposed": [float(v or 0) for v in rows[i + 1][2:13]]}
    return {"meta": meta, "sheets": sheets, "cells": cells}


def half_unit(vec) -> float:
    """Printed-rounding bound on a total: each printed component is within half a unit of its value. If the
    printed total is the sum of the printed components, its error is at most half a unit per nonzero component;
    otherwise the total was rounded on its own and carries one more half unit."""
    comps = [vec[j] for j in COMPONENTS]
    unit = 0.01 if any(abs(v - round(v)) > 1e-9 for v in vec) else 1.0
    k = sum(1 for v in comps if v != 0)
    return 0.5 * unit * (k if abs(sum(comps) - vec[TOTAL]) < 1e-6 else k + 1)


def log_floor(p: float, d: float) -> float:
    return math.log(p / (p - d))


def pair_positions(pb: dict, pa: dict, column="proposed"):
    """Positions where both programs priced the same written profile: identical description block, both
    totals nonzero. Returns the paired rows and the sheets excluded with the reason."""
    rows, excluded = [], {}
    for key, cb in sorted(pb["cells"].items()):
        sh, terr = key.split("|", 1)
        ca = pa["cells"].get(key)
        if ca is None:
            excluded.setdefault(sh, "no matching block in A")
            continue
        if pb["sheets"].get(sh) != pa["sheets"].get(sh):
            excluded[sh] = "profile description differs between the two workbooks"
            continue
        b, a = cb[column][TOTAL], ca[column][TOTAL]
        if b <= 0 or a <= 0:
            # unused territory rows (Territory 10, 11) and sub-profiles one company left blank
            excluded.setdefault("unpriced_blocks", 0)
            excluded["unpriced_blocks"] += 1
            continue
        db, da = half_unit(cb[column]), half_unit(ca[column])
        rows.append({"profile": sh, "territory": terr, "B": b, "A": a, "B_vector": cb[column], "A_vector": ca[column],
                     "r": math.log(a / b), "eps": log_floor(b, db) + log_floor(a, da)})
    return rows, excluded


def square_floor(x, y) -> float:
    return x["eps"] + y["eps"]


def b159_10(pb, pa):
    rows, excluded = pair_positions(pb, pa)
    n = len(rows)
    if n == 0:
        return None, {"positions": 0, "excluded_sheets": excluded}
    # direct reading of the scalar-field rival: one position, one price, whoever runs the procedure
    direct_off = sum(abs(x["r"]) > x["eps"] for x in rows)
    # squares: class (program) x position; zero for every pair iff the A/B ratio is one constant
    above, total, worst = 0, 0, (0.0, None, None, 0.0)
    for i in range(n):
        for j in range(i + 1, n):
            s = rows[i]["r"] - rows[j]["r"]
            f = square_floor(rows[i], rows[j])
            total += 1
            if abs(s) > f:
                above += 1
            if abs(s) > abs(worst[0]):
                worst = (s, rows[i], rows[j], f)
    order = sorted(range(n), key=lambda k: rows[k]["r"])
    ref = rows[order[(n - 1) // 2]]
    star = [(x["r"] - ref["r"], square_floor(x, ref)) for x in rows if x is not ref]
    star_above = sum(abs(s) > f for s, f in star)
    eps = sorted(x["eps"] for x in rows)
    rs = sorted(x["r"] for x in rows)
    per_profile = {}
    for x in rows:
        per_profile.setdefault(x["profile"], []).append(x["A"] / x["B"] - 1)
    out = {"positions": n, "profiles": sorted({x["profile"] for x in rows}), "excluded_sheets": excluded,
           "independent_squares_b1": n - 1,
           "direct_positions_off_floor": direct_off,
           "pairs": total, "pairs_above_floor": above,
           "star_reference": f"{ref['profile']} | {ref['territory']}", "star_squares": len(star),
           "star_squares_above_floor": star_above,
           "per_profile_change_min_max": {k: [f"{min(v):+.4f}", f"{max(v):+.4f}"] for k, v in sorted(per_profile.items())},
           "log_ratio_min_median_max": [f"{rs[0]:.4f}", f"{rs[(n - 1) // 2]:.4f}", f"{rs[-1]:.4f}"],
           "position_floor_min_median_max": [f"{eps[0]:.5f}", f"{eps[(n - 1) // 2]:.5f}", f"{eps[-1]:.5f}"],
           "largest_square": {"value": f"{worst[0]:.4f}", "floor": f"{worst[3]:.5f}",
                              "x": f"{worst[1]['profile']} | {worst[1]['territory']}" if worst[1] else "",
                              "y": f"{worst[2]['profile']} | {worst[2]['territory']}" if worst[2] else "",
                              "times_floor": f"{abs(worst[0]) / worst[3]:.1f}" if worst[3] else ""},
           "table": [{"profile": x["profile"], "territory": x["territory"], "B_total": x["B"], "A_total": x["A"],
                      "log_A_over_B": f"{x['r']:.4f}", "floor": f"{x['eps']:.5f}",
                      "B_coverages": x["B_vector"], "A_coverages": x["A_vector"]} for x in rows]}
    return (star_above > 0), out


def b159_11(texts, pb, pa, pa_next=None):
    rows, _ = pair_positions(pb, pa)
    letter = qfound(texts, "negative_capping_confirmed") and qfound(texts, "update_received")
    disp = []
    for x in rows:
        u = x["A"] / x["B"] - 1
        disp.append({"position": f"{x['profile']} | {x['territory']}", "uncapped": f"{u:+.4f}",
                     "capped": f"{min(max(u, CAP_DOWN), CAP_UP):+.4f}"})
    us = sorted(x["A"] / x["B"] - 1 for x in rows)
    n = len(us)
    up = sum(u > CAP_UP for u in us)
    down = sum(u < CAP_DOWN for u in us)
    foregone = sum(x["B"] * max(x["A"] / x["B"] - 1 - CAP_UP, 0) for x in rows)
    collected = sum(x["B"] * max(CAP_DOWN - (x["A"] / x["B"] - 1), 0) for x in rows)
    out = {"positions": n, "board_letter_found": letter,
           "uncapped_min_median_max": [f"{us[0]:+.4f}", f"{us[(n - 1) // 2]:+.4f}", f"{us[-1]:+.4f}"] if n else [],
           "above_cap_up": up, "below_cap_down": down, "inside_caps": n - up - down,
           "unweighted_premium_foregone": f"{foregone:.0f}", "unweighted_extra_collected": f"{collected:.0f}",
           "note": "positions are the Board's standard profiles, one each; the Board's letter is about the book, "
                   "weighted by its policies. The two are different objects and are printed side by side, not compared",
           "rows": disp}
    if pa_next is not None:
        nxt = [c["proposed"][TOTAL] / c["current"][TOTAL] - 1 for k, c in pa_next["cells"].items()
               if A_NEXT_SHEET.match(k.split("|")[0]) and c["current"][TOTAL] > 0 and c["proposed"][TOTAL] > 0]
        nxt.sort()
        out["A_next_step_on_2025_profiles"] = {
            "positions": len(nxt), "workbook": Path(A_NEXT_PROFILES).name,
            "change_min_median_max": [f"{nxt[0]:+.4f}", f"{nxt[(len(nxt) - 1) // 2]:+.4f}", f"{nxt[-1]:+.4f}"] if nxt else []}
    return (letter and n > 0 and len(disp) == n), out


def partition(cells: dict, sheet: str, column="proposed") -> list:
    """Territories of one profile sheet grouped by identical printed coverage vectors."""
    groups = {}
    for key, c in sorted(cells.items()):
        sh, terr = key.split("|", 1)
        if sh == sheet and c[column][TOTAL] > 0:
            groups.setdefault(tuple(c[column]), []).append(terr)
    return sorted(sorted(g) for g in groups.values())


def b159_12(pb, pa):
    rows, _ = pair_positions(pb, pa)
    profiles = sorted({x["profile"] for x in rows})
    if not profiles:
        return None, {"profiles": 0}
    per = []
    for sh in profiles:
        b, a = partition(pb["cells"], sh), partition(pa["cells"], sh)
        per.append({"profile": sh, "B_blocks": b, "A_blocks": a, "B_levels": len(b), "A_levels": len(a),
                    "differ": b != a})
    differ = sum(p["differ"] for p in per)

    def refines(fine, coarse):
        return all(any(set(f) <= set(c) for c in coarse) for f in fine)
    for p in per:
        p["B_refines_A"] = refines(p["B_blocks"], p["A_blocks"])
        p["A_refines_B"] = refines(p["A_blocks"], p["B_blocks"])
    split = sum(any(g == ["Halifax (B3H)"] for g in p["A_blocks"]) for p in per)
    return differ > 0, {"profiles": len(per), "profiles_where_partitions_differ": differ,
                        "profiles_where_neither_refines": sum(not p["B_refines_A"] and not p["A_refines_B"] for p in per),
                        "profiles_where_B_strictly_refines_A": sum(p["B_refines_A"] and p["differ"] for p in per),
                        "profiles_where_A_splits_halifax": split, "per_profile": per}


# ---------------------------------------------------------------- 11c mapping

MAPPING = [
    ("B159-3", "two numbers parsed, capped <= uncapped", True),
    ("B159-3", "two numbers parsed, capped > uncapped", False),
    ("B159-3", "numbers not in the text", None),
    ("B159-4", "distribution or aggregate in the public text", True),
    ("B159-4", "neither in the public text", None),
    ("B159-6", "event with the acquirer's own values printed, provenance set differs", True),
    ("B159-6", "event with the acquirer's own values printed, provenance set equal or empty", False),
    ("B159-6", "event whose acquirer's own values are not printed", None),
    ("B159-10", "at least one star square above its printed-rounding floor", True),
    ("B159-10", "every star square within its floor (the A/B ratio is one constant at this resolution)", False),
    ("B159-10", "no position priced by both programs on the same written profile", None),
    ("B159-12", "the two programs group the nine territories differently on at least one profile", True),
    ("B159-12", "identical territory partitions on every paired profile", False),
    ("B159-12", "no paired profile", None),
]

# ---------------------------------------------------------------- selftest

MUTATION = None


def load_profiles():
    return {"B": read_profiles(RAW / B_PROFILES), "A": read_profiles(RAW / A_PROFILES),
            "A_next": read_profiles(RAW / A_NEXT_PROFILES, A_NEXT_SHEET)}


def run_selftest(texts=None, rg=None, prof=None, verbose=False):
    texts = texts if texts is not None else load_texts()
    rg = rg if rg is not None else read_rate_groups()
    prof = prof if prof is not None else load_profiles()
    rows = []

    def expect(cond, msg):
        rows.append({"check": msg, "ok": bool(cond)})
        if verbose:
            print(("ok   " if cond else "FAIL ") + msg)

    def drop(key, quote_id):
        t = dict(texts)
        t[key] = t[key].replace(nq(qtext(quote_id)), "")
        return t

    # B159-1
    p, _ = b159_1(texts)
    expect(p, "B159-1 passes on the real files")
    fake_q = QUOTES + [("planted", "M12606", "Definity proposed to keep every Travelers rate unchanged.")]
    expect(not b159_1(texts, quotes=fake_q)[0], "B159-1 fails on a quote not in its source")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    man["files"][0] = dict(man["files"][0], sha256="0" * 64)
    expect(not b159_1(texts, manifest=man)[0], "B159-1 fails on a hash that does not match")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    held = [i for i, e in enumerate(man["files"]) if e.get("status") == WITHHELD]
    expect(bool(held), "the manifest names at least one withheld file")
    if held:
        man["files"][held[0]] = dict(man["files"][held[0]], path=B_PROFILES)   # a readable file sits at its path
        expect(not b159_1(texts, manifest=man)[0], "B159-1 fails when a withheld file is present under a readable name")
    # B159-2
    expect(b159_2(texts)[0], "B159-2 passes on the real texts")
    expect(not b159_2(drop("M12629", "cv_differ"))[0], "B159-2 fails when the commercial decision lacks 'differ'")
    swapped = [(i, s, ("The first Travelers Canada policy will renew on July 1, 2027, and by June 30, 2026, all "
                       "Travelers Canada policies will have been renewed into Definity.") if i == "ppv_window" else q)
               for i, s, q in QUOTES]
    t2 = dict(texts)
    t2["M12606"] = t2["M12606"].replace(nq(qtext("ppv_window")), nq(qtext("ppv_window", swapped)))
    expect(not b159_2(t2, quotes=swapped)[0], "B159-2 fails on a window whose start is after its end")
    # B159-3
    expect(b159_3(texts)[0] is True, "B159-3 passes on the real text")
    t3 = dict(texts)
    t3["M12629"] = t3["M12629"].replace("this increase remain at 4.2%", "this increase remain at 4.9%")
    expect(b159_3(t3)[0] is False, "B159-3 fails when capped exceeds uncapped")
    t3b = dict(texts)
    t3b["M12629"] = t3b["M12629"].replace("portfolio rate increase by 4.2%", "portfolio rate increase").replace(
        "remain at 4.2%", "remain")
    expect(b159_3(t3b)[0] is None, "B159-3 goes to the third state when the numbers are gone")
    # B159-4
    expect(b159_4(texts)[0] is None, "B159-4 is undetermined on the real private passenger text")
    t4 = dict(texts)
    t4["M12606"] = t4["M12606"] + (" Renewing the Travelers Canada portfolio into Definity without the capping "
                                   "mechanism would see an overall increase of 6.1%.")
    expect(b159_4(t4)[0] is True, "B159-4 reads an aggregate when one is planted")
    # B159-5
    expect(b159_5(texts, rg)[0], "B159-5 passes on the real workbook")
    rg5 = json.loads(json.dumps(rg))
    rg5 = {int(k): v for k, v in rg5.items()}
    rg5[2025]["profiles"][6]["comb_coll_dcpd"] = 99
    expect(not b159_5(texts, rg5)[0], "B159-5 fails when a merged rate group lies outside the separated pair")
    expect(not b159_5(drop("M12803", "a_clear_version"), rg)[0], "B159-5 fails when A's table version is not confirmed")
    # B159-6
    expect(b159_6(texts)[0], "B159-6 passes on the real texts")
    t6b = dict(texts)
    t6b["INTACT2023"] = t6b["INTACT2023"].replace(
        "capped renewal premium increases at 5% and capped renewal premium decreases at -14%",
        "capped renewal premium increases at 35%").replace("the cap increases to 45%", "the cap is unchanged")
    p6b, r6b = b159_6(t6b)
    expect(not p6b, "B159-6 fails when the acquirer's own cap set equals the provenance set")
    expect(not b159_6(drop("INTACT2023", "rsa_removed"))[0], "B159-6 fails when the RSA line's removal is not found")
    # B159-7
    expect(b159_7(texts)[0], "B159-7 passes on the real dates")
    expect(not segments_check(dt.date(2026, 7, 1), dt.date(2027, 6, 30), [dt.date(2026, 12, 30), dt.date(2026, 10, 21)])[0],
           "B159-7 fails on cut dates out of order")
    expect(not segments_check(dt.date(2026, 7, 1), dt.date(2027, 6, 30), [dt.date(2027, 8, 1), dt.date(2027, 9, 1)])[0],
           "B159-7 fails on cut dates past the window")
    # B159-8
    expect(b159_8(texts)[0], "B159-8 passes on the real table")
    expect(not b159_8(texts, WANTED + [("planted", "maybe", [], "")])[0], "B159-8 fails on a state outside the set")
    expect(not b159_8(texts, WANTED + [("planted", "confidential_by_rule", ["staff_report"], "")])[0],
           "B159-8 fails on a confidentiality claim without a filing-requirements quote")
    # B159-9
    expect(b159_9(texts)[0], "B159-9 passes on the real texts")
    expect(not b159_9(drop("M12284", "m12284_8"))[0], "B159-9 fails when the 8.0% is not in the Dominion decision")
    # B159-2 and B159-7 read the amending orders
    expect(b159_2(texts)[1]["private_passenger"]["window_start"] == "2026-07-11",
           "B159-2 takes the private passenger start from the Amending Order")
    expect(b159_2(drop("M12606_AMEND", "ppv_window_amended"))[1]["private_passenger"]["window_start"] == "2026-07-01",
           "B159-2 falls back to the order's start when the Amending Order is absent")
    r7 = b159_7(texts)[1]
    expect(r7["window"][0] == "2026-07-11" and r7["segments"][-1]["from"] == "2027-01-27",
           "B159-7 uses both amended dates")
    expect(b159_7(drop("M12803_AMEND", "a_clear_dates_amended"))[1]["segments"][-1]["from"] == "2026-12-30",
           "B159-7 falls back to the CLEAR date of the decision when the amended order is absent")
    # B159-10: the square
    pb, pa = prof["B"], prof["A"]
    expect(b159_10(pb, pa)[0] is True, "B159-10 reads squares above the floor on the real profiles")
    sep = json.loads(json.dumps(pb))
    for c in sep["cells"].values():
        for col in ("current", "proposed"):
            comps = [float(round(1.1 * c[col][j])) if j in COMPONENTS else c[col][j] for j in range(11)]
            comps[5] = sum(comps[j] for j in (0, 1, 2, 3, 4))
            comps[9] = sum(comps[j] for j in (6, 7, 8))
            comps[TOTAL] = sum(comps[j] for j in COMPONENTS)
            c[col] = comps
    expect(b159_10(pb, sep)[0] is False, "B159-10 is False when A is B scaled by one constant and rounded")
    nodesc = json.loads(json.dumps(pa))
    nodesc["sheets"] = {k: v + ["planted line"] for k, v in nodesc["sheets"].items()}
    expect(b159_10(pb, nodesc)[0] is None, "B159-10 goes to the third state when no profile description matches")
    # B159-11
    expect(b159_11(texts, pb, pa)[0], "B159-11 passes on the real profiles and letter")
    expect(not b159_11(drop("M12606_LETTER", "negative_capping_confirmed"), pb, pa)[0],
           "B159-11 fails when the Board's negative-capping sentence is not found")
    expect(not b159_11(texts, pb, nodesc)[0], "B159-11 fails when no position is paired")
    # B159-12
    expect(b159_12(pb, pa)[0] is True, "B159-12 finds differing territory partitions on the real profiles")
    expect(b159_12(pb, json.loads(json.dumps(pb)))[0] is False, "B159-12 is False when A carries B's own vectors")
    return rows


def selftest() -> int:
    rows = run_selftest(verbose=True)
    bad = [r for r in rows if not r["ok"]]
    print(f"selftest: {len(rows)} checks, {len(bad)} failure(s)")
    return 1 if bad else 0


# Mutation test (11f, third clause): each switch breaks the implementation on purpose; the selftest must
# report at least one failure for each.
def mutated(name):
    g = globals()
    saved = {}

    def patch(fn_name, new):
        saved[fn_name] = g[fn_name]
        g[fn_name] = new

    if name == "between_always_true":
        orig = b159_5

        def m(texts, rg):
            p, r = orig(texts, rg)
            return all(r["versions"].values()), r
        patch("b159_5", m)
    elif name == "capped_ignored":
        orig3 = b159_3

        def m3(texts):
            p, r = orig3(texts)
            return (True if p is not None else None), r
        patch("b159_3", m3)
    elif name == "quotes_not_checked":
        orig1 = b159_1

        def m1(texts, quotes=QUOTES, manifest=None, raw=RAW):
            p, r = orig1(texts, quotes, manifest, raw)
            return all(f["match"] for f in r["files"]), r
        patch("b159_1", m1)
    elif name == "withheld_not_checked":
        orig1w = b159_1

        def m1w(texts, quotes=QUOTES, manifest=None, raw=RAW):
            p, r = orig1w(texts, quotes, manifest, raw)
            return (all(f["match"] for f in r["files"]) and not r["missing"]), r
        patch("b159_1", m1w)
    elif name == "magnitude_always_none":
        patch("magnitude_state", lambda text: {"state": "none", "distribution_sentences": [],
                                                 "aggregate_sentences": [], "uncapped_pct": None,
                                                 "capped_pct": None})
    elif name == "segments_no_order":
        orig7 = segments_check

        def m7(start, end, cuts):
            p, r = orig7(start, end, sorted(c for c in cuts))
            return p, r
        patch("segments_check", m7)
    elif name == "state_set_open":
        orig8 = b159_8

        def m8(texts, wanted=WANTED):
            p, r = orig8(texts, wanted)
            return all(all(o["quotes"].values()) for o in r["objects"]), r
        patch("b159_8", m8)
    elif name == "floor_zero":
        patch("square_floor", lambda x, y: 0.0)
    elif name == "partition_not_compared":
        orig12 = b159_12

        def m12(pb, pa):
            p, r = orig12(pb, pa)
            return (True if p is not None else None), r
        patch("b159_12", m12)
    elif name == "amendment_ignored":
        orig2 = b159_2

        def m2(texts, quotes=QUOTES):
            t = dict(texts)
            t["M12606_AMEND"] = ""
            return orig2(t, quotes)
        patch("b159_2", m2)
    return saved


def mutation_test(texts, rg, prof) -> int:
    names = ["between_always_true", "capped_ignored", "quotes_not_checked", "magnitude_always_none",
             "segments_no_order", "state_set_open", "floor_zero", "partition_not_compared", "amendment_ignored",
             "withheld_not_checked"]
    caught = 0
    for n in names:
        saved = mutated(n)
        rows = run_selftest(texts, rg, prof)
        globals().update(saved)
        hit = any(not r["ok"] for r in rows)
        caught += hit
        print(f"mutation {n}: {'caught' if hit else 'MISSED'}")
    print(f"mutations caught {caught} of {len(names)}")
    return 0 if caught == len(names) else 1


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mutation", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    texts = load_texts()
    rg = read_rate_groups()
    prof = load_profiles()
    if a.selftest:
        return selftest()
    if a.mutation:
        return mutation_test(texts, rg, prof)

    st_rows = run_selftest(texts, rg, prof)
    print(f"selftest: {len(st_rows)} checks, {sum(not r['ok'] for r in st_rows)} failure(s)")
    p1, r1 = b159_1(texts)
    p2, r2 = b159_2(texts)
    p3, r3 = b159_3(texts)
    p4, r4 = b159_4(texts)
    p5, r5 = b159_5(texts, rg)
    p6, r6 = b159_6(texts)
    p7, r7 = b159_7(texts)
    p8, r8 = b159_8(texts)
    p9, r9 = b159_9(texts)
    p10, r10 = b159_10(prof["B"], prof["A"])
    p11, r11 = b159_11(texts, prof["B"], prof["A"], prof["A_next"])
    p12, r12 = b159_12(prof["B"], prof["A"])
    r10["workbooks"] = {"B": {"file": Path(B_PROFILES).name, **prof["B"]["meta"]},
                        "A": {"file": Path(A_PROFILES).name, **prof["A"]["meta"]}}

    print(f"B159-1 files {sum(f['match'] for f in r1['files'])}/{len(r1['files'])} hash match; quotes "
          f"{r1['quotes_found']}/{r1['quotes_total']}; missing {r1['missing']}; withheld "
          f"{[(w['path'], w['present_under_readable_name']) for w in r1['withheld']]}")
    for k, v in r2.items():
        print(f"B159-2 {k}: {v['citation']} elements {v['elements']} window {v['window_start']}..{v['window_end']}")
    print(f"B159-3 commercial: state {r3['state']}, uncapped {r3['uncapped_pct']}%, capped {r3['capped_pct']}%")
    print(f"B159-4 private passenger: state {r4['state']}; update ordered {r4['update_ordered']}")
    for y, d in sorted(r5["per_year"].items()):
        print(f"B159-5 {y} ({d['tab']}; footer '{d['footer']}'): {d['distinct_vehicles']} vehicles, "
              f"COLL != DCPD under B in {d['coll_dcpd_differ_under_B']}")
        for v in d["vehicles"]:
            print(f"   {v['vehicle'][:40]:40s} B {v['B_coll_comp_dcpd']} A {v['A_collDCPD_comp']} "
                  f"between {v['merged_between']}")
    print(f"B159-5 2026 tab vehicles differing from 2025 tab: {r5['tab2026_vehicles_differing_from_tab2025']}")
    for e in r6["events"]:
        print(f"B159-6 {e['event']}: provenance {e['provenance']} own {e['acquirer_own']} verdict {e['verdict']}")
    print(f"B159-6 temporary lines: {r6['temporary_lines_private_passenger']}")
    for s in r7["segments"]:
        print(f"B159-7 {s['from']}..{s['to_inclusive']} {s['calendar_days']}d share {s['calendar_share']}  {s['program']}")
    print(f"B159-8 {r8['counts']}")
    print(f"B159-9 {r9}")
    print(f"B159-10 {r10['positions']} positions on {len(r10.get('profiles', []))} profiles; excluded {r10['excluded_sheets']}")
    print(f"   direct off floor {r10.get('direct_positions_off_floor')}; pairs above floor {r10.get('pairs_above_floor')}/"
          f"{r10.get('pairs')}; star {r10.get('star_squares_above_floor')}/{r10.get('star_squares')} around "
          f"{r10.get('star_reference')}; log A/B {r10.get('log_ratio_min_median_max')}; floor "
          f"{r10.get('position_floor_min_median_max')}; largest {r10.get('largest_square')}")
    for x in r10.get("table", []):
        print(f"   {x['profile']:13s} {x['territory']:20s} B {x['B_total']:7.0f} A {x['A_total']:7.0f} "
              f"log {x['log_A_over_B']} floor {x['floor']}")
    print(f"B159-11 {({k: v for k, v in r11.items() if k != 'rows'})}")
    for p in r12.get("per_profile", []):
        print(f"B159-12 {p['profile']:13s} B {p['B_levels']} levels A {p['A_levels']} levels differ {p['differ']}")
        if p["differ"]:
            print(f"   B {p['B_blocks']}\n   A {p['A_blocks']}")

    def fmt_pairs(key):
        return "; ".join(f"{v['vehicle']} {v['B_coll_comp_dcpd']}->{v['A_collDCPD_comp']}"
                         for v in r5["per_year"][key]["vehicles"])

    ramp25 = r5["conversion_pairing"][f"B{B_YEAR}_separated_to_A2025_combined"]
    crit = [
        {"name": "B159-1", "kind": "bookkeeping", "passed": p1,
         "detail": f"{sum(f['match'] for f in r1['files'])} of {len(r1['files'])} files match the SHA-256 in "
                   f"data/raw/b159/b159_manifest.json; {len(r1['withheld'])} withheld file(s) are absent under their "
                   "readable names and never opened; "
                   f"{r1['quotes_found']} of {r1['quotes_total']} quotes are found "
                   "in the whitespace-collapsed text snapshots with page furniture removed."},
        {"name": "B159-2", "kind": "own_reading", "passed": p2,
         "detail": "The Board writes the swap for both rating programs. Private passenger (2026 NSRAB 20): each "
                   "Travelers Canada policy renews on its renewal date into a Definity policy, from "
                   f"{r2['private_passenger']['window_start']} to {r2['private_passenger']['window_end']} (the order "
                   f"said {r2['private_passenger']['window_start_in_order']}; the Amending Order of 2026-03-25 moved "
                   "the first renewal for internal system constraints); "
                   f"'{qtext('ppv_differ')}' '{qtext('ppv_large')}' Definity's manual is unchanged. Commercial "
                   f"(2026 NSRAB 8): '{qtext('cv_differ')}' Same customers and vehicles, a different pricing "
                   "procedure, different prices. The risk-pricing reading (one risk, one premium whoever runs the "
                   "procedure) predicts no change at the policy level; the regulator's text records many large "
                   "changes. No rival criterion is registered (the framework gives no opposite point prediction on "
                   "the direction)."},
        {"name": "B159-3", "kind": "own_reading", "passed": p3,
         "detail": f"Commercial vehicles: renewing the Travelers book into Definity's program moves the portfolio "
                   f"rate by +{r3['uncapped_pct']}% uncapped and +{r3['capped_pct']}% capped (caps +15%, +25% after a "
                   "new claim or conviction, -5% on decreases). The book's risks are those of the Travelers "
                   "portfolio; the +4.2% is the average move from the procedure alone. Only the average is public; "
                   "the spread around it is in the confidential pages (B159-8)."},
        {"name": "B159-4", "kind": "own_reading", "passed": p4,
         "detail": f"Private passenger: the public decision carries no portfolio or distribution figure for the "
                   f"swap (state '{r4['state']}'). The Board ordered an update within six months of the order "
                   "(order dated 2026-02-05) on whether the capping keeps premium foregone at or above extra premium "
                   "collected. Definity filed it on 2026-08-05; the company's correspondence is not in the matter's "
                   "public listing, and the Board's letter of the same day (document 103078) gives the sign only: "
                   f"'{qtext('negative_capping_confirmed')}' The distribution exists: the filing requirements make "
                   "every company fill CONF-8 (uncapped) and CONF-9 (capped) with exposure counts in 17 percent bins "
                   "and 17 dollar bins; those pages are routinely kept confidential. Undetermined, not zero; the "
                   "profile-resolution counterpart is B159-11."},
        {"name": "B159-5", "kind": "own_reading", "passed": p5,
         "detail": "Same vehicles, two table versions. The Travelers side rates on the CLEAR table with collision, "
                   "DCPD and comprehensive separated (three physical-damage rate groups per vehicle); Definity on the "
                   "version with collision and DCPD combined (two). Conversion pairing, 2025 separated to 2025 "
                   "combined, collision and DCPD rate groups: "
                   + "; ".join(f"{v['vehicle']} COLL {v['collision'][0]}->{v['collision'][1]}, DCPD {v['dcpd'][0]}->"
                               f"{v['dcpd'][1]}" for v in ramp25)
                   + f". In all {r5['vehicle_years']} vehicle-years (9 distinct vehicles, 2024-2026 tables) the merged "
                   "rate group lies between the two separated ones; comprehensive is the same in both versions. "
                   "The Board's 2026 tab carries a footer naming the 2025 tables while its numbers differ from the "
                   f"2025 tab in {r5['tab2026_vehicles_differing_from_tab2025']} of 9 vehicles; read as 2026. Rate "
                   "groups are classes, not prices: the relativities that turn them into premiums are confidential."},
        {"name": "B159-6", "kind": "own_reading", "passed": p6,
         "detail": "Both Nova Scotia acquisition conversions add class lines keyed on the policy's provenance. "
                   + "; ".join(f"{e['event']}: provenance caps {e['provenance']}, acquirer's own "
                               f"{e['acquirer_own'] if e['acquirer_own'] is not None else 'not printed'}"
                               for e in r6["events"])
                   + ". The RSA line was removed in 2023 once all RSA clients had renewed onto Intact's system. "
                   "Private passenger also carries a temporary Conversion Credit Score relativity until the first "
                   "renewal as a Definity policy, and Travelers collector cars are renewed as private passenger "
                   "vehicles because Definity has no collector car algorithm (a class line deleted)."},
        {"name": "B159-7", "kind": "instrument", "passed": p7,
         "detail": "The reading's index is the share of the book already converted (D53), not a date. Inside the "
                   "window Definity's own program changes twice: "
                   + "; ".join(f"{s['from']} to {s['to_inclusive']} ({s['calendar_days']} days): {s['program']}"
                               for s in r7["segments"])
                   + ". Two amending orders moved two of the cut dates: the first renewal from 2026-07-01 to "
                   "2026-07-11 (order of 2026-03-25) and the 2026 CLEAR table's renewal date from 2026-12-30 to "
                   "2027-01-27 (order of 2026-10-02). Calendar shares only; the renewal-date distribution of the book "
                   "is not public, so the dose "
                   "cannot be mapped to dates from public material. The conversion caps run for two renewals, the "
                   "Board's two-cycle limit."},
        {"name": "B159-8", "kind": "bookkeeping", "passed": p8,
         "detail": "Availability of every wanted object, one state each: "
                   + "; ".join(f"{k} {v}" for k, v in r8["counts"].items())
                   + ". The policy-level displacement and both companies' relativities are confidential by the "
                   "Board's filing requirements. The rating profiles are public in the matter files and were read "
                   "(B159-10 to B159-12); M12606 itself carries none, because a filing that changes no rate does not "
                   "require them. Staff Report, information-request responses and Definity's six-month update are "
                   "not in the public listings. One Dominion exhibit listed Public carries a 'Confidential' cover "
                   "with base rates and differentials; it was opened only to identify it and is used for no reading."},
        {"name": "B159-9", "kind": "known_answer", "passed": p9,
         "detail": "M12606 [3] cites the Travelers side's overall 8% increase to 2025 NSUARB 25; that citation is "
                   "Hartford Fire Insurance Company adopting IAO rates for commercial vehicles (M12044). The 8.0% "
                   "private passenger increase for Dominion of Canada (Travelers Canada) is 2025 NSRAB 65 "
                   "(M12284, decided 2025-08-07)."},
        {"name": "B159-10", "kind": "own_reading", "passed": p10,
         "detail": f"Same standard risk, two programs, two prices. {r10['positions']} positions ("
                   f"{len(r10.get('profiles', []))} CARR profiles x 9 Board territories) priced by both companies on "
                   "identical written profiles: Dominion of Canada (Travelers Canada) M12284 exhibit T-8 and Definity "
                   "M12161 exhibit D-2, both 2022-version workbooks, 'proposed' columns, in force for Travelers "
                   "renewals from 2025-12-21 and Definity renewals from 2025-11-21 to 2026-10-20, so both stand at "
                   "the first renewal into Definity (2026-07-11). Class = program, position = profile x territory. "
                   f"Log of A/B over positions runs {r10.get('log_ratio_min_median_max')} (min, median, max). The "
                   "floor is the printed rounding: whole-dollar components, half a dollar each, summed into the "
                   f"printed total; per position it runs {r10.get('position_floor_min_median_max')} in log. The "
                   "scalar-field reading (one position, one price, whichever program) is off its floor at "
                   f"{r10.get('direct_positions_off_floor')} of {r10['positions']} positions. The weaker separable "
                   "reading (A = constant x B) makes every square zero; the "
                   f"{r10.get('independent_squares_b1')} independent squares (a star around the median position, "
                   f"{r10.get('star_reference')}) stand above their floor in {r10.get('star_squares_above_floor')}, "
                   f"and all pairs in {r10.get('pairs_above_floor')} of {r10.get('pairs')}. Largest square "
                   f"{r10.get('largest_square', {}).get('value')} ({r10.get('largest_square', {}).get('x')} against "
                   f"{r10.get('largest_square', {}).get('y')}), {r10.get('largest_square', {}).get('times_floor')} "
                   "times its floor. The move runs along driver age and experience; A/B - 1 (min, max over the nine "
                   "territories) for the 19-year-old male (5.1) "
                   f"{r10.get('per_profile_change_min_max', {}).get('5.1')}, the 52-year-old with a 21-year-old "
                   f"occasional driver (Combined 1.1) {r10.get('per_profile_change_min_max', {}).get('Combined 1.1')}, "
                   f"the 70-year-old (9.1) {r10.get('per_profile_change_min_max', {}).get('9.1')}, the 35-year-old "
                   f"commuter (10.1) {r10.get('per_profile_change_min_max', {}).get('10.1')}. Not paired: Dominion's 2025-12-21 high-theft "
                   "list update (M12466) post-dates its profile workbook; Definity's charged premium passes its "
                   "expected loss cost through a proprietary formula (2025 NSRAB 38 [19]); the profiles are new "
                   "business, the conversion carries tenure."},
        {"name": "B159-11", "kind": "own_reading", "passed": p11,
         "detail": f"The swap at profile resolution. A/B - 1 over the {r11['positions']} positions runs "
                   f"{r11.get('uncapped_min_median_max')} (min, median, max); {r11['above_cap_up']} positions sit "
                   f"above the +15% cap, {r11['below_cap_down']} below the -5% floor, {r11['inside_caps']} inside. "
                   f"Unweighted over positions, premium foregone above the cap is {r11['unweighted_premium_foregone']} "
                   f"dollars and extra premium collected below the floor {r11['unweighted_extra_collected']}. The "
                   "Board's letter of 2026-08-05 states for the book, weighted by its policies, that foregone exceeds "
                   "collected; the profiles are one each and unweighted, a different object, printed beside it. "
                   "Definity's next step on its own 2025-version profiles (M12803 exhibit D-3, renewals from "
                   f"2026-10-21) moves {r11.get('A_next_step_on_2025_profiles', {}).get('change_min_median_max')} "
                   f"over {r11.get('A_next_step_on_2025_profiles', {}).get('positions')} positions; the Travelers side "
                   "filed no 2025-version profiles, so the later segments of the window have no B to pair with."},
        {"name": "B159-12", "kind": "own_reading", "passed": p12,
         "detail": f"Territory class lines. On each of the {r12.get('profiles')} paired profiles the nine Board "
                   "territories are grouped by identical printed coverage vectors. Dominion: "
                   + "; ".join(sorted({" / ".join("+".join(t.split(" (")[0] for t in g) for g in p["B_blocks"])
                                       for p in r12.get("per_profile", [])}))
                   + ". Definity: "
                   + "; ".join(sorted({" / ".join("+".join(t.split(" (")[0] for t in g) for g in p["A_blocks"])
                                       for p in r12.get("per_profile", [])}))
                   + f". The partitions differ on {r12.get('profiles_where_partitions_differ')} of "
                   f"{r12.get('profiles')} profiles: on {r12.get('profiles_where_B_strictly_refines_A')} Dominion's "
                   f"grouping strictly refines Definity's, on {r12.get('profiles_where_neither_refines')} neither "
                   "refines the other. Dominion splits Amherst from "
                   "New Glasgow and Antigonish and Kentville from Yarmouth, which Definity joins; Definity splits "
                   f"Halifax from Dartmouth on {r12.get('profiles_where_A_splits_halifax')} profiles, which Dominion "
                   "joins. The swap moves a policy across "
                   "territory lines as well as rate levels. Definity's territories were unchanged in 2025 NSRAB 38."},
    ]
    record = {
        "stage": "B159",
        "title": "Definity takes over Travelers Canada: the same policies renew into the acquirer's rating program",
        "config": {"source_manifest": "data/raw/b159/b159_manifest.json", "conversion_window": r7["window"],
                   "profile_workbook": Path(PROFILES).name, "rate_group_tabs": RG_TABS, "b_table_year": B_YEAR,
                   "a_table_years_on_ramp": list(A_YEARS_ON_RAMP),
                   "profiles_B": B_PROFILES, "profiles_A": A_PROFILES, "profiles_A_next": A_NEXT_PROFILES,
                   "profile_column": "proposed", "caps_first_renewal": [CAP_DOWN, CAP_UP]},
        "criteria": crit,
        "mapping_11c": [{"criterion": c, "state": s, "verdict": v} for c, s, v in MAPPING],
        "selftest": st_rows,
        "B159_1": r1, "B159_2": r2, "B159_3": r3, "B159_4": r4, "B159_5": r5, "B159_6": r6, "B159_7": r7,
        "B159_8": r8, "B159_9": r9, "B159_10": r10, "B159_11": r11, "B159_12": r12,
    }
    text = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        from safe_write import create, rewrite
        if RECORD.exists():
            rewrite(RECORD, "B159_record", lambda _t: text, session=SESSION)
        else:
            create(RECORD, "B159_record", text, session=SESSION)
        print(f"wrote {RECORD.name}")
    print("criteria:", {c["name"]: c["passed"] for c in crit})
    return 1 if any(c["passed"] is False for c in crit) else 0


if __name__ == "__main__":
    sys.exit(main())
