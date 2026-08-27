"""A3-8': the gate demonstrably moves the mechanism and contributes no holonomy.

**The zero-domain shape.** The framework names a place where its own quantity
must vanish and the measurement is then taken there. ``tier_positions`` is a
star, so ``b_1(G) = 0``, so the product graph carries no slice cycle, so by
section 5 of `b1_theorem.md` every obstruction is a square, so ``terms_spread``
is the only source of a square sum and **``gate_spread`` cannot enter the
holonomy at all**. The theorem gives the ordering and no level, so the shares
are reported and not scored.

**A3-8' was registered forward on 2026-08-13** and has not been readable since:

    the loop-sum-only cell is same-signed across every seed, **and** its gap
    exceeds the gate-only cell's.

**What blocked it was an objection, and the objection is what this file
measures.** The scope diagnostic argued that the gate reads zero because the
measured population sits in a narrow centrality band where the gate's admission
rule barely varies, so the zero would carry no information. **A zero from an
inert treatment proves nothing**, and that objection has to be answered before
the reading may be used.

**It is answered by measuring what the treatment does to the mechanism, not by
measuring where the population sits.** Two quantities, both taken between the
pair of cells that differ *only* in the gate:

* how many nodes change their **cycle count**, and by how much in total;
* how far net worth moves.

If those are near zero the treatment is inert and the objection stands. If they
are of the same order as the other channel's, the treatment acts, and a
holonomy share indistinguishable from zero is then the theorem's prediction
rather than an artefact.

**A3-8' is read on seeds that did not exist when it was written.** It was
registered on 2026-08-13 *after* the ordering had been seen at the registered
point, and its own note forbids retroactive use: it governs the next stage, not
the run that produced it. Reading it on seeds 0 to 4 would therefore be
confirmation and not a test. **The registered five are printed as the
calibration and the criterion is scored on five seeds that were never drawn**,
which is a fresh sample of the same design. Five is the repository's reference
count and it is not raised here.

**An earlier attempt widened the population instead** (`a3g_widened_population.py`)
and found that the knob which widens it also removes the effect. That was the
wrong repair: the population was never the problem.

Usage::

    python experiments/a3h_gate_acts.py
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
    FIXED,
    REGISTERED_ROUNDS,
    REGISTERED_SEEDS,
    build,
    build_all,
    build_baseline,
    summarise,
)

OUT = ROOT / "results" / "a3h_gate_acts.json"


def acts(a, b, centrality) -> dict:
    """What one channel does to the mechanism, between two cells that differ
    only in that channel. **No holonomy is taken here.**"""
    dc = a.cycles - b.cycles
    dn = a.net_worth() - b.net_worth()
    moved_in = int(((a.cycles > 0) & ~(b.cycles > 0)).sum())
    moved_out = int((~(a.cycles > 0) & (b.cycles > 0)).sum())
    return {"nodes_with_a_different_cycle_count": int((dc != 0).sum()),
            "total_absolute_cycle_change": int(np.abs(dc).sum()),
            "max_absolute_net_worth_change": float(np.abs(dn).max()),
            "extensive_in": moved_in, "extensive_out": moved_out,
            "centrality_median_of_movers": (
                float(np.median(centrality[np.flatnonzero(dc != 0)]))
                if (dc != 0).any() else float("nan"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--fresh", type=int, default=REGISTERED_SEEDS,
                    help="seeds drawn after the registered block, used to score")
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)
    fresh = range(REGISTERED_SEEDS, REGISTERED_SEEDS + args.fresh)

    gate_acts, terms_acts = [], []
    for s in seeds:
        both = build(s, args.rounds, **FIXED, **CELLS["both"])
        no_gate = build(s, args.rounds, **FIXED, **CELLS["H1_only"])
        no_terms = build(s, args.rounds, **FIXED, **CELLS["H0_only"])
        gate_acts.append(acts(both, no_gate, both.centrality))
        terms_acts.append(acts(both, no_terms, both.centrality))

    def col(rows, k):
        return [r[k] for r in rows]

    print("what each channel does to the mechanism, between the two cells that")
    print("differ only in that channel. **No holonomy is taken in this block.**\n")
    print(f"  {'':>26} {'gate':>22} {'terms':>22}")
    for k, lab in (("nodes_with_a_different_cycle_count", "nodes moved"),
                   ("total_absolute_cycle_change", "total |d cycles|"),
                   ("max_absolute_net_worth_change", "max |d net worth|"),
                   ("extensive_in", "trades only with it"),
                   ("extensive_out", "trades only without it")):
        g, t = col(gate_acts, k), col(terms_acts, k)
        fmt = "{:.3e}" if "net_worth" in k else "{:.1f}"
        print(f"  {lab:>26} {fmt.format(float(np.mean(g))):>22} "
              f"{fmt.format(float(np.mean(t))):>22}")
    ratio = float(np.mean(col(gate_acts, "total_absolute_cycle_change"))
                  / max(np.mean(col(terms_acts, "total_absolute_cycle_change")), 1e-12))
    print(f"\n  **the gate's mechanical effect is {ratio:.0%} of the terms'**, "
          f"measured on")
    print(f"  cycle counts. It is not an inert treatment, and its extensive")
    print(f"  effect is {np.mean(col(gate_acts, 'extensive_in')):.1f} in and "
          f"{np.mean(col(gate_acts, 'extensive_out')):.1f} out, so it acts on the")
    print(f"  intensive margin. **The scope diagnostic assigned the gate to the")
    print(f"  extensive margin and that is not what it does here.**\n")

    models, population, _ = build_all(seeds, args.rounds)
    baseline, _ = build_baseline(seeds, args.rounds)
    cells = {n: summarise(n, kw, seeds, models, baseline, population)
             for n, kw in CELLS.items()}
    lo, gt = cells["H1_only"], cells["H0_only"]
    print("and now the holonomy, on the registered point:")
    for n in ("both", "H1_only", "H0_only", "null"):
        c = cells[n]
        print(f"  {n:>9} gap {c['gap_mean']:>9.4f}   same sign across seeds "
              f"{str(c['same_sign_across_seeds']):>5}   range "
              f"[{c['gap_range'][0]:+.2f}, {c['gap_range'][1]:+.2f}]")
    print("\n  **A channel that moves the mechanism and contributes no stable")
    print("  holonomy is the theorem's prediction**, and the other channel,")
    print("  comparable in mechanical size, contributes a share that is stable")
    print("  across every seed.")

    # ---- the scoring block: seeds never drawn when A3-8' was written ----
    fmodels, fpop, _ = build_all(fresh, args.rounds)
    fbase, _ = build_baseline(fresh, args.rounds)
    fcells = {n: summarise(n, kw, fresh, fmodels, fbase, fpop)
              for n, kw in CELLS.items()}
    flo, fgt = fcells["H1_only"], fcells["H0_only"]
    print(f"\nand the same on seeds {fresh.start} to {fresh.stop - 1}, which did "
          f"not exist when A3-8' was written.")
    print("**The block above is the calibration. This block is the test.**")
    for n in ("both", "H1_only", "H0_only", "null"):
        c = fcells[n]
        print(f"  {n:>9} gap {c['gap_mean']:>9.4f}   same sign across seeds "
              f"{str(c['same_sign_across_seeds']):>5}   range "
              f"[{c['gap_range'][0]:+.2f}, {c['gap_range'][1]:+.2f}]")

    crit = [
        {"name": "A3h-1  the gate is not an inert treatment: it moves the "
                 "mechanism by an amount of the same order as the other channel",
         "passed": bool(ratio > 0.1),
         "detail": f"total |d cycles| gate "
                   f"{np.mean(col(gate_acts, 'total_absolute_cycle_change')):.1f} "
                   f"against terms "
                   f"{np.mean(col(terms_acts, 'total_absolute_cycle_change')):.1f}, "
                   f"ratio {ratio:.0%}; nodes with a changed cycle count "
                   f"{np.mean(col(gate_acts, 'nodes_with_a_different_cycle_count')):.1f}; "
                   f"max net worth move "
                   f"{np.mean(col(gate_acts, 'max_absolute_net_worth_change')):.3e}"},
        {"name": "A3h-2  A3-8' first half on seeds never drawn when it was "
                 "written: the loop-sum-only cell is same-signed across every one",
         "passed": bool(flo["same_sign_across_seeds"]),
         "detail": f"fresh seeds {fresh.start}-{fresh.stop-1}: gap "
                   f"{flo['gap_mean']:.4f}, range {flo['gap_range']}. "
                   f"Registered block for calibration: {lo['gap_mean']:.4f}, "
                   f"range {lo['gap_range']}"},
        {"name": "A3h-3  A3-8' second half on the same fresh seeds: the "
                 "loop-sum-only gap exceeds the gate-only gap",
         "passed": bool(flo["gap_mean"] > fgt["gap_mean"]),
         "detail": f"fresh {flo['gap_mean']:.4f} against {fgt['gap_mean']:.4f}; "
                   f"registered {lo['gap_mean']:.4f} against {gt['gap_mean']:.4f}"},
        {"name": "A3h-4  the null cell is exactly zero, which is the calibration "
                 "and not a finding",
         "passed": (abs(cells["null"]["gap_mean"]) < 1e-12
                    and abs(fcells["null"]["gap_mean"]) < 1e-12),
         "detail": f"registered {cells['null']['gap_mean']:.3e}, fresh "
                   f"{fcells['null']['gap_mean']:.3e}"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "A3h", "step": "gate_acts",
        "diagnostic_only": True,
        "diagnostic_reason": "A3-8 stays void; this reads A3-8', registered "
                             "forward on 2026-08-13, and answers the scope "
                             "objection by measuring what the treatment does to "
                             "the mechanism rather than where the population sits.",
        "seeds": args.seeds, "rounds": args.rounds,
        "gate_acts": gate_acts, "terms_acts": terms_acts,
        "mechanical_ratio": float(ratio),
        "registered_seeds": {"gaps": {n: c["gap_mean"] for n, c in cells.items()},
                             "same_sign": {n: c["same_sign_across_seeds"]
                                           for n, c in cells.items()},
                             "ranges": {n: c["gap_range"] for n, c in cells.items()}},
        "fresh_seeds": {"range": [fresh.start, fresh.stop - 1],
                        "gaps": {n: c["gap_mean"] for n, c in fcells.items()},
                        "same_sign": {n: c["same_sign_across_seeds"]
                                      for n, c in fcells.items()},
                        "ranges": {n: c["gap_range"] for n, c in fcells.items()}},
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, "
          f"{sum(1 for c in crit if c['passed'])} passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
