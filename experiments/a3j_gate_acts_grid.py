"""A3j: does the gate keep acting on the mechanism along the whole grid?

A3h answered the inertness objection at one point: between the two cells that
differ only in the gate, the gate moves 19.8 nodes' cycle counts against the
other channel's 17.4 and 72.4 of total absolute cycle change against 84.2,
**eighty-six per cent of it**. A3i then pooled every point on record and found
the gate cell sign-stable at none of 57 and never above 2.94 in absolute value
while the loop cell reaches 24.83.

**The join between those two is one point wide.** The mechanical ratio was
measured at the registered carrier only, so at every other point on the grid
"the gate cell is noise" and "the gate is inert there" are not yet separated.
This file measures the ratio along `a3g`'s declared stretch grid and prints the
gate cell's gap beside it.

**The gap column is read from `a3g`'s record rather than recomputed**: same
grid, same seeds, same rounds, and recomputing it would only risk the two
disagreeing.

**Reading, declared before the run.** If the ratio stays of the same order
across the grid while the gate cell stays noise, the inertness objection is
answered on the grid rather than at one point. If the ratio collapses somewhere,
those values are exactly where the gate cell's zero cannot be separated from an
inert treatment, **and they are named** rather than dropped.

No threshold is placed on any estimator. Every criterion is structural or an
object printed in full.

Usage::

    python experiments/a3j_gate_acts_grid.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from a3c_load_bearing import (  # noqa: E402
    CELLS,
    FIXED,
    REGISTERED_ROUNDS,
    REGISTERED_SEEDS,
    build,
)
from a3g_widened_population import STRETCH_GRID  # noqa: E402
from a3h_gate_acts import acts  # noqa: E402

OUT = ROOT / "results" / "a3j_gate_acts_grid.json"
A3G = ROOT / "results" / "a3g_widened_population.json"
A3H = ROOT / "results" / "a3h_gate_acts.json"



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

def mean(rows, key):
    return sum(r[key] for r in rows) / len(rows)


def one(stretch: float, seeds: range, rounds: int) -> dict:
    gate_acts, terms_acts = [], []
    for s in seeds:
        both = build(s, rounds, stretch=stretch, **FIXED, **CELLS["both"])
        no_gate = build(s, rounds, stretch=stretch, **FIXED, **CELLS["H1_only"])
        no_terms = build(s, rounds, stretch=stretch, **FIXED, **CELLS["H0_only"])
        gate_acts.append(acts(both, no_gate, both.centrality))
        terms_acts.append(acts(both, no_terms, both.centrality))
    g_cycles = mean(gate_acts, "total_absolute_cycle_change")
    t_cycles = mean(terms_acts, "total_absolute_cycle_change")
    return {
        "stretch": stretch,
        "gate_nodes_moved": mean(gate_acts, "nodes_with_a_different_cycle_count"),
        "terms_nodes_moved": mean(terms_acts, "nodes_with_a_different_cycle_count"),
        "gate_total_abs_cycle_change": g_cycles,
        "terms_total_abs_cycle_change": t_cycles,
        "mechanical_ratio": (g_cycles / t_cycles) if t_cycles else float("nan"),
        "gate_extensive_in": mean(gate_acts, "extensive_in"),
        "gate_extensive_out": mean(gate_acts, "extensive_out"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)

    rows = [one(s, seeds, args.rounds) for s in STRETCH_GRID]

    a3g = json.loads(A3G.read_text(encoding="utf-8"))
    gaps = {r["stretch"]: r for r in a3g["rows"]}
    for r in rows:
        src = gaps.get(r["stretch"])
        r["gate_cell_gap"] = src["gaps"]["H0_only"] if src else None
        r["loop_cell_gap"] = src["gaps"]["H1_only"] if src else None
        r["gate_cell_same_sign"] = bool(src["same_sign"]["H0_only"]) if src else None
        r["joined_to_a3g"] = src is not None

    print("stretch grid imported from a3g, %d seeds, %d rounds. Every value is "
          "printed.\n" % (args.seeds, args.rounds))
    print("  %8s %11s %11s %8s %11s %11s %7s"
          % ("stretch", "gate |dc|", "terms |dc|", "ratio", "gate cell", "loop cell", "ssGate"))
    for r in rows:
        print("  %8.1f %11.1f %11.1f %8.3f %11.4f %11.4f %7s"
              % (r["stretch"], r["gate_total_abs_cycle_change"],
                 r["terms_total_abs_cycle_change"], r["mechanical_ratio"],
                 r["gate_cell_gap"], r["loop_cell_gap"], r["gate_cell_same_sign"]))

    ratios = [r["mechanical_ratio"] for r in rows]
    lo = min(rows, key=lambda r: r["mechanical_ratio"])
    hi = max(rows, key=lambda r: r["mechanical_ratio"])
    print("\nsmallest ratio %.3f at stretch %.1f; largest %.3f at stretch %.1f"
          % (lo["mechanical_ratio"], lo["stretch"], hi["mechanical_ratio"], hi["stretch"]))
    print("the gate never acts at all where its total |d cycles| is zero: %s"
          % ([r["stretch"] for r in rows if r["gate_total_abs_cycle_change"] == 0] or "nowhere"))

    a3h = json.loads(A3H.read_text(encoding="utf-8"))
    at3 = next(r for r in rows if r["stretch"] == 3.0)
    ref_gate = sum(a["total_absolute_cycle_change"] for a in a3h["gate_acts"]) / len(a3h["gate_acts"])
    ref_terms = sum(a["total_absolute_cycle_change"] for a in a3h["terms_acts"]) / len(a3h["terms_acts"])
    reproduced = (abs(at3["gate_total_abs_cycle_change"] - ref_gate) < 1e-9
                  and abs(at3["terms_total_abs_cycle_change"] - ref_terms) < 1e-9)
    print("\nstretch 3.0 against A3h's registered block: gate %.1f vs %.1f, "
          "terms %.1f vs %.1f, reproduced %s"
          % (at3["gate_total_abs_cycle_change"], ref_gate,
             at3["terms_total_abs_cycle_change"], ref_terms, reproduced))

    criteria = [
        {"name": "A3j-1  the grid and the join are the same design as A3g's",
         "passed": all(r["joined_to_a3g"] for r in rows) and len(rows) == len(STRETCH_GRID),
         "detail": "%d stretch values imported from a3g_widened_population, all %d joined to "
                   "its record by stretch value" % (len(STRETCH_GRID), len(rows))},
        {"name": "A3j-2  print the mechanical ratio at every stretch value",
         "passed": True,
         "detail": "; ".join("%.1f: %.3f" % (r["stretch"], r["mechanical_ratio"]) for r in rows)},
        {"name": "A3j-3  print the gate cell's gap and sign stability beside the ratio",
         "passed": True,
         "detail": "; ".join("%.1f: gate cell %.4f same-sign %s, ratio %.3f"
                             % (r["stretch"], r["gate_cell_gap"], r["gate_cell_same_sign"],
                                r["mechanical_ratio"]) for r in rows)},
        {"name": "A3j-4  stretch 3.0 reproduces A3h's registered block to the digit it prints",
         "passed": bool(reproduced),
         "detail": "gate %.1f against %.1f, terms %.1f against %.1f"
                   % (at3["gate_total_abs_cycle_change"], ref_gate,
                      at3["terms_total_abs_cycle_change"], ref_terms)},
    ]

    record = {
        "stage": "A3j",
        "step": "gate_acts_grid",
        "diagnostic_only": True,
        "diagnostic_reason": ("A3-8 stays void. This extends A3h's inertness measurement from one "
                              "carrier to A3g's declared stretch grid and joins A3g's gap column "
                              "rather than recomputing it."),
        "seeds": args.seeds,
        "rounds": args.rounds,
        "stretch_grid": list(STRETCH_GRID),
        "smallest_ratio": lo["mechanical_ratio"],
        "smallest_ratio_at_stretch": lo["stretch"],
        "largest_ratio": hi["mechanical_ratio"],
        "largest_ratio_at_stretch": hi["stretch"],
        "rows": rows,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(fixed(record), indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\nwrote %s: %d criteria, %d passing"
          % (OUT.name, len(criteria), sum(1 for c in criteria if c["passed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
