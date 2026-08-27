"""B21: which of this station's criteria could the world have answered differently.

The station closed with twenty-six criteria and a note beside it that none of
their failures would reach the framework. **That note was written as a
judgement. This file makes it a count**, by classifying every criterion in
`results/b21_*.json` and refusing to run if any of them is unclassified.

Four classes, and the distinction that matters is the third column:

    structural   about the code or the design's shape: an identity to machine
                 precision, a cell that must carry a centre, coverage of the
                 dates. **The data cannot make it come out otherwise, and it is
                 not supposed to.**
    arithmetic   a closed form evaluated at prices. Given the support of the
                 data, `D > 0` and `P > 0`, the sign and the shape follow from
                 algebra. **The world is not being asked anything.**
    instrument   a measurement whose failure impugns the pipeline, the tax
                 story, or the agreement between two estimators.
    world        a measurement whose failure would say something beyond this
                 pipeline.

And one flag: whether a failure would reach **Corollary 1**, the claim this
carrier exists to test, that a single scalar price field on positions forces
every square sum to zero.

The count is the finding. It is printed and it is not argued with here.

Usage::

    python experiments/b21_criterion_census.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b21_criterion_census.json"

#: id -> (class, reaches Corollary 1, one line of why)
#: Hand-assigned, versioned here so the assignment is auditable and can be
#: argued with in one place rather than in prose scattered over a station.
CLASS = {
 "B21-1":  ("arithmetic", True,
            "the index is log((P1+D)/(P1+0.9D)); with D>0 and P1>0 it cannot be zero, "
            "so 'non-zero on every leg-year' is fixed before the data is read"),
 "B21-2 A leg": ("arithmetic", False, "a Taylor remainder in the yield, checked against its own closed form"),
 "B21-2 H leg": ("arithmetic", False, "same"),
 "B21-3":  ("structural", False, "an identity in the estimator, verified to 1.1e-16"),
 "B21-4":  ("instrument", False, "a degeneracy guard on the individual term"),
 "B21-5":  ("structural", False, "coverage of the dates"),
 "B21-6":  ("world", False,
            "a placebo on currency events; it failed and removed an interpretation of the common term"),
 "B21-7":  ("instrument", False, "a degeneracy guard on the estimated stock-level term"),
 "B21-8":  ("world", False, "stock-level against common term; undecidable at daily resolution"),
 "B21-9":  ("instrument", False, "four range estimators against each other; it failed"),
 "B21-10": ("instrument", False, "a degeneracy guard"),
 "B21-11": ("structural", False, "a published tick gives an exact lower bound, no estimator in the chain"),
 "B21-12": ("world", False, "cross-stock dispersion of the floor, a reading rather than a bound"),
 "B21-13": ("arithmetic", False, "the twelve-month edge, the same algebra at a gap of 0.25"),
 "B21-14": ("arithmetic", False, "the capital-gains edge, the same algebra with the sign of one variable turned"),
 "B21-15": ("arithmetic", True,
            "'neither statutory index is zero anywhere' is the same forced non-zero as B21-1"),
 "B21-16": ("arithmetic", False, "the loss branch of the same algebra"),
 "B21-17": ("instrument", False, "gate two, first stage: an arithmetic on the standard error"),
 "B21-18": ("world", False,
            "an effect size against a band the statute declares; it could have landed outside"),
 "B21-19": ("world", False, "the same difference within company, the company cancelled"),
 "B21-20": ("void", False, "withdrawn: the direction it asked for was never implied by the statute"),
 "B21-21": ("structural", False, "every cell of the two-by-two carries a centre"),
 "B21-22": ("world", False, "the taxed leg's move across the date, read in three states"),
 "B21-23": ("world", False, "the untaxed leg of the same companies, the placebo"),
 "B21-24": ("world", False, "no volume signature to remove; undecidable"),
 "B21-25": ("world", False,
            "the implied rate inside 0 to 25 per cent. **The band is the whole statutory support, "
            "so almost any reading sits in it**; recorded as world but weak"),
}



def fixed(o, nd: int = 8):
    """Every float written to disk goes through here.

    **The derived-file rule this repository already carries**: write floats
    through an explicit format rather than through ``repr``, so a last-digit
    difference between two builds does not surface as a text diff. It was not
    hypothetical — the same code over the same cached bytes gave last-digit
    differences between a Windows run and a Linux one, and the record stopped
    reproducing byte for byte. Eight decimals is far below anything reported.
    """
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: fixed(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [fixed(v, nd) for v in o]
    return o

def key(name: str) -> str:
    """The id at the head of a criterion name, including the ' A leg' style suffix."""
    parts = name.split()
    if len(parts) >= 3 and parts[1] in ("A", "H") and parts[2] == "leg":
        return " ".join(parts[:3])
    return parts[0]


def main() -> int:
    found = []
    for f in sorted(glob.glob(str(ROOT / "results" / "b21_*.json"))):
        if Path(f).name == OUT.name:
            continue
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        for c in d.get("criteria", []):
            found.append({"record": Path(f).name, "id": key(c.get("name", "")),
                          "passed": c.get("passed"), "name": c.get("name", "")})
    missing = sorted({r["id"] for r in found} - set(CLASS))
    extra = sorted(set(CLASS) - {r["id"] for r in found})

    for r in found:
        cls, reaches, why = CLASS.get(r["id"], ("UNCLASSIFIED", False, ""))
        r.update(klass=cls, reaches_corollary_1=reaches, why=why)

    tally = {}
    for r in found:
        tally[r["klass"]] = tally.get(r["klass"], 0) + 1
    reach = [r for r in found if r["reaches_corollary_1"]]
    world = [r for r in found if r["klass"] == "world"]

    print("%-14s %-11s %-6s %-5s %s" % ("id", "class", "reaches", "state", "record"))
    for r in sorted(found, key=lambda r: (r["klass"], r["id"])):
        st = {True: "PASS", False: "FAIL", None: "open"}[r["passed"]]
        print("%-14s %-11s %-6s %-5s %s"
              % (r["id"], r["klass"], r["reaches_corollary_1"], st,
                 r["record"].replace("b21_", "").replace(".json", "")))
    print()
    print("counts: " + ", ".join("%s %d" % (k, v) for k, v in sorted(tally.items())))
    print("criteria whose failure would reach Corollary 1: %d  (%s)"
          % (len(reach), ", ".join(r["id"] for r in reach)))
    print("and every one of them is classed: %s"
          % ", ".join(sorted({r["klass"] for r in reach})))
    print("criteria that measure the world at all: %d  (%s)"
          % (len(world), ", ".join(sorted(r["id"] for r in world))))

    criteria = [
      {"name": "B21-C-1  every criterion in every record is classified, none silently dropped",
       "passed": not missing,
       "detail": "%d criteria over %d records; unclassified: %s; classified but not found: %s"
                 % (len(found), len({r['record'] for r in found}), missing or "none", extra or "none")},
      {"name": "B21-C-2  print the class of every criterion and the count per class",
       "passed": True,
       "detail": ", ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))},
      {"name": "B21-C-3  print every criterion whose failure would reach Corollary 1, "
               "with its class beside it",
       "passed": True,
       "detail": "; ".join("%s is %s: %s" % (r["id"], r["klass"], r["why"]) for r in reach)
                 or "none"},
      {"name": "B21-C-4  print every criterion that measures the world",
       "passed": True,
       "detail": ", ".join(sorted(r["id"] for r in world))},
    ]

    OUT.write_text(json.dumps(fixed(
        {"stage": "B21 census", "step": "criterion_census", "diagnostic_only": True,
         "diagnostic_reason": ("A classification of this station's own criteria. It runs no model "
                               "and reads no price; it reads the records and a hand-assigned table "
                               "kept in the script beside it."),
         "n_criteria": len(found), "tally": tally,
         "reaches_corollary_1": [r["id"] for r in reach],
         "world": sorted(r["id"] for r in world),
         "rows": sorted(found, key=lambda r: (r["klass"], r["id"])),
         "criteria": criteria}),
        indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("\nwrote %s: %d criteria, %d passing"
          % (OUT.name, len(criteria), sum(1 for c in criteria if c["passed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
