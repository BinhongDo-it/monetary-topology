"""A1a: what the joint says that the two margins could not.

**Diagnostic. It registers nothing, gates nothing and feeds no criterion.**
**Measure first, decide afterwards, and keep the two steps in separate files so
the measurement cannot be tuned to the decision.**

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
    extract,
    joint,
    rank_groups,
    read_rows,
)

#: ``MORTPAY`` in the Federal Reserve's variable-definition macro is these three
#: plus the payments on other residential property, on land contracts and on
#: the home-equity lines the primary residence secures. The three are the
#: loans on the primary residence that ``NH_MORT`` counts. ``NH_MORT`` is net
#: of the home-equity lines, so their payment is in ``MORTPAY`` and their debt
#: is outside ``NH_MORT``.
PRIMARY_MORTGAGE = ("PAYMORT1", "PAYMORT2", "PAYMORT3")
#: The other residential property (``PAYORE1``, ``PAYORE2``, ``PAYOREV``) and the
#: land contracts (``PAYLC1``, ``PAYLC2``, ``PAYLCO``) inside ``MORTPAY``. What
#: ``MORTPAY`` holds beyond these six and the three above is the payment on the
#: home-equity lines the primary residence secures, read as the remainder.
OTHER_PROPERTY = ("PAYORE1", "PAYORE2", "PAYOREV", "PAYLC1", "PAYLC2", "PAYLCO")
#: The three land-contract columns among the six, counted on their own so the
#: record says how much of the other-property part they carry.
LAND_CONTRACT = ("PAYLC1", "PAYLC2", "PAYLCO")


def mortgage_payment_coverage(respondents: list, wealth: list[int],
                              income: list[int]) -> dict[str, object]:
    """The mortgage payment column beside the payment on the ``NH_MORT`` loans.

    The probe sets ``MORTPAY`` beside ``NH_MORT`` on one row, and the two do not
    cover the same debt. The stock is the primary-residence loans ``NH_MORT``
    counts. The payment adds other residential property, land contracts and
    the home-equity lines the primary residence secures. What ``MORTPAY`` pays
    beyond the ``NH_MORT`` loans is split in two: other property and land
    contracts, read from their six columns, and the primary residence's
    home-equity line, the remainder. A row pays beyond the ``NH_MORT`` loans
    when that excess is above a cent, and such a row falls in one of two
    classes: some payment on other property or a land contract, or the
    home-equity line alone. Everything is reported overall and by cell, over
    the mortgaged rows the probe already counts. Rows are implicates.
    """
    if not respondents or any(c not in respondents[0].extra
                              for c in PRIMARY_MORTGAGE + OTHER_PROPERTY):
        return {}

    def own(r) -> float:
        return sum(r.extra[c] for c in PRIMARY_MORTGAGE)

    def other(r) -> float:
        return sum(r.extra[c] for c in OTHER_PROPERTY)

    def line(r) -> float:
        return r.mortgage_payment - own(r) - other(r)

    def beyond(r) -> bool:
        return r.mortgage_payment - own(r) > 0.01

    def line_only(r) -> bool:
        return beyond(r) and other(r) <= 0.01

    def mean(rows, get) -> float:
        w = sum(r.weight for r in rows)
        return sum(r.weight * get(r) for r in rows) / w if w else 0.0

    rows = [(r, w, i) for r, w, i in zip(respondents, wealth, income, strict=True)
            if r.owns and r.mortgaged]
    mortgaged = [r for r, _w, _i in rows]
    wider = [r for r in mortgaged if beyond(r)]
    weight = sum(r.weight for r in mortgaged)
    cells = []
    for w in range(len(GROUPS)):
        for i in range(len(GROUPS)):
            here = [r for r, ww, ii in rows if ww == w and ii == i]
            cells.append({
                "wealth_group": w, "income_group": i, "rows_mortgaged": len(here),
                "payment_per_mortgaged": mean(here, lambda r: r.mortgage_payment),
                "nh_mort_loan_payment_per_mortgaged": mean(here, own),
                "rows_with_other_property_or_land_contract_payments": sum(
                    1 for r in here if beyond(r) and not line_only(r)),
                "rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans":
                    sum(1 for r in here if line_only(r)),
                "other_property_and_land_contract_payment_per_mortgaged":
                    mean(here, other),
                "primary_residence_home_equity_line_payment_per_mortgaged":
                    mean(here, line),
            })
    return {
        "rows_mortgaged": len(mortgaged),
        "rows_paying_beyond_the_NH_MORT_loans": len(wider),
        "rows_with_other_property_or_land_contract_payments": sum(
            1 for r in wider if not line_only(r)),
        "rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans": sum(
            1 for r in wider if line_only(r)),
        "rows_with_a_land_contract_payment": sum(
            1 for r in mortgaged
            if sum(r.extra[c] for c in LAND_CONTRACT) > 0.01),
        "weighted_share_paying_beyond_the_NH_MORT_loans": (
            sum(r.weight for r in wider) / weight if weight else 0.0),
        "mean_MORTPAY": mean(mortgaged, lambda r: r.mortgage_payment),
        "mean_nh_mort_loans": mean(mortgaged, own),
        "mean_other_property_and_land_contracts": mean(mortgaged, other),
        "mean_primary_residence_home_equity_line": mean(mortgaged, line),
        "by_cell": cells,
    }

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
    respondents = extract(read_rows(ARCHIVE, selection.member), selection)
    result = joint(respondents, not args.no_anchors)
    cells = table(result)
    coverage = mortgage_payment_coverage(
        respondents, rank_groups(respondents, "networth"),
        rank_groups(respondents, "income"))
    own_payment = {(c["wealth_group"], c["income_group"]):
                   c["nh_mort_loan_payment_per_mortgaged"]
                   for c in coverage.get("by_cell", [])}

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
    print("  pay/mo is MORTPAY: the NH_MORT loans, other property, land "
          "contracts and the primary residence's home-equity line")
    print("  own/mo is the payment on the NH_MORT loans alone, the debt mtg "
          "debt is")
    print(f"  {'wealth':<10}{'income':<10}{'renter':>8}{'mtgd':>8}{'outr':>8}"
          f"{'rent/mo':>10}{'pay/mo':>10}{'own/mo':>10}{'mtg debt':>12}"
          f"{'weight':>9}")
    for w in range(len(GROUPS)):
        for i in range(len(GROUPS)):
            c = cells[(w, i)]
            if c["share_of_population"] < 5e-4:
                continue
            print(f"  {GROUPS[w]:<10}{GROUPS[i]:<10}"
                  f"{c['renter_share']:>8.3f}{c['mortgaged_share']:>8.3f}"
                  f"{c['outright_share']:>8.3f}{c['rent_per_renter']:>10,.0f}"
                  f"{c['payment_per_mortgaged']:>10,.0f}"
                  f"{own_payment.get((w, i), float('nan')):>10,.0f}"
                  f"{c['mortgage_debt_per_mortgaged']:>12,.0f}"
                  f"{c['share_of_population']:>9.4f}")

    if coverage:
        print(f"\n  {coverage['rows_paying_beyond_the_NH_MORT_loans']:,} of "
              f"{coverage['rows_mortgaged']:,} mortgaged rows "
              f"({coverage['weighted_share_paying_beyond_the_NH_MORT_loans']:.2%}"
              f" of mortgaged families by weight) pay MORTPAY beyond the "
              f"NH_MORT loans: "
              f"{coverage['rows_with_other_property_or_land_contract_payments']:,}"
              f" on other property or land contracts, "
              f"{coverage['rows_with_only_the_home_equity_line_beyond_the_NH_MORT_loans']:,}"
              f" on the primary residence's home-equity line alone")
        print(f"  a month per mortgaged family: "
              f"{coverage['mean_MORTPAY']:,.2f} in all, "
              f"{coverage['mean_nh_mort_loans']:,.2f} on the NH_MORT "
              f"loans, "
              f"{coverage['mean_other_property_and_land_contracts']:,.2f} on "
              f"other property and land contracts, "
              f"{coverage['mean_primary_residence_home_equity_line']:,.2f} on "
              f"the primary residence's home-equity line")

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
    # payment_per_mortgaged is MORTPAY. The payment on the NH_MORT loans goes
    # beside it, so both payments sit next to the debt they are set against.
    beside = "nh_mort_loan_payment_per_mortgaged"
    if own_payment:
        columns.insert(columns.index("payment_per_mortgaged") + 1, beside)
    out_csv = PROCESSED / "scf_joint_cells.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for cell in result["cells"]:  # type: ignore[union-attr]
            row = dict(cell)
            if own_payment:
                row[beside] = own_payment[(GROUPS.index(cell["wealth"]),
                                           GROUPS.index(cell["income"]))]
            writer.writerow(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS / "a1a_joint_probe.json"
    out_json.write_text(
        json.dumps(
            {
                "stage": "A1a",
                "diagnostic_only": True,
                "diagnostic_reason": (
                    "registers nothing and feeds no criterion; it measures "
                    "what the marginal-crossing construction assumed"
                ),
                "wave": selection.wave,
                "selection_file": SELECTION.name,
                "model_consumer_credit": list(MODEL_CONSUMER_CREDIT),
                "copula_0_76": [list(r) for r in COPULA_0_76],
                "z1_consumer_credit": Z1_CONSUMER_CREDIT,
                "z1_home_mortgages": Z1_HOME_MORTGAGES,
                "mortgage_payment_coverage": coverage,
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
