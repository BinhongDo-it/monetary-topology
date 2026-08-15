"""A5 cap probe: how much of A5-1's shape is the absence of a holding cap?

**Status: diagnostic, not a registered criterion.** It scores nothing, moves no
threshold, writes no file and touches no mechanism. Registered as a diagnostic
in ``docs/a5_reachability.md`` §8.5, on the model of
``experiments/a4a_domain_probe.py``. No number it prints reaches ``RESULTS.md``.

**It is not a proposal to change the default.** ``AssetSpec.max_units = 0`` is
defended in its own docstring on structural grounds: at a cap of one, every node
that can afford anything already holds something within a few rounds, an offered
unit has no eligible buyer, three hundred rounds produce zero transactions, and
A3-3, A3-4 and A3-7 have nothing to be evaluated on. Nothing here touches that
argument, and A5-1 stays failed at the registered cap.

The question
------------

§8.1 recorded that entry participation is not monotone in reachability: it rises
from ``22.2%`` at ``ρ = 0.25`` to ``29.6%`` at ``ρ = 1.0`` and then collapses,
which is why A5-1 fails. It read the rise as ordinary participation being
crowded out from below, on the reasoning that at the cheapest prices the whole
stock sells at the opening and sells to the richest, because no cap limits how
much one node may hold. **That reading is an inference from the direction of six
numbers and not a measurement of who bought what.** §8.1 also recorded that
``max_units`` therefore interacts with ``ρ`` and the two cannot be swept
independently, and left it as an open defect in the design.

This module measures the interaction. It does not resolve it: resolving it would
mean choosing a cap, and choosing a cap is a design decision that belongs in the
stage document rather than in a probe.

What is reported
----------------

``--probe opening`` prints, for each registered ``ρ`` and each cap in
``{0, 1, 2, 3}``, the share of the stock sold at the opening allocation, the
number of holders, the largest holder's share of the units sold, the HHI of unit
ownership, and the production layer's share of holders and of units. Everything
here is read on a constructed model before any round is run, because entry is
what reachability is about.

``--probe inert`` compares each cap against the registered cap array by array,
per ``ρ`` and per seed, **at the opening and again after the full run**. A cell
bitwise identical at both is named and marked inert. ``centrality_bins`` was
declared, validated, documented as feeding the loop sum, read by no line in the
repository, and duly swept across two values that reported clean; a contrast arm
that reaches no code passes every comparison perfectly and is worth nothing.

The two times are reported separately because **they disagree, and the first
version of this probe got the label wrong on that account**: a cap of three
reproduces the registered opening allocation in every cell and then runs 74.6
transactions against 201.4 at one point of the grid. It does not bind on the
first day, because nobody buys a fourth unit then, and it binds over three
hundred rounds, because nodes that keep buying reach four. ``inert`` without a
time quantifier is the window error `MEASUREMENT.md` puts first.

``--probe guard`` checks that the cap-zero column of ``--probe opening``
reproduces ``a5_reachability.entry_participation`` bitwise. That is the quantity
A5-1 and A5-2 are scored on, and a probe that disagreed with the criterion it
was written to diagnose would be measuring something else under the same name.

``--probe trades`` runs the full three hundred rounds at each cap and counts
transactions. **This goes one step past §8.5's list**, and the reason is that
§8.5 cites ``max_units``'s own docstring as the ground for not changing the
default, and that docstring's central claim, that a cap of one produces zero
transactions over three hundred rounds, is a run nobody has recorded. A cited
claim that has not been run is a claim and not evidence. It is checked here at
A5's registered price scale rather than A3's, so a disagreement with the
docstring would be about the scale before it was about the claim.
"""

from __future__ import annotations

import argparse
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from a5_reachability import (  # noqa: E402
    REGISTERED_SEEDS,
    RHO_GRID,
    ROUNDS,
    build,
    entry_participation,
    run,
)

from monetary_topology.asset import AssetSpec  # noqa: E402

#: The registered cap sits first, so every table's first column is the cell the
#: stage is actually scored on and the rest are contrasts against it.
CAP_GRID: tuple[int, ...] = (0, 1, 2, 3)

