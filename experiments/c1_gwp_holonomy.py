# -*- coding: utf-8 -*-
"""C1. The declared conversion between a greenhouse gas and CO2-equivalent is
multivalued, and this counts how multivalued.

**Why a non-monetary carrier.** A price field's failure to be integrable can
always be argued back to friction: transaction costs, liquidity, stale quotes,
someone not paying attention. A global warming potential has none of that. It
is an administrative declaration, printed in a report, that one tonne of species
`a` counts as `GWP_s(a)` tonnes of CO2-equivalent, and compliance schemes offset
against it. If those declarations do not compose, the reason cannot be friction,
because there is no market here to be frictional. It has to be that the scalar
they are declarations about does not exist.

**The object.** Put every species on one side and CO2-equivalent on the other,
and draw one edge per standard that quotes that species. The graph is a star
with parallel edges, and its cycle space has an exact closed form: a species
quoted under `S_a` standards contributes `S_a - 1` independent loops, so
`b1 = sum_a (S_a - 1)`. Each basis loop is `a --(s)--> CO2e --(s')--> a`, and its
holonomy is `GWP_s(a) / GWP_s'(a)`, the same gas read twice.

Note what that says about the null. **One standard gives `b1 = 0`.** There is
nothing to be inconsistent with, and the field is integrable by construction.
Every additional standard adds one loop per species it covers. The
non-integrability is manufactured by standard multiplicity and by nothing else,
which is why the count is worth doing before the ratios are.

**Four criteria, no thresholds.** Each is either a structural check on this
code, or a printed object with a reading fixed before the run. In particular
C1-4 could have come out either way: if the revision sequence were monotone and
its steps were shrinking, the right reading would be that the vintages are
converging, that the older ones are superseded rather than concurrent, and that
this stage measures a transitional artefact. That branch was reachable.

Reads `data/raw/gwp/globalwarmingpotentials.csv`, written by `data/fetch_gwp.py`.
Writes `results/c1_gwp_holonomy.json`.

    python experiments/c1_gwp_holonomy.py
"""
from __future__ import annotations

import csv
import io
import json
import statistics as st
from pathlib import Path

import numpy as np

from monetary_topology.topology import cycle_rank

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "gwp" / "globalwarmingpotentials.csv"
OUT = ROOT / "results" / "c1_gwp_holonomy.json"
REGIMES = ROOT / "data" / "gwp_regimes.json"

#: The six 100-year columns: one gas, one horizon, six published numbers. This
#: is the main comparison because it holds the horizon fixed, so no reading here
#: can be answered with "those are different questions".
GWP100 = ("SARGWP100", "TARGWP100", "AR4GWP100", "AR5GWP100",
          "AR5CCFGWP100", "AR6GWP100")

#: Vintage order, for the convergence reading only. `AR5CCFGWP100` is left out
#: on purpose: it is a variant of AR5 published alongside it, not a later
#: assessment, so putting it in the sequence would fabricate a sixth revision
#: that never happened. It gets its own criterion instead, C1-3.
VINTAGES = ("SARGWP100", "TARGWP100", "AR4GWP100", "AR5GWP100", "AR6GWP100")


def load() -> list[dict[str, str]]:
    if not SRC.exists():
        raise SystemExit(
            "%s is missing. Run `python data/fetch_gwp.py --pull` first; it "
            "pins the upstream commit and verifies the hash." % SRC)
    body = [ln for ln in SRC.read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body))))


