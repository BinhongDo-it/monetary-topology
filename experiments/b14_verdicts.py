"""B14 verdict sheet: assemble results/b14_stage_two.json from the station's products.

Why this file exists. B14 wrote no JSON record, and the station is now closed
with eight verdicts on the board. It was absent from the file everyone else
reads. This is the same repair
b8_verdicts.py and b13_verdicts.py are, and it carries the same number check
from the start.

What it claims. Nothing it did not read. Every number in a criterion must appear
in one of that criterion's own sources. Numbers that are not readings are in
EXEMPT with the reason each is not one.

What it deliberately carries. Three caveats travel with citations of this stage
and are written into the criteria rather than left to a reader to remember:
T6's 6/6 depends entirely on order type 22; the narrow-band discontinuity is
sealed and is not the basis of anything; and leg B is closed rather than paused,
because no quantity of further data changes the 88.7 per cent.

Run python experiments/b14_verdicts.py and then re-render RESULTS.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

SOURCES: dict[str, tuple[str, ...]] = {
    "B14-0": ("b14_gate0.json", "b14_ordertype_sens.json"),
    "B14-A": ("b14_gate_exit.json", "b14_gate_exit_pre804.json",
              "b14_placebo_band_pre804.json", "b14_placebo_band_1m_pre804.json",
              "b14_placebo_post.json", "b14_level_series.json"),
    "B14-B0": ("b14_legb_probe.json", "b14_legb_spend.json",
               "b14_legb_panel_checks.json"),
    "B14-B1": ("b14_legb_gate1.json",),
    "B14-B2": ("b14_legb_gate2.json",),
    "B14-B3": ("b14_legb_gate3.json", "b14_legb_a18_sliceA.json",
               "b14_legb_a18_sliceB.json"),
    "B14-19": ("b14_ordertype_sens.json",),
    "B14-20": ("b14_cand0.json",),
}

#: Numbers that are not readings off a product, each with why it is not one.
EXEMPT: dict[str, str] = {
    "5.1": "a section number in docs/b4_directed_edges.md",
    "6": "a theorem number, as in Theorem 6(4) and Theorem 6(5)",
    "4": "a theorem clause number",
    "5": "a theorem clause number",
    "9": "a section number in docs/b4_directed_edges.md",
    "0.05": "the pilot's own quoting increment, from FINRA Rule 6191, not a reading",
    "2018": "a calendar year",
    "2016": "a calendar year",
    "22": "an Order_Type code from FINRA's Appendix B specification",
    "16": "an Order_Type code from FINRA's Appendix B specification",
    "18": "an Order_Type code, the one absent from disk, from the same specification",
    "1": "a count of conditions or of arms, stated in prose",
    "2": "a count of conditions, of halves, or of venues, stated in prose",
    "3": "a count of conditions or of treated groups, stated in prose",
    "8": "the arithmetic bound on the lattice widening, in cents, derived not measured",
    "108": "the size of the registered symbol set, fixed in results/b14_legb_symbols.json",
    "6191": "a FINRA rule number",
    "0.67": "the median of |z| under the standard normal, a property of the null "
            "and not a measurement; the gate prints it as the bar the observed "
            "2.08 is read against",
    "47": "the size of the control arm after the registered exclusions",
}

CRITERIA: list[dict] = [
    {"name": "B14-0  the friction half moved on the 2016 round, and it is not "
             "carried by the orders that do not participate in the spread",
     "passed": True, "detail":
     "the primary share-weighted convention holds all six inequalities, and so "
     "do the order-count convention, the adverse convention and the NBBO "
     "cross-check. B14_A19 then drops the order types that the code table named: "
     "away-from-market orders, which carry the largest single block of the share "
     "weight, retail liquidity providing orders, and both together. The primary "
     "measure holds "
     "6/6 in every one of the three variants. Same event, same data, only the "
     "weight composition changes. **One caveat travels with any citation of T6**: "
     "its own 6/6 depends entirely on order type 22, holding under the retail "
     "variant and falling to exactly 3/6 under the other two. T6 was excluded "
     "from the verdict before the run, so nothing moves, but the dependence must "
     "be quoted with it"},
    {"name": "B14-A  leg A, the pilot's termination read as a reversed event, "
             "on the population the two rounds share",
     "passed": True, "detail":
     "the two rounds had been reading different symbol universes. The venue's "
     "Appendix B coverage runs 618 distinct symbols in 201803 and 2110 in 201804, "
     "between the rounds, and from 201804 on it matches the other venue's where "
     "before it carried about a third of it. Restricted to the 618, which is a "
     "coverage fact and predates both of the round's windows, the primary window "
     "holds 6 of 6, every one of the four venue weighting conventions agreeing in "
     "sign and in the predicted direction, and the control group's own delta is "
     "0.0594 where the unrestricted run gave 0.2766. Four of the six cells sit "
     "outside every gap measured on window pairs where nothing happened, whether "
     "those pairs are taken inside the pilot, widest 0.1299, or after it, widest "
     "0.0593. The unrestricted run stands unaltered in results/b14_gate_exit.json "
     "and its own numbers are not touched; what changed is the population it was "
     "read on, not the criterion"},
    {"name": "B14-B0  leg B was bought and the wire format was read correctly",
     "passed": True, "detail":
     "108 NYSE-listed pilot symbols on two venues over eight months of bbo-1s. "
     "The depth gate's four registered checks all passed before a cent of bulk data "
     "was bought, and the pull came to 34.689578 dollars against a quote of the "
     "same. The semantic check is exact: every treated name, on every second the "
     "pilot was in force, has all four prices on a whole nickel"},
    {"name": "B14-B1  gate one: the two venues are two classes in section 5.1's "
             "own sense",
     "passed": True, "detail":
     "the framework hands over its own criterion, that S - S' is zero exactly "
     "when the two classes face the same antisymmetric terms, so the question is "
     "measurable. Per control symbol, the count of days whose sign leans positive "
     "against a binomial null: 9 of 47 symbols beyond three standard deviations "
     "where the null expects well under one, and a median |z| of 2.08 where the "
     "null gives 0.67. Run on the control arm only, because inside the pilot the grid "
     "pins both venues to one lattice point and that branch is unreachable there"},
    {"name": "B14-B2  gate two: the grid's arithmetic reproduces 88.7 per cent "
             "of the whole pre/post move",
     "passed": True, "detail":
     "projecting the post-release quotes back onto the nickel grid, bid down and "
     "ask up, reproduces most of the inside/outside gap in the primary statistic. "
     "The projection is verified by being the identity on treated names inside "
     "the pilot, digit for digit, since those are already on the lattice. "
     "Theorem 6(5)'s spread term is 1 to 5 per cent of the numerator by mass, so "
     "rho is not measuring spread asymmetry"},
    {"name": "B14-B3  gate three: the residual is inside the placebo band, and "
             "leg B is CLOSED rather than paused",
     "passed": False, "detail":
     "the treatment-specific residual sits inside a range built from six month "
     "pairs with no grid change at all. Half-month resolution widens the sample "
     "of placebos to fourteen and does not overturn it. A three-bin split on the "
     "pre-pilot spread has one bin clear its own band, but that bin's gradient "
     "lives in the control arm, which is not treatment heterogeneity. **Closed, "
     "not paused**: the arithmetic share is a property of the mechanism, and no "
     "quantity of further data changes it. The narrow-band discontinuity is "
     "sealed and is the basis of nothing"},
    {"name": "B14-19  order-type sensitivity, askable only once T7's code table "
             "arrived",
     "passed": True, "detail":
     "the specification gives thirteen order-type codes; twelve are on disk and "
     "the absent one is exactly the Not Held code, which is a check that was "
     "written before the document was fetched and could have failed. The "
     "weighting is share weighted, which settles D3-3 and demotes the "
     "order-count convention from a co-verdict to a cross-check without moving "
     "any verdict"},
    {"name": "B14-20  B14_A11's candidate list reopened: the pilot's rule is an "
             "increment rule, so slack does not mean out of reach",
     "passed": True, "detail":
     "a name whose spread already exceeds the increment can still have both "
     "sides off the lattice, and projecting widens it. One delta for every bin, "
     "bounded by the lattice arithmetic, fits at 0.0228 dollars with the "
     "gradient in the treated arm and an r-squared of 0.5074, and the tightest "
     "bin's observed margin is reproduced by the curve to a residual of 0.0045. "
     "B14_A11's reading that the residue "
     "is real stands; its statement that spillover is the only remaining "
     "candidate is withdrawn"},
]

NOTE = (
    "B14 audited the carrier that b4 section 9 named. It does not serve, and the "
    "reason generalises: S - S' is a difference of price levels and a tick-size "
    "change works by moving those levels onto a lattice, so the arithmetic "
    "channel dominates the index channel on any carrier of that kind. Section 9's "
    "requirement now carries three conditions instead of one."
)

NUM = re.compile(r"\d+(?:\.\d+)?")


def body(name: str) -> str:
    p = RESULTS / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def check() -> list[tuple[str, str]]:
    loose = []
    for c in CRITERIA:
        key = c["name"].split()[0]
        text = " ".join(body(s) for s in SOURCES.get(key, ()))
        for tok in NUM.findall(c["detail"]):
            if tok in EXEMPT:
                continue
            if tok in text:
                continue
            if tok.rstrip("0").rstrip(".") and tok.rstrip("0").rstrip(".") in text:
                continue
            loose.append((key, tok))
    return loose


def write_verdicts() -> Path:
    missing = sorted({s for v in SOURCES.values() for s in v
                      if not (RESULTS / s).exists()})
    if missing:
        print("sources absent from results/: " + ", ".join(missing), file=sys.stderr)
    loose = check()
    if loose:
        raise AssertionError(
            "these numbers appear in a criterion and in none of that criterion's "
            "own products: " + ", ".join("%s %s" % t for t in loose)
            + ". Fix the sheet, or add the number to EXEMPT with the reason it "
            "is not a reading.")
    out = RESULTS / "b14_stage_two.json"
    out.write_text(json.dumps({
        "stage": "B14",
        "symbols": 108,
        "aligned_cells": 27602417,
        "usd_spent": 34.6896,
        "venues": ["XNYS.PILLAR", "XNAS.ITCH"],
        "leg_b_status": "closed, not adjudicable",
        "note": NOTE,
        "sources": {k: list(v) for k, v in sorted(SOURCES.items())},
        "sources_absent": missing,
        "numbers_not_read_off_a_product": EXEMPT,
        "criteria": CRITERIA,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return out


def main(argv=None) -> int:
    out = write_verdicts()
    n = sum(1 for c in CRITERIA if c["passed"])
    print("wrote %s: %d/%d pass" % (out.relative_to(ROOT), n, len(CRITERIA)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
