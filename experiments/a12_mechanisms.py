"""A12: does the coverage result survive the two mechanisms added after it.

A8 read four surfaces off one curve with the write-off chain and the subsistence
floor both switched off, because neither existed yet. Both act on quantities the
four surfaces are read from: destruction presses on M/R directly, and a floor
moves the production layer out of circulation, which is where the support set and
the payroll channel live. So this is a question rather than a re-run, and it can
fail.

The four surface definitions are imported from A8's module rather than restated,
so the two stages cannot drift apart.

Usage::

    python experiments/a12_mechanisms.py --rounds 300

Writes ``results/a12_mechanisms.json``.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import A3Config, A3Model, AssetSpec
from monetary_topology.config import WageChannel
from monetary_topology.redistribution import A6Config, FiscalSpec, run_a6
from monetary_topology.mechanisms import gini
from monetary_topology.network import (
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
    WriteOffSpec,
    run_network,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SFC_TOLERANCE = 1e-9
DIGITS = 6
TAIL = 25

#: Spacing. The floor is A11's middle setting, where the production layer loses
#: about three quarters rather than all of itself, since the wiped-out setting
#: carries no information. The write-off is A10's mildest.
FLOOR_MULTIPLE = 0.20
WRITEOFF = WriteOffSpec(rate=0.02, trigger=5.0)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A8 = _load(ROOT / "experiments" / "a8_coverage.py", "_a8")
_A2 = _load(ROOT / "experiments" / "a2_support_contraction.py", "_a2")
EDGES = tuple(_A2.AUTONOMOUS_EDGES)
ELASTICITIES = tuple(_A2.ELASTICITIES)
MID = int(_A2.INTERMEDIATE_SIZE)

#: The carrier, taken from A8 rather than restated, for the same reason the
#: surface definitions are: two stages that read the same curve must not be
#: able to drift apart on what the curve is drawn over.
Carrier = _A8.Carrier
carrier_at = _A8.carrier_at
BASE_CARRIER = _A8.BASE


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    #: A criterion whose object is not on the table. Distinct from FAIL:
    #: FAIL says the thing was looked at and did not hold, this says there
    #: was nothing to look at. Reachable only off the registered carrier,
    #: where the record a criterion compares against may not exist yet.
    undecidable: bool = False

    def line(self) -> str:
        mark = "----" if self.undecidable else (
            "PASS" if self.passed else "FAIL")
        return f"  [{mark}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


def base_config(
    f2i: int, elasticity: float, rounds: int, seed: int,
    carrier: Carrier = BASE_CARRIER,
) -> NetworkConfig:
    return NetworkConfig(
        spec=NetworkSpec(
            seed=seed,
            layer1_size=carrier.layer1_size,
            intermediate_size=carrier.intermediate_size,
            layer2_size=carrier.layer2_size,
            financial_to_intermediate_edges=f2i,
        ),
        rounds=rounds, seed=seed, wages=WageChannel(elasticity=elasticity),
    )


#: A6's transfer rate, taken from A9's reading rather than chosen here: 0.20 is
#: where both of that stage's readings turned together. The transfer is a levy on
#: the financial layer paid out per head across the production layer, so it moves
#: claims rather than creating them.
TRANSFER_RATE = 0.20

#: Arm -> (subsistence, write-off, transfer rate). ``None`` for the floor means
#: the floor is on at ``FLOOR_MULTIPLE``.
#: The refilled write-off. The hydra clause is a switch because the manuscript
#: says whether the head grows back is political rather than mechanical.
WRITEOFF_REFILL = dataclasses.replace(WRITEOFF, refill=True)

#: The floor's need, in the units claims and resources share at the opening.
#: Constant across the grid, because neither the resource pool nor the node
#: count varies inside one. **It is not constant across carriers**: the
#: floor is a level on the real side and its natural scale is the resource
#: pool over the node count, so a larger carrier divides the same pool
#: further and subsistence per node falls with it. Stated here at the
#: registered carrier and recomputed by ``need_for`` wherever that moves.
#: Written once per carrier so the three floor variants carry the same
#: number and only their two booleans differ.
def need_for(carrier: Carrier) -> float:
    return FLOOR_MULTIPLE * 100.0 / carrier.nodes


FLOOR_NEED = need_for(BASE_CARRIER)

def arms_for(need: float) -> dict:
    """Arm -> (subsistence, write-off, transfer rate), at one floor need.

    A function rather than a literal because three of the arms name a floor
    level, and that level is a number per carrier, not a constant of the model.
    The arms whose floor is ``None`` never needed one: ``one_run`` builds those
    from the config's own resource pool and node count, so they were already
    right at any size and only the named variants were not.
    """
    return {
        "off": (SubsistenceSpec(), WriteOffSpec(), 0.0),
        "floor": (None, WriteOffSpec(), 0.0),
        "writeoff": (SubsistenceSpec(), WRITEOFF, 0.0),
        "both": (None, WRITEOFF, 0.0),
        "floor+transfer": (None, WriteOffSpec(), TRANSFER_RATE),
        "both+transfer": (None, WRITEOFF, TRANSFER_RATE),
        # Added 2026-08-23. Arm names describe the switches, not the episodes:
        # section 18's two regimes motivated the settings, and an arm named for
        # an episode would claim a correspondence this stage does not establish.
        # ``None`` above builds the floor with both of its
        # booleans off, which is the original behaviour and the only variant this
        # stage had run. The two named variants below are the manuscript's two
        # regimes and neither had ever been run anywhere.
        "floor payroll severed": (SubsistenceSpec.payroll_severed(need=need), WriteOffSpec(), 0.0),
        "floor payroll kept": (
            SubsistenceSpec.payroll_kept_reversible(need=need), WriteOffSpec(), 0.0),
        "writeoff refill": (SubsistenceSpec(), WRITEOFF_REFILL, 0.0),
        "severed+norefill": (
            SubsistenceSpec.payroll_severed(need=need), WRITEOFF, 0.0),
        "kept+refill": (
            SubsistenceSpec.payroll_kept_reversible(need=need), WRITEOFF_REFILL, 0.0),
        # Added 2026-08-24. The three arms above put a node below the floor
        # **out of the graph**, and with ``cut_payroll`` false it then draws a
        # wage every round and spends nothing: measured, a hundred and sixty
        # five such nodes end the run holding 85.6 percent of every claim
        # outstanding. Receiving and not passing on is retention, and retention
        # is this framework's mechanism for the top layer, so those arms apply a
        # top-layer operation to the bottom.
        #
        # ``drawdown`` is the state that has somebody in it: below the floor the
        # node stays in the graph and spends ``min(need, holdings)``, so it goes
        # on consuming, consumes less, and eats its savings. Nothing is
        # absorbing; a node with nothing spends nothing and one whose edge
        # returns is simply not below the floor any more.
        "floor drawdown": (
            SubsistenceSpec(need=need, mode="drawdown"), WriteOffSpec(), 0.0),
        "drawdown+writeoff": (
            SubsistenceSpec(need=need, mode="drawdown"), WRITEOFF, 0.0),
        "drawdown+transfer": (
            SubsistenceSpec(need=need, mode="drawdown"), WriteOffSpec(), TRANSFER_RATE),
    }


#: The arms at the registered carrier.
ARMS = arms_for(FLOOR_NEED)

#: The two arms-with-transfers and the arms they are read against. Paired cell
#: by cell on ``(f2i, elasticity)``, never by summary statistic: the median over
#: this grid reads 165 against 165 on the excluded-node count while the cells
#: underneath it are 11 down, 12 level and 22 up.
TRANSFER_PAIRS = (
    ("floor", "floor+transfer"),
    ("both", "both+transfer"),
    ("floor drawdown", "drawdown+transfer"),
)

#: Quantities A12-5's verdict may rest on, with True where a larger number is
#: the better outcome. Both are about who is still in circulation, which is what
#: the floor takes away and therefore what a transfer would have to give back.
JUDGED = (("starved", False), ("support_ratio", True))

#: Printed beside the judged quantities and deliberately not judged on.
#: A per-head transfer paid out of the financial layer is a levelling device, so
#: the closing gini's direction is what this channel is defined to do; a verdict
#: read off it asks a device whether it is itself. Measured, across both
#: carriers, the gini moves by -0.20 to -0.86 in 90 of 90 paired cells and never
#: once in the other direction.
PRINTED = ("wage_funding", "gini_close")


def one_run(
    arm: str, f2i: int, elasticity: float, rounds: int, seed: int,
    arms: dict | None = None, carrier: Carrier = BASE_CARRIER,
) -> dict:
    base = base_config(f2i, elasticity, rounds, seed, carrier)
    floor_spec, write_spec, transfer = (ARMS if arms is None else arms)[arm]
    if floor_spec is None:
        floor_spec = SubsistenceSpec(
            need=FLOOR_MULTIPLE * base.total_resources / base.spec.size
        )
    cfg = dataclasses.replace(base, subsistence=floor_spec, writeoff=write_spec)
    if transfer > 0.0:
        # A6's model is a subclass of this one, so the floor and the write-off
        # ride along untouched and the only addition is the fiscal channel.
        #
        # **It cannot ride on the asset carrier.** ``A6Model`` and
        # ``A3Model`` are both subclasses of ``Network`` and there is no
        # composition point between them, so a transfer arm on the asset
        # carrier has no object to run. ``main`` drops those arms by name
        # rather than silently, and A12-5 reads its third state there.
        if carrier.asset:
            raise ValueError(
                "transfer arms have no model on the asset carrier"
            )
        _, h = run_a6(
            A6Config(fiscal=FiscalSpec(rate=transfer, channel="transfer"), network=cfg)
        )
    elif carrier.asset:
        h = A3Model(A3Config(asset=AssetSpec(), network=cfg)).run()
    else:
        h = run_network(cfg)

    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    destroyed = np.asarray(h.written_off, dtype=float)
    gap = float(
        np.abs(m - (m[0] + np.cumsum(np.asarray(h.issuance, dtype=float))
                    - np.cumsum(destroyed))).max()
    )
    support = np.asarray(h.effective_support, dtype=float)
    row = {
        "arm": arm, "f2i": int(f2i), "elasticity": float(elasticity),
        "mr_ratio": r(h.total_ratio[-1] / h.total_ratio[0]),
        "mara_ratio": r(float(np.asarray(h.active_ratio, dtype=float)[-TAIL:].mean())
                        / h.active_ratio[0]),
        "m_ratio": r(m[-1] / m[0]),
        "gini_open": r(gini(h.holdings[0])), "gini_close": r(gini(h.holdings[-1])),
        "resource_levels": int(np.unique(h.total_resources).size),
        "support_ratio": r(support[-TAIL:].mean() / support[0]),
        "wage_funding": r(float(np.asarray(h.wage_funding_ratio, dtype=float)[-TAIL:].mean())),
        "wage_owed_ratio": r(float(np.asarray(h.wage_owed, dtype=float)[-TAIL:].mean())
                             / max(float(h.wage_owed[0]), 1e-12)),
        "starved": int(h.starved[-1]),
        "transfer_rate": transfer,
        "written_off_total": r(float(destroyed.sum())),
        "claims_conserved": bool(gap < SFC_TOLERANCE),
    }
    # A8's own definitions, imported rather than restated.
    row["surfaces"] = _A8.surfaces_present(row)
    row["all_four"] = bool(all(row["surfaces"].values()))
    return row


def transfer_criterion(rows: list[dict], hits: dict) -> Criterion:
    """A12-5. Pulled out of ``main`` so it can be replayed on a stored
    record without re-running five hundred simulations: it is a pure
    function of the rows, so a replay and a re-run return the same object.
    """
    # A12-5, reshaped 2026-08-24. Its first form asked whether the transfer arm
    # carries all four surfaces, and that question had one answer available to
    # it: surface three needs the closing gini above the opening one, and a
    # per-head transfer lowers the gini by construction. Measured afterwards,
    # 90 of 90 paired cells across both carriers, range -0.20 to -0.86, never
    # once positive. So the criterion's other branch was not reachable and the
    # arm was answering its own construction rather than a question.
    #
    # The reachable question underneath it is the one the floor raised: the
    # floor pushes nodes out of circulation and the transfer hands them income,
    # so does the transfer put them back. Nothing in the construction settles
    # that. The verdict therefore rests on the two quantities about who is still
    # in circulation, and the two quantities the channel is defined to move are
    # printed beside them without a verdict on them.
    #
    # The reachability check below is the executable form of that lesson: a
    # quantity that comes back one-directional over every paired cell is locked
    # by the construction and leaves the verdict rather than deciding it. If
    # both leave, the criterion reads undecidable, which is a third state and
    # not a failure.
    # The pairs may not exist. On the asset carrier the transfer arms have no
    # model to run, so they are dropped before the grid, and a criterion whose
    # object is absent reads its third state rather than failing: FAIL says
    # the thing was looked at and did not hold.
    present = [
        (base, arm) for base, arm in TRANSFER_PAIRS
        if any(r["arm"] == arm for r in rows)
    ]
    if not present:
        return Criterion(
            "A12-5  the transfer channel, and who is left in circulation",
            False,
            "No transfer arm ran on this carrier, so there is nothing to "
            "pair against. A6 and A3 are both Network subclasses and have "
            "no composition point, so a fiscal channel on the asset carrier "
            "has no model. This is absence of an object, not a failed "
            "reading.",
            undecidable=True,
        )

    def direction_counts(base: str, arm: str, key: str) -> tuple[int, int, int]:
        """Paired cells where the transfer arm reads below, level with, above."""
        b = {(r["f2i"], r["elasticity"]): r for r in rows if r["arm"] == base}
        t = {(r["f2i"], r["elasticity"]): r for r in rows if r["arm"] == arm}
        cells = sorted(set(b) & set(t))
        return (
            sum(1 for c in cells if t[c][key] < b[c][key]),
            sum(1 for c in cells if t[c][key] == b[c][key]),
            sum(1 for c in cells if t[c][key] > b[c][key]),
        )

    def totals(key: str) -> tuple[int, int, int]:
        d = s_ = u = 0
        for base, arm in present:
            dd, ss, uu = direction_counts(base, arm, key)
            d, s_, u = d + dd, s_ + ss, u + uu
        return d, s_, u

    paired = all(
        {(r["f2i"], r["elasticity"]) for r in rows if r["arm"] == base}
        == {(r["f2i"], r["elasticity"]) for r in rows if r["arm"] == arm}
        and len([r for r in rows if r["arm"] == base]) > 0
        for base, arm in present
    )

    counted = {key: totals(key) for key, _ in JUDGED}
    locked = [k for k, (d, _s, u) in counted.items() if d == 0 or u == 0]
    live = [k for k, _ in JUDGED if k not in locked]
    better = {
        k: ((counted[k][2] > counted[k][0]) if hib else (counted[k][0] > counted[k][2]))
        for k, hib in JUDGED
        if k in live
    }

    if not live:
        branch = ("undecidable: every candidate quantity came back one-directional, "
                  "so the construction is answering, not the run")
    elif all(better.values()):
        branch = "branch A: the transfer puts back the circulation the floor removed"
    elif not any(better.values()):
        branch = ("branch B: the transfer pays income out and takes circulation "
                  "away with it")
    else:
        branch = ("branch C: the two quantities point opposite ways, reported "
                  "separately rather than merged into one verdict")

    def counts_text(key: str) -> str:
        parts = []
        for base, arm in present:
            d, s_, u = direction_counts(base, arm, key)
            parts.append(f"{base}->{arm} {d}/{s_}/{u}")
        return f"{key} down/level/up " + ", ".join(parts)

    return Criterion(
        "A12-5  the transfer channel, and who is left in circulation",
        paired and bool(live),
        f"{branch}. Judged on: {live or 'nothing'}"
        + (f"; dropped as one-directional: {locked}" if locked else "")
        + ". " + "; ".join(counts_text(k) for k, _ in JUDGED)
        + ". Printed, not judged on: "
        + "; ".join(counts_text(k) for k in PRINTED)
        + ". Edges carrying all four surfaces: "
        + ", ".join(
            f"{k} {hits[k]}"
            for k in ("floor", "floor+transfer", "both+transfer")
            if k in hits
        )
        + ("" if paired else ". PAIRING FAILED, the arms do not cover the same cells"),
        undecidable=paired and not live,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--nodes", type=int, default=_A8.BASE_NODES,
        help="carrier size, resolved through A8 so the two stages cannot "
        "disagree about it. The default is the registered carrier.",
    )
    parser.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier, through A8 so the two "
        "stages cannot disagree. The transfer arms are dropped there and "
        "named, because A6 and A3 are both Network subclasses with no "
        "composition point.",
    )
    args = parser.parse_args()

    carrier = carrier_at(args.nodes, asset=args.asset)
    arms = arms_for(need_for(carrier))
    dropped = [k for k, (_f, _w, rate) in arms.items()
               if rate > 0.0 and carrier.asset]
    for k in dropped:
        del arms[k]

    print("stage A12: the coverage result under the two later mechanisms")
    print(f"  rounds={args.rounds} seed={args.seed} arms={list(arms)}")
    print(
        f"  carrier {carrier.nodes} nodes "
        f"({carrier.layer1_size}/{carrier.intermediate_size}/"
        f"{carrier.layer2_size}), edges {list(carrier.edges)}, "
        f"floor need {need_for(carrier):.4f}, "
        f"asset layer {'on' if carrier.asset else 'off'}"
    )
    if dropped:
        print(f"  arms dropped on this carrier: {dropped}")
    print()

    rows = [
        one_run(arm, f2i, e, args.rounds, args.seed, arms, carrier)
        for arm in arms for f2i in carrier.edges for e in ELASTICITIES
    ]

    hits = {
        arm: sorted({row["f2i"] for row in rows if row["arm"] == arm and row["all_four"]})
        for arm in arms
    }
    # ``fired`` is a count, not a median. A median over the grid hides a sparse
    # event: the write-off fires in ten of these forty-five cells and the median
    # destroyed is 0.0, so a reader of the median alone concludes the mechanism
    # never ran. It did.
    fired = {arm: sum(1 for row in rows
                      if row["arm"] == arm and row["written_off_total"] > 0)
             for arm in arms}
    print(f"{'arm':>24s} | {'edges carrying all four surfaces':<44s} | "
          f"{'starved':>7s} {'fired':>6s} {'med destroyed':>13s} {'gini':>7s}")
    for arm in arms:
        g = [row for row in rows if row["arm"] == arm]
        print(f"{arm:>24s} | {str(hits[arm]):<44s} | "
              f"{float(np.median([row['starved'] for row in g])):7.0f} "
              f"{fired[arm]:>4d}/{len(g):<2d} "
              f"{float(np.median([row['written_off_total'] for row in g])):13.1f} "
              f"{float(np.median([row['gini_close'] for row in g])):7.4f}")

    criteria = []
    base = base_config(1, 0.0, args.rounds, args.seed, carrier)
    differing: set[str] = set()
    for floor_spec, write_spec, _rate in arms.values():
        fs = floor_spec or SubsistenceSpec(
            need=FLOOR_MULTIPLE * base.total_resources / base.spec.size
        )
        a = dataclasses.replace(base, subsistence=fs, writeoff=write_spec)
        for f in dataclasses.fields(NetworkConfig):
            if getattr(a, f.name) != getattr(base, f.name):
                differing.add(f.name)
    criteria.append(Criterion(
        "A12-1  one structure, the two mechanism fields only",
        differing <= {"subsistence", "writeoff"},
        f"fields differing from the control across {len(arms)} arms: "
        f"{sorted(differing)}",
    ))

    conserved = sum(1 for row in rows if row["claims_conserved"])
    criteria.append(Criterion(
        "A12-2  the identity holds with destruction in it",
        conserved == len(rows),
        f"{conserved}/{len(rows)} runs, below {SFC_TOLERANCE:.0e}",
    ))

    # A8's record on **this** carrier, not on whichever one happens to be in
    # results/. Comparing an off arm at one size against a record at another
    # would be a criterion whose scope and whose object do not coincide, and
    # the answer it returned would be about the carrier rather than about the
    # two mechanisms this stage is testing.
    a8_path = RESULTS / f"a8_coverage{carrier.tag}.json"
    if a8_path.exists():
        a8 = json.loads(a8_path.read_text(encoding="utf-8"))
        a8_hits = sorted(
            {row["f2i"] for row in a8["grid_runs"] if row["all_four"]})
        criteria.append(Criterion(
            "A12-3  the both-off arm reproduces A8",
            hits["off"] == a8_hits,
            f"this stage {hits['off']} against {a8_path.name} {a8_hits}",
        ))
    else:
        criteria.append(Criterion(
            "A12-3  the both-off arm reproduces A8",
            False,
            f"this stage {hits['off']}; {a8_path.name} does not exist, so "
            f"there is no A8 reading on this carrier to compare against. "
            f"Run A8 at --nodes {carrier.nodes} first.",
            undecidable=True,
        ))

    # Reshaped 2026-08-24. The registered form read the three arms that put a
    # node below the floor **out of the graph**, and that state describes
    # nobody: with ``cut_payroll`` false such a node draws a wage every round
    # and spends nothing, so a hundred and sixty five of them end the run
    # holding 85.6 percent of every claim outstanding. Receiving and not
    # passing on is retention, which this framework assigns to the top layer,
    # so the registered arms applied a top-layer operation to the bottom and
    # the emptiness this criterion read was that operation's doing.
    #
    # The judged set is now the arms whose subsistence state has somebody in
    # it: ``drawdown`` keeps the node in the graph and spends
    # ``min(need, holdings)``, so it consumes, consumes less, and eats its
    # savings. The exit arms stay in the printed line because their emptiness
    # is a real reading about that construction, and they are named as
    # controls rather than as regimes.
    JUDGED_ARMS = ("floor drawdown", "writeoff", "drawdown+writeoff")
    CONTROL_ARMS = ("floor", "both", "floor payroll kept")
    judged_here = [a for a in JUDGED_ARMS if a in hits]
    empty = [a for a in judged_here if not hits[a]]
    criteria.append(Criterion(
        "A12-4  the coverage result survives each mechanism",
        bool(judged_here) and not empty,
        "Judged on the arms whose subsistence state has somebody in it: "
        + "; ".join(f"{a} {hits[a]}" for a in judged_here)
        + (f". Empty at {empty}" if empty else "")
        + ". Against the control with no mechanism: off "
        + str(hits.get("off"))
        + ". Printed and NOT judged on, because a node below the floor there draws"
        " a wage and spends nothing, which is retention and not subsistence: "
        + "; ".join(f"{a} {hits[a]}" for a in CONTROL_ARMS if a in hits),
        undecidable=not judged_here,
    ))

    def med_of(arm: str, key: str) -> float:
        g = [row for row in rows if row["arm"] == arm]
        return float(np.median([row[key] for row in g])) if g else float("nan")

    criteria.append(transfer_criterion(rows, hits))

    # Registered 2026-08-23, after the three switches were run for the first
    # time. A12-4 reads empty on the ``floor`` arm, and that arm carries the
    # floor with both of its booleans off. The question this raises is whether
    # the emptiness belongs to the floor or to that setting of it.
    # Renamed 2026-08-24. Its registered name said the payroll-cut variant
    # **restores** the coverage the plain floor removes, and that wording
    # takes the removal for a fact about the floor. It is not: with payroll
    # left on, a node below the floor draws a wage every round and spends
    # nothing, and a hundred and sixty five of those end the run holding 85.6
    # percent of every claim outstanding. What this criterion measures is
    # therefore which of the two booleans lets that accumulation happen, and
    # the answer is the payroll one. **The numbers are unchanged and the
    # reading is what moved.** The arm that models a household below
    # subsistence is neither of these; it is the drawdown arm, and A12-4
    # judges on that.
    floor_arms = ("floor", "floor payroll severed", "floor payroll kept",
                  "floor drawdown")
    criteria.append(Criterion(
        "A12-6  which of the exit floor's two booleans carries the "
        "construction artefact",
        bool(hits["floor payroll severed"]),
        "Cutting payroll is what stops the accumulation; the reversible "
        "boolean moves nothing. Edges carrying all four surfaces: "
        + "; ".join(f"{arm} {hits[arm]}" for arm in floor_arms if arm in hits)
        + ". Closing gini "
        + ", ".join(f"{arm} {med_of(arm, 'gini_close'):.4f}"
                    for arm in floor_arms if arm in hits)
        + f", against off {med_of('off', 'gini_close'):.4f}"
        + ". Wage funding "
        + ", ".join(f"{arm} {med_of(arm, 'wage_funding'):.4f}"
                    for arm in floor_arms if arm in hits)
        + f", against off {med_of('off', 'wage_funding'):.4f}",
    ))

    # A count rather than a median, for the reason in the comment above the
    # table. An arm that never fires passes every criterion by never running.
    wo_arms = [arm for arm, (_f, w, _r) in arms.items() if w.active]
    criteria.append(Criterion(
        "A12-7  every write-off-bearing arm fired in at least one cell",
        all(fired[arm] > 0 for arm in wo_arms),
        "; ".join(f"{arm} {fired[arm]}/{len(carrier.edges) * len(ELASTICITIES)}"
                  for arm in wo_arms),
    ))

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    n_undecidable = sum(c.undecidable for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed"
          + (f", {n_undecidable} undecidable" if n_undecidable else ""))

    RESULTS.mkdir(parents=True, exist_ok=True)
    # Same reason as A8's: a run on another carrier writes its own file
    # instead of overwriting this stage's record, because the two carry the
    # same field names over different definitions.
    path = RESULTS / f"a12_mechanisms{carrier.tag}.json"
    path.write_text(json.dumps({
        "stage": "A12", "rounds": args.rounds, "seed": args.seed,
        "floor_multiple": FLOOR_MULTIPLE,
        "floor_need": r(need_for(carrier)),
        "carrier": {
            "nodes": carrier.nodes,
            "layer1_size": carrier.layer1_size,
            "intermediate_size": carrier.intermediate_size,
            "layer2_size": carrier.layer2_size,
            "edges": list(carrier.edges),
            "rescaled": carrier.rescaled,
            "asset_layer": carrier.asset,
            "arms_dropped": list(dropped),
        },
        "writeoff": {"rate": WRITEOFF.rate, "trigger": WRITEOFF.trigger},
        "edges_carrying_all_four": {k: v for k, v in hits.items()},
        "runs": rows,
        # Closed when every criterion holds on the registered carrier. A run on
        # any other carrier stays diagnostic whatever it reads, because its
        # numbers are a second channel rather than a second setting of one.
        **(
            {}
            if not carrier.rescaled and n_pass + n_undecidable == len(criteria)
            else {
                "diagnostic_only": True,
                "diagnostic_reason": (
                    (
                        ""
                        if not carrier.rescaled
                        else (
                            (
                                ""
                                if carrier.nodes == _A8.BASE_NODES
                                else f"Carrier at {carrier.nodes} nodes rather "
                                f"than the {_A8.BASE_NODES} this stage is "
                                f"registered at; the edge grid is solved for "
                                f"equal autonomous share and the floor need is "
                                f"the resource pool over the node count, so the "
                                f"readings are comparable in shape and not in "
                                f"level. "
                            )
                            + (
                                ""
                                if not carrier.asset
                                else "A3's asset layer is on this carrier and "
                                "the registered one has no asset layer, so the "
                                "two are two channels and not two settings of "
                                "one. Reported beside the registered run, never "
                                "in place of it. "
                            )
                        )
                    )
                    + (
                        ""
                        if n_pass + n_undecidable == len(criteria)
                        else "Criteria outstanding on this run. "
                    )
                ).strip(),
            }
        ),
        "criteria": [{"name": c.name, "passed": bool(c.passed),
                      "detail": c.detail,
                      **({"undecidable": True} if c.undecidable else {})}
                     for c in criteria],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {path.relative_to(ROOT)}")
    # An undecidable criterion is not a failure: nothing was looked at, so
    # nothing failed. Unreachable on the registered carrier, where the file
    # it needs is always there.
    return 0 if n_pass + n_undecidable == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
