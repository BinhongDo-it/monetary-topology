"""A3-8 diagnostic: is the gate arm measured on a population that can see it?

**Status: diagnostic, not a registered criterion.** Nothing here scores A3-8 or
any other criterion. It reports two readings of the same cells and leaves the
comparison to the reader. No number in `RESULTS.md` is produced or changed by
this file.

The question
------------

`a3c_load_bearing.py`'s population is the **intersection** of the agents who
complete at least one round trip in *every* cell. That choice is deliberate and
its reason is sound: a population that moves with the treatment is the error
`MEASUREMENT.md` rule 5 exists for.

But the two channels A3-8 separates do not act on the same margin.

* ``terms_spread`` acts on the **intensive** margin. Among agents who trade, it
  changes the rate. An estimand conditioned on trading can see it.
* ``gate_spread`` acts on the **extensive** margin. It changes **who trades at
  all**. An agent excluded by the gate has ``cycles == 0`` in the ``H0_only``
  cell, so it is dropped from the intersection, so the effect of excluding it
  is not in the estimand.

If that is what is happening, then the registered reading of the gate channel
(``+1.409`` at the registered point, sign unstable across seeds at every cell of
the §6.5 grid) is not evidence that the gate carries nothing. It is the reading
of a quantity that cannot contain the gate's main effect, and its instability is
the residual second-order term moving in noise rather than a sample-size effect.

Either outcome is informative, which is why this is worth running:

* Gate effect appears on the wider population and collapses on the intersection
  -> the registered gate reading is scope-limited and A3-8's negative content
  about the gate has to be restated as a statement about the intensive margin.
* Gate effect is near zero on both -> the gate really does carry nothing here,
  and the registered reading is **strengthened**, because the obvious
  alternative explanation has been checked and excluded.

What is reported
----------------

1. **Participation by tercile and cell.** The direct test. If the gate acts on
   the extensive margin, the peripheral tercile's participation should fall in
   the cells where ``gate_spread`` is on and not in the cells where it is off.
   This needs no gap and no baseline; it is a count.

2. **The gap on three populations**, each cell against the separately built
   null, everything else identical to `a3c_load_bearing.py`:

   * ``shared``: cycles > 0 in **every** cell. The registered population.
   * ``any_cell``: cycles > 0 in **at least one** cell. Already computed inside
     ``build_all`` to count how many were dropped, never used as a population.
     Agents excluded by the gate in one cell are retained here, so the gate's
     extensive margin is inside the estimand.
   * ``production``: the whole production layer, traded or not. The widest
     reading, and the one that dilutes hardest, reported so the middle case is
     bracketed rather than taken on its own.

   Terciles are taken on centrality, which is a graph property fixed before any
   treatment, so the split is identical across cells and populations of the same
   membership rule.

3. **Cross-seed sign consistency** for every cell and population, since that is
   what the registered reading turns on.

Determinism
-----------

Fixed iteration order, explicit float formats, no wall-clock content, no file
writes. Output is a function of ``--seeds`` and ``--rounds`` alone.

Run
---

    python experiments/a3d_gate_margin.py
    python experiments/a3d_gate_margin.py --seeds 20      # the sign question
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
from a3c_load_bearing import (
    CELLS,
    REGISTERED_ROUNDS,
    REGISTERED_SEEDS,
    build_all,
    build_baseline,
    gap,
    terciles,
)

#: Fixed order, so the printed table does not depend on dict insertion order.
CELL_ORDER = ("both", "H1_only", "H0_only", "null")

#: Fixed order for the population rules.
POP_ORDER = ("shared", "any_cell", "production")

F = "{:+.4f}"


def populations(models: dict, seeds: range) -> dict[str, dict[int, np.ndarray]]:
    """The three membership rules, per seed.

    ``shared`` reproduces ``build_all``'s population exactly. It is recomputed
    here rather than taken from ``build_all``'s return value so that the three
    rules are visibly built by the same loop from the same arrays, and a
    divergence between this and the registered population would be a bug in this
    file rather than a silent difference in the comparison.
    """
    out: dict[str, dict[int, np.ndarray]] = {k: {} for k in POP_ORDER}
    for seed in seeds:
        n = models[("null", seed)]._n
        shared = np.ones(n, dtype=bool)
        any_cell = np.zeros(n, dtype=bool)
        for name in CELL_ORDER:
            walked = models[(name, seed)].cycles > 0
            shared &= walked
            any_cell |= walked
        prod = models[("null", seed)]._is_production.copy()
        out["shared"][seed] = np.flatnonzero(shared)
        out["any_cell"][seed] = np.flatnonzero(any_cell)
        out["production"][seed] = np.flatnonzero(prod)
    return out


def participation(models: dict, seeds: range) -> dict[str, dict[str, float]]:
    """Mean count of participating nodes per cell, split by centrality tercile.

    The split is taken on the **production layer**, identically in every cell,
    because centrality is fixed before treatment. So a difference between cells
    in this table is a difference in who traded and nothing else.
    """
    rows: dict[str, dict[str, float]] = {}
    for name in CELL_ORDER:
        hi_n, lo_n, tot, prod_n = [], [], [], []
        rank_lo, rank_md, rank_hi = [], [], []
        csize, psize = [], []
        for seed in seeds:
            m = models[(name, seed)]
            prod = np.flatnonzero(m._is_production)
            central, peripheral = terciles(m, prod)
            walked = m.cycles > 0
            hi_n.append(float(walked[central].sum()))
            lo_n.append(float(walked[peripheral].sum()))
            tot.append(float(walked[prod].sum()))
            prod_n.append(float(prod.size))
            csize.append(float(central.size))
            psize.append(float(peripheral.size))
            # Where the participants sit in the production layer's centrality
            # ranking, as percentiles. If this band is narrow and high, then
            # "central against peripheral" inside the estimand is a contrast
            # between two slices of the top of the ranking, and the gate, which
            # sorts on centrality, has little room left to act.
            order = prod[np.argsort(m.centrality[prod])]
            pct = np.empty(m._n)
            pct[order] = np.linspace(0.0, 100.0, order.size)
            part = prod[walked[prod]]
            if part.size:
                rank_lo.append(float(pct[part].min()))
                rank_md.append(float(np.median(pct[part])))
                rank_hi.append(float(pct[part].max()))
        rows[name] = {
            "central": float(np.mean(hi_n)),
            "peripheral": float(np.mean(lo_n)),
            "total": float(np.mean(tot)),
            "prod_size": float(np.mean(prod_n)),
            "central_size": float(np.mean(csize)),
            "peripheral_size": float(np.mean(psize)),
            "pct_lo": float(np.mean(rank_lo)) if rank_lo else float("nan"),
            "pct_md": float(np.mean(rank_md)) if rank_md else float("nan"),
            "pct_hi": float(np.mean(rank_hi)) if rank_hi else float("nan"),
        }
    return rows


def gaps(models: dict, base: dict, seeds: range, pops: dict) -> dict:
    """``gap`` per cell per population rule, plus the per-seed sign record."""
    out: dict[str, dict[str, dict]] = {}
    for pname in POP_ORDER:
        out[pname] = {}
        for cname in CELL_ORDER:
            per_seed = []
            for seed in seeds:
                pop = pops[pname][seed]
                if pop.size == 0:
                    per_seed.append(float("nan"))
                    continue
                g, _, _ = gap(
                    models[(cname, seed)], base[seed].net_worth(), pop
                )
                per_seed.append(g)
            arr = np.array(per_seed, dtype=float)
            finite = arr[np.isfinite(arr)]
            if finite.size == 0:
                out[pname][cname] = {"mean": float("nan"), "stable": False,
                                     "lo": float("nan"), "hi": float("nan"),
                                     "n": 0}
                continue
            signs = np.sign(finite)
            # Same convention as a3c: a channel whose per-seed sign moves is not
            # quotable. The null is the one cell where an exact zero is the
            # expected reading rather than a degenerate one, so it is exempt.
            one_sign = bool(np.all(signs == signs[0]) and signs[0] != 0)
            out[pname][cname] = {
                "mean": float(finite.mean()),
                "lo": float(finite.min()),
                "hi": float(finite.max()),
                "stable": one_sign or cname == "null",
                "n": int(finite.size),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)

    print("=" * 78)
    print("A3-8 diagnostic: can the estimand contain the gate's effect?")
    print(f"seeds = {args.seeds}, rounds = {args.rounds}")
    print("=" * 78)

    models, registered_pop, devs = build_all(seeds, args.rounds)
    base, bdevs = build_baseline(seeds, args.rounds)
    real_devs = sorted(
        d for d in (devs | bdevs) if not d.startswith("__dropped__")
    )
    if real_devs:
        print("\nDESIGN DEVIATIONS RAISED, nothing below is readable:")
        for d in real_devs:
            print("  " + d)
        return 1

    pops = populations(models, seeds)

    # The population rule is reproduced, not assumed. If this ever prints a
    # mismatch the comparison below is between two different things.
    for seed in seeds:
        if not np.array_equal(pops["shared"][seed], registered_pop[seed]):
            print(f"\nMISMATCH at seed {seed}: `shared` is not the registered "
                  f"population. Fix this file before reading anything.")
            return 1
    print("\n`shared` reproduces the registered population at every seed.")

    print("\n" + "-" * 78)
    print("1. PARTICIPATION (mean nodes with cycles > 0, production layer)")
    print("-" * 78)
    part = participation(models, seeds)
    sizes = part["null"]
    print(f"\n  production layer {sizes['prod_size']:.0f} nodes; terciles on it:"
          f" central {sizes['central_size']:.0f},"
          f" peripheral {sizes['peripheral_size']:.0f}")
    print("\n  cell       k_pay  k_gate   central  periph    total   share"
          "   centrality pct of participants")
    for name in CELL_ORDER:
        kw = CELLS[name]
        r = part[name]
        share = r["total"] / max(r["prod_size"], 1.0)
        print(f"  {name:<10}{kw['terms_spread']:6.1f}{kw['gate_spread']:8.1f}"
              f"{r['central']:10.1f}{r['peripheral']:8.1f}"
              f"{r['total']:9.1f}{share:8.1%}"
              f"   [{r['pct_lo']:5.1f}, {r['pct_md']:5.1f}, {r['pct_hi']:5.1f}]")
    print("\n  Read 1: compare `H0_only` (gate on, terms off) against `null`")
    print("  (both off). A fall in the peripheral column there is the gate")
    print("  acting on the extensive margin, and every node it removes is a")
    print("  node the registered population drops.")
    print("\n  Read 2, and check this before reading anything else: if the")
    print("  peripheral column is at or near zero in the **null** cell, then")
    print("  the peripheral tercile does not trade under any configuration and")
    print("  the gate is not what removed it. In that case the estimand's own")
    print("  'peripheral' group is peripheral **among participants**, and the")
    print("  bracket above says how narrow a slice of the centrality ranking")
    print("  that is. A narrow high band is a scope statement about A3-8 that")
    print("  holds whatever the gap comes out to.")

    print("\n" + "-" * 78)
    print("2. GAP BY POPULATION RULE (each cell against the separate null)")
    print("-" * 78)
    g = gaps(models, base, seeds, pops)
    mean_sizes = {
        p: float(np.mean([pops[p][s].size for s in seeds])) for p in POP_ORDER
    }
    for pname in POP_ORDER:
        print(f"\n  population = {pname}  (mean size {mean_sizes[pname]:.1f})")
        print("    cell           gap      per-seed range      sign")
        for cname in CELL_ORDER:
            r = g[pname][cname]
            tag = "stable" if r["stable"] else "MOVES"
            print(f"    {cname:<10}" + F.format(r["mean"]).rjust(10)
                  + "   [" + F.format(r["lo"]) + ", " + F.format(r["hi"])
                  + "]   " + tag)

    print("\n" + "-" * 78)
    print("3. THE COMPARISON THIS FILE EXISTS FOR")
    print("-" * 78)
    sh = g["shared"]["H0_only"]
    an = g["any_cell"]["H0_only"]
    pr = g["production"]["H0_only"]
    print(f"\n  H0_only on the registered population : {F.format(sh['mean'])}"
          f"   {'stable' if sh['stable'] else 'MOVES'}")
    print(f"  H0_only on any_cell                  : {F.format(an['mean'])}"
          f"   {'stable' if an['stable'] else 'MOVES'}")
    print(f"  H0_only on the production layer      : {F.format(pr['mean'])}"
          f"   {'stable' if pr['stable'] else 'MOVES'}")
    print("\n  If the gate effect is present on the wider rules and absent on")
    print("  the registered one, the registered gate reading is scope-limited")
    print("  and A3-8's negative content has to be restated as a claim about")
    print("  the intensive margin only. If it is near zero everywhere, the")
    print("  registered reading survives a check it had not been given, and")
    print("  the obvious alternative explanation is excluded.")
    print("\n  Not decided here. This file reports; the criterion is not")
    print("  rewritten by its own diagnostic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
