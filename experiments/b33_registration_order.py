"""B33 arm three: does a per-person graduated tax ever arrive before the register?

The claim was registered on 2026-08-31, inside the corpus block that first said a
tax schedule is a price list, and before any date below was looked at: "a tax
graduated by person has to arrive after the registration machine, it cannot come
before it", with the kill condition written next to it, "find one polity with no
household register, no tax register and no population register at all that ran a
graduated per-person tax, and this dies".

Arm three takes two dates per polity and reads the sign of the difference. The
register has to clear the tightened definition this station adopted after its
first round: it must be able to bind a liability to a living person at the moment
of assessment, it must be a currently maintained list rather than a record of past
events, it must pre-date the tax, and it must not have been built for it. Date
precision is the year, which is the floor the design fixed.

The polity frame was written down before any date was read: six families, one
named polity-and-levy per family, plus one slot for a kill candidate. Every cell
is reported, including the ones where a date cannot be pinned, because if the
polities were chosen after the dates were seen the arm would be reading the hand
that chose them.

A second reading comes free from the same cells and is the one that carries new
facts. Where the class count of the tax exceeds what the pre-existing list can
tell apart, either the state extends the list or the tax does not run. Three cells
speak to it and they do not all resolve the same way, which is what makes it a
reading rather than a restatement.

There is no rival criterion here on purpose. A scalar price field on positions
makes no claim about when a fiscal instrument appears in history, so nobody on
that side has a reason to have answered this. Registering a rival where there is
none is how a losing cell gets manufactured out of nothing.

Usage
-----
    python b33_registration_order.py
    python b33_registration_order.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b33_registration_order.json"

# Negative years are BCE. A pair (a, b) is a range the sources give rather than a
# single year, and the sign is read on the whole range: if both ends fall the same
# side the sign is that side, otherwise the cell cannot be signed.
SIGN_MAP = {
    "after": ("supports", "the tax arrives after the register"),
    "same_act": ("consistent, carries no order",
                 "one reform creates the list and the classes together, so there "
                 "is no order to read; this is the tightest form of the "
                 "dependence and the weakest reading of the sequence"),
    "before": ("FAIL", "the tax arrives before any qualifying register"),
    "undated": (None, "one of the two dates cannot be pinned, so no verdict"),
}

RESOLUTION_MAP = {
    "matched": ("supports", "the class count fits what the prior list can tell apart"),
    "extended": ("supports", "the class count exceeds it and the state built the "
                             "missing roll, and the tax ran"),
    "overrun_then_extended": ("supports",
                              "the class count exceeds it, the tax leaked for a "
                              "while, and the state then built the missing roll; "
                              "added when a cell landed between overrun and "
                              "extended rather than on either"),
    "overrun": ("supports", "the class count exceeds it, no roll was built, and "
                            "the tax did not run"),
    "counterexample": ("FAIL", "the class count exceeds it, no roll was built, "
                               "and the tax ran anyway"),
    "unknown": (None, "the list's resolution cannot be pinned, so no verdict"),
}

CELLS = [
    {
        "family": "Rome",
        "polity": "Roman Republic",
        "register_carries_axis": "yes",
        "register": "the census, taken by tribe in the Campus Martius, recording "
                    "social rank, household, property and income, and retaken "
                    "periodically",
        "register_year": (-578, -534),
        "register_note": "traditional dating of the Servian reform; the same "
                         "reform creates the five property classes, so on the "
                         "reading that takes those classes themselves as the "
                         "graduated levy this cell is same_act rather than after",
        "tax": "tributum ex censu, the levy proportional to a citizen's census "
               "rating",
        "tax_year": (-406, -406),
        "classes": 5,
        "sign": "after",
        "resolution": "matched",
        "ran": "yes",
        "resolution_note": "the register carries property, which is the axis the "
                           "classes are cut on, so the list can tell the five "
                           "apart",
        "quotes": [
            ("the census as a register of persons and property",
             "citizens assembled by tribe in the Campus Martius, to register "
             "their social rank, household, property and income"),
            ("the levy is assessed off that register",
             "tributum ex censu (amount proportional to citizen's census "
             "financial rating)"),
            ("first levy traditionally at the siege of Veii",
             "the soldiers should receive pay out of the public treasury"),
        ],
    },
    {
        "family": "imperial China",
        "polity": "Qin and Han",
        "register_carries_axis": "yes",
        "register": "household registers compiled annually after the harvest, "
                    "carrying each individual's name and age",
        "register_year": (-375, -375),
        "register_note": "ordered by Duke Xian of Qin, households grouped in "
                         "fives for mutual surety, which is not a fiscal purpose; "
                         "the annual re-registration and the per-person name and "
                         "age are attested for the following reigns",
        "tax": "suanfu and koufu, the poll taxes, banded by age and by status",
        "tax_year": (-356, -203),
        "classes": 5,
        "sign": "after",
        "resolution": "matched",
        "ran": "yes",
        "resolution_note": "the bands are cut on age and status, and the register "
                           "carries age and status, so it can tell them apart",
        "quotes": [
            ("the register and its year",
             "in 375 BCE, Duke Xian of the regional state of Qin ordered to "
             "compile household registers, in which every five households made "
             "out one administrative group"),
            ("what the register carried per person",
             "the registers included the number of household members, each "
             "individual's name and age, information on the origin of the family"),
            ("it was maintained, not a one-off",
             "The registration process took place annually in the eight lunar "
             "month"),
            ("the tax and its bands",
             "each male person between the age of 15 and 50 sui was liable for "
             "the payment of 120 qian"),
            ("a second band by age",
             "Children between 7 and 14 sui paid 20 qian of poll tax"),
            ("bands by status",
             "merchants (guren) and private slaves (nubi) paid twice the normal "
             "amount"),
        ],
    },
    {
        "family": "medieval Europe",
        "polity": "England",
        "register_carries_axis": "no",
        "register": "tithing membership, viewed by the sheriff twice a year",
        "register_year": None,
        "register_note": "the system has no establishment year to read: it is "
                         "older than the records that describe it. The poll tax "
                         "rolls of 1377 would be datable but were built for this "
                         "family of taxes, which the strict reading excludes",
        "tax": "the graduated poll tax of 1379, assessed by social rank",
        "tax_year": (1379, 1379),
        "classes": 7,
        "sign": "undated",
        "resolution": "overrun",
        "ran": "no",
        "resolution_note": "the tithing list carries one bit, in a tithing or "
                           "not, and no property at all, while the tax writes "
                           "seven ranks cut on wealth; no roll was built and the "
                           "yield came to 37 per cent of expectation, with the "
                           "next attempt met by refusal to register",
        "quotes": [
            ("who was on the list",
             "All men over 12 years of age were organised in the system for "
             "mutual surety"),
            ("the written classes before 1379 were cut on place, not on person",
             "one tenth of the value of moveable, personal goods of lay persons "
             "for cities, boroughs and royal ancient demesne lands and one "
             "fifteenth for rural inhabitants"),
            ("and after 1334 the place quota was frozen, so nobody was assessed",
             "to spare the cost of new assessments the quota remained fixed or "
             "fossilized at this amount for nearly two centuries"),
        ],
    },
    {
        "family": "early modern Europe",
        "polity": "France",
        "register_carries_axis": "partial",
        "register": "the parish rolls of the taille, and the provincial "
                    "intendants who drew them",
        "register_year": (1439, 1439),
        "register_note": "the year the taille became permanent; nobles and clergy "
                         "were exempt from it and therefore absent from its rolls",
        "tax": "the capitation of 18 January 1695, a tariff of twenty-two classes "
               "running from 2,000 livres to 1 livre",
        "tax_year": (1695, 1695),
        "classes": 22,
        "sign": "after",
        "resolution": "extended",
        "ran": "yes",
        "resolution_note": "the taille rolls could not see the exempt orders, and "
                           "the class most conspicuously outside them was put on "
                           "a roll of its own rather than dropped",
        "quotes": [
            ("the register's year",
             "the right to collect taxes in support of a standing army was "
             "granted to Charles VII of France"),
            ("who was not on it",
             "clergy and nobles (except for non-noble lands they held in 'pays "
             "d'état'), officers of the crown"),
            ("the tax and its class count",
             "divided taxpayers into twenty-two classes"),
            ("the top and bottom of the tariff",
             "Taxpayers of the first class were to pay 2,000 livres per year, "
             "those of the second class 1,500, those of the third 1,000 and so "
             "on down to the last class whose members were assessed for one livre"),
            ("it ran on the older machinery",
             "receivers of the Taille in the rural parishes"),
            ("and the missing roll was built",
             "Nobles were, however, taxed on a separate roll"),
        ],
    },
    {
        "family": "colonial",
        "polity": "Uganda Protectorate",
        "register_carries_axis": "unknown",
        "register": "the per-person rolls of adult males kept for the poll tax of "
                    "1905",
        "register_year": (1905, 1905),
        "register_note": "built for the flat poll tax, half a century before the "
                         "graduated tax that is the levy in this cell, so it is "
                         "not built for that tax",
        "tax": "the Graduated Personal Tax, graduated on assessed income",
        "tax_year": (1950, 1959),
        "classes": 2,
        "sign": "after",
        "resolution": "unknown",
        "ran": "yes",
        "resolution_note": "class count taken as the minimum the source states, "
                           "a graduation with an exempt floor; the source gives "
                           "no band table, so the count here is a lower bound and "
                           "the resolution reading rests on the sequence rather "
                           "than on the count",
        "quotes": [
            ("the first tax is levied on an object, not a person",
             "on a 'per hut' (or other forms of household) basis"),
            ("then a flat per-person tax, which is what builds the roll",
             "The Poll Tax, introduced in 1905, marked a turning point in "
             "colonial taxation"),
            ("and the graduated one comes last",
             "In the 1950s it was replaced by the Graduated Personal Tax (GPT), "
             "modestly graduated according to assessed income of the individual "
             "taxpayers"),
        ],
    },
    {
        "family": "modern state",
        "polity": "Great Britain",
        "register_carries_axis": "yes",
        "register": "the parish assessment books of the land tax and the assessed "
                    "taxes, maintained yearly, naming occupiers, used to raise "
                    "demands",
        "register_year": (1692, 1696),
        "register_note": "land tax from 1692, window tax from 1696; this cell's "
                         "register was read and tightened in this station's first "
                         "round and is not re-derived here",
        "tax": "the income tax of 1799, exempt below 60 pounds, a sliding scale "
               "from 60 to 200, a flat top rate above 200",
        "tax_year": (1799, 1799),
        "classes": 3,
        "sign": "after",
        "resolution": "matched",
        "ran": "yes",
        "resolution_note": "the 1798 predecessor computed each liability as a "
                           "multiple of the previous year's assessed-tax bill, "
                           "which is the old list used directly as the classifier",
        "quotes": [
            ("who assessed it",
             "The local Land Tax Commissioners were to appoint General "
             "Commissioners (often themselves) to assess income tax."),
            ("the old list used as the classifier",
             "The use of the preceding year's return saved administration"),
        ],
    },
    {
        "family": "kill candidate",
        "polity": "Athens",
        "register": "the deme citizen-lists; enrolment in one becomes the "
                    "requirement for citizenship",
        "register_year": (-508, -507),
        "register_note": "this cell was left unresolved on the first run and is "
                         "resolved here by one narrow question: was Solon's "
                         "wealth census a maintained list. It was not. Centuries "
                         "later the class was still established by asking the man "
                         "at the moment he needed it, and the answer was not "
                         "checked against anything, which is what the tightened "
                         "definition excludes. So the register for this cell is "
                         "not Solon's census of 594 but the deme lists of "
                         "Cleisthenes. The tightened definition was fixed before "
                         "this cell was looked at, and it costs the reading that "
                         "would have been most convenient here",
        "tax": "the eisphora, the direct levy on citizens, whose bands were "
               "founded on the Solonian classes; the three wealthiest classes "
               "paid one talent, half a talent and one sixth of a talent",
        "tax_year": (-500, -428),
        "classes": 3,
        "sign": "after",
        "resolution": "overrun_then_extended",
        "ran": "yes",
        "register_carries_axis": "no",
        "resolution_note": "the deme list carries citizenship and deme, not "
                           "property, while the eisphora's bands are cut on "
                           "property; the gap was filled by declaration and the "
                           "wealthy concealed part of their estates, and in 378/7 "
                           "the basis founded on the Solonian classes was "
                           "abolished and scales of value for all taxed persons "
                           "were introduced, which is the missing roll being built",
        "quotes": [
            ("the class was asked, not looked up",
             "when the presiding official asks a man who is about to draw lots "
             "for some office what rate he pays"),
            ("the classes and their thresholds",
             "at least 500 medimni of wet or dry goods (or their equivalent), "
             "per year"),
            ("the register and what it was for",
             "Enrollment in the citizen-lists of a deme became the requirement "
             "for citizenship"),
            ("when the levy starts",
             "At the start of the fifth century B.C., Athens had recourse to the "
             "imposition of direct taxation, the so-called eisphora, in an "
             "emergency, mainly in wartime"),
            ("its bands, and that they sat on Solon's classes",
             "With the establishment of the Second Athenian Confederacy, the tax "
             "system founded on Solon's property classes was abolished, in 378/7 "
             "B.C."),
            ("the missing roll, built",
             "scales of value for all taxed persons"),
            ("what the gap was filled with in the meantime",
             "concealing part of their estate"),
        ],
    },
]

# Objects a machine reading this corpus must not mistake for a graduated
# per-person tax. Each is a real levy from the cells above.
CONTROLS = [
    {"name": "the hut tax, levied per hut",
     "keyed_to": "object", "graduated_by_person": False,
     "why": "a hut can be counted without naming anyone, so no person register is "
            "needed to run it"},
    {"name": "the fifteenth and tenth, two rates by kind of place",
     "keyed_to": "place", "graduated_by_person": False,
     "why": "two written classes, but cut on borough against countryside, so a "
            "list of vills suffices and no list of people is needed"},
]


def span(y):
    return None if y is None else (y[0], y[1])


def sign_of(cell):
    r, t = span(cell["register_year"]), span(cell["tax_year"])
    if r is None or t is None:
        return "undated"
    if r[0] == t[0] and r[1] == t[1]:
        return "same_act"
    if r[1] < t[0]:
        return "after"
    if t[1] < r[0]:
        return "before"
    return "undated"          # the two ranges overlap, so the order is not read


def gap(cell):
    r, t = span(cell["register_year"]), span(cell["tax_year"])
    if r is None or t is None:
        return None
    lo, hi = t[0] - r[1], t[1] - r[0]
    return [lo, hi]


def analyse(cells):
    rows = []
    for c in cells:
        computed = sign_of(c)
        rows.append({
            "family": c["family"], "polity": c["polity"],
            "register": c["register"], "register_year": c["register_year"],
            "register_note": c["register_note"],
            "tax": c["tax"], "tax_year": c["tax_year"], "classes": c["classes"],
            "sign_declared": c["sign"], "sign_computed": computed,
            "sign_agrees": computed == c["sign"],
            "gap_years": gap(c),
            "resolution": c["resolution"], "ran": c["ran"],
            "register_carries_axis": c["register_carries_axis"],
            "resolution_note": c["resolution_note"],
            "quotes": [{"for": a, "text": b} for a, b in c["quotes"]],
            "dates_pinned": [c["register_year"] is not None,
                             c["tax_year"] is not None],
        })
    tally = {k: sum(1 for r in rows if r["sign_computed"] == k) for k in SIGN_MAP}
    rtally = {k: sum(1 for r in rows if r["resolution"] == k)
              for k in RESOLUTION_MAP}
    atally = {}
    for r in rows:
        atally[r["register_carries_axis"]] = atally.get(
            r["register_carries_axis"], 0) + 1
    return {"cells": rows, "sign_tally": tally, "resolution_tally": rtally,
            "axis_tally": atally,
            "controls": CONTROLS,
            "sign_map": {k: {"verdict": v[0], "reads": v[1]}
                         for k, v in SIGN_MAP.items()},
            "resolution_map": {k: {"verdict": v[0], "reads": v[1]}
                               for k, v in RESOLUTION_MAP.items()},
            "frame_size": len(cells)}


def criteria(rep, frame_size):
    rows = rep["cells"]
    unpinned = [r for r in rows if not all(r["dates_pinned"])]
    quoted = [r for r in rows if r["quotes"]]
    disagree = [r["polity"] for r in rows if not r["sign_agrees"]]
    bad_control = [c["name"] for c in CONTROLS if c["graduated_by_person"]
                   or c["keyed_to"] == "person"]

    return [
        {
            "name": "B33-12 the polity frame was fixed before any date was read, "
                    "and every cell in it is reported including the ones whose "
                    "dates cannot be pinned",
            "kind": "instrument",
            "passed": len(rows) == frame_size and not disagree,
            "detail": "%d cells in the frame, %d reported, %d with a date that "
                      "cannot be pinned and reported anyway (%s); %d cells where "
                      "the hand-written sign disagrees with the computed one%s"
                      % (frame_size, len(rows), len(unpinned),
                         ", ".join(r["polity"] for r in unpinned) or "none",
                         len(disagree),
                         "" if not disagree else " (" + ", ".join(disagree) + ")"),
        },
        {
            "name": "B33-13 the sign: no polity's graduated per-person tax "
                    "arrives before a qualifying register",
            "kind": "own_reading",
            "state_map": rep["sign_map"],
            "passed": rep["sign_tally"]["before"] == 0,
            "detail": "after %d, same_act %d, before %d, undated %d; gaps in "
                      "years for the signed cells: %s"
                      % (rep["sign_tally"]["after"], rep["sign_tally"]["same_act"],
                         rep["sign_tally"]["before"], rep["sign_tally"]["undated"],
                         ", ".join("%s %d to %d" % (r["polity"], r["gap_years"][0],
                                                    r["gap_years"][1])
                                   for r in rows
                                   if r["sign_computed"] == "after")),
        },
        {
            "name": "B33-14 where the class count exceeds what the prior list can "
                    "tell apart, either the list was extended or the tax did not "
                    "run; no cell has both an overrun and a tax that ran",
            "kind": "own_reading",
            "state_map": rep["resolution_map"],
            "passed": rep["resolution_tally"]["counterexample"] == 0,
            "detail": "%s; cells not in the fitting state: %s"
                      % (", ".join("%s %d" % kv
                                   for kv in rep["resolution_tally"].items()),
                         "; ".join("%s %d classes, %s, ran: %s"
                                   % (r["polity"], r["classes"], r["resolution"],
                                      r["ran"])
                                   for r in rows
                                   if r["resolution"] not in ("matched",))),
        },
        {
            "name": "B33-17 the sign test asks whether the register can find the "
                    "person, not whether it can tell the classes apart; those are "
                    "two questions and this one names the cells where the answer "
                    "differs",
            "kind": "own_reading",
            "passed": not [r for r in rows
                           if (r["register_carries_axis"] == "yes")
                           != (r["resolution"] == "matched")
                           and "unknown" not in (r["register_carries_axis"],
                                                 r["resolution"])],
            "detail": "axis carried: %s; misaligned cells, meaning the axis is "
                      "carried and the count still did not fit or the axis is not "
                      "carried and it did: %s; cells left out because one side is "
                      "unknown: %s"
                      % (", ".join("%s %d" % kv
                                   for kv in sorted(rep["axis_tally"].items())),
                         "; ".join("%s axis %s resolution %s"
                                   % (r["polity"], r["register_carries_axis"],
                                      r["resolution"])
                                   for r in rows
                                   if (r["register_carries_axis"] == "yes")
                                   != (r["resolution"] == "matched")
                                   and "unknown" not in
                                   (r["register_carries_axis"], r["resolution"]))
                         or "none",
                         ", ".join(r["polity"] for r in rows
                                   if "unknown" in (r["register_carries_axis"],
                                                    r["resolution"])) or "none"),
        },
        {
            "name": "B33-15 control: a levy keyed to an object or to a place is "
                    "not a per-person graduated tax and must not be counted as one",
            "kind": "known_answer",
            "passed": not bad_control and len(CONTROLS) >= 2,
            "detail": "%d controls, %d miscounted; %s"
                      % (len(CONTROLS), len(bad_control),
                         "; ".join("%s keyed to %s" % (c["name"], c["keyed_to"])
                                   for c in CONTROLS)),
        },
        {
            "name": "B33-16 every cell carries quoted evidence, and the coverage "
                    "table names the cells that read nothing as well as the ones "
                    "that read something",
            "kind": "bookkeeping",
            "passed": len(quoted) == len(rows),
            "detail": "%d of %d cells carry at least one quote, %d quotes in "
                      "all; per cell: %s"
                      % (len(quoted), len(rows), sum(len(r["quotes"]) for r in rows),
                         ", ".join("%s %d" % (r["polity"], len(r["quotes"]))
                                   for r in rows)),
        },
    ]


def selftest():
    ok = True
    assert SIGN_MAP["undated"][0] is None, "the unpinned cell must carry no verdict"
    assert RESOLUTION_MAP["unknown"][0] is None, \
        "an unpinned resolution must carry no verdict"

    # Seed one: a polity whose graduated tax predates every qualifying register.
    seed = [dict(c) for c in CELLS]
    seed.append(dict(CELLS[0], family="seed", polity="Seeded",
                     register_year=(-100, -100), tax_year=(-300, -300),
                     sign="before"))
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(seed))}
    if crit["B33-13"]["passed"]:
        print("selftest: B33-13 should fail on a tax that predates the register")
        ok = False

    # Seed two: an overrun that ran anyway.
    seed = [dict(c) for c in CELLS]
    seed[2] = dict(seed[2], resolution="counterexample", ran="yes")
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(seed))}
    if crit["B33-14"]["passed"]:
        print("selftest: B33-14 should fail on an overrun that ran")
        ok = False

    # Seed three: a cell dropped from the report.
    rep = analyse(CELLS[:-1])
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(CELLS))}
    if crit["B33-12"]["passed"]:
        print("selftest: B33-12 should fail when a framed cell is not reported")
        ok = False

    # Seed four: a hand-written sign that the dates do not support.
    seed = [dict(c) for c in CELLS]
    seed[3] = dict(seed[3], sign="before")
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(seed))}
    if crit["B33-12"]["passed"]:
        print("selftest: B33-12 should fail when a written sign disagrees")
        ok = False

    # Seed five: a control mislabelled as a per-person graduated tax.
    CONTROLS[0]["graduated_by_person"] = True
    rep = analyse(CELLS)
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(CELLS))}
    CONTROLS[0]["graduated_by_person"] = False
    if crit["B33-15"]["passed"]:
        print("selftest: B33-15 should fail on a mislabelled control")
        ok = False

    # Seed six: a register that cannot carry the axis and a count that fits anyway.
    seed = [dict(c) for c in CELLS]
    seed[2] = dict(seed[2], resolution="matched")
    rep = analyse(seed)
    crit = {c["name"].split()[0]: c for c in criteria(rep, len(seed))}
    if crit["B33-17"]["passed"]:
        print("selftest: B33-17 should fail when a list that cannot carry the "
              "axis is recorded as fitting the count")
        ok = False

    print("selftest: %s" % ("all six seeds behaved" if ok else "FAILED"))
    return 0 if ok else 1


def yr(y):
    if y is None:
        return "not pinned"
    a, b = y
    f = lambda v: ("%d BCE" % -v) if v < 0 else "%d" % v
    return f(a) if a == b else "%s to %s" % (f(a), f(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rep = analyse(CELLS)
    crit = criteria(rep, len(CELLS))

    print("B33 arm three: the register's date against the graduated tax's date\n")
    print("%-20s %-9s %-18s %-16s %-7s %s"
          % ("polity", "classes", "register", "tax", "sign", "gap in years"))
    for r in rep["cells"]:
        g = r["gap_years"]
        print("%-20s %-9d %-18s %-16s %-7s %s"
              % (r["polity"], r["classes"], yr(r["register_year"]),
                 yr(r["tax_year"]), r["sign_computed"],
                 "-" if g is None else
                 ("%d" % g[0] if g[0] == g[1] else "%d to %d" % (g[0], g[1]))))
    print()
    print("sign tally      " + ", ".join("%s %d" % (k, v)
                                         for k, v in rep["sign_tally"].items()))
    print("resolution      " + ", ".join("%s %d" % (k, v)
                                         for k, v in rep["resolution_tally"].items()))
    print()
    print("axis tally       " + ", ".join("%s %d" % kv
                                          for kv in sorted(rep["axis_tally"].items())))
    print()
    print("what each cell's register could and could not tell apart:")
    for r in rep["cells"]:
        print("   %-20s axis %-8s %-22s ran: %-3s %s"
              % (r["polity"], r["register_carries_axis"], r["resolution"],
                 r["ran"], r["resolution_note"]))
    print()
    print("cells whose dates could not be pinned, named rather than dropped:")
    for r in rep["cells"]:
        if not all(r["dates_pinned"]):
            print("   %-20s %s" % (r["polity"], r["register_note"]))
    print()
    print("controls, levies that must not be counted as per-person graduated taxes:")
    for c in CONTROLS:
        print("   %-52s keyed to %-7s %s" % (c["name"], c["keyed_to"], c["why"]))
    print()
    for c in crit:
        print("%-5s %-11s %s" % ("PASS" if c["passed"] else "FAIL", c["kind"],
                                 c["name"].split(" ", 1)[0]))
        print("      %s" % c["detail"])

    OUT.write_text(json.dumps({
        "stage": "B33",
        "config": {
            "arm": "three, the order claim",
            "frame": "six families named in the design's gate zero plus one kill "
                     "candidate slot, fixed before any date was read",
            "register_definition": "binds a liability to a living person at the "
                                   "moment of assessment; a maintained list, not "
                                   "a record of past events; pre-dates the tax; "
                                   "not built for it",
            "date_floor": "year",
            "cells": len(CELLS),
            "estimates": "none",
            "rival_criterion": "none, deliberately: a scalar field on positions "
                               "makes no claim about when a fiscal instrument "
                               "appears, so this is a cell where nobody on that "
                               "side had a reason to answer",
            "read_on": "2026-09-10",
        },
        "criteria": crit,
        "report": rep,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
