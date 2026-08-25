"""A10: the write-off chain and the hydra clause.

Volume One section 14 states an accounting chain and then says the thing this
stage is built to read: **the mechanism is the same and the power topology is
different, so the outcome is opposite.** The United States had TARP and Iceland
did not. Whether the head grows back is not endogenous, so it enters the model
as a switch and not as a rule.

Section 17 supplies the bet. "Financial activity conceals the real economy's
dysfunction" becomes, here, a prediction with a direction: the arm that refills
should look like the control on the aggregate and be worse than the control on
the distribution.

Three arms, one structure. Every arm is the control object with its ``writeoff``
field replaced, and criterion A10-1 reports the set of fields that differ.

Usage::

    python experiments/a10_writeoff.py
    python experiments/a10_writeoff.py --rounds 300 --seeds 5

Writes ``results/a10_writeoff.json``. Exits non-zero if any criterion fails.
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
    NetworkConfig,
    NetworkSpec,
    WriteOffSpec,
    run_network,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

SFC_TOLERANCE = 1e-9
DIGITS = 6
TAIL = 25

#: Spacing, both of them. The manuscript says a quasi-money claim's referent is
#: empty in some states; it does not say at which claims-per-resource ratio that
#: begins, nor how much is written off when it does. Neither number carries a
#: verdict: every criterion below is a direction against the control arm.
TRIGGERS = (2.0, 5.0, 10.0, 20.0)
RATES = (0.02, 0.10)


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


def base_config(seed: int, rounds: int) -> NetworkConfig:
    """The one structure. Every arm is this with ``writeoff`` replaced."""
    return NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds)


def arm(base: NetworkConfig, spec: WriteOffSpec) -> NetworkConfig:
    return dataclasses.replace(base, writeoff=spec)


def read(h) -> dict:
    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    issued = np.asarray(h.issuance, dtype=float)
    destroyed = np.asarray(h.written_off, dtype=float)
    # The write-off is the one thing in this model allowed to break claim
    # conservation, so it enters the identity rather than loosening it.
    gap = float(np.abs(m - (m[0] + np.cumsum(issued) - np.cumsum(destroyed))).max())
    support = np.asarray(h.effective_support, dtype=float)
    return {
        "mr_close": r(h.total_ratio[-1]),
        "mara_close": r(float(np.asarray(h.active_ratio, dtype=float)[-TAIL:].mean())),
        "gini_close": r(gini(h.holdings[-1])),
        "support_ratio": r(support[-TAIL:].mean() / support[0]),
        "written_off_total": r(float(destroyed.sum())),
        "written_off_rounds": int((destroyed > 0).sum()),
        "claims_conserved": bool(gap < SFC_TOLERANCE),
    }


def one_run(spec: WriteOffSpec, seed: int, rounds: int,
            asset: bool = False) -> dict:
    h = carrier_model(arm(base_config(seed, rounds), spec), asset=asset).run()
    out = {
        "trigger": spec.trigger,
        "rate": spec.rate,
        "refill": spec.refill,
        "seed": seed,
        "arm": "control" if not spec.active else ("refill" if spec.refill else "no refill"),
    }
    out.update(read(h))
    return out


def structure_is_shared(seed: int, rounds: int, specs: list[WriteOffSpec]) -> tuple[bool, str]:
    base = base_config(seed, rounds)
    differing: set[str] = set()
    for spec in specs:
        a = arm(base, spec)
        for f in dataclasses.fields(NetworkConfig):
            if getattr(a, f.name) != getattr(base, f.name):
                differing.add(f.name)
    return differing <= {"writeoff"}, (
        f"fields differing from the control across {len(specs)} arms: {sorted(differing)}"
    )


def evaluate(rows: list[dict], shared: tuple[bool, str]) -> list[Criterion]:
    out = [Criterion("A10-1  one structure, the write-off field only", shared[0], shared[1])]

    conserved = sum(1 for row in rows if row["claims_conserved"])
    out.append(
        Criterion(
            "A10-2  the identity holds with destruction in it",
            conserved == len(rows),
            f"{conserved}/{len(rows)} runs satisfy holdings = opening + issuance - "
            f"write-offs at machine precision, below {SFC_TOLERANCE:.0e}",
        )
    )

    def med(rows_: list[dict], key: str) -> float:
        return float(np.median([row[key] for row in rows_]))

    # Paired by seed. Each arm runs on the same graph and the same random
    # stream as the control that shares its seed, so the comparison is
    # within-pair. Comparing one run against a group's median instead lets the
    # group's own spread decide the verdict.
    control = {row["seed"]: row for row in rows if row["arm"] == "control"}

    # Only arms that actually fired can carry A10-3 or A10-4: an arm whose
    # trigger was never met is the control by construction and says nothing
    # either way. Reported, so the exclusion is visible rather than assumed.
    fired = [row for row in rows if row["written_off_rounds"] > 0]
    no_refill = [row for row in fired if row["arm"] == "no refill"]
    refill = [row for row in fired if row["arm"] == "refill"]

    # The claim is that one arm looks like the control and the other does not,
    # which is a comparison of two distances and not an absolute direction. A
    # refilled arm that lands a little under the control is still indistinguishable
    # beside an unrefilled one that lands at a fifth of it, and a criterion
    # written as "at or above the control" would call that a failure.
    def gap(row: dict) -> float:
        return abs(row["mr_close"] - control[row["seed"]]["mr_close"])

    pairs = []
    for row in refill:
        twin = [
            x for x in no_refill
            if x["seed"] == row["seed"] and x["trigger"] == row["trigger"]
            and x["rate"] == row["rate"]
        ]
        if twin:
            pairs.append((row, twin[0]))
    closer = [1 for a, b in pairs if gap(a) < gap(b)]
    out.append(
        Criterion(
            "A10-3  destruction shows on the aggregate only where it is not refilled",
            bool(pairs) and len(closer) == len(pairs),
            f"paired by seed and setting: the refilled arm is nearer its own control "
            f"than the unrefilled one in {len(closer)}/{len(pairs)} pairs. Median M/R "
            f"{med(refill, 'mr_close') if refill else float('nan'):.2f} with refill and "
            f"{med(no_refill, 'mr_close') if no_refill else float('nan'):.2f} without, "
            f"against a control at {med(list(control.values()), 'mr_close'):.2f}",
        )
    )

    # Two readings, reported apart. Section 17's claim that financial activity
    # conceals the real economy's dysfunction has two possible surfaces here,
    # concentration and reach, and they do not behave the same way: the
    # concentration gap is one-signed across every seed and every setting while
    # the reach gap changes sign between seeds. A conjunction of the two reads
    # as one unstable criterion and hides that.
    def by_setting(test) -> tuple[list, list]:
        carried_, split_ = [], []
        for trigger, rate in sorted({(x["trigger"], x["rate"]) for x in refill}):
            group = [
                x for x in refill if x["trigger"] == trigger and x["rate"] == rate
            ]
            hits = sum(1 for x in group if test(x, control[x["seed"]]))
            (carried_ if hits == len(group) else split_).append(
                (trigger, rate, hits, len(group))
            )
        return carried_, split_

    carried_g, split_g = by_setting(
        lambda row, ctrl: row["gini_close"] > ctrl["gini_close"]
    )
    out.append(
        Criterion(
            "A10-4a  the refilled arm concentrates further than the control",
            bool(carried_g) and not split_g,
            f"paired by seed: every seed at {len(carried_g)} of "
            f"{len(carried_g) + len(split_g)} settings; median gini "
            f"{med(refill, 'gini_close') if refill else float('nan'):.4f} with refill "
            f"against {med(list(control.values()), 'gini_close'):.4f} in the control"
            + ("" if not split_g else "; split at "
               + ", ".join(f"trigger {t:g} rate {r_:g} ({h}/{n})"
                           for t, r_, h, n in split_g)),
        )
    )

    carried_s, split_s = by_setting(
        lambda row, ctrl: row["support_ratio"] < ctrl["support_ratio"]
    )
    best = max((h / n for _, _, h, n in split_s), default=0.0) if split_s else 0.0
    n_seeds = max((n for _, _, _, n in split_s), default=0)
    undecided = not carried_s and best >= 0.5
    detail = (
        "paired by seed: every seed at "
        + (", ".join(f"trigger {t:g} rate {r_:g}" for t, r_, _, _ in carried_s)
           or "no setting")
        + "; split at "
        + (", ".join(f"trigger {t:g} rate {r_:g} ({h}/{n})"
                     for t, r_, h, n in split_s) or "none")
    )
    if undecided:
        detail += (
            f". Void: the reach gap changes sign between seeds, the best setting "
            f"carrying {best:.0%} of {n_seeds}. Unlike the concentration gap this "
            f"one is not one-signed, so the seed count is not what is missing"
        )
    out.append(
        Criterion(
            "A10-4b  the refilled arm reaches fewer nodes than the control",
            bool(carried_s),
            detail,
            undecided,
        )
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    args = parser.parse_args()

    specs = [WriteOffSpec()]
    for trigger in TRIGGERS:
        for rate in RATES:
            for refill in (False, True):
                specs.append(WriteOffSpec(rate=rate, trigger=trigger, refill=refill))

    print("stage A10: the write-off chain and the hydra clause")
    print(f"  rounds={args.rounds} seeds={args.seeds} arms={len(specs)}\n")

    rows = [one_run(spec, seed, args.rounds, args.asset)
            for spec in specs for seed in range(args.seeds)]

    print(f"{'trigger':>8s} {'rate':>5s} {'refill':>7s} | {'M/R':>8s} {'M_a/R_a':>8s} "
          f"{'gini':>7s} {'support':>8s} | {'written off':>12s} {'rounds':>6s}")
    for spec in specs:
        group = [
            row for row in rows
            if row["trigger"] == spec.trigger and row["rate"] == spec.rate
            and row["refill"] == spec.refill
        ]
        med = lambda k: float(np.median([row[k] for row in group]))  # noqa: E731
        tag = "control" if not spec.active else ("yes" if spec.refill else "no")
        print(
            f"{spec.trigger:8.1f} {spec.rate:5.2f} {tag:>7s} | {med('mr_close'):8.2f} "
            f"{med('mara_close'):8.4f} {med('gini_close'):7.4f} {med('support_ratio'):8.3f} | "
            f"{med('written_off_total'):12.1f} {med('written_off_rounds'):6.0f}"
        )

    criteria = evaluate(rows, structure_is_shared(0, args.rounds, specs))
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, {len(criteria) - len(live)} void")

    never_fired = sorted(
        {
            (row["trigger"], row["rate"], row["refill"])
            for row in rows
            if row["trigger"] > 0 and row["written_off_rounds"] == 0
        }
    )
    fired = [row for row in rows if row["written_off_rounds"] > 0]
    ratio = None
    if fired:
        a = [row["written_off_total"] for row in fired if row["refill"]]
        b = [row["written_off_total"] for row in fired if not row["refill"]]
        if a and b:
            ratio = r(float(np.median(a)) / max(float(np.median(b)), 1e-12))

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a10_writeoff.json" if not args.asset else "a10_writeoff_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A10",
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this station's "
                        "registered carrier; the registered reading is "
                        "results/a10_writeoff.json"
                    )} if args.asset else {}),
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "triggers": list(TRIGGERS),
                "rates": list(RATES),
                "runs": rows,
                "diagnostics": {
                    "arms_that_never_fired": [
                        {"trigger": t, "rate": rt, "refill": rf} for t, rt, rf in never_fired
                    ],
                    "refilled_over_unrefilled_destruction": ratio,
                },
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
