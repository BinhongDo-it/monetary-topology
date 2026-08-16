"""A1a: what the joint says that the two margins could not.

**Diagnostic. It registers nothing, gates nothing and feeds no criterion.**
``PROJECT_PLAN.md`` §16.1's shape: measure first, decide afterwards, and keep
the two steps in separate files so the measurement cannot be tuned to the
decision.

Usage::

    python experiments/a1a_joint_probe.py

Writes ``results/a1a_joint_probe.json`` and
``data/processed/scf_joint_cells.csv``.

What it is answering
----------------------
Stage A1's population is built by crossing marginals: income, the basket, the
rents and tenure by income decile from the CEX, consumer credit and mortgage
debt by net-worth group from the DFA, and every household inside a wealth group
carrying that group's average debt. Two things were then read off that
construction as if they were data:

* the permutation arm's tightest cell, next-9%-by-wealth households sitting in
  the bottom half by income, whose published debt exceeded what their published
  income could service;
* the main arm's tightest cell, the bottom half's renters, at 94% of disposable.

Neither is a published group. Both are crossings, and a crossing that cannot
service itself is a statement about the crossing. This probe replaces the
crossing with the joint the SCF already publishes, and reports three things:

**The coupling.** How the two rankings actually line up, against the Gaussian
copula at Kennickell's 0.76 that stood in for it.

**The conditional debt.** What a household in a given wealth group and a given
income group actually owes, against the group average the model gave it.

**The level.** What the SCF's own aggregates come to against the financial
accounts the model scaled by. Where they disagree, the disagreement is
reported. It is not reconciled here and nothing is rescaled to make it go away.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.scf import GROUPS  # noqa: E402
from monetary_topology.scf_joint import (  # noqa: E402
    JointSelection,
    read_joint,
)

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
ARCHIVE = RAW / "scfp2022excel.zip"
SELECTION = ROOT / "data" / "scf_joint_variables.json"

#: What stage A1 currently gives each wealth group, per household, from the DFA
#: shares at the Z.1 2026Q1 scale. Printed beside the measured figure so the
#: distance is visible rather than described.
MODEL_CONSUMER_CREDIT = (38_674.0, 32_571.0, 41_893.0, 123_190.0)

#: The stand-in the permutation arm used, ``coupling(POPULATION_WEIGHTS, 0.76)``
#: in ``experiments/a1_default_cascade.py``. Kennickell (1999) on the 1995 SCF.
COPULA_0_76 = (
    (0.7823, 0.2129, 0.0048, 0.0000),
    (0.2662, 0.6240, 0.1068, 0.0030),
    (0.0266, 0.4746, 0.4395, 0.0592),
    (0.0009, 0.1208, 0.5326, 0.3456),
)

#: Z.1 2026Q1, the scale the model uses, in dollars.
Z1_CONSUMER_CREDIT = 5_073_031e6
Z1_HOME_MORTGAGES = 13_820_984e6


def table(result: dict[str, object]) -> dict[tuple[int, int], dict[str, object]]:
    index = {g: i for i, g in enumerate(GROUPS)}
    return {
        (index[c["wealth"]], index[c["income"]]): c
        for c in result["cells"]  # type: ignore[index]
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-anchors", action="store_true",
                    help="skip the three anchors; for reading another wave")
    args = ap.parse_args()

    print("A1a: the income and net worth joint, diagnostic only")
    if not ARCHIVE.exists():
        print(f"  {ARCHIVE.name} is absent; run data/fetch_scf.py",
              file=sys.stderr)
        return 1
    selection = JointSelection.load(SELECTION)
    result = read_joint(ARCHIVE, selection, check_anchors=not args.no_anchors)
    cells = table(result)

    print(f"\n  wave {selection.wave}, {result['records']:,} implicate rows, "
          f"{result['weighted_families']:,.0f} families, overall ownership "
          f"{result['overall_ownership']:.4f}")

    print("\ncoupling: income mix of each net-worth group")
    print(f"  {'':<10}" + "".join(f"{g:>12}" for g in GROUPS)
          + "     copula 0.76 for comparison")
    for w in range(len(GROUPS)):
        measured = "".join(
            f"{cells[(w, i)]['share_of_wealth_group']:>12.4f}"
            for i in range(len(GROUPS))
        )
        stood_in = " ".join(f"{v:.4f}" for v in COPULA_0_76[w])
        print(f"  {GROUPS[w]:<10}{measured}     {stood_in}")

    print("\nconsumer credit per household, measured on the joint")
    print(f"  {'':<10}" + "".join(f"{g:>12}" for g in GROUPS)
          + f"{'group mean':>13}{'model gives':>13}")
    for w in range(len(GROUPS)):
        row = "".join(
            f"{cells[(w, i)]['mean_consumer_credit']:>12,.0f}"
            for i in range(len(GROUPS))
        )
        measured_group = result["consumer_credit_by_wealth"][w]  # type: ignore[index]
        print(f"  {GROUPS[w]:<10}{row}{measured_group:>13,.0f}"
              f"{MODEL_CONSUMER_CREDIT[w]:>13,.0f}")

    print("\ntenure and the shelter flows, measured on the joint")
    print(f"  {'wealth':<10}{'income':<10}{'renter':>8}{'mtgd':>8}{'outr':>8}"
          f"{'rent/mo':>10}{'pay/mo':>10}{'mtg debt':>12}{'weight':>9}")
    for w in range(len(GROUPS)):
        for i in range(len(GROUPS)):
            c = cells[(w, i)]
            if c["share_of_population"] < 5e-4:
                continue
            print(f"  {GROUPS[w]:<10}{GROUPS[i]:<10}"
                  f"{c['renter_share']:>8.3f}{c['mortgaged_share']:>8.3f}"
                  f"{c['outright_share']:>8.3f}{c['rent_per_renter']:>10,.0f}"
                  f"{c['payment_per_mortgaged']:>10,.0f}"
                  f"{c['mortgage_debt_per_mortgaged']:>12,.0f}"
                  f"{c['share_of_population']:>9.4f}")

    card = float(result["aggregate_card"])  # type: ignore[arg-type]
    vehicle = float(result["aggregate_vehicle"])  # type: ignore[arg-type]
    mortgage = float(result["aggregate_mortgage"])  # type: ignore[arg-type]
    print("\naggregates, against the financial accounts the model scales by")
    print(f"    SCF cards + vehicles   {(card + vehicle) / 1e12:>8.3f} tn")
    print(f"    Z.1 consumer credit    {Z1_CONSUMER_CREDIT / 1e12:>8.3f} tn"
          f"   ratio {(card + vehicle) / Z1_CONSUMER_CREDIT:.3f}")
    print(f"    SCF primary mortgages  {mortgage / 1e12:>8.3f} tn")
    print(f"    Z.1 home mortgages     {Z1_HOME_MORTGAGES / 1e12:>8.3f} tn"
          f"   ratio {mortgage / Z1_HOME_MORTGAGES:.3f}")
    print("    The two are different vintages and different definitions and "
          "this probe reconciles neither.")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    columns = list(result["cells"][0])  # type: ignore[index]
    out_csv = PROCESSED / "scf_joint_cells.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for cell in result["cells"]:  # type: ignore[union-attr]
            writer.writerow(cell)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS / "a1a_joint_probe.json"
    out_json.write_text(
        json.dumps(
            {
                "stage": "A1a",
                "diagnostic_only": (
                    "registers nothing and feeds no criterion; it measures "
                    "what the marginal-crossing construction assumed"
                ),
                "wave": selection.wave,
                "selection_file": SELECTION.name,
                "model_consumer_credit": list(MODEL_CONSUMER_CREDIT),
                "copula_0_76": [list(r) for r in COPULA_0_76],
                "z1_consumer_credit": Z1_CONSUMER_CREDIT,
                "z1_home_mortgages": Z1_HOME_MORTGAGES,
                **result,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out_csv.relative_to(ROOT)}")
    print(f"  wrote {out_json.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