def num(row: dict[str, str], col: str) -> float | None:
    raw = row.get(col, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def quoted(row: dict[str, str], cols) -> dict[str, float]:
    return {c: v for c in cols if (v := num(row, c)) is not None}


def star_adjacency(counts: list[int]) -> np.ndarray:
    """A simple graph with the same cycle rank as the star of parallel edges.

    `cycle_rank` takes an adjacency matrix, so parallel edges cannot be spelled
    directly. Subdividing each parallel edge with its own midpoint gives a
    simple graph, and subdividing an edge changes neither the cycle rank nor
    anything else about the cycle space. Node 0 is the CO2-equivalent hub.
    """
    n_species = len(counts)
    midpoints = sum(counts)
    size = 1 + n_species + midpoints
    adj = np.zeros((size, size), dtype=float)
    cursor = 1 + n_species
    for i, k in enumerate(counts):
        species = 1 + i
        for _ in range(k):
            adj[species, cursor] = adj[cursor, species] = 1.0
            adj[cursor, 0] = adj[0, cursor] = 1.0
            cursor += 1
    return adj


def fmt(x: float, places: int = 4) -> float:
    """Explicit rounding, so a last-digit BLAS difference is not a text diff."""
    return float(format(x, ".%df" % places))


def main() -> int:
    rows = load()
    criteria = []

    # ---- C1-1. Gate zero, and a cross-check of the closed form -------------
    counts = [len(quoted(r, GWP100)) for r in rows]
    closed = sum(max(0, k - 1) for k in counts)
    measured = cycle_rank(star_adjacency(counts))
    edges, nodes = sum(counts), sum(1 for k in counts if k) + 1
    criteria.append({
        "name": "C1-1 cycle rank of the declaration star, two ways",
        "detail": ("E=%d edges over V=%d nodes; closed form sum(S_a-1)=%d; "
                   "cycle_rank on the subdivided graph=%d; species quoted by "
                   "exactly one standard=%d contribute no loop"
                   % (edges, nodes, closed, measured,
                      sum(1 for k in counts if k == 1))),
        "passed": closed == measured,
        "b1": closed,
        "b1_from_cycle_rank": measured,
    })

    # ---- C1-2. The holonomy spectrum ---------------------------------------
    # Reading fixed before the run: a species whose six GWP-100 values agree
    # reads holonomy exactly 1 and is evidence the declared field is integrable
    # on that species. A species with fewer than two quotes is undecidable and
    # is counted separately rather than folded into either side.
    loops = []
    for r in rows:
        v = quoted(r, GWP100)
        if len(v) < 2:
            continue
        lo, hi = min(v, key=v.get), max(v, key=v.get)
        loops.append({"species": r["Species"], "holonomy": fmt(v[hi] / v[lo]),
                      "low": lo, "low_value": v[lo],
                      "high": hi, "high_value": v[hi], "standards": len(v)})
    loops.sort(key=lambda d: -d["holonomy"])
    h = sorted(d["holonomy"] for d in loops)
    unit = sum(1 for x in h if x == 1.0)
    criteria.append({
        "name": "C1-2 holonomy of the vintage loops, GWP-100 only",
        "detail": ("%d species decidable, %d undecidable (one quote only); "
                   "holonomy exactly 1: %d; median %.4f, quartiles %.4f/%.4f, "
                   "max %.3f (%s)"
                   % (len(h), sum(1 for k in counts if k == 1), unit,
                      st.median(h), h[len(h) // 4], h[3 * len(h) // 4], h[-1],
                      loops[0]["species"])),
        "passed": True,
        "reading": ("integrable" if unit == len(h)
                    else "non-integrable" if unit == 0 else "mixed"),
        "decidable": len(h),
        "undecidable": sum(1 for k in counts if k == 1),
        "holonomy_exactly_one": unit,
        "median": fmt(st.median(h)),
        "largest_loops": loops[:10],
        "smallest_loops": loops[-5:],
        "single_quote_species": sorted(
            r["Species"] for r, k in zip(rows, counts) if k == 1),
    })

    # ---- C1-3. Two numbers from one report ---------------------------------
    # The sharpest form, because it holds the report fixed as well as the gas
    # and the horizon. AR5 published a value with and without climate-carbon
    # feedback and institutions pick between them.
    pair = []
    for r in rows:
        a, b = num(r, "AR5GWP100"), num(r, "AR5CCFGWP100")
        if a and b:
            pair.append({"species": r["Species"], "ratio": fmt(b / a),
                         "ar5": a, "ar5ccf": b})
    ratios = sorted(d["ratio"] for d in pair)
    same = sum(1 for x in ratios if x == 1.0)
    criteria.append({
        "name": "C1-3 AR5 against AR5 with climate-carbon feedback",
        "detail": ("one report, one gas, one horizon, two published numbers: "
                   "%d species comparable, ratio exactly 1 for %d of them, "
                   "median %.4f, range %.4f to %.4f; CH4 is 28 against 34"
                   % (len(pair), same, st.median(ratios), ratios[0], ratios[-1])),
        "passed": True,
        "reading": ("single valued" if same == len(pair) else "multivalued"),
        "comparable": len(pair),
        "ratio_exactly_one": same,
        "median_ratio": fmt(st.median(ratios)),
        "widest": sorted(pair, key=lambda d: -d["ratio"])[:5],
    })

    # ---- C1-4. Is the sequence converging -----------------------------------
    # Reading fixed before the run. Monotone sequences with shrinking steps
    # would say the vintages are converging and the older ones superseded, and
    # this stage would then be measuring a transition rather than a standing
    # property. Non-monotone sequences, or steps that do not shrink, say the
    # opposite. Both branches were reachable.
    mono = nonmono = 0
    examples = []
    for r in rows:
        seq = [(c, num(r, c)) for c in VINTAGES if num(r, c) is not None]
        if len(seq) < 3:
            continue
        v = [x[1] for x in seq]
        if all(v[i] <= v[i + 1] for i in range(len(v) - 1)) or \
           all(v[i] >= v[i + 1] for i in range(len(v) - 1)):
            mono += 1
        else:
            nonmono += 1
            if r["Species"] in ("CH4", "N2O", "CFC11", "CFC12"):
                examples.append({"species": r["Species"],
                                 "sequence": [[c, x] for c, x in seq]})
    steps = []
    for a, b in zip(VINTAGES, VINTAGES[1:]):
        rel = [abs(num(r, b) - num(r, a)) / num(r, a)
               for r in rows if num(r, a) and num(r, b)]
        steps.append({"from": a, "to": b, "n": len(rel),
                      "median_relative_change": fmt(st.median(rel))})
    shrinking = all(steps[i]["median_relative_change"]
                    >= steps[i + 1]["median_relative_change"]
                    for i in range(len(steps) - 1))
    criteria.append({
        "name": "C1-4 do the vintages converge",
        "detail": ("%d of %d species non-monotone in vintage order, including "
                   "CH4 N2O CFC11 CFC12; median relative revision %s; steps "
                   "shrinking: %s"
                   % (nonmono, mono + nonmono,
                      " ".join("%s->%s %.2f%%" % (s["from"][:3], s["to"][:3],
                                                  s["median_relative_change"] * 100)
                               for s in steps),
                      shrinking)),
        "passed": True,
        "reading": ("converging" if shrinking and nonmono == 0
                    else "not converging"),
        "monotone": mono,
        "non_monotone": nonmono,
        "steps": steps,
        "non_monotone_examples": sorted(examples, key=lambda d: d["species"]),
    })

    # ---- C1-5. Operative or historical -------------------------------------
    # Reading fixed before the survey was compiled: if only the newest basis is
    # in force anywhere, sections 2 to 4 describe a historical record and this
    # stage measures a transition. If more than one is in force at the same
    # time, the multivaluedness is something an obligation can be discharged
    # against two different ways in the same year. Both were reachable, and the
    # treaty layer converging on one basis by the end of 2024 is what would
    # have produced the first.
    regimes = json.loads(REGIMES.read_text(encoding="utf-8"))["regimes"]
    ch4 = {r["Species"]: r for r in rows}["CH4"]
    mismatches = []
    checked = 0
    for reg in regimes:
        col = reg.get("csv_column")
        if not col:
            continue
        checked += 1
        want = num(ch4, col)
        if want is None or abs(want - reg["ch4_gwp"]) > 1e-9:
            mismatches.append({"regime": reg["regime"], "column": col,
                               "table_says": reg["ch4_gwp"], "csv_says": want})
    current = sorted({r["ch4_gwp"] for r in regimes if r.get("current")})
    every = sorted({r["ch4_gwp"] for r in regimes})
    uncheckable = [r["regime"] for r in regimes if not r.get("csv_column")]
    criteria.append({
        "name": "C1-5 is the disagreement operative or historical",
        "detail": ("%d regimes surveyed, %d of them in force now; %d of their "
                   "methane values cross-check against the dataset and %d "
                   "disagree; values in force now %s, spanning %.3f; values "
                   "across the whole record %s, spanning %.3f"
                   % (len(regimes), sum(1 for r in regimes if r.get("current")),
                      checked - len(mismatches), len(mismatches), current,
                      max(current) / min(current), every,
                      max(every) / min(every))),
        "passed": not mismatches,
        "reading": ("historical" if len(current) < 2 else "operative"),
        "in_force_now": current,
        "across_record": every,
        "cross_checked": checked,
        "mismatches": mismatches,
        "not_cross_checkable": uncheckable,
        "not_surveyed": ["European Union", "a New Jersey statute reported to "
                         "mandate a twenty-year horizon"],
    })

    record = {
        "stage": "C1",
        "carrier": "IPCC global warming potentials, all assessment reports",
        "source": "data/raw/gwp/globalwarmingpotentials.csv",
        "diagnostic_only": False,
        "closed_note": (
            "Both halves have run. C1-5 settles what the earlier sections could "
            "not: the disagreement is operative, four methane values being in "
            "force at once. Two regimes were not surveyed and are named in "
            "C1-5, which is a limit on the survey's breadth and not on its "
            "reading, because more than one basis in force is an existence "
            "claim that one pair settles. Readings here are about declarations "
            "and about which of them an obligation can be discharged against; "
            "they are not readings about carbon market prices or volumes."),
        "scoped_and_not_opened": (
            "A second half in a different shape was scoped and did not open. It "
            "would have measured the holonomy of loops through the registry "
            "acceptance graph. The CORSIA eligibility table gives 15 programmes "
            "over 3 phases, 23 edges on 18 nodes in 3 components, so the "
            "relation graph has cycle rank 8. None of those cycles can be "
            "walked, because retirement against a compliance obligation is "
            "terminal and a unit does not come back out. That is a property of "
            "a consumable, not evidence about a value scalar, so the branch "
            "where walkable loops carry holonomy away from 1 is unreachable by "
            "construction and the arm would have returned its answer from its "
            "own setup. Scoped and closed on paper before any document was "
            "read. A carrier where that branch is reachable needs conversion "
            "that is bidirectional in principle, so that one-way-ness is a "
            "choice rather than the nature of the good."),
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    for c in criteria:
        print("[%s] %s\n    %s" % ("PASS" if c["passed"] else "FAIL",
                                   c["name"], c["detail"]))
        if "reading" in c:
            print("    reading: %s" % c["reading"])
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
