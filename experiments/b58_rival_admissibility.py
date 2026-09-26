"""B58. Whether the rival's own feasibility conditions hold on the carriers this
project has scored it on.

B56 and B57 score third-degree price discrimination on published class tables.
Neither of them checks the thing the rival itself says has to be true before it
applies. The standard survey states the conditions:

    It is well known that price discrimination is only feasible under certain
    conditions: (i) firm(s) have short-run market power, (ii) consumers can be
    segmented either directly or indirectly, and (iii) arbitrage across
    differently priced goods is infeasible.
        -- Stole, Handbook of Industrial Organization vol. 3, ch. 34

Those three make it feasible. The point prediction that B56 scores, the inverse
elasticity rule, needs a fourth thing that is not on that list: the seller has
to be maximising profit. So does the cost argument B57 scores, that a seller
will not pay to tell apart classes it then prices identically.

This station runs that screen over every carrier contributing a zero pair to
B57-11, and it can lose: a carrier where a condition fails cannot score against
the rival at all, and its pairs come out of the count.

It does not re-judge anything. The rival verdicts stay in B56-5, B57-6 and
B57-11. This station partitions their inputs by admissibility and prints the
partition, so that a headline number is never carried without the screen.

Three states per condition, and the undetermined one maps to no verdict (11c).
"""

import json
from pathlib import Path

HOLDS, FAILS, OPEN, CONTESTED = "holds", "fails", "not_established", "contested"


def c(answer, reason):
    """Answer standing on a document, or true by definition."""
    return {"answer": answer, "checked": True, "reason": reason}


def u(answer, reason):
    """Answer carried on judgement, with no document behind it."""
    return {"answer": answer, "checked": False, "reason": reason}


# --------------------------------------------------------------------------
# The rival, written out. Every element carries where it was read.

STOLE = ("Stole, Price Discrimination and Competition, Handbook of Industrial "
         "Organization vol. 3, ch. 34, read 2026-09-08")
ELLISON = ("MIT 14.271 Industrial Organization I, Fall 2022, lecture 3 slides "
           "(Ellison), read 2026-09-08")
ROCHET_CHONE = ("Rochet and Chone, Ironing, Sweeping, and Multidimensional "
                "Screening, Econometrica 66(4), 783-826, introduction read "
                "2026-09-08")

RIVAL = {
    "feasibility_i_market_power": {
        "text": "firm(s) have short-run market power", "source": STOLE},
    "feasibility_ii_segmentation": {
        "text": "consumers can be segmented either directly or indirectly",
        "source": STOLE},
    "feasibility_iii_no_arbitrage": {
        "text": "arbitrage across differently priced goods is infeasible",
        "source": STOLE},
    "taxonomy": {
        "text": "Pigou (1920) introduced the terminology of first-, second- and "
                "third-degree price discrimination", "source": STOLE},
    "first_degree": {
        "text": "Perfect price discrimination. The firm knows consumer "
                "preferences completely and can price separately to each "
                "consumer", "source": ELLISON},
    "second_degree": {
        "text": "Pricing based on self-selection, consumers with different "
                "preferences choose to buy different goods at different prices",
        "source": ELLISON},
    "third_degree": {
        "text": "Pricing based on limited observed characteristics, e.g. age, "
                "student status, gender, health status", "source": ELLISON},
    "third_degree_foc": {
        "text": "(p_i* - c) / p_i* = - 1 / eps_i(p_i*), per market i",
        "source": ELLISON},
    "second_degree_utility": {
        "text": "v(q, theta) - T, with v_q > 0, v_theta > 0, v_qtheta > 0, "
                "v_qq < 0", "source": ELLISON},
    "second_degree_ir": {"text": "U(theta) >= 0 for all theta", "source": ELLISON},
    "second_degree_ic": {
        "text": "theta in argmax_thetahat v(x(thetahat), theta) - T(thetahat)",
        "source": ELLISON},
    "second_degree_local_ic": {
        "text": "U(theta) = U(theta_low) + integral from theta_low to theta of "
                "v_theta(x(s), s) ds", "source": ELLISON},
    "multidimensional": {
        "text": "one does not know the direction of the (local) incentive "
                "compatibility constraints that will be binding",
        "source": ROCHET_CHONE},
}