def opening(seed: int, rho: float, cap: int):
    """The constructed model at one point of the two-dimensional grid.

    ``build`` is stage A5's own constructor, so the price scaling, the network
    and the authority are the stage's and not this module's. The probe supplies
    one number and inherits everything else.
    """
    return build(seed, rho, max_units=cap)


def opening_stats(model) -> dict[str, float]:
    """Who holds what, the moment the market opens.

    ``units`` is ``(n, Q)``; every quantity below is on the row sums, because
    the question is how many units a node ended up with and not which tiers
    they came from.
    """
    per_node = model.units.sum(axis=1)
    sold = float(per_node.sum())
    stock = float(sum(model.supply))
    layer1 = model.a3.network.spec.layer1_size
    prod = per_node[layer1:]
    n_prod = prod.size
    held = per_node > 0
    # An empty market has no distribution to describe, and dividing by zero to
    # say so would print `nan` in five columns instead of one honest zero.
    if sold <= 0.0:
        return {
            "sold_share": 0.0,
            "holders": 0.0,
            "top_share": 0.0,
            "hhi": 0.0,
            "prod_entry": 0.0,
            "prod_units_share": 0.0,
        }
    return {
        "sold_share": sold / stock,
        "holders": float(held.sum()),
        "top_share": float(per_node.max()) / sold,
        "hhi": float(((per_node / sold) ** 2).sum()),
        "prod_entry": float((prod > 0).mean()) if n_prod else 0.0,
        "prod_units_share": float(prod.sum()) / sold,
    }


def mean_stats(seeds: int, rho: float, cap: int) -> dict[str, float]:
    rows = [opening_stats(opening(s, rho, cap)) for s in range(seeds)]
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def probe_opening(seeds: int) -> None:
    print("\n1. The opening allocation, by reachability and by cap")
    print(
        "   Read before any round runs. `prod_entry` is the quantity A5-1 and\n"
        "   A5-2 are scored on. **A5-1 is scored at cap 0 and stays failed;\n"
        "   the other columns are contrasts and decide nothing.**"
    )
    for cap in CAP_GRID:
        tag = "registered" if cap == AssetSpec().max_units else "contrast"
        label = "no cap" if cap == 0 else f"cap {cap}"
        print(f"\n   {label} ({tag}), {seeds} seeds")
        print(
            f"   {'rho':>6} {'stock sold':>11} {'holders':>8} {'top share':>10}"
            f" {'HHI':>7} {'prod entry':>11} {'prod units':>11}"
        )
        entries = []
        for rho in RHO_GRID:
            s = mean_stats(seeds, rho, cap)
            entries.append(s["prod_entry"])
            print(
                f"   {rho:>6} {s['sold_share']:>10.1%} {s['holders']:>8.1f}"
                f" {s['top_share']:>9.1%} {s['hhi']:>7.4f}"
                f" {s['prod_entry']:>10.1%} {s['prod_units_share']:>10.1%}"
            )
        # A computed property of the column, printed so that the reading §8.1
        # left as an inference has a number under it. It is not a verdict: no
        # threshold is registered for it and none is invented here.
        falling = all(a >= b - 1e-12 for a, b in pairwise(entries))
        peak = RHO_GRID[int(np.argmax(entries))]
        print(
            f"   prod entry monotone decreasing in rho: {falling}"
            f"   peak at rho = {peak}"
        )


