"""A13: whether position can be bought and sold, and whether it matters.

Every stage before this one ran on a graph fixed at construction. Measured
rather than inferred: the adjacency and the routing matrix are bitwise identical
after three hundred rounds. That is the framework's thesis written into the
construction, and the thesis is what the stages were built to test, so this
stage opens the channel the construction closed.

What the switch does, and where its two rates come from, is in ``RewireSpec``.
The short form: acquisition fires twice, once to qualify and once for the
cluster, because Chetty et al. (2022) find that perfect exposure by status still
leaves nearly half the connection gap standing; loss is bimodal at about one
third, because Eckbo, Thorburn and Wang (2015) find one third of the CEOs of
bankrupt firms keep full-time executive employment with no median pay change
while two thirds leave the market outright. Neither rate is chosen here.

Why the qualification is a rank and a share rather than a level. Measured before
the arms were written: the richest production node peaks in **round zero** at
``1.0477`` and falls monotonically to ``0.4518``, while the claim stock grows
from ``100`` to ``3412``. A level in claim units is therefore crossed in 300 of
300 rounds at ``0.25``, in 7 at ``0.50``, in 1 at ``1.00``, and in none at
``2.00``. There is no usable band: below it everyone always qualifies and above
it nobody ever does, and the same level loosens for the core and tightens for
the periphery as the stock grows. A rank always has somebody in it, and a share
travels with the stock.

Scope. Most arms here buy edges only. They do not transfer the financial
layer's spending propensity or its role in the payroll channel, both of which
stay with the construction's own split, so those arms read what buying access
does rather than what holding the layer's other two properties does.

A financial-layer node differs from a production-layer node in three ways, not
one: the edges it holds, the spending propensity it draws from, and whether it
pays wages. Promotion above hands over only the first. Handing over all three at
once attributes nothing, so it is a ladder instead, added 2026-08-24: ``both``
buys the edges, ``both + propensity`` adds the layer's spending propensity, and
``both + propensity + payroll`` adds its role in the payroll channel. Each step's difference
belongs to the mechanism that step added, and A13-8 prints the steps.

Usage::

    python experiments/a13_mobility.py
    python experiments/a13_mobility.py --rounds 300 --seeds 5

Writes ``results/a13_mobility.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
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
    RewireSpec,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

DIGITS = 6

#: The two published rates, used as the centre of the sweep rather than as
#: settings. Both are for populations this model's nodes are not, so they place
#: the grid and carry no verdict.
CLUSTER_RATE = 0.5
RETAIN_RATE = 1.0 / 3.0

#: Spans this stage compares itself against, read from the records rather than
#: restated. A2d measured both on the same quantity, terminal top1% wealth.
A2D_RECORD = "a2d_terminal_selector.json"


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


def top_share(v: np.ndarray, k: int) -> float:
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = s.sum()
    return float(s[:k].sum() / total) if total > 0 else float("nan")


ARMS: dict[str, RewireSpec] = {
    "off": RewireSpec(),
    # Rank alone. Registered as the unbounded arm: there is always a top
    # non-core node, so somebody joins every round for ever.
    "rank k=1 cluster 0": RewireSpec(acquire_top_k=1, cluster_rate=0.0),
    "rank k=1 cluster .5": RewireSpec(acquire_top_k=1, cluster_rate=CLUSTER_RATE),
    "rank k=1 cluster 1": RewireSpec(acquire_top_k=1, cluster_rate=1.0),
    "rank k=5 cluster .5": RewireSpec(acquire_top_k=5, cluster_rate=CLUSTER_RATE),
    # Rank and share together. The share is what bounds the core.
    "rank k=2 share .001": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE),
    "rank k=2 share .002": RewireSpec(
        acquire_top_k=2, min_claim_share=0.002, cluster_rate=CLUSTER_RATE),
    # Demotion alone.
    "demote .005": RewireSpec(demote_claim_share=0.005, retain_rate=RETAIN_RATE),
    "demote .005 retain 0": RewireSpec(demote_claim_share=0.005, retain_rate=0.0),
    "demote .005 retain 1": RewireSpec(demote_claim_share=0.005, retain_rate=1.0),
    # Both directions.
    "both": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE),
    "both, degree not conserved": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE, conserve_degree=False),
    "both, every 10 rounds": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE, interval=10),
    # Added 2026-08-24. Demotion in the arms above redirects a node's outbound
    # edges and leaves what the core sends it untouched, which implements the
    # half of the published asymmetry that recovers and none of the half that
    # does not. Grindaker, Kostol and Roszbach find no enduring effect on a
    # displaced executive's labour income after five years and a permanent fall
    # in capital income of about five percent of gross income a year. The
    # recovering half is free here, since the wage mask is never rewired and the
    # out-edges are replaced rather than deleted. The permanent half needs the
    # inbound cut.
    "demote, inbound cut": RewireSpec(
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        demote_cuts_inbound=True),
    "both, inbound cut": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        demote_cuts_inbound=True),
    # Added 2026-08-24. The arms above buy edges and nothing else, so what they
    # measure is what buying access does. A financial-layer node differs from a
    # production-layer node in three ways: the edges it holds, the spending
    # propensity it draws from, and whether it pays wages. Handing over all
    # three at once attributes nothing, which is why this is a ladder with
    # one rung per property and `both` as its first rung. Read the three in
    # order and each step's difference belongs to the thing that step added.
    "both + propensity": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        transfer_propensity=True),
    "both + propensity + payroll": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        transfer_propensity=True, transfer_payroll=True),
}

#: The ladder, in order, first rung first. A13-8 reads the differences between
#: consecutive rungs, so the order is the criterion's meaning and not a display
#: choice.
LADDER = ("both", "both + propensity", "both + propensity + payroll")


def one(spec: RewireSpec, seed: int, rounds: int,
        asset: bool = False) -> dict:
    cfg = NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed,
                        rounds=rounds, rewire=spec)
    net = carrier_model(cfg, asset=asset)
    h = net.run()
    close = h.holdings[-1]
    n = h.node_count
    return {
        "seed": seed,
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top10_wealth": r(top_share(close, n // 10)),
        "gini": r(gini(close)),
        "support": r(float(h.effective_support[-1])),
        "mr_close": r(float(h.total_ratio[-1])),
        "promoted": int(h.promoted.sum()),
        "demoted": int(h.demoted.sum()),
        "core_close": int(net._in_core.sum()),
        "core_open": int(cfg.spec.layer1_size),
    }


def mean_over(rows: list[dict], key: str) -> float:
    return r(float(np.mean([row[key] for row in rows])))


def evaluate(by_arm: dict[str, list[dict]]) -> list[Criterion]:
    out: list[Criterion] = []
    every = [row for rows in by_arm.values() for row in rows]

    out.append(Criterion(
        "A13-1  every arm ran and returned a finite share",
        len(by_arm) == len(ARMS)
        and all(np.isfinite(row["top1_wealth"]) for row in every),
        f"{len(by_arm)}/{len(ARMS)} arms, {len(every)} runs. The stock-flow "
        f"identity is asserted inside the loop, so reaching here is also the "
        f"claim that it held in every round of every run.",
    ))

    # The off arm is the pre-switch construction. Discipline 19 says the check
    # is run rather than argued, and this is where it is run.
    off = by_arm["off"]
    out.append(Criterion(
        "A13-2  the off arm moves nothing",
        all(row["promoted"] == 0 and row["demoted"] == 0 for row in off),
        f"promoted {sum(row['promoted'] for row in off)}, demoted "
        f"{sum(row['demoted'] for row in off)} across {len(off)} runs. With the "
        f"switch off `_rewire` is unreachable, so this is the construction "
        f"itself and every record taken before 2026-08-23 is this arm.",
    ))

    # The span, against the two A2d measured on the same quantity.
    vals = [mean_over(rows, "top1_wealth") for rows in by_arm.values()]
    span = r(max(vals) - min(vals))
    ref = json.loads((RESULTS / A2D_RECORD).read_text(encoding="utf-8"))
    sig = [row["top1_wealth"] for row in ref["sigma_grid"]]
    st = [row["top1_wealth"] for row in ref["structure_grid"]]
    sig_w, st_w = r(max(sig) - min(sig)), r(max(st) - min(st))
    out.append(Criterion(
        "A13-3  mobility's span on terminal top1% wealth, against sigma's and "
        "the structure's",
        True,
        f"mobility {r(min(vals))}-{r(max(vals))}, width {span}. From A2d's "
        f"record on the same quantity: sigma width {sig_w}, structure width "
        f"{st_w}. Read: the larger span names what selects the terminal "
        f"distribution. This criterion prints the three and does not draw a "
        f"line.",
    ))

    # Rank alone is unbounded, and the terminal core size is the object that
    # says so. Three states, all reachable a priori.
    rank_only = [a for a in ARMS if a.startswith("rank") and "share" not in a]
    grew = {a: mean_over(by_arm[a], "core_close") for a in rank_only}
    bounded = {a: mean_over(by_arm[a], "core_close")
               for a in ARMS if "share" in a}
    n_nodes = NetworkSpec().layer1_size + NetworkSpec().layer2_size
    out.append(Criterion(
        "A13-4  the terminal core size, rank alone against rank with a share",
        True,
        "rank alone: " + ", ".join(f"{a} {v:.1f}" for a, v in grew.items())
        + f" out of {n_nodes}; with a share: "
        + ", ".join(f"{a} {v:.1f}" for a, v in bounded.items())
        + f", from an opening core of {NetworkSpec().layer1_size}. Read: a rank "
        f"always has somebody in it, so rank alone admits somebody every round "
        f"for ever; the share is what bounds the object.",
    ))

    # An arm that never fires passes everything by never running. Two arms
    # cannot fire by construction and are named rather than filtered silently:
    # ``off`` is the switch off, and ``retain 1`` sets the retention rate to one
    # with only demotion configured, so every candidate is retained. That second
    # arm is a null and its reading is checked below rather than skipped.
    cannot_fire = {
        a for a, s in ARMS.items()
        if not s.active
        or (s.retain_rate >= 1.0 and s.acquire_top_k == 0 and s.acquire_level == 0.0)
    }
    firing = {a: (mean_over(by_arm[a], "promoted"), mean_over(by_arm[a], "demoted"))
              for a in ARMS if a not in cannot_fire}
    out.append(Criterion(
        "A13-5  every arm that can fire, fired",
        all(p > 0 or d > 0 for p, d in firing.values()),
        "; ".join(f"{a} +{p:.0f}/-{d:.0f}" for a, (p, d) in firing.items())
        + f". Cannot fire by construction and excluded: {sorted(cannot_fire)}.",
    ))

    # The null that cannot fire has to land on the construction exactly, and it
    # is free: retaining every candidate is the same object as not demoting.
    null_arm = "demote .005 retain 1"
    same = all(
        by_arm[null_arm][i][k] == by_arm["off"][i][k]
        for i in range(len(by_arm["off"]))
        for k in ("top1_wealth", "gini", "support", "mr_close")
    )
    out.append(Criterion(
        "A13-5a  retaining every candidate is bitwise the construction",
        same,
        f"{null_arm} against off, four readings per seed over "
        f"{len(by_arm['off'])} seeds: "
        + ("identical" if same else "not identical, so the demotion path is "
           "doing something when it is told to do nothing"),
    ))

    # What does move. Printed, not scored.
    mr = {a: mean_over(rows, "mr_close") for a, rows in by_arm.items()}
    out.append(Criterion(
        "A13-6  what mobility does move: M/R",
        True,
        f"off {mr['off']}, and across the mobility arms "
        f"{r(min(mr.values()))}-{r(max(mr.values()))}. "
        + "; ".join(f"{a} {v}" for a, v in mr.items() if a != "off")
        + ". Read beside A13-3: the two quantities separate under this "
        f"mechanism, and which of them moves is the reading.",
    ))
    # The revolving door. Registered 2026-08-24 with the inbound arms, and it
    # reads a count rather than a level because what it is about is how many
    # times the same nodes cross, not where anybody ends.
    churn = {a: mean_over(rows, "demoted") for a, rows in by_arm.items()
             if ARMS[a].active}
    out_only = [a for a in churn if not ARMS[a].demote_cuts_inbound]
    cut = [a for a in churn if ARMS[a].demote_cuts_inbound]
    out.append(Criterion(
        "A13-7  demotions counted, outbound-only against inbound-cut",
        bool(cut) and bool(out_only),
        "; ".join(f"{a} {churn[a]:.0f}" for a in sorted(churn))
        + ". Read: leaving what the core sends a demoted node untouched lets its "
          "share recover to the promotion condition, so the same nodes cross "
          "repeatedly. Cutting the inbound edges closes that, and the count is "
          "where it shows. This criterion passes when both kinds of arm are "
          "present, which is the only way the comparison exists at all.",
    ))

    # A13-8. One rung per mechanism, so each difference has one owner.
    top1 = {a: mean_over(rows, "top1_wealth") for a, rows in by_arm.items()}
    rungs = [a for a in LADDER if a in top1]
    if len(rungs) == len(LADDER):
        steps = []
        for lo, hi in zip(rungs, rungs[1:]):
            steps.append(
                f"{lo} -> {hi}: top1% {top1[lo]:.6f} -> {top1[hi]:.6f} "
                f"({top1[hi] - top1[lo]:+.6f})"
            )
        first, last = top1[rungs[0]], top1[rungs[-1]]
        out.append(Criterion(
            "A13-8  what a promoted node acquires, one mechanism per rung",
            True,
            "; ".join(steps)
            + f". Whole ladder {first:.6f} -> {last:.6f} ({last - first:+.6f}), "
              f"against the off arm at {top1['off']:.6f}. "
              "Read: the arms before this one buy edges only, so they measure "
              "what buying access does. This ladder adds the spending "
              "propensity and then the payroll role, one at a time, so each "
              "step's difference belongs to the mechanism that step added. "
              "The criterion prints the steps and draws no line: what it "
              "settles is whether the three mechanisms are separable at all, "
              "not how large any of them is.",
        ))
    else:
        out.append(Criterion(
            "A13-8  what a promoted node acquires, one mechanism per rung",
            False,
            f"the ladder needs all of {list(LADDER)} and this run has "
            f"{rungs}; not judged",
            void=True,
        ))

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    ap.add_argument(
        "--no-write", action="store_true",
        help="print the table and the criteria and write no record. For a "
             "smoke run at reduced rounds or seeds, which otherwise "
             "overwrites the registered record at the same path with "
             "numbers taken on a different grid. Bought on 2026-08-24 by "
             "doing exactly that.",
    )
    args = ap.parse_args()

    print(f"A13  rounds={args.rounds} seeds={args.seeds} arms={len(ARMS)}\n")
    hdr = (f"{'arm':<28}{'top1%':>9}{'top10%':>9}{'gini':>9}{'support':>9}"
           f"{'M/R':>9}{'+':>6}{'-':>6}{'core':>6}")
    print(hdr)
    print("-" * len(hdr))

    by_arm: dict[str, list[dict]] = {}
    for tag, spec in ARMS.items():
        rows = [one(spec, seed, args.rounds, args.asset)
                for seed in range(args.seeds)]
        by_arm[tag] = rows
        print(f"{tag:<28}{mean_over(rows,'top1_wealth'):>9.4f}"
              f"{mean_over(rows,'top10_wealth'):>9.4f}{mean_over(rows,'gini'):>9.4f}"
              f"{mean_over(rows,'support'):>9.3f}{mean_over(rows,'mr_close'):>9.2f}"
              f"{mean_over(rows,'promoted'):>6.0f}{mean_over(rows,'demoted'):>6.0f}"
              f"{mean_over(rows,'core_close'):>6.1f}")

    criteria = evaluate(by_arm)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    if args.no_write:
        print("\n  --no-write: no record written")
        return 0 if all(c.passed for c in live) else 1

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a13_mobility.json" if not args.asset else "a13_mobility_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A13",
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "cluster_rate": CLUSTER_RATE,
                "retain_rate": RETAIN_RATE,
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this "
                        "station's registered carrier; the registered "
                        "reading is results/a13_mobility.json"
                    )} if args.asset else {}),
                "arms": {a: [str(v) for v in [ARMS[a]]] for a in ARMS},
                "runs": {a: rows for a, rows in by_arm.items()},
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "detail": c.detail, "void": bool(c.void)}
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
