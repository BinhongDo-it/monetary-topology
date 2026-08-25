"""A11: the subsistence floor, and whether position decides who starves.

Volume One section 8 draws the line this stage is built to test: **MPC is a
property of an agent; this framework talks about the edges of the graph. An
agent with a high marginal propensity and no in-edge starves anyway.** That is
falsifiable here, because the repository already carries the arm that erases the
topology while leaving every behavioural parameter alone: ``uniform_access``
puts every node on a complete graph. If starvation still lands on the same set
of nodes there, the claim does not hold on this carrier.

The floor itself is derived rather than transcribed; the derivation is in
``SubsistenceSpec``. Leaving is absorbing and it destroys nothing: a node that
drops out freezes, and the claim total is untouched.

Usage::

    python experiments/a11_subsistence.py
    python experiments/a11_subsistence.py --rounds 300 --seeds 5

Writes ``results/a11_subsistence.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.mechanisms import gini
from monetary_topology.network import (
    Network,
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

SFC_TOLERANCE = 1e-9
DIGITS = 6
TAIL = 25

#: Multiples of the resource pool per node. Both the pool and the node count are
#: existing construction quantities, so the scale introduces no new number. The
#: multiples are spacing and carry no verdict.
NEED_MULTIPLES = (0.05, 0.20, 0.50, 1.00)
GRACES = (1, 5)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else ("PASS" if self.passed else "FAIL")
        return f"  [{mark}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


def base_config(seed: int, rounds: int, uniform: bool) -> NetworkConfig:
    return NetworkConfig(
        spec=NetworkSpec(seed=seed, uniform_access=uniform), seed=seed, rounds=rounds
    )


def one_run(need_mult: float, grace: int, seed: int, rounds: int,
            uniform: bool, asset: bool = False) -> dict:
    base = base_config(seed, rounds, uniform)
    n = base.spec.size
    scale = base.total_resources / n
    spec = (
        SubsistenceSpec(need=need_mult * scale, grace=grace)
        if need_mult > 0
        else SubsistenceSpec()
    )
    cfg = dataclasses.replace(base, subsistence=spec)
    net = carrier_model(cfg, asset=asset)
    h = net.run()

    alive = net._alive
    dead = ~alive
    # The two node sets, by index rather than by name: on the complete graph the
    # layers no longer mean anything behaviourally, and that is the point. The
    # same index ranges are compared on both graphs.
    fin = base.spec.financial_nodes
    prod = base.spec.household_nodes
    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    issued = np.asarray(h.issuance, dtype=float)
    destroyed = np.asarray(h.written_off, dtype=float)
    gap = float(np.abs(m - (m[0] + np.cumsum(issued) - np.cumsum(destroyed))).max())
    support = np.asarray(h.effective_support, dtype=float)

    return {
        "need_multiple": need_mult,
        "grace": grace,
        "seed": seed,
        "graph": "complete" if uniform else "stratified",
        "need": r(spec.need),
        "starved": int(dead.sum()),
        "starved_financial": int(dead[fin].sum()),
        "starved_production": int(dead[prod].sum()),
        "financial_nodes": int(fin.size),
        "production_nodes": int(prod.size),
        "starved_rate_financial": r(dead[fin].mean()),
        "starved_rate_production": r(dead[prod].mean()),
        "frozen_holdings": r(float(net.holdings[dead].sum())),
        "mr_close": r(h.total_ratio[-1]),
        "mara_close": r(float(np.asarray(h.active_ratio, dtype=float)[-TAIL:].mean())),
        "gini_close": r(gini(h.holdings[-1])),
        "support_ratio": r(support[-TAIL:].mean() / support[0]),
        "claims_conserved": bool(gap < SFC_TOLERANCE),
    }


def evaluate(rows: list[dict], shared: tuple[bool, str]) -> list[Criterion]:
    out = [Criterion("A11-1  one structure, the subsistence field only", shared[0], shared[1])]

    conserved = sum(1 for row in rows if row["claims_conserved"])
    out.append(
        Criterion(
            "A11-2  leaving destroys nothing",
            conserved == len(rows),
            f"{conserved}/{len(rows)} runs hold the claim identity with the floor on, "
            f"below {SFC_TOLERANCE:.0e}. A node that drops out freezes rather than "
            f"being written off, so this is a check that the two mechanisms do not "
            f"touch",
        )
    )

    def med(rows_: list[dict], key: str) -> float:
        return float(np.median([row[key] for row in rows_])) if rows_ else float("nan")

    strat = [row for row in rows if row["graph"] == "stratified" and row["starved"] > 0]
    comp = [row for row in rows if row["graph"] == "complete" and row["starved"] > 0]

    # The gap between the two sets' starvation rates, on each graph. On the
    # stratified graph the framework's claim says it should be wide; erasing the
    # topology should close it, and the behavioural parameters are untouched
    # between the two.
    def spread(rows_: list[dict]) -> list[float]:
        return [
            row["starved_rate_production"] - row["starved_rate_financial"] for row in rows_
        ]

    fewer = [row for row in strat if row["starved_rate_financial"] < row["starved_rate_production"]]
    out.append(
        Criterion(
            "A11-3  on the stratified graph starvation lands on the production side",
            bool(strat) and len(fewer) == len(strat),
            f"{len(fewer)}/{len(strat)} firing runs have the financial layer starving at "
            f"a lower rate than the production layer; median rates "
            f"{med(strat, 'starved_rate_financial'):.3f} against "
            f"{med(strat, 'starved_rate_production'):.3f}",
        )
    )

    paired = []
    for row in comp:
        twin = [
            x for x in strat
            if x["seed"] == row["seed"] and x["need_multiple"] == row["need_multiple"]
            and x["grace"] == row["grace"]
        ]
        if twin:
            paired.append((row, twin[0]))
    closed = [
        1 for c, s in paired
        if abs(c["starved_rate_production"] - c["starved_rate_financial"])
        < abs(s["starved_rate_production"] - s["starved_rate_financial"])
    ]
    out.append(
        Criterion(
            "A11-4  erasing the topology closes the gap",
            bool(paired) and len(closed) == len(paired),
            f"paired by seed, floor and grace: the gap between the two sets' "
            f"starvation rates is narrower on the complete graph in "
            f"{len(closed)}/{len(paired)} pairs. Median gap "
            f"{med(comp, 'starved_rate_production') - med(comp, 'starved_rate_financial'):+.3f} "
            f"complete against "
            f"{med(strat, 'starved_rate_production') - med(strat, 'starved_rate_financial'):+.3f} "
            f"stratified",
        )
    )
    return out


def structure_is_shared(seed: int, rounds: int) -> tuple[bool, str]:
    base = base_config(seed, rounds, False)
    scale = base.total_resources / base.spec.size
    differing: set[str] = set()
    for mult in NEED_MULTIPLES:
        for grace in GRACES:
            a = dataclasses.replace(
                base, subsistence=SubsistenceSpec(need=mult * scale, grace=grace)
            )
            for f in dataclasses.fields(NetworkConfig):
                if getattr(a, f.name) != getattr(base, f.name):
                    differing.add(f.name)
    return differing <= {"subsistence"}, (
        f"fields differing from the control across all arms: {sorted(differing)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    args = parser.parse_args()

    print("stage A11: the subsistence floor")
    print(f"  rounds={args.rounds} seeds={args.seeds}\n")

    rows = []
    for uniform in (False, True):
        for seed in range(args.seeds):
            rows.append(one_run(0.0, 1, seed, args.rounds, uniform, args.asset))
        for mult in NEED_MULTIPLES:
            for grace in GRACES:
                for seed in range(args.seeds):
                    rows.append(
                        one_run(mult, grace, seed, args.rounds, uniform, args.asset))

    print(f"{'graph':>11s} {'need':>6s} {'grace':>5s} | {'starved':>7s} {'fin':>5s} {'prod':>5s} "
          f"| {'M/R':>7s} {'gini':>7s} {'M_a/R_a':>8s} {'frozen':>9s}")
    for uniform in (False, True):
        tag = "complete" if uniform else "stratified"
        for mult in (0.0,) + NEED_MULTIPLES:
            for grace in (GRACES if mult else (1,)):
                g = [
                    row for row in rows
                    if row["graph"] == tag and row["need_multiple"] == mult
                    and row["grace"] == grace
                ]
                if not g:
                    continue
                med = lambda k: float(np.median([row[k] for row in g]))  # noqa: E731
                label = "off" if not mult else f"{mult:g}x"
                print(
                    f"{tag:>11s} {label:>6s} {grace:5d} | {med('starved'):7.0f} "
                    f"{med('starved_financial'):5.0f} {med('starved_production'):5.0f} | "
                    f"{med('mr_close'):7.2f} {med('gini_close'):7.4f} {med('mara_close'):8.4f} "
                    f"{med('frozen_holdings'):9.1f}"
                )

    criteria = evaluate(rows, structure_is_shared(0, args.rounds))
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, {len(criteria) - len(live)} void")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a11_subsistence.json" if not args.asset
        else "a11_subsistence_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A11",
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this station's "
                        "registered carrier; the registered reading is "
                        "results/a11_subsistence.json"
                    )} if args.asset else {}),
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "need_multiples": list(NEED_MULTIPLES),
                "graces": list(GRACES),
                "runs": rows,
                "criteria": [
                    {
                        "name": c.name,
                        "passed": bool(c.passed),
                        "detail": c.detail,
                        "void": bool(c.void),
                    }
                    for c in criteria
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
