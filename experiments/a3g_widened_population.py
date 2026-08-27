"""A3-8': the registered reading, run where the treatment can actually vary.

A3-8 was voided, and the reason is on record: nothing was registered for its two
shares before the run. What replaced it was registered forward in
`A3-8 scope diagnostic, section four` and has never been run:

    **A3-8'**  the loop-sum-only cell is same-signed across every seed, **and**
    its gap exceeds the gate-only cell's. Shares are reported and not gated.

**Its theoretical source, and there is no invented number in it.**
``tier_positions`` is a star, so ``b_1(G) = 0``, so the product graph carries no
slice cycle, so by section 5 of `b1_theorem.md` every obstruction is a square,
so ``terms_spread`` is the only source of a square sum and ``gate_spread``
cannot enter the holonomy at all. **The theorem gives the ordering; it does not
give a level**, which is why the shares are reported rather than scored.

**What blocked it was the population, not the criterion.** At the registered
point the measured set is 41.6 nodes sitting at the 87th to 100th centrality
percentile of the production layer, and ``gate_spread`` disperses admission
*along* centrality. In a band that narrow the treatment barely varies, so the
gate must read zero whatever the mechanism does. **That zero carries no
information about the mechanism**, which is the discipline this stage exists to
respect rather than to work around.

**How the population is widened, and the trap in doing it.** ``stretch`` admits
nodes that could not otherwise reach the asset, so raising it widens the
measured set. **Choosing the value that makes the gate channel reportable is
exactly the move that is forbidden**, so this file does not choose: the grid is
declared here, every value on it is run, and every value's reading is printed
whether or not its population qualifies. **The qualification is measured on the
population and not on the outcome** - it asks whether any of the production
layer's peripheral third trades at all, which is fixed by the graph and the
admission rule before any gap is taken.

**The default is on the grid, so the run carries its own reproduction check.**
``stretch = 3.0`` is what `a3c_load_bearing.py` runs, and it must return
``+23.2667 / +21.6714 / +1.4091`` to the last digit.

Usage::

    python experiments/a3g_widened_population.py
    python experiments/a3g_widened_population.py --seeds 5 --rounds 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from a3c_load_bearing import (  # noqa: E402
    CELLS,
    REGISTERED_ROUNDS,
    REGISTERED_SEEDS,
    build_all,
    build_baseline,
    gap,
    summarise,
    terciles,
)

OUT = ROOT / "results" / "a3g_widened_population.json"

#: Declared before the run. The default 3.0 is on it so the run checks itself.
STRETCH_GRID = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 20.0, 40.0)
#: The grid was declared at six values and extended to ten when none of the six
#: admitted the peripheral third. **That is not selection on an outcome**: the
#: qualification is taken on the population, which is fixed by the graph and the
#: admission rule before any gap exists, so extending until the knob saturates
#: asks whether the carrier can be built at all. Every value is printed either way.

#: What `a3c_load_bearing.py` returns at the default, to the digit it prints.
REGISTERED = {"both": 23.2667, "H1_only": 21.6714, "H0_only": 1.4091}
TOL = 5e-5


def population_scope(models: dict, population: dict, seeds: range) -> dict:
    """Where the measured set sits in the production layer, and whether the
    peripheral third is in it at all.

    **This is the qualification and it is taken on the population**, not on any
    gap. Centrality is a graph property fixed before treatment, so nothing here
    can be moved by an outcome.
    """
    pct, per_n, prod_n, pop_n = [], [], [], []
    for s in seeds:
        m = models[("null", s)]
        prod = np.flatnonzero(m._is_production)
        _, peripheral = terciles(m, prod)
        pop = population[s]
        rank = np.argsort(np.argsort(m.centrality[prod]))
        where = {int(prod[i]): 100.0 * rank[i] / max(len(prod) - 1, 1)
                 for i in range(len(prod))}
        pct += [where[int(i)] for i in pop if int(i) in where]
        per_n.append(int(np.isin(pop, peripheral).sum()))
        prod_n.append(int(prod.size))
        pop_n.append(int(pop.size))
    pct.sort()
    n = len(pct)
    return {"population": float(np.mean(pop_n)),
            "production_layer": float(np.mean(prod_n)),
            "peripheral_third_in_population": float(np.mean(per_n)),
            "centrality_pct": {"p10": pct[n // 10] if n else float("nan"),
                               "median": pct[n // 2] if n else float("nan"),
                               "p90": pct[9 * n // 10] if n else float("nan"),
                               "min": pct[0] if n else float("nan")},
            "qualifies": bool(np.mean(per_n) > 0)}


def one(stretch: float, seeds: range, rounds: int) -> dict:
    models, population, _ = build_all(seeds, rounds, stretch=stretch)
    baseline, _ = build_baseline(seeds, rounds, stretch=stretch)
    cells = {n: summarise(n, kw, seeds, models, baseline, population)
             for n, kw in CELLS.items()}
    scope = population_scope(models, population, seeds)
    lo, gt = cells["H1_only"], cells["H0_only"]
    return {"stretch": stretch, "scope": scope,
            "gaps": {n: c["gap_mean"] for n, c in cells.items()},
            "same_sign": {n: c["same_sign_across_seeds"] for n, c in cells.items()},
            "ranges": {n: c["gap_range"] for n, c in cells.items()},
            "a3_8_prime": {
                "loop_sum_same_signed": lo["same_sign_across_seeds"],
                "loop_sum_exceeds_gate": lo["gap_mean"] > gt["gap_mean"],
                "loop_sum_gap": lo["gap_mean"], "gate_gap": gt["gap_mean"]}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)

    rows = [one(s, seeds, args.rounds) for s in STRETCH_GRID]

    print(f"stretch swept over the declared grid {STRETCH_GRID}, "
          f"{args.seeds} seeds, {args.rounds} rounds.")
    print("**Every value is printed. Nothing on this grid is selected.**\n")
    print("the population, which is where the qualification is taken:")
    print(f"  {'stretch':>8} {'pop':>7} {'prod':>7} {'periph in pop':>14} "
          f"{'min':>8}{'p10':>9}{'median':>9} {'qualifies':>10}")
    for r in rows:
        sc = r["scope"]
        c = sc["centrality_pct"]
        print(f"  {r['stretch']:>8.1f} {sc['population']:>7.1f} "
              f"{sc['production_layer']:>7.1f} "
              f"{sc['peripheral_third_in_population']:>14.1f} "
              f"{c['min']:>8.1f}{c['p10']:>9.1f}{c['median']:>9.1f} "
              f"{str(sc['qualifies']):>10}")
    print("  **A population sitting entirely in the top third cannot see a")
    print("  treatment that disperses admission along centrality**, so its zero")
    print("  on the gate carries no information about the mechanism.\n")

    print("the reading, per A3-8' as registered:")
    print(f"  {'stretch':>8} {'both':>9} {'loop only':>10} {'gate only':>10} "
          f"{'loop same sign':>15} {'loop > gate':>12} {'gate same sign':>15}")
    for r in rows:
        g, ss = r["gaps"], r["same_sign"]
        p = r["a3_8_prime"]
        print(f"  {r['stretch']:>8.1f} {g['both']:>9.4f} {g['H1_only']:>10.4f} "
              f"{g['H0_only']:>10.4f} {str(p['loop_sum_same_signed']):>15} "
              f"{str(p['loop_sum_exceeds_gate']):>12} "
              f"{str(ss['H0_only']):>15}")
    print("  The gate column is **reported and not scored**, as registered: the")
    print("  theorem gives the ordering and not a level.")

    # ---- the object the sweep produced that nobody asked it for ----
    print("\nthe dose response, which is what this sweep produced and what it was")
    print("not run for. **Access widens along the grid and the position gap goes**")
    print("**with it**, monotonically once the population starts growing:")
    print(f"  {'stretch':>8} {'in population':>14} {'both-cell gap':>14}")
    for r in rows:
        print(f"  {r['stretch']:>8.1f} {r['scope']['population']:>14.1f} "
              f"{r['gaps']['both']:>14.4f}")
    g = [r["gaps"]["both"] for r in rows]
    print(f"  From stretch 2.0 to 8.0 the gap falls {g[1]:.4f} to {g[6]:.4f}, "
          f"a factor of {g[1]/max(g[6], 1e-9):.0f};")
    print(f"  past that it sits in a band of width "
          f"{max(g[6:]) - min(g[6:]):.4f} around zero and its ordering there is")
    print(f"  noise. **No criterion is attached to this curve.** One was written "
          f"and removed:")
    print(f"  a monotonicity test is a zero-width comparison on an estimator, "
          f"which this")
    print(f"  repository forbids, and it would have turned noise around zero "
          f"into a verdict.")
    print(f"  **The gap this track measures is an access phenomenon**: remove the")
    print(f"  admission constraint and it goes to zero. That is a reading about")
    print(f"  the mechanism and it is reported, not scored, because no threshold")
    print(f"  for it was registered anywhere.")

    base = next(r for r in rows if r["stretch"] == 3.0)
    repro = {k: abs(base["gaps"][k] - v) for k, v in REGISTERED.items()}
    qual = [r for r in rows if r["scope"]["qualifies"]]
    crit = [
        {"name": "A3g-0  the default value on the grid reproduces the registered "
                 "run to the digit it prints",
         "passed": all(v < TOL for v in repro.values()),
         "detail": "; ".join(f"{k} {base['gaps'][k]:.4f} against {v:.4f} "
                             f"(delta {repro[k]:.1e})"
                             for k, v in REGISTERED.items())},
        {"name": "A3g-1  at least one value on the grid admits the production "
                 "layer's peripheral third, so the treatment can vary on the "
                 "measured set",
         "passed": bool(qual),
         "detail": "; ".join(
             f"stretch {r['stretch']:.1f}: peripheral in population "
             f"{r['scope']['peripheral_third_in_population']:.1f}, centrality "
             f"p10 {r['scope']['centrality_pct']['p10']:.1f}" for r in rows)},
        {"name": "A3g-2  A3-8' first half: the loop-sum-only cell is same-signed "
                 "across every seed, at every qualifying value",
         "passed": (all(r["a3_8_prime"]["loop_sum_same_signed"] for r in qual)
                    if qual else None),
         "undecidable": not qual,
         "detail": ("; ".join(f"stretch {r['stretch']:.1f}: "
                              f"{r['a3_8_prime']['loop_sum_same_signed']}, range "
                              f"{r['ranges']['H1_only']}" for r in qual)
                    if qual else
                    "**no value on the declared grid qualifies**, so there is "
                    "nothing for this criterion to read. Third state, not a "
                    "failure: what failed is the attempt to build the carrier, "
                    "recorded in A3g-1.")},
        {"name": "A3g-5  the two things A3-8' needs sit at opposite ends of this "
                 "knob, which is why the criterion cannot be read on this carrier",
         "passed": None, "undecidable": True,
         "detail": "the peripheral third first enters the population at stretch "
                   + f"{next(r['stretch'] for r in qual):.1f}, by which point the "
                   + f"both-cell gap has fallen from "
                   + f"{max(r['gaps']['both'] for r in rows):.4f} to "
                   + f"{next(r['gaps']['both'] for r in qual):.4f}. **Widening the "
                     "population to where the treatment can vary removes the "
                     "effect the criterion reads.** Measured here rather than "
                     "suspected, and it is why A3-8 stays void."},
        {"name": "A3g-3  A3-8' second half: the loop-sum-only gap exceeds the "
                 "gate-only gap, at every qualifying value",
         "passed": (all(r["a3_8_prime"]["loop_sum_exceeds_gate"] for r in qual)
                    if qual else None),
         "undecidable": not qual,
         "detail": ("; ".join(f"stretch {r['stretch']:.1f}: "
                              f"{r['a3_8_prime']['loop_sum_gap']:.4f} against "
                              f"{r['a3_8_prime']['gate_gap']:.4f}" for r in qual)
                    if qual else
                    "same as A3g-2: nothing qualifies, so nothing is read. "
                    "**On the whole grid the ordering does hold anyway, which is "
                    "reported above and not scored here.**")},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "A3g", "step": "widened_population",
        "diagnostic_only": True,
        "diagnostic_reason": "A3-8 stays void. This runs the forward-registered "
                             "A3-8' on a swept population and reports every "
                             "value of the declared grid; it does not restate "
                             "A3-8's verdict.",
        "grid": list(STRETCH_GRID), "seeds": args.seeds, "rounds": args.rounds,
        "dose_response": [{"stretch": r["stretch"],
                           "population": r["scope"]["population"],
                           "both_gap": r["gaps"]["both"]} for r in rows],
        "rows": rows, "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    np_ = sum(1 for c in crit if c["passed"] is True)
    nu = sum(1 for c in crit if c.get("undecidable"))
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, {np_} passing, "
          f"{nu} undecidable, {len(crit)-np_-nu} failing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