def probe_inert(seeds: int) -> None:
    """Bitwise comparison against the registered cap, **at two times**.

    A first version of this probe compared the opening allocation only and
    printed the word ``INERT`` against a cap of three, which reproduced the
    registered allocation in all thirty cells. ``--probe trades`` then showed
    that same cap running 74.6 transactions against 201.4 at one point of the
    grid. **Both readings were correct and the label was wrong**: the cap does
    not bind at the opening, because nobody buys a fourth unit on the first
    day, and it does bind over three hundred rounds, because nodes that keep
    buying reach four. An arm inert at one time is not an inert arm, and
    ``inert`` without a time quantifier is the window error `MEASUREMENT.md`
    puts first.

    So the comparison is made twice and the word carries its scope. An arm is
    reported inert only where it is inert at both.
    """
    print("\n2. Does the cap reach code, cell by cell")
    print(
        "   Bitwise comparison of each cap against the registered cap, at the\n"
        "   opening and again after the full run. An arm that reaches no code\n"
        "   reproduces perfectly, which is what `centrality_bins` did through a\n"
        "   field, a validator and a documented meaning. **The two times are\n"
        "   reported separately because they disagree**: a cap of three changes\n"
        "   no opening allocation and changes the run substantially."
    )
    registered = AssetSpec().max_units
    fully_inert: list[str] = []
    for cap in CAP_GRID:
        if cap == registered:
            continue
        open_diff = run_diff = total = 0
        for rho in RHO_GRID:
            for seed in range(seeds):
                total += 1
                same_open = np.array_equal(
                    opening(seed, rho, registered).units,
                    opening(seed, rho, cap).units,
                )
                ref, arm = run(seed, rho), run(seed, rho, max_units=cap)
                same_run = np.array_equal(ref.units, arm.units) and np.array_equal(
                    ref.holdings, arm.holdings
                )
                open_diff += not same_open
                run_diff += not same_run
                if same_open and same_run:
                    fully_inert.append(f"cap {cap}, rho {rho}, seed {seed}")
        verdict = "INERT AT BOTH TIMES" if run_diff == 0 and open_diff == 0 else "live"
        print(
            f"   cap {cap}: opening {open_diff}/{total} differ,"
            f" end of run {run_diff}/{total} differ   {verdict}"
        )
    if fully_inert:
        print(f"\n   cells inert at both times, named ({len(fully_inert)}):")
        for name in fully_inert:
            print(f"     {name}")
    else:
        print(
            "\n   no cell is inert at both times: every contrast reaches code"
            "\n   somewhere, and a cap that looks inert at the opening is not"
        )


def probe_guard(seeds: int) -> None:
    print("\n3. The probe against the criterion it diagnoses")
    print(
        "   `prod_entry` at the registered cap must equal\n"
        "   `a5_reachability.entry_participation` bitwise, or the probe is\n"
        "   measuring something else under the same name."
    )
    registered = AssetSpec().max_units
    worst = 0.0
    for rho in RHO_GRID:
        for seed in range(seeds):
            mine = opening_stats(opening(seed, rho, registered))["prod_entry"]
            theirs = entry_participation(seed, rho)
            worst = max(worst, abs(mine - theirs))
    print(f"   largest disagreement over {len(RHO_GRID) * seeds} cells: {worst:.3e}")
    print(f"   bitwise equal everywhere: {worst == 0.0}")


def probe_trades(seeds: int) -> None:
    print(f"\n4. Transactions over {ROUNDS} rounds, by cap")
    print(
        "   Beyond §8.5's list. `max_units`'s docstring defends the registered\n"
        "   zero by asserting that a cap of one produces zero transactions over\n"
        "   three hundred rounds, and that run is not recorded anywhere. This\n"
        "   is at A5's price scale, not A3's, so a disagreement is about the\n"
        "   scale before it is about the claim."
    )
    print(f"\n   {'rho':>6} " + " ".join(f"{'cap ' + str(c):>10}" for c in CAP_GRID))
    for rho in RHO_GRID:
        cells = []
        for cap in CAP_GRID:
            trades = [
                float(sum(run(s, rho, max_units=cap).sales))
                for s in range(seeds)
            ]
            cells.append(float(np.mean(trades)))
        print(f"   {rho:>6} " + " ".join(f"{c:>10.1f}" for c in cells))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument(
        "--probe",
        choices=("all", "opening", "inert", "guard", "trades"),
        default="all",
    )
    args = ap.parse_args()

    print("A5 cap probe: diagnostic, scores nothing, writes nothing")

    if args.probe in ("all", "opening"):
        probe_opening(args.seeds)
    if args.probe in ("all", "inert"):
        probe_inert(args.seeds)
    if args.probe in ("all", "guard"):
        probe_guard(args.seeds)
    if args.probe in ("all", "trades"):
        probe_trades(args.seeds)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
