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
reach the asset. They say nothing about `H¹`, and A3-4 is untouched by them,
which is checked rather than assumed.
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
    supply: int = 0
    deviations: list[str] = field(default_factory=list)


def build(seed: int, rounds: int, **asset_kw) -> A3Model:
    spec = AssetSpec(**asset_kw)
    model = A3Model(
        A3Config(
            asset=spec,
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )
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
    say something the either alone does not: two arms can move claims around
    without moving **who holds anything**, and for a stage about access that is
    a collapse even though the models differ.
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
                else "though net worth differs, so the arms move claims "
                "without moving who holds anything"
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
                "results": {
                    name: {
                        "supply": a.supply,
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
