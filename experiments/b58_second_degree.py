"""B58 second arm: score a quantity on the second-degree construction.

The station's own coverage criterion, B58-5, counted the rival's thirteen
elements and found the first and second degree carry no scored quantity at all.
This arm fills the second-degree half. It buys nothing: the input is the record
`results/tariff_blocks_count.json`, already on disk, fifty-three national
residential electricity schedules from one published survey annex.

Two of the located premises can be read off a published schedule.

The first is `v` taking only `(q, theta)`. If utility outside the transfer
depends on quantity and type alone, the optimal tariff is a function of quantity
alone. A schedule that prices a time band, a voltage level, or a customer class
alongside its consumption blocks is not a `T(q)`. This needs no assumption about
what the seller is maximising, so the whole corpus is admissible for it, and it
is registered here as the rival criterion.

The second is the quantity discount. It follows from the same premises plus
profit maximisation and a monotone hazard rate, and profit maximisation is the
fifth condition this station already separated out for the third degree, because
it is not in the rival's own feasibility list. Scoring it needs the seller's
objective established per schedule, which is not done here. The direction is
therefore printed as an object and not scored against the rival, and the missing
partition is registered in the record.

Criteria are written here and the record carries their text. No threshold sits on
any estimate. Directions are computed from the charges the survey printed, not
from the survey's own type label, and both are reported so they can disagree.

    python experiments/b58_second_degree.py
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "tariff_blocks_count.json"
OUT = ROOT / "results" / "b58_second_degree.json"

# A type label counts as pricing something besides consumption when it names a
# second argument. Written before the labels were tabulated; every label the
# corpus carries is printed in the record whether or not it matches.
SECOND_ARGUMENT = ("tou", "voltage")

# "Multiple" is not counted as a second argument. The survey does not say what it
# multiplies over, and reading a second argument out of an unexplained word is
# the shape D26 warns about. Registered as unresolved rather than counted.
UNRESOLVED = ("multiple",)

# The located premises, each with the source it was taken from. They were prose
# in a detail string until 2026-09-13, which made B58-6's verdict a hardwired
# True: a premise could lose its source and nothing would notice (rule 11f).
PREMISES = (
    ("quasilinear utility, v(q, theta) - T", "MIT 14.271 (Ellison) lec3"),
    ("v depends on q and theta and on nothing else", "MIT 14.271 (Ellison) lec3"),
    ("single crossing, v_qtheta > 0", "MIT 14.271 (Ellison) lec3"),
    ("path-independent local incentive compatibility", "MIT 14.271 (Ellison) lec3"),
)
# Held out on purpose. It is not among Stole ch.34's three feasibility
# conditions, and this station made the same separation for the third degree.
SEPARATED = (("profit maximisation",
              "not among Stole ch.34's three feasibility conditions"),)


# 11c: three cells, two of them scored and one carrying no verdict. Written as a
# table so B58-7 can assert it rather than restate it in prose.
CELL_VERDICT = {
    "quantity_only": "the rival's point prediction holds on this cell",
    "more_than_quantity": "the rival's point prediction fails on this cell",
    "unresolved": "no verdict",
}
SCORED_CELLS = tuple(c for c, v in CELL_VERDICT.items() if v != "no verdict")


def direction(charges):
    """Direction of the marginal charge across the blocks the schedule draws."""
    vals = [float(c) for c in charges]
    if len(vals) < 2:
        return "single_block"
    if len(set(vals)) == 1:
        return "flat"
    up = all(b >= a for a, b in zip(vals, vals[1:]))
    down = all(b <= a for a, b in zip(vals, vals[1:]))
    if up:
        return "increasing"
    if down:
        return "decreasing"
    return "non_monotone"


def arguments_of_T(type_label):
    low = (type_label or "").lower()
    if any(k in low for k in SECOND_ARGUMENT):
        return "more_than_quantity"
    if any(k in low for k in UNRESOLVED):
        return "unresolved"
    return "quantity_only"


def main():
    if not SRC.exists():
        print(f"input missing: {SRC}", file=sys.stderr)
        return 2
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rows = src["clean"]

    schedules = []
    for r in sorted(rows, key=lambda x: x["country"]):
        schedules.append(
            {
                "country": r["country"],
                "survey_type_label": r.get("type"),
                "blocks_drawn": r["n"],
                "charges": list(r["charges"]),
                "direction_from_charges": direction(r["charges"]),
                "arguments_of_T": arguments_of_T(r.get("type")),
            }
        )

    dirs = Counter(s["direction_from_charges"] for s in schedules)
    args = Counter(s["arguments_of_T"] for s in schedules)
    labels = Counter(s["survey_type_label"] for s in schedules)

    # A label and its own printed charges can disagree. Print every case.
    label_vs_charges = [
        {
            "country": s["country"],
            "survey_type_label": s["survey_type_label"],
            "charges": s["charges"],
            "direction_from_charges": s["direction_from_charges"],
        }
        for s in schedules
        if (s["survey_type_label"] or "").lower().startswith("dbt")
        and s["direction_from_charges"] != "decreasing"
    ]

    second_arg = sorted(
        (s["country"], s["survey_type_label"])
        for s in schedules
        if s["arguments_of_T"] == "more_than_quantity"
    )
    unresolved = sorted(
        (s["country"], s["survey_type_label"])
        for s in schedules
        if s["arguments_of_T"] == "unresolved"
    )

    # ---- criteria -------------------------------------------------------
    # B58-10 polarity, 11e first clause second half: a rival criterion registers
    # that the rival's point prediction does NOT hold on these cells, so PASS is
    # the rival being wrong.
    rival_holds = args["more_than_quantity"] == 0

    # B58-6: every located premise carries a source, and the one held out is not
    # among them. Fails if a premise is added without a source, or if profit
    # maximisation is quietly folded back in.
    premises_sourced = (len(PREMISES) == 4
                        and all(p.strip() and s.strip() for p, s in PREMISES))
    held_out = {p.lower() for p, _ in SEPARATED}
    profit_max_held_out = (bool(held_out) and not any(
        h in p.lower() for p, _ in PREMISES for h in held_out))

    # B58-7 is 11c: the map from cell to verdict, written down rather than
    # implied, with the undecided cell asserted to carry none.
    cells_named = set(args) <= set(CELL_VERDICT)
    unresolved_unscored = CELL_VERDICT["unresolved"] == "no verdict"
    scored_adds_up = (sum(args[c] for c in SCORED_CELLS)
                      == args["quantity_only"] + args["more_than_quantity"])

    criteria = [
        {
            "name": "B58-6",
            "kind": "premise",
            "criterion": (
                "the second-degree premises carry their source, and profit "
                "maximisation is listed separately because it is not among them"
            ),
            "passed": premises_sourced and profit_max_held_out,
            "detail": (
                f"{len(PREMISES)} premises, each carrying its source: "
                + "; ".join(f"{p} [{s}]" for p, s in PREMISES)
                + f". Held out separately: "
                + "; ".join(f"{p} ({why})" for p, why in SEPARATED)
                + ". Profit maximisation is the fifth and is not in Stole ch.34's "
                "own three feasibility conditions, which is the same separation "
                "this station made for the third degree."
            ),
        },
        {
            "name": "B58-7",
            "kind": "instrument",
            "criterion": (
                "every cell maps to a named outcome and the unresolved cell maps "
                "to no verdict"
            ),
            "passed": cells_named and unresolved_unscored and scored_adds_up,
            "detail": (
                "cell to verdict, printed rather than left in the head: "
                + "; ".join(f"{c} -> {v}" for c, v in sorted(CELL_VERDICT.items()))
                + f". Observed cells {sorted(args)}, all named. "
                f"{sum(args[c] for c in SCORED_CELLS)} schedules enter B58-10 and "
                f"{args['unresolved']} do not. 'Multiple' is read as unresolved "
                "because the survey does not say what it multiplies over, and it "
                "is neither scored for nor against the rival."
            ),
        },
        {
            "name": "B58-8",
            "kind": "own_reading",
            "criterion": (
                "print the object: every schedule with its country, the survey's "
                "own type label, its blocks, its charges, and the direction "
                "computed from those charges"
            ),
            "passed": len(schedules) == len(rows),
            "detail": (
                f"{len(schedules)} schedules printed in full, none summarised away. "
                f"Label and charges disagree on {len(label_vs_charges)} schedule(s), "
                "each printed."
            ),
        },
        {
            "name": "B58-9",
            "kind": "own_reading",
            "criterion": (
                "print the direction distribution, and do not score it against the "
                "rival without the seller's objective"
            ),
            "passed": bool(dirs) and sum(dirs.values()) == len(schedules),
            "detail": (
                f"every one of {len(schedules)} schedules carries a direction, "
                f"{sum(dirs.values())} accounted for. Directions from the printed "
                "charges: "
                + ", ".join(f"{k} {v}" for k, v in sorted(dirs.items()))
                + ". The rival's quantity-discount prediction follows from the four "
                "premises plus profit maximisation and a monotone hazard rate. This "
                "station separated profit maximisation out for the third degree and "
                "the same separation applies here, so scoring this direction against "
                "the rival needs the objective established per schedule. That "
                "partition is not run in this arm and is registered as not done."
            ),
        },
        {
            "name": "B58-10",
            "kind": "rival",
            "grid": "B",
            "rival_shape": "point",
            "rival_premise": (
                "v depends on (q, theta) and on nothing else, so the optimal tariff "
                "is a function of quantity alone: T = T(q). MIT 14.271 lec3."
            ),
            "rival_entailment": (
                "With utility outside the transfer taking only quantity and type, "
                "the seller's problem has quantity as its only instrument and the "
                "tariff it solves for is a schedule over quantity. A published "
                "schedule that also prices a time band or a voltage level takes an "
                "argument the model does not carry, so on that schedule T is not "
                "T(q). This step uses no assumption about what the seller maximises."
            ),
            "cite": "MIT 14.271 (Ellison) lec3; Rochet-Chone 1998, Econometrica 66(4)",
            "criterion": (
                "the rival's point prediction that a published residential tariff "
                "prices quantity and nothing else does not hold on these schedules"
            ),
            "passed": not rival_holds,
            "detail": (
                f"{args['more_than_quantity']} of {len(schedules)} schedules price a "
                "second argument by the survey's own type label: "
                + "; ".join(f"{c} ({t})" for c, t in second_arg)
                + f". quantity_only {args['quantity_only']}, unresolved "
                f"{args['unresolved']}. Both outcomes were reachable: the survey's "
                "own vocabulary carries pure IBT and pure Linear labels, which are "
                "quantity-only. Our own reading on the same corpus is the counting "
                "law, which indexes values by whatever the programme writes down and "
                "therefore permits a non-quantity argument; it is scored separately "
                "in the TB- family. Grid B: our reading holds and the rival's point "
                "prediction does not. Scope, per 11e third clause: the located "
                "premises are the one-dimensional model, and these schedules were "
                "measured to lie outside it, so the premise is false on the ground "
                "measured rather than silent about it."
            ),
        },
        {
            "name": "B58-11",
            "kind": "bookkeeping",
            "criterion": "the coverage line B58-5 wrote is restated against this arm",
            # filled in below, once the list this criterion counts exists
            "passed": None,
            "detail": (
                "B58-5 recorded the second degree as premises located to source with "
                "zero quantities scored. After this arm the second degree carries one "
                "scored rival quantity (B58-10) and two printed objects (B58-8, "
                "B58-9). The first degree still carries zero readings and that half "
                "of B58-5 stands unchanged."
            ),
        },
    ]

    # B58-11 counts the criteria this arm actually wrote, so it can only be
    # settled once the list exists. Hardwired True until 2026-09-13 (rule 11f):
    # it restated a count instead of taking it.
    scored_rival = sum(1 for c in criteria if c.get("kind") == "rival")
    printed_objects = sum(1 for c in criteria if c.get("kind") == "own_reading")
    for c in criteria:
        if c["name"] == "B58-11":
            c["passed"] = scored_rival == 1 and printed_objects == 2
            c["detail"] += (
                f" Counted against this arm's own table rather than restated: "
                f"{scored_rival} scored rival quantity and {printed_objects} "
                f"printed objects."
            )

    record = {
        "stage": "B58",
        "arm": "second degree",
        "config": {
            "source_record": SRC.name,
            "second_argument_keys": list(SECOND_ARGUMENT),
            "unresolved_keys": list(UNRESOLVED),
            "schedules": len(schedules),
        },
        "schedules": schedules,
        "direction_histogram": dict(sorted(dirs.items())),
        "arguments_histogram": dict(sorted(args.items())),
        "survey_type_labels": dict(sorted(labels.items(), key=lambda kv: str(kv[0]))),
        "second_argument_schedules": [list(x) for x in second_arg],
        "unresolved_schedules": [list(x) for x in unresolved],
        "label_disagrees_with_charges": label_vs_charges,
        "registered_not_done": (
            "the seller's objective per schedule, which B58-9 needs before the "
            "quantity-discount direction can be scored against the rival"
        ),
        "criteria": criteria,
    }

    OUT.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    failed = [c for c in criteria if c.get("passed") is False]
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"{mark}[{c['kind']}] {c['name']}: {c['detail'][:160]}")
    print()
    print("directions:", dict(sorted(dirs.items())))
    print("arguments :", dict(sorted(args.items())))
    print("wrote", OUT.name)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