# The fourth requirement, which is not on Stole's list and which both scored
# predictions need. Kept separate for exactly that reason.
PROFIT_MAX = ("the inverse elasticity rule is a first-order condition of profit "
              "maximisation, and the cost argument B57 scores is a profit "
              "argument. neither is on Stole's feasibility list")

# --------------------------------------------------------------------------
# The carriers, one row per B57 row that contributes a zero pair to B57-11.

CARRIERS = {
    "cinema_village_categories": {
        "seller": "an independent cinema", "zero_pairs": 6,
        "market_power": c(HOLDS, "the rival's own definition of third degree is pricing based on limited observed characteristics, e.g. age, student status, gender, health status. a seller posting senior, student and child prices is an instance of that definition, so the rival classifies this carrier as one of its own. a defender who denies the condition here is denying that this is price discrimination at all, which removes the carrier from the rival's domain and removes the rival's claim to explain why the classes exist"),
        "segmentation": c(HOLDS, "the published page requires an age ID, a "
                                 "student ID and a federal disability ID, so the "
                                 "segmentation is direct and paid for"),
        "no_arbitrage": c(HOLDS, "a ticket admits to one showing and the "
                                 "discount categories are checked at entry, so "
                                 "a discounted ticket cannot be resold to "
                                 "someone outside the class"),
        "profit_maximisation": u(OPEN, "not read. no filing, no tax status, and "
                                       "no statement of objective was located"),
    },
    "cinema_arts_evening": {
        "seller": "an independent cinema", "zero_pairs": 3,
        "market_power": c(HOLDS, "granted on the rival's own definition, as "
                                 "for the other cinema"),
        "segmentation": c(HOLDS, "the same page prices College Tuesdays with "
                                 "valid ID, so the classes are credentialed"),
        "no_arbitrage": c(HOLDS, "same as the other cinema"),
        "profit_maximisation": u(OPEN, "not read"),
    },
    "transit_federal_three": {
        "seller": "three public transit operators", "zero_pairs": 3,
        "market_power": c(HOLDS, "granted on the rival's own definition, which "
                                 "names age and student status; and a scheduled "
                                 "network in one metropolitan area"),
        "segmentation": c(HOLDS, "each operator issues a distinct credential per "
                                 "class and inspects it at the farebox"),
        "no_arbitrage": c(HOLDS, "the reduced-fare credential is issued to a "
                                 "named person and inspected at the farebox"),
        "profit_maximisation": c(CONTESTED,
            "49 U.S.C. 5307(c)(1)(D) conditions a federal grant on a reduced "
            "fare not exceeding half the peak fare for the three named classes. "
            "the condition caps the level and names the three together; it does "
            "not require them to carry one number. the objective is contested "
            "rather than absent"),
    },
    "mbta_reduced_list": {
        "seller": "one public transit operator", "zero_pairs": 6,
        "market_power": c(HOLDS, "granted on the rival's own definition, as above"),
        "segmentation": c(HOLDS, "the reduced-fare list is credentialed per entry"),
        "no_arbitrage": c(HOLDS, "as above"),
        "profit_maximisation": c(CONTESTED, "same grant condition, and this list "
                                            "also holds a student line and an "
                                            "income line the condition does not "
                                            "name"),
    },
    "rtd_discount_four": {
        "seller": "one public transit operator", "zero_pairs": 6,
        "market_power": c(HOLDS, "granted on the rival's own definition, as above"),
        "segmentation": c(HOLDS, "four separately branded programmes, each with "
                                 "its own eligibility test"),
        "no_arbitrage": c(HOLDS, "as above"),
        "profit_maximisation": c(CONTESTED, "same grant condition, and the income "
                                            "programme is not named by it"),
    },
    "income_vs_senior": {
        "seller": "three public transit operators", "zero_pairs": 1,
        "market_power": c(HOLDS, "granted on the rival's own definition, as above"),
        "segmentation": c(HOLDS, "each side has its own eligibility test and "
                                 "credential on the operators' own pages"),
        "no_arbitrage": c(HOLDS, "as above"),
        "profit_maximisation": c(CONTESTED, "same grant condition; the income "
                                            "line is not named by it"),
    },
    "king_county_types": {
        "seller": "one public transit operator", "zero_pairs": 3,
        "market_power": c(HOLDS, "granted on the rival's own definition, as above"),
        "segmentation": c(HOLDS, "the operator's own fare page lists the types "
                                 "separately with separate eligibility"),
        "no_arbitrage": c(HOLDS, "as above"),
        "profit_maximisation": c(CONTESTED, "same grant condition"),
    },
    "marcus_matinee": {
        "seller": "a cinema chain listed on the New York Stock Exchange",
        "zero_pairs": 1,
        "market_power": c(HOLDS, "granted on the rival's own definition, which "
                                 "names age among the limited observed "
                                 "characteristics third degree prices on"),
        "segmentation": c(HOLDS, "the announcement prices by two stated age bands, "
                                 "which is the rival's own example of direct "
                                 "segmentation; the same chain names a valid "
                                 "school ID and a valid military ID on its other "
                                 "rates"),
        "no_arbitrage": c(HOLDS, "a ticket admits to one showing"),
        "profit_maximisation": c(HOLDS,
            "The Marcus Corporation, NYSE: MCS, identifies itself that way in a "
            "release filed with the SEC and reports total revenues, Adjusted "
            "EBITDA and net earnings per diluted common share as its measures, "
            "management stating it is focused on driving performance at every "
            "level. what was looked for and NOT found: no filing states an "
            "objective of maximising profit, and the Business and Strategy "
            "sections of the 10-K read carry no objective sentence at all. this "
            "is the weakest of the four answers here and is marked as the closest "
            "readable thing to the rival's own assumption rather than as that "
            "assumption itself"),
    },
    "amtrak_everyday_discounts": {
        "seller": "a national rail carrier a statute directs to operate for profit",
        "zero_pairs": 6,
        "market_power": c(HOLDS, "granted on the rival's own definition, which "
                                 "names age and student status among the "
                                 "characteristics third degree prices on"),
        "segmentation": c(HOLDS, "the page prices six named classes under one "
                                 "heading with three different figures"),
        "no_arbitrage": c(HOLDS, "a ticket is issued to a named passenger and "
                                 "inspected on board"),
        "profit_maximisation": c(HOLDS,
            "49 U.S.C. 24301(a)(2): the carrier shall be operated and managed as "
            "a for-profit corporation. (a)(3): it is not a department, agency, or "
            "instrumentality of the United States Government. this section "
            "imposes no route or service obligation and (g) preempts state law on "
            "rates, routes and service. a statutory command to operate for profit "
            "is a harder document than an exchange listing. what was NOT looked "
            "at: whether any appropriations legislation attaches fare conditions "
            "to these particular classes"),
    },
    "sg_emergency_rule": {
        "seller": "a national health ministry, in the one context its own rule "
                  "bans the distinction",
        "zero_pairs": 3,
        "market_power": c(HOLDS, "a national hospital system"),
        "segmentation": c(HOLDS, "the same announcement prints the three statuses "
                                 "with different subsidies in five other rows"),
        "no_arbitrage": c(HOLDS, "treatment is delivered to a named patient"),
        "profit_maximisation": c(FAILS,
            "a health ministry setting subsidy rates does not maximise profit, and "
            "in this context it is not setting a price at all: the announcement "
            "says emergency department fees will not discriminate between "
            "nationality or citizenship. a prediction about how a profit-maximising "
            "firm prices has no referent here, and this zero is the clearest case "
            "on the board of one that belongs to neither account: the seller did "
            "not choose it and its credentials did not force it, a published rule "
            "bans the line"),
    },
    "jp_health_insurance_art74": {
        "seller": "a statute", "zero_pairs": 1,
        "market_power": c(FAILS, "there is no firm. the article sets the patient "
                                 "share of a fee computed under another article, "
                                 "for every insurer in the country"),
        "segmentation": c(HOLDS, "the article partitions by age and by a "
                                 "cabinet-order income threshold"),
        "no_arbitrage": c(HOLDS, "the share follows the patient, not the treatment"),
        "profit_maximisation": c(FAILS, "a statute does not maximise profit"),
    },
}

