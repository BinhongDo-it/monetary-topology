"""A6: what the siphon costs in redistribution, and whether topology is cheaper.

Registered in ``docs/a6_siphon_cost.md``. This file evaluates and does not
design: every threshold it compares against is written there.

Usage::

    python experiments/a6_siphon_cost.py
    python experiments/a6_siphon_cost.py --seeds 5 --rounds 300
    python experiments/a6_siphon_cost.py --skip-long   # omit A6-5's 2000 rounds

Writes ``results/a6_siphon_cost.json``.

The stage asks one question with a unit attached. **Issuance is off in every
cell**, so the levy is the only thing holding the economy open, and `R*` — the
smallest rate that keeps the support set from contracting — is the price of the
siphon in tax points rather than a statement about the monetary authority.

Three things this file is built to make visible.

**Every headline is reported per seed.** `R*` is found by a grid scan per seed
and the whole set is printed, not just its median. A comparison whose ordering
flips across seeds is refused rather than averaged, which is the rule adopted
after `a3c_load_bearing.py` quoted a share that one seed contradicted.

**Landing on the grid's smallest non-zero point is a bound, not a value.** If
`R*` comes back at the first non-zero rate the scan can see, all that has been
established is `R* ≤` that rate, and the ratio built from it is a bound in the
direction that favours the framework. Flagged wherever it happens.

**The uniform-access, fair-retention cell is the zero calibration.** It is also
half of A6-3's prediction, and that is not a coincidence: the criterion is that
a flat graph with flat propensities needs no redistribution at all. If it comes
back needing some, the measurement is wrong before any other cell is read.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    NetworkConfig,
    NetworkSpec,
)
from monetary_topology.redistribution import (  # noqa: E402
    A6Config,
    FiscalSpec,
    contracted,
    find_rate,
    run_a6,
    support_trend,
)

RESULTS = ROOT / "results"

REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300
REGISTERED_LONG = 2000

#: §5. Registered thresholds, named here so a reader can check them against the
#: document rather than hunting through the code.
A6_3_SIPHON_FLOOR = 0.02
A6_3_FLAT_CEILING = 0.005
A6_4_RATIO = 0.75
A6_5_DRIFT = 0.10

#: The scan grid `find_rate` uses. Repeated here only so the smallest non-zero
#: point can be recognised when `R*` lands on it.
FIRST_NONZERO = 0.005


def config_for(
    seed: int, rounds: int, access: bool, fair: bool, channel: str
) -> A6Config:
    """One cell of §4's factorial.

    ``access`` is the stratified graph; its absence is `uniform_access`, the
    complete graph with uniform terms. Issuance is off in every cell, which is
    what makes `R*` a measurement of the economy.
    """
    return A6Config(
        fiscal=FiscalSpec(channel=channel, fair_retention=fair),
        network=NetworkConfig(
            spec=NetworkSpec(seed=seed, uniform_access=not access),
            seed=seed,
            rounds=rounds,
            authority=MonetaryAuthority(rule="none"),
        ),
    )


def cell_rates(
    seeds: range, rounds: int, access: bool, fair: bool, channel: str
) -> dict:
    """`R*` per seed for one cell, plus what the scan says about monotonicity."""
    rates: list[float | None] = []
    monotone: list[bool] = []
    for seed in seeds:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r, mono = find_rate(config_for(seed, rounds, access, fair, channel))
        rates.append(r)
        monotone.append(mono)
    found = [r for r in rates if r is not None]
    return {
        "access": access,
        "fair": fair,
        "channel": channel,
        "rates": rates,
        "median": float(np.median(found)) if found else None,
        "unsolved_seeds": int(sum(r is None for r in rates)),
        "monotone_above": bool(all(monotone)),
        # Landing on the grid's first non-zero point establishes an upper bound
        # and nothing finer. Reported so a ratio built on it is read as a bound.
        "at_grid_floor": bool(found and max(found) <= FIRST_NONZERO),
    }


def zero_levy_contracts(seeds: range, rounds: int) -> dict:
    """A6-1. Does every cell contract with no redistribution at all?"""
    out = {}
    for access in (True, False):
        for fair in (True, False):
            for channel in ("transfer", "infrastructure"):
                bad = []
                for seed in seeds:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        _, h = run_a6(
                            config_for(seed, rounds, access, fair, channel)
                        )
                    bad.append(contracted(h.effective_support))
                key = f"access={access} fair={fair} {channel}"
                out[key] = {
                    "contracted_in_all_seeds": bool(all(bad)),
                    "seeds_contracting": int(sum(bad)),
                }
    return out


def long_run(seeds: range, rate: float, rounds: int) -> dict:
    """A6-5. At `R*`, does the support set stay open over the long horizon?

    Three hundred rounds is enough to find `R*` and not enough to claim
    "forever", which is why the document registers this separately.
    """
    trends, drifts, ratios, collapsed = [], [], [], []
    for seed in seeds:
        cfg = config_for(seed, rounds, access=True, fair=True,
                         channel="infrastructure")
        cfg = replace(cfg, fiscal=replace(cfg.fiscal, rate=rate))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, h = run_a6(cfg)
        y = np.asarray(h.effective_support, dtype=float)
        trends.append(support_trend(y, last=500))
        mid = y[500] if y.size > 500 else y[0]
        drifts.append(abs(float(y[-1] - mid)) / max(abs(float(mid)), 1e-12))
        # The registered band is symmetric, so it cannot tell "grew by two
        # thirds" from "collapsed to a fifteenth". Both fail it and they are
        # opposite outcomes, so the direction is reported beside the verdict.
        ratios.append(float(y[-1] / y[0]) if y[0] else float("nan"))
        collapsed.append(bool(y[0] and y[-1] < y[0]))
    return {
        "rate": rate,
        "rounds": rounds,
        "tail_trend": [float(t) for t in trends],
        "drift_from_round_500": [float(d) for d in drifts],
        "end_over_start": [float(r) for r in ratios],
        "seeds_collapsed": int(sum(collapsed)),
        "seeds": len(ratios),
        "stationary": bool(
            all(t >= 0 for t in trends) and all(d <= A6_5_DRIFT for d in drifts)
        ),
        # The verdict that matters for the policy reading, separate from the
        # registered band: did the economy stay open at all?
        "open_in_every_seed": bool(not any(collapsed)),
    }


def palma_track(seeds: range, rounds: int, rate: float) -> dict:
    """A6-6. Reported, never judged.

    The expectation is that the support set can be held open while Palma drifts.
    If that is what happens it is the stage's most quotable result: **a closed
    economy that stays reachable is not a closed economy that stays equal**, and
    conflating the two is what makes the first look impossible.
    """
    first, last = [], []
    for seed in seeds:
        cfg = config_for(seed, rounds, access=True, fair=True,
                         channel="infrastructure")
        cfg = replace(cfg, fiscal=replace(cfg.fiscal, rate=rate))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m, _ = run_a6(cfg)
        track = np.asarray(m.palma_history, dtype=float)
        first.append(float(track[0]))
        last.append(float(track[-1]))
    return {
        "palma_start": float(np.median(first)),
        "palma_end": float(np.median(last)),
        "per_seed": [
            [float(a), float(b)] for a, b in zip(first, last, strict=True)
        ],
        # Both directions are tested. Reporting only "rose" would leave a fall
        # and a mixed result indistinguishable, and the two mean different
        # things: one is a finding, the other is noise.
        "rose_in_every_seed": bool(
            all(b > a for a, b in zip(first, last, strict=True))
        ),
        "fell_in_every_seed": bool(
            all(b < a for a, b in zip(first, last, strict=True))
        ),
    }


def _fmt(r: float | None) -> str:
    return "none" if r is None else f"{r:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    ap.add_argument("--long", type=int, default=REGISTERED_LONG)
    ap.add_argument("--skip-long", action="store_true")
    args = ap.parse_args()
    seeds = range(args.seeds)

    print("A6: the siphon in tax points\n")
    print(f"  {args.seeds} seeds, {args.rounds} rounds, issuance off in every "
          f"cell")

    floor = zero_levy_contracts(seeds, args.rounds)
    a6_1 = all(v["contracted_in_all_seeds"] for v in floor.values())
    n_cells = len(floor)
    print(f"\n  A6-1  something to fix: "
          f"{'pass' if a6_1 else 'FAIL'} -- the support set contracts at R=0 "
          f"in {sum(v['contracted_in_all_seeds'] for v in floor.values())}"
          f"/{n_cells} cells, all seeds")

    cells = {}
    for access in (True, False):
        for fair in (True, False):
            for channel in ("transfer", "infrastructure"):
                key = f"{'access' if access else 'flat'}/" \
                      f"{'fair' if fair else 'stratified'}/{channel[0].upper()}"
                cells[key] = cell_rates(seeds, args.rounds, access, fair,
                                        channel)

    print("\n  R* by cell (grid scan, per seed)")
    print("    cell                        median   per seed")
    for key, c in cells.items():
        mark = "  <= grid floor" if c["at_grid_floor"] else ""
        print(f"    {key:26s}  {_fmt(c['median']):>6s}   "
              f"{[_fmt(r) for r in c['rates']]}{mark}")

    a6_2 = all(c["unsolved_seeds"] == 0 for c in cells.values())
    print(f"\n  A6-2  R* exists: {'pass' if a6_2 else 'FAIL'} -- "
          f"{sum(c['unsolved_seeds'] for c in cells.values())} seed-cells with "
          f"no rate on the grid holding the economy open")

    siphon = cells["access/fair/T"]
    flat = cells["flat/fair/T"]
    a6_3 = bool(
        siphon["median"] is not None
        and flat["median"] is not None
        and siphon["median"] > A6_3_SIPHON_FLOOR
        and flat["median"] < A6_3_FLAT_CEILING
    )
    print(f"\n  A6-3  the siphon: {'pass' if a6_3 else 'FAIL'} -- with "
          f"retention already fair and no issuance anywhere, the stratified "
          f"graph needs R* = {_fmt(siphon['median'])} "
          f"(> {A6_3_SIPHON_FLOOR}) and the flat graph needs "
          f"{_fmt(flat['median'])} (< {A6_3_FLAT_CEILING}). The flat cell is "
          f"also the zero calibration")

    ratios, bounded = {}, False
    for fair in (True, False):
        tag = "fair" if fair else "stratified"
        t = cells[f"access/{tag}/T"]
        i = cells[f"access/{tag}/I"]
        per_seed = [
            (a / b) if (a is not None and b) else None
            for a, b in zip(i["rates"], t["rates"], strict=True)
        ]
        good = [x for x in per_seed if x is not None]
        bounded = bounded or i["at_grid_floor"]
        ratios[tag] = {
            "per_seed": per_seed,
            "median": float(np.median(good)) if good else None,
            "all_below_threshold": bool(good) and all(
                x < A6_4_RATIO for x in good
            ),
            "is_upper_bound": i["at_grid_floor"],
        }
    a6_4 = all(v["all_below_threshold"] for v in ratios.values())
    print(f"\n  A6-4  topology cheaper than quantity: "
          f"{'pass' if a6_4 else 'FAIL'} -- R*(I)/R*(T) under access, "
          f"against {A6_4_RATIO}")
    for tag, v in ratios.items():
        note = (
            "  ** an upper bound: R*(I) sits on the grid's first non-zero "
            "point, so the true ratio is smaller and the criterion passes on "
            "the bound"
            if v["is_upper_bound"] else ""
        )
        print(f"      {tag:11s} median {_fmt(v['median'])}, per seed "
              f"{[_fmt(x) for x in v['per_seed']]}{note}")

    star = cells["access/fair/I"]["median"]
    long_result = None
    if not args.skip_long and star is not None:
        long_result = long_run(seeds, star, args.long)
        print(f"\n  A6-5  the autarky runs: "
              f"{'pass' if long_result['stationary'] else 'FAIL'} -- at "
              f"R* = {_fmt(star)} over {args.long} rounds, drift from round "
              f"500 {[f'{d:.1%}' for d in long_result['drift_from_round_500']]}"
              f" against {A6_5_DRIFT:.0%}")
        print(f"      end over start, per seed: "
              f"{[f'{r:.2f}x' for r in long_result['end_over_start']]} -- "
              f"**{long_result['seeds_collapsed']} of "
              f"{long_result['seeds']} seeds collapsed**, the rest ended more "
              f"open than they began. The registered band is symmetric and "
              f"cannot tell those apart, so both are printed")
    else:
        print("\n  A6-5  skipped")

    palma_result = None
    if star is not None:
        palma_result = palma_track(seeds, args.rounds, star)
        if palma_result["rose_in_every_seed"]:
            shape = "rose in every seed"
        elif palma_result["fell_in_every_seed"]:
            shape = "FELL in every seed, against the stated expectation"
        else:
            shape = "mixed across seeds, so no direction may be quoted"
        print(f"\n  A6-6  reported, not judged: Palma "
              f"{palma_result['palma_start']:.2f} -> "
              f"{palma_result['palma_end']:.2f}, {shape}. Holding the support "
              f"set open and holding the distribution still are two questions, "
              f"and this cell answers both at once rather than trading one off "
              f"against the other")

    RESULTS.mkdir(parents=True, exist_ok=True)
    registered = (
        args.seeds == REGISTERED_SEEDS and args.rounds == REGISTERED_ROUNDS
    )
    out = RESULTS / (
        "a6_siphon_cost.json"
        if registered
        else f"a6_siphon_cost.offparam_{args.seeds}x{args.rounds}.json"
    )
    if not registered:
        print(f"\n  off-parameter run against the registered "
              f"{REGISTERED_SEEDS}x{REGISTERED_ROUNDS}: writing beside the "
              f"registered result, not over it")
    verdicts = {
        "A6-1": a6_1, "A6-2": a6_2, "A6-3": a6_3, "A6-4": a6_4,
        "A6-5": None if long_result is None else long_result["stationary"],
    }
    live = [v for v in verdicts.values() if v is not None]
    print(f"\n  {sum(live)}/{len(live)} criteria passed; A6-6 is reported and "
          f"not judged")
    out.write_text(
        json.dumps(
            {
                "stage": "A6",
                "seeds": args.seeds,
                "rounds": args.rounds,
                "long_rounds": None if long_result is None else args.long,
                "thresholds": {
                    "A6-3 siphon floor": A6_3_SIPHON_FLOOR,
                    "A6-3 flat ceiling": A6_3_FLAT_CEILING,
                    "A6-4 ratio": A6_4_RATIO,
                    "A6-5 drift": A6_5_DRIFT,
                },
                "zero_levy": floor,
                "cells": cells,
                "ratios": ratios,
                "long_run": long_result,
                "palma": palma_result,
                "verdicts": verdicts,
                "ratio_is_upper_bound": bounded,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if all(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
