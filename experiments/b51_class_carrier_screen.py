"""B51: the screen that decides where a class difference can be read at all.

B49 counted how many of eight energy products can carry a class difference and
got two. That count came from a rule, not from the energy sector: a difference
between two classes is only readable where the holder of the cheaper price
cannot pass it to the holder of the dearer one. This file writes the rule out in
full, applies it to carriers outside energy, and checks it against the one set of
answers already on disk.

The screen is four questions, asked in order. The first is new here.

  Q0  one commodity.   Are the two classes buying the same thing?
  Q1  no transfer.     Can the holder pass it to the other class cheaply?
  Q2  two posted prices. Does each class have a published price?
  Q3  imposed split.   Is the division set by a third party rather than chosen
                       by the parties?

Q0 was implicit in Q1 all along and never written down. "The two prices cannot
be arbitraged against each other" presupposes that they are two prices of one
thing. Written out, it removes fixed broadband and cable television, where the
business package carries a service level, a static address and symmetric
capacity, so the gap between the two prices contains product specification. One
kilowatt hour is one kilowatt hour, and that is why electricity survives.

Q1 has two sources, and only the first has ever been used here.

  A  the commodity cannot be transferred. It arrives over a fixed network and
     nothing moves past the meter.
  B  the eligibility cannot be transferred. The commodity moves freely, and
     identity is checked at the point of consumption.

Source B covers tuition at a resident against a non-resident rate, named
concession fares, and resident admission pricing. It is a larger family than
source A, and it was out of view because Q1 was read as a rule about commodities
when it is a rule about whether a channel exists between two classes.

Criteria:

  B51-1  the screen passes electricity and piped gas, the two carriers already
         read. Failing either means the screen is wrong.
  B51-2  the screen's Q2 answer for each of the eight energy products agrees,
         product by product, with whether that product has any paired cell in
         the B49 record. The screen reads a rule; the record counts rows. Two
         independent paths to the same eight answers.
  B51-3  every candidate carries an answer to all four questions, and every
         answer carries a ground.
  B51-4  every candidate that does not pass names which questions it failed,
         rather than only that it failed.

Answers whose ground has not been checked against a source are marked
unverified. An unverified answer is neither a pass nor a failure: it is the third
state, and B51-3 counts it as present rather than as settled.

Run:

    python experiments\\b51_class_carrier_screen.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
B49 = ROOT / "results" / "b49_energy_class_square.json"
OUT = ROOT / "results" / "b51_class_carrier_screen.json"

QUESTIONS = ["Q0_one_commodity", "Q1_no_transfer", "Q2_two_posted_prices",
             "Q3_imposed_split"]

# yes / no / unverified for each question, each with the ground it rests on.
# "checked" means the ground was read against a source; "unverified" means it
# was not, and the answer is carried without being settled.
Y = "yes"
N = "no"
U = "unverified"


def c(answer, ground):
    return {"answer": answer, "ground": ground, "checked": True}


def u(answer, ground):
    return {"answer": answer, "ground": ground, "checked": False}


CANDIDATES = {
    # ---- energy, the eight products B49 already counted --------------------
    "electricity": {
        "family": "A: commodity cannot be transferred",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "one kilowatt hour is one kilowatt hour; the "
                                 "two classes take delivery of the same good"),
        "Q1_no_transfer": c(Y, "delivered over a fixed network and the "
                               "connection point defines the class; nothing "
                               "moves past the meter"),
        "Q2_two_posted_prices": c(Y, "residential and industrial prices both "
                                     "published per country and year"),
        "Q3_imposed_split": c(Y, "connection voltage, metering and eligibility "
                                 "are set by regulation, not chosen"),
    },
    "piped_natural_gas": {
        "family": "A: commodity cannot be transferred",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same molecule, same pipe"),
        "Q1_no_transfer": c(Y, "delivered over a fixed network; nothing moves "
                               "past the meter"),
        "Q2_two_posted_prices": c(Y, "residential and industrial prices both "
                                     "published"),
        "Q3_imposed_split": c(Y, "connection and eligibility set by regulation"),
    },
    "light_fuel_oil": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same distillate"),
        "Q1_no_transfer": c(N, "travels in drums and tanks; a holder can pass "
                               "it on, so a gap between two buyer classes is "
                               "carriage and handling"),
        "Q2_two_posted_prices": c(Y, "industry and residential prices both "
                                     "published"),
        "Q3_imposed_split": u(U, "not reached: Q1 already fails"),
    },
    "lpg": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same gas"),
        "Q1_no_transfer": c(N, "bottled; a bottle can be carried"),
        "Q2_two_posted_prices": c(Y, "industry, residential and transport "
                                     "prices published"),
        "Q3_imposed_split": u(U, "not reached: Q1 already fails"),
    },
    "fuel_oil": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same residual fuel"),
        "Q1_no_transfer": c(N, "shipped in tanks and wagons"),
        "Q2_two_posted_prices": c(Y, "generation and industry prices published"),
        "Q3_imposed_split": u(U, "not reached: Q1 already fails"),
    },
    "steam_coal": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same coal"),
        "Q1_no_transfer": c(N, "moved in wagons and holds"),
        "Q2_two_posted_prices": c(Y, "generation, industry and residential "
                                     "prices published"),
        "Q3_imposed_split": u(U, "not reached: Q1 already fails"),
    },
    "gasoline": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same fuel at the same pump"),
        "Q1_no_transfer": c(N, "anyone can buy it and carry it away"),
        "Q2_two_posted_prices": c(N, "one class only: it exists in the "
                                     "transport sector and nowhere else, so "
                                     "there is one price and nothing to compare"),
        "Q3_imposed_split": u(U, "not reached: Q1 and Q2 already fail"),
    },
    "automotive_diesel": {
        "family": "none",
        "sector": "energy",
        "Q0_one_commodity": c(Y, "same fuel at the same pump"),
        "Q1_no_transfer": c(N, "anyone can buy it and carry it away"),
        "Q2_two_posted_prices": c(N, "one class only, as with gasoline"),
        "Q3_imposed_split": u(U, "not reached: Q1 and Q2 already fail"),
    },
    # ---- family A outside energy ------------------------------------------
    "piped_water": {
        "family": "A: commodity cannot be transferred",
        "sector": "utilities",
        "Q0_one_commodity": c(Y, "one cubic metre of the same supply"),
        "Q1_no_transfer": c(Y, "delivered over a fixed network; nothing moves "
                               "past the meter"),
        "Q2_two_posted_prices": u(Y, "household and commercial tariffs are "
                                     "published by regulators, but no "
                                     "cross-country source has been opened yet"),
        "Q3_imposed_split": u(Y, "connection and category set by the utility "
                                 "under regulation; not read against a rule "
                                 "book yet"),
    },
    "sewerage": {
        "family": "A: commodity cannot be transferred",
        "sector": "utilities",
        "Q0_one_commodity": c(Y, "the same disposal service per cubic metre"),
        "Q1_no_transfer": c(Y, "delivered over a fixed network"),
        "Q2_two_posted_prices": u(Y, "published alongside water tariffs; no "
                                     "cross-country source opened yet"),
        "Q3_imposed_split": u(Y, "as with water; not read against a rule book"),
    },
    "district_heating": {
        "family": "A: commodity cannot be transferred",
        "sector": "utilities",
        "Q0_one_commodity": c(Y, "one gigajoule of heat from the same network"),
        "Q1_no_transfer": c(Y, "delivered over a fixed network; heat cannot be "
                               "resold past the substation"),
        "Q2_two_posted_prices": u(U, "household prices are published in several "
                                     "countries; whether a separate "
                                     "non-household price is published has not "
                                     "been checked"),
        "Q3_imposed_split": u(Y, "connection is physical and not chosen"),
    },
    "fixed_broadband": {
        "family": "none",
        "sector": "utilities",
        "Q0_one_commodity": c(N, "the business package carries a service level, "
                                 "a static address and symmetric capacity, so "
                                 "the two classes are not buying one thing and "
                                 "the gap contains product specification"),
        "Q1_no_transfer": u(U, "not reached: Q0 already fails"),
        "Q2_two_posted_prices": c(Y, "residential and business tariffs both "
                                     "published"),
        "Q3_imposed_split": c(N, "the operator defines the two packages, so the "
                                 "split is chosen rather than imposed"),
    },
    "cable_television": {
        "family": "none",
        "sector": "utilities",
        "Q0_one_commodity": c(N, "commercial packages carry different rights "
                                 "and channel sets"),
        "Q1_no_transfer": u(U, "not reached: Q0 already fails"),
        "Q2_two_posted_prices": c(Y, "both published"),
        "Q3_imposed_split": c(N, "the operator defines the packages"),
    },
    # ---- family B, never used here before ---------------------------------
    "tuition_resident_rate": {
        "family": "B: eligibility cannot be transferred",
        "sector": "education",
        "Q0_one_commodity": c(Y, "the same course and the same degree, taught "
                                 "in the same room in the same term"),
        "Q1_no_transfer": c(Y, "a place cannot be handed on: residency is "
                               "checked at enrolment and the seat is named"),
        "Q2_two_posted_prices": c(Y, "settled by B53: 5,605 published "
                                     "schedules over 56 states from one "
                                     "cross-institution source, each printing "
                                     "in-district, in-state and out-of-state"),
        "Q3_imposed_split": c(Y, "settled by B53 by measurement rather than "
                                 "by reading one statute: private schedules "
                                 "write one value 3,424 times in 3,439, public "
                                 "ones write two or three 1,973 times in "
                                 "2,166, so the split is not the seller's to "
                                 "choose"),
    },
    "named_concession_fare": {
        "family": "B: eligibility cannot be transferred",
        "sector": "transport",
        "Q0_one_commodity": c(Y, "the same seat on the same train"),
        "Q1_no_transfer": c(Y, "the ticket is named and the eligibility is "
                               "checked on board"),
        "Q2_two_posted_prices": u(Y, "fare tables publish the full and the "
                                     "concession rate; no cross-country source "
                                     "opened yet"),
        "Q3_imposed_split": u(Y, "age or student status, set outside the "
                                 "transaction; the rule has not been read"),
    },
    "resident_admission_price": {
        "family": "B: eligibility cannot be transferred",
        "sector": "culture",
        "Q0_one_commodity": c(Y, "the same exhibition on the same day"),
        "Q1_no_transfer": c(Y, "proof of residence is checked at entry"),
        "Q2_two_posted_prices": u(Y, "both prices are posted at the door; no "
                                     "systematic source opened yet"),
        "Q3_imposed_split": u(U, "residence is a legal status, but the operator "
                                 "chooses whether to offer the split at all, "
                                 "so this may fail the second clause"),
    },
    "prescription_copayment": {
        "family": "B: eligibility cannot be transferred",
        "sector": "health",
        "Q0_one_commodity": c(Y, "the same molecule at the same dose"),
        "Q1_no_transfer": c(Y, "the prescription is named"),
        "Q2_two_posted_prices": u(U, "what is published may be a reimbursement "
                                     "rate rather than a price, which would "
                                     "make the two numbers incommensurable"),
        "Q3_imposed_split": u(Y, "eligibility is set by statute"),
    },
}


# Carriers whose class difference has been measured on a station of its own.
# electricity and piped natural gas by B49 and B52, resident tuition by B53.
KNOWN_CARRIERS = ("electricity", "piped_natural_gas", "tuition_resident_rate")


def verdict(cand: dict) -> dict:
    """Three states, and an unchecked answer is the middle one.

    A "yes" whose ground was never read against a source is not a yes. Reading
    it as one is the same error as reading an undecidable measurement as a
    pass: the boxes are drawn correctly and the mapping from box to verdict is
    written one notch too strong. So an unchecked answer leaves the candidate
    open, whatever it says, and only a checked failure closes it.
    """
    failed = [q for q in QUESTIONS
              if cand[q]["answer"] == N and cand[q].get("checked")]
    if failed:
        unset = [q for q in QUESTIONS if cand[q]["answer"] == U
                 or not cand[q].get("checked")]
        return {"verdict": "does not carry a class difference",
                "failed_questions": failed,
                "unresolved_questions": [q for q in unset if q not in failed]}
    unset = [q for q in QUESTIONS
             if cand[q]["answer"] == U or not cand[q].get("checked")]
    if unset:
        return {"verdict": "not settled: an answer is still open",
                "failed_questions": [], "unresolved_questions": unset}
    return {"verdict": "carries a class difference",
            "failed_questions": [], "unresolved_questions": []}


def main() -> int:
    if not B49.exists():
        raise SystemExit("the energy count this run checks against is not on "
                         "disk: %s" % B49)
    b49 = json.loads(B49.read_text(encoding="utf-8"))
    paired = {p: g["paired_cells"] for p, g in b49["product_grid"].items()}
    # the screen's own names against the codes that record uses
    CODE = {"electricity": "ELECTR", "piped_natural_gas": "NATGAS",
            "light_fuel_oil": "KEROSENE", "lpg": "LPG", "fuel_oil": "RESFUEL",
            "steam_coal": "COAL", "gasoline": "GASOLINE",
            "automotive_diesel": "DIESEL"}

    rec: dict = {
        "stage": "B51",
        "config": {
            "questions": QUESTIONS,
            "checked_against": str(B49.relative_to(ROOT)).replace("\\", "/"),
            "families": {
                "A": "the commodity cannot be transferred",
                "B": "the eligibility cannot be transferred",
            },
        },
        "candidates": {},
    }

    print("B51  the screen, candidate by candidate")
    print("  a bare letter is an answer read against a source; a trailing ? is "
          "an answer carried without one")
    print("  %-26s %-11s %-4s %-4s %-4s %-4s  %s"
          % ("candidate", "family", "Q0", "Q1", "Q2", "Q3", "verdict"))
    passes, fails, open_ = [], [], []
    for name in sorted(CANDIDATES):
        cand = CANDIDATES[name]
        v = verdict(cand)
        rec["candidates"][name] = dict(cand)
        rec["candidates"][name].update(v)
        short = {"carries a class difference": "carries",
                 "does not carry a class difference": "fails " + ",".join(
                     q.split("_")[0] for q in v["failed_questions"]),
                 }.get(v["verdict"], "open: " + ",".join(
                     q.split("_")[0] for q in v["unresolved_questions"]))
        def mark(q):
            a = cand[q]["answer"]
            if a == U:
                return "-"
            return a[:1] if cand[q].get("checked") else a[:1] + "?"
        print("  %-26s %-11s %-4s %-4s %-4s %-4s  %s"
              % (name, cand["family"][:1] if cand["family"] != "none" else "-",
                 mark("Q0_one_commodity"), mark("Q1_no_transfer"),
                 mark("Q2_two_posted_prices"), mark("Q3_imposed_split"), short))
        (passes if v["verdict"].startswith("carries")
         else fails if v["verdict"].startswith("does not")
         else open_).append(name)

    rec["summary"] = {"carries": passes, "fails": fails, "open": open_}
    print("\n  carries: %d   fails: %d   open: %d"
          % (len(passes), len(fails), len(open_)))
    print("  carries -> %s" % ", ".join(passes))
    print("  open    -> %s" % ", ".join(open_))

    # ---- B51-2: the screen's Q2 against the record's paired-cell counts -----
    print("\nB51-2  the screen's Q2 against the paired-cell counts already on disk")
    agree, disagree = [], []
    for name, code in sorted(CODE.items()):
        screen = CANDIDATES[name]["Q2_two_posted_prices"]["answer"] == Y
        record = paired[code] > 0
        ok = screen == record
        (agree if ok else disagree).append(name)
        print("  %-26s screen says %-3s   record has %5d paired cells -> %-3s   %s"
              % (name, "yes" if screen else "no", paired[code],
                 "yes" if record else "no", "agree" if ok else "DISAGREE"))
    rec["q2_against_record"] = {"agree": agree, "disagree": disagree,
                                "paired_cells": paired}

    grounds_present = all(
        all(q in c and c[q].get("ground") for q in QUESTIONS)
        for c in CANDIDATES.values())
    named = all(rec["candidates"][n]["failed_questions"] for n in fails)

    rec["criteria"] = {
        # The known-answer set grows as carriers are measured. It held two when
        # this station first ran; B53 measured resident tuition, so it holds
        # three. Widening it cannot make the check easier: every carrier in it
        # is one the screen has to pass.
        "B51-1": {
            "kind": "known_answer",
            "name": "the screen passes every carrier whose class difference "
                    "has been measured",
            "passed": all(n in passes for n in KNOWN_CARRIERS),
            "detail": "; ".join(
                "%s: %s" % (n, rec["candidates"][n]["verdict"])
                for n in KNOWN_CARRIERS),
        },
        "B51-2": {
            "kind": "known_answer",
            "name": "the screen's Q2 answer agrees with the paired-cell count "
                    "in the record, product by product: a rule read against "
                    "rows counted",
            "passed": not disagree,
            "detail": "%d of %d agree%s"
                      % (len(agree), len(CODE),
                         "" if not disagree else "; disagree: "
                         + ", ".join(disagree)),
        },
        "B51-3": {
            "kind": "bookkeeping",
            "name": "every candidate answers all four questions and every "
                    "answer carries a ground",
            "passed": grounds_present,
            "detail": "%d candidates, %d questions each"
                      % (len(CANDIDATES), len(QUESTIONS)),
        },
        "B51-4": {
            "kind": "bookkeeping",
            "name": "every candidate that does not pass names which questions "
                    "it failed",
            "passed": named,
            "detail": "; ".join(
                "%s fails %s" % (n, ",".join(
                    q.split("_")[0] for q in
                    rec["candidates"][n]["failed_questions"]))
                for n in fails) or "none fail",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\nwritten: %s" % OUT)
    for name in sorted(rec["criteria"]):
        c_ = rec["criteria"][name]
        print("  %-7s %-4s %s" % (name, "PASS" if c_["passed"] else "FAIL",
                                  c_["detail"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