CONDITIONS = ("market_power", "segmentation", "no_arbitrage", "profit_maximisation")
FEASIBILITY = CONDITIONS[:3]

# What this project has read the rival on, and what it has not.
COVERAGE = {
    "feasibility_i_market_power": "screened here, per carrier",
    "feasibility_ii_segmentation": "screened here, per carrier, and every carrier "
                                   "stands on its own published page",
    "feasibility_iii_no_arbitrage": "screened here, per carrier",
    "first_degree": "no reading. this project has scored nothing against it",
    "second_degree": "no reading. the premises are located (the utility form, "
                     "single crossing, the IC argmax, and the local IC line "
                     "integral) but no quantity has been scored",
    "third_degree": "three readings: B56-5 on the inverse elasticity point "
                    "prediction, B57-6 with B57-11 on the cost argument, and "
                    "B57-12 on the cost defence, read against the credentials "
                    "the sellers issue rather than argued",
    "third_degree_foc": "B56-5. 3 operators read, 0 hit it",
    "second_degree_local_ic": "located, not scored. the line integral is path "
                              "independent for free when the type is one "
                              "dimensional, which is where the standard model "
                              "avoids the question rather than answering it",
    "multidimensional": "introduction read, body not read. the map from that "
                        "integrability condition to this framework's D has not "
                        "been written, and is registered as not done",
}


