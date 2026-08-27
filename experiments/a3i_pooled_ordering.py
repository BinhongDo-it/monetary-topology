"""A3i: pool every point on record where the two A3-8' cells were both computed.

This runs no model. It reads records already on disk and tallies the two
clauses of A3-8' separately:

    clause one   the loop-sum-only cell is same-sign across seeds
    clause two   the loop-sum-only cell's gap exceeds the gate-only cell's

Theorem 2 licenses an ordering and not a level, so clause two is the one the
theorem speaks to. Clause one is a stability statement the theorem never made.

Criteria are structural or printed objects. No threshold is placed on any
estimator.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# (path, carrier label, arm label, how to read it)
A7_GRIDS = [
    ("a7_continuous_c.json", "D_reach", "uniform"),
    ("a7_continuous_c.offparam_grid_preferential_20x300.json", "D_reach", "preferential"),
]
A7_FIXED = [
    ("a7_continuous_c.offparam_dfixed_uniform_20x300.json", "D_fixed"),
    ("a7_continuous_c.offparam_dfixed_preferential_20x300.json", "D_fixed"),
]



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

def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def collect():
    rows = []
    for name, carrier, arm in A7_GRIDS:
        d = load(name)
        for r in d["rows"]:
            g, ss = r["gaps"], r["same_sign_across_seeds"]
            rows.append({
                "source": name, "carrier": carrier, "arm": arm,
                "point": "s=%s" % r["s"], "seeds": d["seeds"],
                "loop_only": g["H1_only"], "gate_only": g["H0_only"],
                "loop_same_sign": bool(ss["H1_only"]),
                "gate_same_sign": bool(ss["H0_only"]),
            })
    for name, carrier in A7_FIXED:
        d = load(name)
        res = d["result"]
        for conv in sorted(res["cells"]["H1_only"]):
            for s in res["points"]:
                k = str(s)
                h1 = res["cells"]["H1_only"][conv][k]
                h0 = res["cells"]["H0_only"][conv][k]
                rows.append({
                    "source": name, "carrier": carrier + "/" + conv,
                    "arm": res["arm"], "point": "s=%s" % s, "seeds": d["seeds"],
                    "loop_only": h1["mean"], "gate_only": h0["mean"],
                    "loop_same_sign": bool(h1["same_sign_across_seeds"]),
                    "gate_same_sign": bool(h0["same_sign_across_seeds"]),
                })
    d = load("a3g_widened_population.json")
    for r in d["rows"]:
        g, ss = r["gaps"], r["same_sign"]
        rows.append({
            "source": "a3g_widened_population.json", "carrier": "A3 default",
            "arm": "stretch sweep", "point": "stretch=%s" % r["stretch"],
            "seeds": d["seeds"],
            "loop_only": g["H1_only"], "gate_only": g["H0_only"],
            "loop_same_sign": bool(ss["H1_only"]),
            "gate_same_sign": bool(ss["H0_only"]),
        })
    d = load("a3h_gate_acts.json")
    for block, label in (("registered_seeds", "seeds 0-4"), ("fresh_seeds", "seeds 5-9")):
        g, ss = d[block]["gaps"], d[block]["same_sign"]
        rows.append({
            "source": "a3h_gate_acts.json", "carrier": "A3 default",
            "arm": "seed block", "point": label, "seeds": d["seeds"],
            "loop_only": g["H1_only"], "gate_only": g["H0_only"],
            "loop_same_sign": bool(ss["H1_only"]),
            "gate_same_sign": bool(ss["H0_only"]),
        })
    return rows


def dedupe(rows):
    """Two pairs of rows are the same run read twice.

    D_reach at s = 0 is arm-independent (a7_continuous_c.md 11.4), so the
    uniform and preferential grids print the same numbers there.
    A3h's registered block is A3g's stretch 3.0 row.
    Both are dropped by exact value match, and what was dropped is printed.
    """
    seen, kept, dropped = {}, [], []
    for r in rows:
        key = (round(r["loop_only"], 9), round(r["gate_only"], 9), r["seeds"])
        if key in seen and seen[key]["carrier"].split("/")[0] == r["carrier"].split("/")[0]:
            dropped.append({"dropped": r["source"] + " " + r["point"],
                            "same_as": seen[key]["source"] + " " + seen[key]["point"]})
            continue
        seen[key] = r
        kept.append(r)
    return kept, dropped


def main():
    rows = collect()
    rows, dropped = dedupe(rows)
    rows.sort(key=lambda r: (r["carrier"], r["arm"], r["point"]))

    gate_stable = [r for r in rows if r["gate_same_sign"]]
    loop_stable = [r for r in rows if r["loop_same_sign"]]
    ordering_fails = [r for r in rows if not (r["loop_only"] > r["gate_only"])]

    print("points on record after de-duplication: %d" % len(rows))
    for r in dropped:
        print("  dropped as a duplicate: %s == %s" % (r["dropped"], r["same_as"]))
    print()
    print("%-24s %-14s %-14s %10s %10s %6s %6s %6s"
          % ("carrier", "arm", "point", "loop", "gate", "ssLoop", "ssGate", "L>G"))
    for r in rows:
        print("%-24s %-14s %-14s %10.4f %10.4f %6s %6s %6s"
              % (r["carrier"], r["arm"], r["point"], r["loop_only"], r["gate_only"],
                 r["loop_same_sign"], r["gate_same_sign"],
                 r["loop_only"] > r["gate_only"]))
    print()
    print("clause two, ordering  loop > gate at %d of %d points" % (len(rows) - len(ordering_fails), len(rows)))
    print("clause one, stability loop same-sign at %d of %d points" % (len(loop_stable), len(rows)))
    print("gate cell same-sign             at %d of %d points" % (len(gate_stable), len(rows)))
    print("largest |gate cell| anywhere    %.4f" % max(abs(r["gate_only"]) for r in rows))
    print("largest |loop cell| anywhere    %.4f" % max(abs(r["loop_only"]) for r in rows))
    print()
    print("every point where the ordering does not hold, with the gate value beside it:")
    for r in ordering_fails:
        print("  %-24s %-14s %-14s loop %9.4f  gate %9.4f  gate is exactly zero: %s"
              % (r["carrier"], r["arm"], r["point"], r["loop_only"], r["gate_only"],
                 r["gate_only"] == 0.0))

    criteria = [
        {"name": "A3i-1  every pooled record loads and yields both cells",
         "passed": len(rows) > 0 and all(
             isinstance(r["loop_only"], float) and isinstance(r["gate_only"], float) for r in rows),
         "detail": "%d points pooled from %d records, %d duplicate rows dropped by exact value match"
                   % (len(rows), len({r["source"] for r in rows}), len(dropped))},
        {"name": "A3i-2  print every point at which the gate cell is sign-stable across seeds",
         "passed": True,
         "detail": "sign-stable at %d of %d points%s; largest |gate cell| anywhere is %.4f"
                   % (len(gate_stable), len(rows),
                      "" if not gate_stable else ": " + ", ".join(
                          r["carrier"] + " " + r["point"] for r in gate_stable),
                      max(abs(r["gate_only"]) for r in rows))},
        {"name": "A3i-3  print every point at which the loop cell does not exceed the gate cell",
         "passed": True,
         "detail": "; ".join(
             "%s %s loop %.4f gate %.4f gate exactly zero %s"
             % (r["carrier"], r["point"], r["loop_only"], r["gate_only"], r["gate_only"] == 0.0)
             for r in ordering_fails) or "none"},
        {"name": "A3i-4  the two clauses of A3-8' are tallied separately",
         "passed": True,
         "detail": "ordering %d/%d, stability %d/%d"
                   % (len(rows) - len(ordering_fails), len(rows), len(loop_stable), len(rows))},
    ]

    record = {
        "stage": "A3i",
        "step": "pooled_ordering",
        "diagnostic_only": True,
        "diagnostic_reason": ("A3-8 stays void. This runs no model: it re-reads records already "
                              "on disk and tallies the two clauses of A3-8' separately, because "
                              "Theorem 2 licenses the ordering and not the stability."),
        "points": len(rows),
        "ordering_holds": len(rows) - len(ordering_fails),
        "loop_sign_stable": len(loop_stable),
        "gate_sign_stable": len(gate_stable),
        "max_abs_gate_cell": max(abs(r["gate_only"]) for r in rows),
        "max_abs_loop_cell": max(abs(r["loop_only"]) for r in rows),
        "duplicates_dropped": dropped,
        "ordering_failures": ordering_fails,
        "rows": rows,
        "criteria": criteria,
    }
    out = RESULTS / "a3i_pooled_ordering.json"
    out.write_text(json.dumps(fixed(record), indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\nwrote %s" % out.name)


if __name__ == "__main__":
    main()
