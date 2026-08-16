"""A1c: the order inside a household. Evaluates, designs nothing.

Registered in ``docs/a1c_prereg.md``. Population, mechanism, inputs, baseline and
zero calibration are A1b's and are inherited by reference; this file adds one
measured quantity and one criterion.

Usage::

    python experiments/a1c_household_order.py
    python experiments/a1c_household_order.py --households 20000

Writes ``results/a1c_household_order.json``.

Why this is a separate stage and not a repair
-----------------------------------------------
``a1_prereg.md`` A1-2 asked, of every defaulting household, which class it
defaulted on **first**, and required card to lead auto to lead shelter. It
failed, and A1b's §8 records where: in this population 40.6% of households hold
neither a revolving balance nor a car loan, so a cross-section of first defaults
is the cost rule composed with the holdings and the registered inequality cannot
hold whatever the cost ordering is.

卷一·十八's claim is about **one household over time**. A household holding a
card, a car loan and a tenancy, squeezed, gives them up in that order. That is
what this file measures, on the households that hold both rungs of each pair.

**A1-2 is not rescued by any of it.** Its failure stands as recorded. Where the
two disagree, both stand, and the disagreement is the finding that a
cross-section of first defaults is not a sequence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from a1b_default_cascade import (  # noqa: E402
    ARCHIVE,
    DEFAULT_HOUSEHOLDS,
    PATH_SEED,
    SCORED_PERIODS,
    SELECTION,
    basket_by_decile,
    to_records,
)
from monetary_topology.cascade import (  # noqa: E402
    CascadeModel,
    CostRule,
    Obligation,
    Tenure,
    build_from_records,
)
from monetary_topology.income_path import (  # noqa: E402
    PathSpec,
    retention_path,
)
from monetary_topology.scf_joint import (  # noqa: E402
    JointSelection,
    read_respondents,
)

RESULTS = ROOT / "results"

#: The manuscript's own adjacency, plus its one transitive consequence.
#:
#: **The third step is rent and not shelter**, restated 2026-08-16 and recorded
#: in ``docs/a1c_prereg.md`` §6 with what had been seen. §2 of that document
#: originally wrote ``shelter`` for rent or mortgage, against a scope
#: ``a1_prereg.md`` §9 had registered three days earlier: "the manuscript's
#: cascade is a renter's cascade", the mortgage entering as an obligation class
#: for the K shape and taking no rung. The pair as first written asked the
#: sequence to hold for a class the project had already excluded from it.
PAIRS = (
    ("card_before_auto", Obligation.CARD, (Obligation.AUTO,)),
    ("auto_before_rent", Obligation.AUTO, (Obligation.RENT,)),
    ("card_before_rent", Obligation.CARD, (Obligation.RENT,)),
)

#: Reported and never scored. ``a1_prereg.md`` §2.2, written 2026-08-13 before
#: any run: "at no arrears the mortgage is the cheapest real obligation to skip
#: ... So a squeezed owner skips the mortgage before the car. This is the
#: reversal of the payment hierarchy reported after 2008, and it is a prediction
#: here rather than an input."
#:
#: **The direction was registered in advance and the decision to gate it was
#: not.** It is reported with its registration quoted, and it stays out of
#: A1c-1, because choosing to score a prediction after watching it come true is
#: choosing the gate on the result even where the direction was not.
MORTGAGE_PAIR = ("mortgage_before_auto", Obligation.MORTGAGE,
                 (Obligation.AUTO,))


class Criterion:
    def __init__(self, name: str, passed: bool, detail: str,
                 void: bool = False) -> None:
        self.name, self.passed, self.detail, self.void = (
            name, passed, detail, void
        )

    def line(self) -> str:
        mark = "VOID" if self.void else ("pass" if self.passed else "FAIL")
        return f"  {mark}  {self.name}\n        {self.detail}"


def missed_at(house, classes) -> tuple[int | None, Obligation | None]:
    """When this household first missed any of these classes, and which one."""
    hit = [(house.first_missed[k], k) for k in classes if k in house.first_missed]
    return min(hit) if hit else (None, None)


def compare_one(households: list, pair) -> dict[str, object]:
    """One pair, the same arithmetic ``compare`` runs on each of its three."""
    return compare(households, (pair,))[pair[0]]


def compare(households: list, pairs=None) -> dict[str, dict[str, object]]:
    """One row per pair, over the households in scope for that pair.

    In scope means the household missed **both** sides at some point. A
    household that missed one or neither is counted apart rather than folded in
    as agreement: it has no order to be right or wrong about, and counting it as
    agreement would make the criterion easier the fewer households obey the
    sequence at all.
    """
    out: dict[str, dict[str, object]] = {}
    for name, earlier, later_classes in (pairs if pairs is not None else PAIRS):
        in_order = tied = inverted = 0
        released = 0
        unattributed: list[str] = []
        for house in households:
            if earlier not in house.first_missed:
                continue
            when_later, later = missed_at(house, later_classes)
            if when_later is None:
                continue
            when_earlier = house.first_missed[earlier]
            if when_later > when_earlier:
                in_order += 1
            elif when_later == when_earlier:
                tied += 1
            else:
                inverted += 1
                # A1c-2. The rule has one clause that produces an inversion of
                # its own accord: what cannot be saved is released first. An
                # inversion is attributed to it when the later class could not
                # have been saved in the period it was first missed while the
                # earlier one could.
                # Both read from the period the later class was first missed,
                # which is what A1c-2 registers. Reading each class's own
                # first-miss period compares two different months and reported
                # two releases as anomalies.
                snapshot = house.savable_when_missed.get(later, frozenset())
                if later not in snapshot and earlier in snapshot:
                    released += 1
                else:
                    unattributed.append(
                        f"{later.value} at {when_later} before {earlier.value} "
                        f"at {when_earlier}"
                    )
        scope = in_order + tied + inverted
        out[name] = {
            "in_scope": scope,
            "in_order": in_order,
            "tied": tied,
            "inverted": inverted,
            "released": released,
            "unattributed": len(unattributed),
            "examples": unattributed[:3],
            "holds": in_order > inverted,
        }
    return out


def a1c_1(rows: dict[str, dict[str, object]], no_pair: int,
          total: int) -> Criterion:
    """In order strictly exceeds inverted, for each of the three pairs.

    The pairs are the renter's cascade. See ``PAIRS`` for why, and
    ``docs/a1c_prereg.md`` §6 for the date and what had been seen.
    """
    empty = [name for name, row in rows.items() if row["in_scope"] == 0]
    if empty:
        return Criterion(
            "A1c-1 the sequence holds inside a household", False,
            f"no household is in scope for {', '.join(empty)}, so the pair is "
            f"undefined rather than satisfied", True,
        )
    holds = all(row["holds"] for row in rows.values())
    parts = []
    for name, row in rows.items():
        mark = "" if row["holds"] else "  <- INVERTS"
        parts.append(
            f"{name}: {row['in_order']:,} in order, {row['tied']:,} tied, "
            f"{row['inverted']:,} inverted, of {row['in_scope']:,} in scope"
            + mark
        )
    detail = "; ".join(parts)
    detail += (
        f". {no_pair:,} of {total:,} households are in scope for no pair at "
        f"all, which is the population A1-2 quantified over and the size of "
        f"the mismatch between the claim and its cross-sectional form"
    )
    if not holds:
        detail += ". A pair that inverts is the manuscript's sequence being "
        detail += "wrong for that pair, not the code being wrong"
    return Criterion("A1c-1 the sequence holds inside a household", holds,
                     detail)


def a1c_2(rows: dict[str, dict[str, object]]) -> Criterion:
    """Every inversion attributed, or named as unattributed. Gates nothing."""
    total_inverted = sum(int(r["inverted"]) for r in rows.values())
    released = sum(int(r["released"]) for r in rows.values())
    unattributed = sum(int(r["unattributed"]) for r in rows.values())
    if total_inverted == 0:
        detail = "no inversion to attribute"
    else:
        detail = (
            f"{total_inverted:,} inversions: {released:,} attributed to the "
            f"release clause, the later class unsavable in the period it was "
            f"first missed while the earlier one was savable; "
            f"{unattributed:,} unattributed"
        )
        examples = [e for r in rows.values() for e in r["examples"]]  # type: ignore[union-attr]
        if examples:
            detail += ". Examples: " + "; ".join(examples[:3])
    return Criterion("A1c-2 every inversion is attributed", True, detail)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--households", type=int, default=DEFAULT_HOUSEHOLDS)
    args = ap.parse_args()

    print("A1c: the order inside a household")
    if not ARCHIVE.exists():
        print(f"  {ARCHIVE.name} is absent; run data/fetch_scf.py",
              file=sys.stderr)
        return 1

    selection = JointSelection.load(SELECTION)
    records = to_records(read_respondents(ARCHIVE, selection),
                         basket_by_decile())
    cost = CostRule()
    households = build_from_records(records, args.households, cost)
    path = retention_path(PathSpec(periods=SCORED_PERIODS, seed=PATH_SEED))
    result = CascadeModel(households, cost).run(path)

    print(f"\n  {args.households:,} households, wave {selection.wave}, A0 path "
          f"at seed {PATH_SEED} over {SCORED_PERIODS} months")
    print(f"  {result.defaulting_households:,} households default at least "
          f"once")

    rows = compare(households)
    mortgage = compare_one(households, MORTGAGE_PAIR)
    print(f"\n  {'pair':<22}{'in scope':>10}{'in order':>10}{'tied':>8}"
          f"{'inverted':>10}{'released':>10}")
    for name, row in rows.items():
        print(f"  {name:<22}{row['in_scope']:>10,}{row['in_order']:>10,}"
              f"{row['tied']:>8,}{row['inverted']:>10,}{row['released']:>10,}")

    in_scope_of_any = {
        id(h) for name, earlier, later in PAIRS for h in households
        if earlier in h.first_missed and missed_at(h, later)[0] is not None
    }
    no_pair = len(households) - len(in_scope_of_any)

    print(f"\n  reported and never scored, the reversal a1_prereg.md 2.2 "
          f"registered on 2026-08-13:")
    print(f"  {'mortgage_before_auto':<22}{mortgage['in_scope']:>10,}"
          f"{mortgage['in_order']:>10,}{mortgage['tied']:>8,}"
          f"{mortgage['inverted']:>10,}{mortgage['released']:>10,}")
    if mortgage["in_scope"]:
        verdict = ("holds" if mortgage["in_order"] > mortgage["inverted"]
                   else "does not hold")
        print(f"    the mortgage going before the car {verdict}: "
              f"{mortgage['in_order']:,} in order against "
              f"{mortgage['inverted']:,} inverted. At zero arrears one missed "
              f"payment consumes a twelfth of the foreclosure clock against a "
              f"third of the repossession clock")

    criteria = [a1c_1(rows, no_pair, len(households)), a1c_2(rows)]
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a1c_household_order.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A1c",
                "complete": True,
                "wave": selection.wave,
                "households": args.households,
                "seeds": "none; A0's path seed is the only randomness",
                "path_seed": PATH_SEED,
                "periods": SCORED_PERIODS,
                "defaulting_households": result.defaulting_households,
                "in_scope_for_no_pair": no_pair,
                "pairs": rows,
                "mortgage_before_auto": {
                    **mortgage,
                    "scored": False,
                    "registered": (
                        "a1_prereg.md 2.2, written 2026-08-13 before any run: "
                        "a squeezed owner skips the mortgage before the car, "
                        "the reversal of the payment hierarchy reported after "
                        "2008, a prediction rather than an input. Reported "
                        "here and not gated, because the direction was "
                        "registered in advance and the decision to gate was "
                        "not"
                    ),
                },
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "void": bool(c.void), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