def verdict(row):
    """Five states, and two of them are not verdicts (11c).

    An unchecked yes on a feasibility condition is the direction that favours
    this project, because a carrier is only admissible against the rival when
    the rival's conditions hold there. So an unchecked holds does not buy
    admissibility, exactly as B51's unchecked yes did not buy a carrier.
    """
    feas = [row[k]["answer"] for k in FEASIBILITY]
    if FAILS in feas:
        return "inadmissible", "a feasibility condition the rival itself states fails"
    pm = row["profit_maximisation"]
    if pm["answer"] == FAILS:
        return "inadmissible", ("feasibility holds, but both scored predictions "
                                "need profit maximisation and it does not apply")
    if OPEN in feas:
        return "undetermined", "a feasibility condition is not established"
    if any(not row[k]["checked"] for k in FEASIBILITY):
        return "undetermined", ("a feasibility condition is a yes with nothing "
                                "behind it, and an unchecked yes here would be "
                                "this project writing itself strong")
    if pm["answer"] == CONTESTED:
        return "admissible_objective_contested", (
            "the three feasibility conditions hold; a named document constrains "
            "the seller's objective, and both scored predictions need it")
    if pm["answer"] == OPEN:
        return "admissible_objective_open", (
            "the three feasibility conditions hold; the seller's objective is "
            "not established either way and no document speaks against it")
    return "admissible", "all four hold"


