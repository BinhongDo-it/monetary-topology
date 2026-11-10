"""A3b: the opening construction as an axis, run across seeds.

Registered in ``docs/a3b_initial_construction.md``. This file evaluates and does
not design.

Usage::

    python experiments/a3b_construction.py
    python experiments/a3b_construction.py --seeds 5 --rounds 300

Writes ``results/a3b_construction.json``.

The question is not which construction is right. It is **which results survive a
change of construction**: those are properties of the flow topology, the rest
were properties of the opening. That is the source manuscript's second
correspondence standard, 拓展性 (extensibility), and this file is the first place
in the repository where it is executed rather than asserted.

Three things this file is built to make visible rather than to hide.

**The zero calibration is `auction` against the pre-A3b defaults.** Turning
`units_per_node`, `residual_owner` and `proceeds` on at once changes three things
simultaneously, so the run reports the `auction` arm with them off as well, and
the difference between the two is the cost of the fix rather than a result.

**`continuous` may be identical to `auction`.** At the calibration measured on
one seed it was, bitwise. The harness therefore tests for that explicitly and
reports it as a collapsed axis instead of quietly presenting a three-point grid
with two identical columns.

**Everything here is a level, not a loop sum.** These arms move `H⁰`, who can
reach the asset. They say nothing about `H¹`. What they do to A3-4 is printed
and not assumed. Trade by trade the identity holds by construction, since a
resale pays `γ · P`, and the entry reads its consequence: on every seed the gap
between the ledger side and the graph side equals the tier-mix term to `1e-10`.
The aggregate comparison moves with how each group's trades fall across the
tiers and with which nodes complete round trips, both of which the opening
changes. On the occupancy arm it has no reading at all.

**Round one is not the opening.** The checkpoint tables start at the end of
round one. The state the constructor leaves, before any round has run, is
printed above them as its own row.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    A3Config,
    A3Model,
    AssetSpec,
    DesignDeviation,
)
from monetary_topology.network import (  # noqa: E402
    NetworkConfig,
    NetworkSpec,
)

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from a3_asset_channel import (  # noqa: E402
    A3_4_TOLERANCE,
    adjusted_trades,
    loop_sum_from_graph,
    terms_differential,
    terms_pair,
)

RESULTS = ROOT / "results"

#: The registered run. Recorded so an off-parameter run cannot claim the
#: registered filename, which is a mistake this repository has already made.
REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300

#: A3b §5. Common to every arm except the zero calibration, which exists to
#: show what these three switches cost on their own.
FIXED = {
    "units_per_node": 1.1,
    "residual_owner": True,
    "proceeds": "seller",
}

#: A3b §3. The axis. Ordered from "ownership tracks claims perfectly" to
#: "ownership does not consult claims at all".
ARMS: dict[str, dict] = {
    "auction": {"construction": "auction"},
    "continuous": {"construction": "continuous", "ownership_rate": 0.653},
    "occupancy": {
        "construction": "occupancy",
        "ownership_rate": 0.70,
        "opening_discount": 0.44,
    },
}

#: Rounds at which the drain is sampled. Chosen before running, and they
#: bracket the whole path rather than the interesting part of it.
CHECKPOINTS = (1, 25, 50, 100, 200, 300)


@dataclass
class ArmResult:
    name: str
    ownership: dict[int, float] = field(default_factory=dict)
    prod_holders: dict[int, float] = field(default_factory=dict)
    prod_units: dict[int, float] = field(default_factory=dict)
    total_units: dict[int, float] = field(default_factory=dict)
    #: The same four measures on the state the constructor leaves, before any
    #: round has run. Round one is one round of trading later.
    opening: dict[str, float] = field(default_factory=dict)
    supply: int = 0
    deviations: list[str] = field(default_factory=list)


def construct(seed: int, rounds: int, **asset_kw) -> A3Model:
    """``build`` without the run: the model as the opening allocation leaves it."""
    spec = AssetSpec(**asset_kw)
    return A3Model(
        A3Config(
            asset=spec,
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )


def build(seed: int, rounds: int, **asset_kw) -> A3Model:
    model = construct(seed, rounds, **asset_kw)
    model.run()
    return model


def _snapshot(model: A3Model) -> tuple[float, int, float, float]:
    held = model.units.sum(axis=1)
    prod = model._is_production
    return (
        float((held > 0).mean()),
        int((held[prod] > 0).sum()),
        float(held[prod].sum()),
        float(held.sum()),
    )


def run_arm(name: str, kw: dict, seeds: range, rounds: int) -> ArmResult:
    """One arm, every checkpoint, every seed.

    A separate run per checkpoint rather than a single run read at
    intermediate rounds. That costs more and it is the honest form: the
    intermediate state of a three-hundred-round run is not the terminal state of
    a fifty-round run unless nothing in the model looks at the horizon, and
    checking that assumption is more work than paying for the runs.
    """
    out = ArmResult(name=name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DesignDeviation)
        first = [_snapshot(construct(seed, rounds, **kw)) for seed in seeds]
    out.opening = {
        "ownership": float(np.mean([s[0] for s in first])),
        "prod_holders": float(np.mean([s[1] for s in first])),
        "prod_units": float(np.mean([s[2] for s in first])),
        "total_units": float(np.mean([s[3] for s in first])),
    }
    for r in CHECKPOINTS:
        if r > rounds:
            continue
        own, ph, pu, tot = [], [], [], []
        for seed in seeds:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", DesignDeviation)
                m = build(seed, r, **kw)
            out.deviations = sorted(
                set(out.deviations)
                | {str(w.message).split(".")[0] for w in caught}
                | set(m.deviations)
            )
            a, b, c, d = _snapshot(m)
            own.append(a)
            ph.append(b)
            pu.append(c)
            tot.append(d)
            out.supply = int(sum(m.supply))
        out.ownership[r] = float(np.mean(own))
        out.prod_holders[r] = float(np.mean(ph))
        out.prod_units[r] = float(np.mean(pu))
        out.total_units[r] = float(np.mean(tot))
    return out


def path(seed: int, rounds: int, **asset_kw) -> tuple[A3Model, dict]:
    """One run read at every round: who holds, and who comes back.

    The checkpoint tables are six points on a path. This is the path. It
    counts the rounds that end with no production-layer holder, whether any
    production-layer node holds again after the layer has emptied, how many
    times a production-layer node that had sold out holds again at all, and
    how many rounds end with more holders than the round before, in the whole
    population and in the financial layer.
    """
    model = construct(seed, rounds, **asset_kw)
    prod = model._is_production
    holds: list[np.ndarray] = [model.units.sum(axis=1) > 0]
    inner = model._post_round

    def after_round(t: int) -> None:
        inner(t)
        holds.append(model.units.sum(axis=1) > 0)

    model._post_round = after_round  # type: ignore[method-assign]
    model.run()

    held = np.array(holds)                       # row 0 is the opening
    in_prod = held[:, prod].sum(axis=1)
    everyone = held.sum(axis=1)
    upstairs = held[:, ~prod].sum(axis=1)
    empty = np.flatnonzero(in_prod[1:] == 0)
    emptied_at = int(empty[0]) + 1 if empty.size else None
    ever = np.maximum.accumulate(held, axis=0)
    # a node that holds at the end of a round, did not at the end of the one
    # before, and had held at some earlier point: it sold out and came back.
    # The two `*_returns_after_selling_out` counts below are returns, one per
    # such node and round, and not distinct nodes: a node that comes back
    # twice counts twice.
    back = held[1:] & ~held[:-1] & ever[:-1]
    return model, {
        "seed": int(seed),
        "production_layer_empty_from_round": emptied_at,
        "production_holder_after_it_emptied": (
            None if emptied_at is None else bool(in_prod[emptied_at:].any())
        ),
        "production_returns_after_selling_out": int(back[:, prod].sum()),
        "financial_returns_after_selling_out": int(
            back[:, ~prod].sum()
        ),
        "rounds_ending_with_more_holders": int((np.diff(everyone) > 0).sum()),
        "rounds_ending_with_more_financial_holders": int(
            (np.diff(upstairs) > 0).sum()
        ),
        "rounds_ending_with_more_production_holders": int(
            (np.diff(in_prod) > 0).sum()
        ),
    }


def transfer_tiers(seed: int, rounds: int, **asset_kw) -> dict:
    """Which tier the occupancy transfer hands a drawn node, read off the model.

    The draw decides who is in the set and does not consult claims. Inside the
    set the walk is in descending claims, low tier first, one unit each, so
    the low tier goes to the front of the set until it runs out and whoever
    is left takes the next tier up. With 140 drawn and 132 low-tier units,
    the next tier goes to the eight with the least claims. Nothing in the
    transfer reads the layer.
    """
    model = construct(seed, rounds, **asset_kw)
    drawn = np.flatnonzero(model._opening_bypass)
    low = int(model.supply[0])
    order = drawn[np.argsort(-model._claims_0[drawn], kind="stable")]
    rest = order[low:]
    one_next_tier = [
        bool(model.units[i, 0] == 0 and model.units[i, 1] == 1
             and model.units[i].sum() == 1)
        for i in rest
    ]
    return {
        "seed": int(seed),
        "drawn": int(drawn.size),
        "drawn_in_the_production_layer": int(model._is_production[drawn].sum()),
        "low_tier_units": low,
        "drawn_past_the_low_tier": int(rest.size),
        "they_hold_one_unit_of_the_next_tier_and_nothing_else": bool(
            rest.size and all(one_next_tier)
        ),
        "they_are_in_the_production_layer": int(
            model._is_production[rest].sum()
        ),
        "drawn_holding_the_next_tier_and_no_low_unit": int(
            sum(1 for i in drawn
                if model.units[i, 0] == 0 and model.units[i, 1] >= 1)
        ),
    }


def a3_4_reading(models: list[A3Model]) -> dict:
    """A3-4 on one arm's runs, and what the gap between its two sides is.

    The ledger side is a mean over trades and the graph side is a mean over
    tiers, so the two differ by how unevenly each group's trades fall across
    the tiers. With terms that factor into a tier part and a node part, which
    is what ``terms_matrix`` builds, that tier-mix term is the whole gap, and
    the flag says whether it was here to ``1e-10``.

    An arm in which one group completes no resale round trip whose purchase
    is dated after round zero (the trades ``adjusted_trades`` keeps) has no
    reading, and says so. ``trades_better_worse_by_seed`` counts those round
    trips and not every sale: on the occupancy arm the worse-termed group's
    only sales are of units it was handed at the opening.
    """
    counts = []
    for m in models:
        better, worse = terms_pair(m)
        adjusted = adjusted_trades(m)
        good, bad = set(better.tolist()), set(worse.tolist())
        counts.append([
            sum(len(v) for (i, _q), v in adjusted.items() if i in good),
            sum(len(v) for (i, _q), v in adjusted.items() if i in bad),
        ])
    found = terms_differential(models)
    if found is None:
        return {
            "void": True,
            "reason": (
                "one of the two groups completed no round trip whose purchase "
                "is dated after round zero, the trades A3-4 reads"
            ),
            "trades_better_worse_by_seed": counts,
        }
    ledger, graph, _price_free = found
    mix, residual = [], []
    for m in models:
        better, worse = terms_pair(m)
        adjusted = adjusted_trades(m)
        good, bad = set(better.tolist()), set(worse.tolist())
        tb = [(q, r) for (i, q), v in adjusted.items() if i in good for r in v]
        tw = [(q, r) for (i, q), v in adjusted.items() if i in bad for r in v]
        if not tb or not tw:
            continue
        observed = float(np.mean([r for _q, r in tb]) - np.mean([r for _q, r in tw]))
        _, holonomy, _ = loop_sum_from_graph(m, better, worse, adjusted)
        # The tier part of the terms, read off the two groups themselves: each
        # node's log terms less their own mean, averaged over the members. If
        # the terms factor it is the same profile for every node; if they do
        # not, the residual below is not zero and the flag drops.
        members = np.concatenate([better, worse])
        logs = np.log(m.terms[members])
        tier_part = (logs - logs.mean(axis=1, keepdims=True)).mean(axis=0)
        tiers = m.terms.shape[1]
        share_b = np.bincount([q for q, _r in tb], minlength=tiers) / len(tb)
        share_w = np.bincount([q for q, _r in tw], minlength=tiers) / len(tw)
        term = float(((share_b - share_w) * (-tier_part)).sum())
        mix.append(term)
        residual.append(abs(observed - holonomy - term))
    rel = abs(ledger - graph) / abs(graph) if graph else None
    return {
        "void": False,
        "ledger": round(ledger, 10),
        "graph": round(graph, 10),
        "relative_error": None if rel is None else round(rel, 8),
        "within_the_registered_tolerance": bool(
            rel is not None and rel < A3_4_TOLERANCE
        ),
        "tier_mix_term": round(float(np.mean(mix)), 10),
        "the_gap_is_the_tier_mix_term": bool(
            residual and max(residual) < 1e-10
        ),
        "trades_better_worse_by_seed": counts,
    }


def collapsed_pairs(
    arms: dict[str, ArmResult], seeds: range, rounds: int
) -> list[dict]:
    """Which arms are indistinguishable **on the measures being reported**.

    The first version of this compared terminal net worth bitwise and, on the
    registered run, announced that all three arms were distinct while every
    number in every table was identical to the last digit for two of them. A
    guard that offers reassurance exactly when the reader needs a warning is
    worse than no guard, so the test now runs on what is reported.

    Net worth is still compared, separately, because the two answers together
    say something the either alone does not: two arms could move claims around
    without moving **who holds anything**, and for a stage about access that
    would be a collapse even though the models differ. On the registered run
    the net-worth flag for ``auction / continuous`` is false at rounding level
    only: bitwise equal in seeds 0, 1 and 3, at most ``4.5e-13`` apart on net
    worth of order ``10^3`` in seeds 2 and 4, with units identical throughout.
    """
    terminal = {}
    for name, kw in ARMS.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DesignDeviation)
            terminal[name] = [
                build(s, rounds, **FIXED, **kw).net_worth() for s in seeds
            ]
    names = list(ARMS)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            same_reported = all(
                getattr(arms[a], k) == getattr(arms[b], k)
                for k in ("ownership", "prod_holders", "prod_units")
            )
            same_net_worth = all(
                np.array_equal(x, y)
                for x, y in zip(terminal[a], terminal[b], strict=True)
            )
            if same_reported:
                out.append(
                    {
                        "pair": f"{a} / {b}",
                        "identical_on_reported_measures": True,
                        "identical_in_net_worth": same_net_worth,
                    }
                )
    return out


def conservation(seeds: range, rounds: int) -> dict[str, float]:
    """Units are never created and never orphaned. Checklist item 7.

    The pre-A3b defect was stock owned by nobody, so the guard that would have
    caught it is that held units equal supply exactly. Reported as the worst
    discrepancy over every arm and seed, which should be zero and is measured
    rather than asserted.
    """
    worst = 0.0
    for kw in ARMS.values():
        for seed in seeds:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DesignDeviation)
                m = build(seed, rounds, **FIXED, **kw)
            worst = max(worst, abs(float(m.units.sum()) - sum(m.supply)))
    return {"worst_unit_discrepancy": worst}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    ap.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    args = ap.parse_args()
    seeds = range(args.seeds)

    print("A3b: the opening construction as an axis\n")
    print(f"  {args.seeds} seeds, {args.rounds} rounds, mean across seeds")

    zero = run_arm("auction (pre-A3b defaults)", ARMS["auction"], seeds, args.rounds)
    arms = {
        name: run_arm(name, {**FIXED, **kw}, seeds, args.rounds)
        for name, kw in ARMS.items()
    }

    print(f"\n  supply: {zero.supply} units pre-A3b, "
          f"{arms['auction'].supply} at units_per_node=1.1")

    def table(title: str, attr: str, fmt: str) -> None:
        print(f"\n  {title}")
        head = "    round  " + "".join(f"{n:>14s}" for n in arms)
        print(head + f"{'auction pre-A3b':>18s}")
        row = "  opening  "
        for a in arms.values():
            row += format(a.opening[attr], fmt).rjust(14)
        print(row + format(zero.opening[attr], fmt).rjust(18))
        for r in CHECKPOINTS:
            if r > args.rounds:
                continue
            row = f"    {r:5d}  "
            for a in arms.values():
                row += format(getattr(a, attr)[r], fmt).rjust(14)
            row += format(getattr(zero, attr)[r], fmt).rjust(18)
            print(row)

    table("ownership rate (share of nodes holding any unit)", "ownership", ".1%")
    table("production-layer holders, of 180", "prod_holders", ".1f")
    table("units held by the production layer", "prod_units", ".1f")

    cons = conservation(seeds, args.rounds)
    collapsed = collapsed_pairs(arms, seeds, args.rounds)
    print(f"\n  units never created or orphaned: worst discrepancy "
          f"{cons['worst_unit_discrepancy']:.1f}")
    if collapsed:
        print("  COLLAPSED AXIS -- indistinguishable on every reported "
              "measure:")
        for c in collapsed:
            tail = (
                "and identical in net worth too"
                if c["identical_in_net_worth"]
                else "though net worth is not bitwise equal; who holds "
                "what is the same"
            )
            print(f"    {c['pair']} -- {tail}")
        print("    This run may not be described as testing three "
              "constructions.")
    else:
        print("  all three arms differ on the reported measures")

    devs = sorted({d for a in arms.values() for d in a.deviations})
    if devs:
        print("\n  deviations reported by the model:")
        for d in devs:
            print(f"    {d}")

    every = {"auction_pre_a3b": ARMS["auction"],
             **{name: {**FIXED, **kw} for name, kw in ARMS.items()}}
    paths: dict[str, list[dict]] = {}
    a3_4: dict[str, dict] = {}
    for name, kw in every.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DesignDeviation)
            ran = [path(seed, args.rounds, **kw) for seed in seeds]
        paths[name] = [summary for _model, summary in ran]
        a3_4[name] = a3_4_reading([model for model, _summary in ran])
    print("\n  the path between the checkpoints, by seed")
    print("    arm               production layer empty from round      "
          "holds again after   sold out and held again (production / "
          "financial, returns)   rounds ending with more holders")
    for name, rows in paths.items():
        print(f"    {name:16s}  "
              + f"{[r['production_layer_empty_from_round'] for r in rows]!s:36s}  "
              + f"{'yes' if any(r['production_holder_after_it_emptied'] for r in rows) else 'no':18s}  "
              + f"{sum(r['production_returns_after_selling_out'] for r in rows)} / "
              + f"{sum(r['financial_returns_after_selling_out'] for r in rows)}"
              + f"{'':30s}{[r['rounds_ending_with_more_holders'] for r in rows]}")
    print("    The holder count is not monotone: financial-layer nodes sell "
          "out and buy back. What\n    does not come back is the production "
          "layer.")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DesignDeviation)
        handed = [
            transfer_tiers(seed, args.rounds, **every["occupancy"])
            for seed in seeds
        ]
    print("\n  occupancy: the tier a drawn node is handed follows its place in "
          "the drawn set by claims,\n  low tier first, and not its layer")
    for h in handed:
        print(f"    seed {h['seed']}: {h['drawn']} drawn, "
              f"{h['drawn_in_the_production_layer']} of them in the production "
              f"layer; {h['low_tier_units']} low-tier units, so the "
              f"{h['drawn_past_the_low_tier']} with the least claims take the "
              f"next tier"
              + ("" if h["they_hold_one_unit_of_the_next_tier_and_nothing_else"]
                 else " (NOT what the model shows)")
              + f"; {h['they_are_in_the_production_layer']} of those are in "
                f"the production layer")

    print("\n  A3-4 on each arm: the ledger side against the graph side")
    for name, r in a3_4.items():
        if r["void"]:
            print(f"    {name:16s}  no reading: {r['reason']}. Round trips "
                  f"read, by group and seed "
                  f"{r['trades_better_worse_by_seed']}")
            continue
        print(f"    {name:16s}  {r['ledger']:+.5f} against {r['graph']:+.5f}, "
              f"relative error {r['relative_error']:.2%} against "
              f"{A3_4_TOLERANCE:.0%}; tier-mix term {r['tier_mix_term']:+.5f}, "
              + ("which is the whole gap"
                 if r["the_gap_is_the_tier_mix_term"]
                 else "which is NOT the whole gap"))

    RESULTS.mkdir(parents=True, exist_ok=True)
    registered = (
        args.seeds == REGISTERED_SEEDS and args.rounds == REGISTERED_ROUNDS
    )
    out = RESULTS / (
        "a3b_construction.json"
        if registered
        else f"a3b_construction.offparam_{args.seeds}x{args.rounds}.json"
    )
    if not registered:
        print(
            f"\n  off-parameter run against the registered "
            f"{REGISTERED_SEEDS}x{REGISTERED_ROUNDS}: writing beside the "
            f"registered result, not over it"
        )
    out.write_text(
        json.dumps(
            {
                "stage": "A3b",
                "seeds": args.seeds,
                "rounds": args.rounds,
                "fixed": FIXED,
                "arms": {k: v for k, v in ARMS.items()},
                "checkpoints": list(CHECKPOINTS),
                "conservation": cons,
                "collapsed_pairs": collapsed,
                "paths": paths,
                "occupancy_transfer": handed,
                "a3_4_by_construction": a3_4,
                "results": {
                    name: {
                        "supply": a.supply,
                        "opening": a.opening,
                        "ownership": a.ownership,
                        "prod_holders": a.prod_holders,
                        "prod_units": a.prod_units,
                        "total_units": a.total_units,
                        "deviations": a.deviations,
                    }
                    for name, a in ({**arms, "auction_pre_a3b": zero}).items()
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