def main():
    rows, crit, KIND = {}, {}, {}
    for name, row in sorted(CARRIERS.items()):
        v, why = verdict(row)
        rows[name] = {"seller": row["seller"], "zero_pairs": row["zero_pairs"],
                      "verdict": v, "why": why,
                      "conditions": {k: row[k] for k in CONDITIONS}}

    # B58-1 premise. Every element of the rival carries where it was read.
    nosrc = [k for k, v in RIVAL.items() if not v.get("source")]
    crit["B58-1"] = {"passed": not nosrc, "kind": "premise",
        "name": "every element of the rival's construction carries the source it "
                "was read from, so nothing in it is this project's paraphrase",
        "detail": "%d elements, %d without a source" % (len(RIVAL), len(nosrc))}

    # B58-2 instrument. The map is printed and the undetermined cell maps to no
    # verdict. This is 11c, and 11c's own third clause: check the mapping, not
    # only the buckets.
    vmap = {
        "a feasibility condition fails": "inadmissible",
        "profit maximisation fails": "inadmissible",
        "a feasibility condition not established": "undetermined",
        "a feasibility condition is an unchecked yes": "undetermined",
        "feasibility holds and checked, objective contested":
            "admissible_objective_contested",
        "feasibility holds and checked, objective open":
            "admissible_objective_open",
        "all four hold": "admissible",
    }
    ADMIT = ("admissible", "admissible_objective_open",
             "admissible_objective_contested")
    leaked = [k for k, r in rows.items() if r["verdict"] in ADMIT
              and any(r["conditions"][c]["answer"] == OPEN
                      or not r["conditions"][c]["checked"] for c in FEASIBILITY)]
    unchecked = sorted(k for k, r in rows.items()
                       if any(not r["conditions"][c]["checked"] for c in CONDITIONS))
    crit["B58-2"] = {"passed": not leaked, "kind": "instrument",
        "name": "the cell to verdict map is written out, and a carrier with an "
                "unestablished feasibility condition never lands on a verdict",
        "detail": "%d cells printed; %d carriers leaked an unestablished or "
                  "unchecked feasibility answer into an admitting verdict; "
                  "%d carriers carry at least one unchecked answer: %s"
                  % (len(vmap), len(leaked), len(unchecked),
                     ", ".join(unchecked) or "none"),
        "map": vmap}

    # B58-3 own reading. Print the object: every carrier, every condition.
    crit["B58-3"] = {"passed": True, "kind": "own_reading",
        "name": "print the object: every carrier, its four answers, whether each "
                "stands on a document, and its verdict",
        "detail": "; ".join("%s %s (%d zero pairs)" % (k, r["verdict"],
                                                       r["zero_pairs"])
                            for k, r in sorted(rows.items()))}

    # B58-4 own reading. The partition of B57-11's 29 zero pairs. This station
    # does not re-judge them; B57-11 keeps its verdict. What is added is that a
    # headline number now cannot be carried without the screen behind it.
    by_verdict = {}
    for k, r in rows.items():
        by_verdict.setdefault(r["verdict"], {"pairs": 0, "rows": []})
        by_verdict[r["verdict"]]["pairs"] += r["zero_pairs"]
        by_verdict[r["verdict"]]["rows"].append(k)
    total = sum(r["zero_pairs"] for r in rows.values())
    crit["B58-4"] = {"passed": True, "kind": "own_reading",
        "name": "B57-11's zero pairs partitioned by whether the rival's own "
                "conditions admit the carrier they sit on",
        "detail": "%d zero pairs; " % total + "; ".join(
            "%s %d (%s)" % (v, d["pairs"], ", ".join(sorted(d["rows"])))
            for v, d in sorted(by_verdict.items())),
        "note": "B57-11 keeps its verdict. this is a partition of its inputs, "
                "not a re-judging of its output"}

    # B58-5 bookkeeping. What the rival has been read on and what it has not.
    unread = [k for k, v in COVERAGE.items() if v.startswith("no reading")]
    crit["B58-5"] = {"passed": True, "kind": "bookkeeping",
        "name": "coverage: which parts of the rival carry a reading and which "
                "carry none, named rather than left to be inferred",
        "detail": "%d elements of the rival, %d mapped here, %d with no reading "
                  "at all: %s" % (len(RIVAL), len(COVERAGE), len(unread),
                                  ", ".join(sorted(unread)))}

    for k, v in crit.items():
        KIND[k] = v["kind"]

    out = {"stage": "B58",
           "config": {"carriers": len(CARRIERS), "zero_pairs_screened": total,
                      "source_of_zero_pairs": "B57-11",
                      "fourth_requirement": PROFIT_MAX},
           "rival": RIVAL, "coverage": COVERAGE, "carriers": rows,
           "criteria": [{"name": k, "passed": v["passed"], "kind": v["kind"],
                         "criterion": v["name"], "detail": v["detail"]}
                        for k, v in sorted(crit.items())]}
    dest = Path(__file__).resolve().parents[1] / "results" / "b58_rival_admissibility.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    print("=== the fourth requirement, which is not on the rival's own list")
    print("    " + PROFIT_MAX)
    print()
    print("=== carriers")
    print("    %-30s %-28s %6s  %s" % ("carrier", "verdict", "zero", "seller"))
    for k, r in sorted(rows.items(), key=lambda x: (x[1]["verdict"], x[0])):
        print("    %-30s %-28s %6d  %s"
              % (k, r["verdict"], r["zero_pairs"], r["seller"]))
    print()
    print("=== B57-11's zero pairs by admissibility")
    for v, d in sorted(by_verdict.items()):
        print("    %-28s %3d pairs   %s" % (v, d["pairs"], ", ".join(sorted(d["rows"]))))
    print("    %-28s %3d pairs" % ("total", total))
    print()
    for k, v in sorted(crit.items()):
        print("%-8s %s  %-13s %s" % (k, "PASS" if v["passed"] else "FAIL",
                                     v["kind"], v["detail"]))
    print("wrote b58_rival_admissibility.json")


if __name__ == "__main__":
    main()
