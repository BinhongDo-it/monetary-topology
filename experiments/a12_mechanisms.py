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

    python experiments/a12_mechanisms.py --rounds 300 --workers 8

Writes ``results/a12_mechanisms.json``. A run at any other round count or seed
writes ``<name>.offparam_s<seed>x<rounds>.json`` and marks it diagnostic, so a
smoke run cannot overwrite the registered record. ``--workers`` only spreads
the grid over processes: every run is deterministic and the rows come back in
grid order, so the record is the same at any worker count.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import A3Config, A3Model, AssetSpec
from monetary_topology.config import WageChannel
from monetary_topology.redistribution import A6Config, A6Model, FiscalSpec, run_a6
from monetary_topology.mechanisms import gini


def top_share(v: np.ndarray, k: int) -> float:
    """Share of the claim stock held by the top ``k`` nodes.

    The same rule the other stations use, so a number here is comparable with
    A2d's and A13's without a translation step. ``k`` is taken by the caller as
    ``max(1, n // 100)`` or ``max(1, n // 1000)``: at two hundred nodes the top
    one per cent is two nodes and the top tenth of a per cent is one, which is
    a floor rather than a construction and is why A14-5 prints the counts.
    """
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = float(s.sum())
    return float(s[:k].sum() / total) if total > 0 else float("nan")
from monetary_topology.network import (
    Network,
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
REGISTERED_ROUNDS = 300
REGISTERED_SEED = 0

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
    #: Not evaluated, because the rows handed in are not the registered grid.
    #: Distinct from both of the above: the object may well exist, but a
    #: verdict read off part of the grid is a verdict about that part. Added
    #: 2026-10-14: removing five rows from the record left all seven PASS.
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else "----" if self.undecidable else (
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
    clocks: bool = False,
    paths: bool = False,
) -> dict:
    """One run, one row.

    ``clocks`` (added 2026-10-14 for A15, off by default): also record the
    concentration measures at two more instants. ``*_open`` is read off
    ``holdings[0]``, which is the state after the first round's network step,
    and ``*_close`` off ``holdings[-1]``, which on the fiscal model is written
    before that round's ``_post_round`` moves cash. With the switch on, the row
    also carries ``*_init`` (the claims before round one) and ``*_post`` (the
    claims after the last ``_post_round``). Off, the row is the same as before.

    ``paths`` (added 2026-10-14 for A12's own audit, off by default): also
    record who was out of the market on every round, not only at the close.
    ``starved`` counts two different objects under the two floor modes: under
    ``exit`` the nodes that have left the graph, under ``drawdown`` the nodes
    below the floor this round, all of which are still in it. The row then
    names which (``starved_object``), carries the nodes in the graph at the
    close, how many rounds and node-rounds anyone was out, how many nodes were
    ever out, and how many times a node came back. With ``clocks`` on as well
    it carries the net-worth Gini after the last ``_post_round`` (claims plus
    units at the closing price on the asset carrier, claims elsewhere) and the
    largest per-node cash move between the recorded close and that instant.
    """
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
        model = A6Model(
            A6Config(fiscal=FiscalSpec(rate=transfer, channel="transfer"), network=cfg)
        )
    elif carrier.asset:
        model = A3Model(A3Config(asset=AssetSpec(), network=cfg))
    else:
        model = Network(cfg)
    held_init = np.asarray(model.holdings, dtype=float).copy()
    # ``run()`` is this same generator drained, so stepping it here changes
    # nothing about the run. The out-of-market set is read at the point the
    # round yields, after ``_post_round``.
    drawdown = cfg.subsistence.mode == "drawdown"
    out_by_round = np.zeros((cfg.rounds, held_init.size), dtype=bool)
    for t in model._run_steps():
        out_by_round[t] = model._below if drawdown else ~model._alive
    h = model._history
    assert h is not None
    held_post = np.asarray(model.holdings, dtype=float).copy()

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
        # Added 2026-08-25 for A15. Recorded, not judged here: this stage's
        # criteria read the four surfaces and none of them reads a top
        # share. A15 reads all three of these together and needs them on
        # the same runs rather than on a re-run of its own.
        #
        # **Scope, added the same day after A16 measured it.** These four are
        # recorded at one floor depth, because ``FLOOR_MULTIPLE`` is 0.20 and
        # this grid does not vary it, and that depth is not a neutral place to
        # read a concentration measure from. At 0.20 the nodes that leave freeze
        # holding 94 per cent of the closing stock, so all three measures move
        # together and what they mostly report is that accumulation. At 0.05 the
        # leavers hold 0.3 per cent and the same three measures separate. So
        # anything read off these fields holds at this depth and is not a
        # statement about the model: A16's floor scan is where the depth is the
        # axis. Recording them without judging them was already the right
        # handling and this is the reason for it.
        "top1_wealth": r(top_share(h.holdings[-1], max(1, h.holdings.shape[1] // 100))),
        "top10_wealth": r(top_share(h.holdings[-1], max(1, h.holdings.shape[1] // 10))),
        "top1_open": r(top_share(h.holdings[0], max(1, h.holdings.shape[1] // 100))),
        "top10_open": r(top_share(h.holdings[0], max(1, h.holdings.shape[1] // 10))),
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
    if clocks:
        k1 = max(1, held_init.size // 100)
        k10 = max(1, held_init.size // 10)
        for tag, held in (("init", held_init), ("post", held_post)):
            row["gini_%s" % tag] = r(gini(held))
            row["top1_%s" % tag] = r(top_share(held, k1))
            row["top10_%s" % tag] = r(top_share(held, k10))
    if paths:
        # Tied to the model's own count every round, so the path fields read
        # the object the history records and not a neighbour of it.
        per_round = out_by_round.sum(axis=1)
        assert np.array_equal(per_round, np.asarray(h.starved, dtype=float))
        sub = cfg.subsistence
        row.update({
            "starved_object": (
                "none" if not sub.active
                else "below_floor_in_graph" if drawdown else "out_of_graph"),
            "in_graph_close": int(model._alive.sum()),
            "out_rounds": int((per_round > 0).sum()),
            "out_node_rounds": int(per_round.sum()),
            "out_peak": int(per_round.max()),
            "ever_out": int(out_by_round.any(axis=0).sum()),
            "returns": int((out_by_round[:-1] & ~out_by_round[1:]).sum()),
        })
        if clocks:
            worth = (np.asarray(model.net_worth(), dtype=float)
                     if hasattr(model, "net_worth") else held_post)
            row["gini_net_worth_post"] = r(gini(worth))
            row["claims_moved_after_record"] = r(float(
                np.abs(held_post - np.asarray(h.holdings[-1], dtype=float)).max()))
    # A8's own definitions, imported rather than restated.
    row["surfaces"] = _A8.surfaces_present(row)
    row["all_four"] = bool(all(row["surfaces"].values()))
    return row


#: The transfer pairs grouped by what ``starved`` counts on them. Added
#: 2026-10-14. On the two exit pairs it counts nodes that have left the
#: graph; on the drawdown pair it counts nodes below the floor this round, and
#: every one of those is still in the graph, trading. A count that pools the
#: three adds two objects together: on the registered carrier the pooled
#: tally read branch A, "the transfer puts back the circulation the floor
#: removed", while the exit pairs read 21 down, 19 level, 50 up on that very
#: count and the drawdown pair, where nothing had been removed, supplied the
#: 43 downs. So each family gets its own reading and its own branch.
TRANSFER_FAMILIES = (
    ("exit", "nodes out of the graph",
     (("floor", "floor+transfer"), ("both", "both+transfer"))),
    ("drawdown", "nodes below the floor this round, every one still in the graph",
     (("floor drawdown", "drawdown+transfer"),)),
)

#: Branch sentences per family. The exit family keeps the sentences A12-5 has
#: always printed. The drawdown family cannot say "puts back the circulation
#: the floor removed", because under drawdown the floor removed nobody.
BRANCHES = {
    "exit": {
        "A": "branch A: the transfer puts back the circulation the floor removed",
        "B": "branch B: the transfer pays income out and takes circulation away "
             "with it",
        "C": "branch C: the two quantities point opposite ways, reported "
             "separately rather than merged into one verdict",
    },
    "drawdown": {
        "A": "branch A: the transfer leaves fewer nodes short of the floor; "
             "nobody here had left the graph, so this is who is short, not a "
             "return to circulation",
        "B": "branch B: the transfer leaves more nodes short of the floor, all "
             "of them still in the graph",
        "C": "branch C: the two quantities point opposite ways, reported "
             "separately rather than merged into one verdict",
    },
}

UNDECIDABLE_BRANCH = ("undecidable: every candidate quantity came back "
                      "one-directional, so the construction is answering, not "
                      "the run")


def _direction_counts(rows: list[dict], base: str, arm: str,
                      key: str) -> tuple[int, int, int]:
    """Paired cells where the transfer arm reads below, level with, above."""
    b = {(x["f2i"], x["elasticity"]): x for x in rows if x["arm"] == base}
    t = {(x["f2i"], x["elasticity"]): x for x in rows if x["arm"] == arm}
    cells = sorted(set(b) & set(t))
    return (
        sum(1 for c in cells if t[c][key] < b[c][key]),
        sum(1 for c in cells if t[c][key] == b[c][key]),
        sum(1 for c in cells if t[c][key] > b[c][key]),
    )


def transfer_reading(rows: list[dict]) -> dict:
    """A12-5's reading per state family, as data. A pure function of the rows.

    For each family whose pairs ran: the direction counts per pair and in
    total, which judged quantities the reachability check dropped as
    one-directional, which are left, and the branch. Each family is read on
    its own pairs only, so a one-directional quantity is dropped from the
    family where it is one-directional and not from the other.
    """
    out = {}
    for family, obj, pairs in TRANSFER_FAMILIES:
        present = [(b, a) for b, a in pairs if any(x["arm"] == a for x in rows)]
        if not present:
            continue
        paired = all(
            {(x["f2i"], x["elasticity"]) for x in rows if x["arm"] == b}
            == {(x["f2i"], x["elasticity"]) for x in rows if x["arm"] == a}
            and any(x["arm"] == b for x in rows)
            for b, a in present
        )
        counts = {}
        totals = {}
        for key in [k for k, _ in JUDGED] + list(PRINTED):
            per = {f"{b}->{a}": list(_direction_counts(rows, b, a, key))
                   for b, a in present}
            counts[key] = per
            totals[key] = [sum(v[i] for v in per.values()) for i in range(3)]
        locked = [k for k, _ in JUDGED
                  if totals[k][0] == 0 or totals[k][2] == 0]
        live = [k for k, _ in JUDGED if k not in locked]
        better = {
            k: ((totals[k][2] > totals[k][0]) if hib
                else (totals[k][0] > totals[k][2]))
            for k, hib in JUDGED if k in live
        }
        if not live:
            branch = UNDECIDABLE_BRANCH
        elif all(better.values()):
            branch = BRANCHES[family]["A"]
        elif not any(better.values()):
            branch = BRANCHES[family]["B"]
        else:
            branch = BRANCHES[family]["C"]
        out[family] = {
            "object": obj,
            "pairs": [f"{b}->{a}" for b, a in present],
            "paired": paired,
            "counts_down_level_up": counts,
            "totals_down_level_up": totals,
            "dropped_one_directional": locked,
            "judged_on": live,
            "branch": branch,
        }
    return out


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
    # The reachability check is the executable form of that lesson: a
    # quantity that comes back one-directional over every paired cell is locked
    # by the construction and leaves the verdict rather than deciding it. If
    # both leave, the family reads undecidable, which is a third state and
    # not a failure.
    #
    # Read per state family since 2026-10-14, see ``TRANSFER_FAMILIES``. The
    # verdict maps as follows, and the mapping is printed in the detail:
    # some family with a judged quantity left and every pair covering the same
    # cells -> PASS; families present but none with a judged quantity left ->
    # undecidable; pairs that do not cover the same cells -> FAIL.
    #
    # The pairs may not exist. On the asset carrier the transfer arms have no
    # model to run, so they are dropped before the grid, and a criterion whose
    # object is absent reads its third state rather than failing: FAIL says
    # the thing was looked at and did not hold.
    name = "A12-5  the transfer channel, and who is left in circulation"
    reading = transfer_reading(rows)
    if not reading:
        return Criterion(
            name,
            False,
            "No transfer arm ran on this carrier, so there is nothing to "
            "pair against. A6 and A3 are both Network subclasses and have "
            "no composition point, so a fiscal channel on the asset carrier "
            "has no model. This is absence of an object, not a failed "
            "reading.",
            undecidable=True,
        )
    paired = all(f["paired"] for f in reading.values())
    any_live = any(f["judged_on"] for f in reading.values())

    def counts_text(f: dict, key: str) -> str:
        return f"{key} down/level/up " + ", ".join(
            f"{p} {d}/{s}/{u}" for p, (d, s, u) in f["counts_down_level_up"][key].items())

    parts = []
    for family, f in reading.items():
        parts.append(
            f"[{family}: starved counts {f['object']}] {f['branch']}. "
            f"Judged on: {f['judged_on'] or 'nothing'}"
            + (f"; dropped as one-directional: {f['dropped_one_directional']}"
               if f["dropped_one_directional"] else "")
            + ". " + "; ".join(counts_text(f, k) for k, _ in JUDGED)
            + ". Printed, not judged on: "
            + "; ".join(counts_text(f, k) for k in PRINTED)
        )
    return Criterion(
        name,
        paired and any_live,
        "Read per state family and never pooled, because starved counts a "
        "different object in each. "
        + ". ".join(parts)
        + ". Verdict mapping: a family with a quantity left and every pair on "
        "the same cells -> PASS; none left -> undecidable; pairs on different "
        "cells -> FAIL"
        + ". Edges carrying all four surfaces: "
        + ", ".join(
            f"{k} {hits[k]}"
            for k in ("floor", "floor+transfer", "both+transfer",
                      "drawdown+transfer")
            if k in hits
        )
        + ("" if paired else ". PAIRING FAILED, the arms do not cover the same cells"),
        undecidable=paired and not any_live,
    )


#: What each row field reads, and at which instant. Added 2026-10-14: the
#: record's field names say "open", "close" and "wealth", and none of the three
#: is the object the name suggests on every arm.
DEFINITIONS = {
    "gini_open, top1_open, top10_open": (
        "Claims in holdings[0], the history row of the first round, written "
        "after that round's network step. Not the claims the model opens "
        "with; those are the *_init fields."),
    "gini_close, top1_wealth, top10_wealth": (
        "Claims in holdings[-1], the history row of the last round, written "
        "before that round's _post_round. The fiscal arms pay the transfer and "
        "the asset carrier settles in _post_round, so on those arms these "
        "precede the last cash move; on the others nothing moves after them. "
        "'wealth' here is claims (cash), not net worth."),
    "gini_init, top1_init, top10_init": (
        "Claims the model holds before round one."),
    "gini_post, top1_post, top10_post": (
        "Claims after the last _post_round, the run's final cash."),
    "gini_net_worth_post": (
        "After the last _post_round: claims plus units held at the closing "
        "price on the asset carrier, claims alone elsewhere."),
    "claims_moved_after_record": (
        "Largest per-node difference between claims after the last "
        "_post_round and holdings[-1]."),
    "starved, frozen in the history": (
        "Read against starved_object. out_of_graph (exit mode): nodes that "
        "have left the graph. below_floor_in_graph (drawdown mode): nodes "
        "below the floor this round, every one still in the graph and "
        "spending min(need, holdings). none: no floor on this arm."),
    "in_graph_close": "Nodes in the graph after the last round.",
    "out_rounds, out_node_rounds, out_peak, ever_out": (
        "Over all rounds, of the set starved counts: rounds with anyone in "
        "it, node-rounds in it, its largest size, nodes ever in it."),
    "returns": (
        "Times a node was in that set on one round and out of it on the next. "
        "Zero by construction on the absorbing exit arms."),
}


def expected_cells(arms: dict, carrier: Carrier) -> list[tuple[str, int, float]]:
    return [(a, int(f), float(e))
            for a in arms for f in carrier.edges for e in ELASTICITIES]


def coverage(rows: list[dict], arms: dict, carrier: Carrier) -> dict:
    """Whether ``rows`` are the registered grid, one row per arm and cell.

    Added 2026-10-14. Without it every criterion below reads whatever rows it
    is handed: five rows taken out of the record left all seven PASS.
    """
    want = expected_cells(arms, carrier)
    got = [(x["arm"], int(x["f2i"]), float(x["elasticity"])) for x in rows]
    missing = [list(k) for k in want if k not in set(got)]
    outside = [list(k) for k in sorted(set(got) - set(want))]
    duplicates = len(got) - len(set(got))
    return {
        "expected_runs": len(want),
        "runs": len(rows),
        "missing": missing,
        "outside_grid": outside,
        "duplicates": duplicates,
        "complete": not missing and not outside and duplicates == 0,
    }


def hits_of(rows: list[dict], arms) -> dict:
    return {arm: sorted({x["f2i"] for x in rows
                         if x["arm"] == arm and x["all_four"]})
            for arm in arms}


def fired_of(rows: list[dict], arms) -> dict:
    # ``fired`` is a count, not a median. A median over the grid hides a sparse
    # event: the write-off fires in ten of these forty-five cells and the median
    # destroyed is 0.0, so a reader of the median alone concludes the mechanism
    # never ran. It did.
    return {arm: sum(1 for x in rows
                     if x["arm"] == arm and x["written_off_total"] > 0)
            for arm in arms}


def reversible_reading(rows: list[dict]) -> dict | None:
    """The exit floor with and without its ``reversible`` boolean, cell by cell.

    Added 2026-10-14. A12-6 used to say this boolean "moves nothing", read off
    the edge sets carrying all four surfaces and the median closing Gini.
    Both stay the same while nodes come back underneath them, so the reading
    is taken on the rows: how many returns, how many cells close with a
    different number of nodes in the graph, and the largest closing-Gini gap.
    """
    a = {(x["f2i"], x["elasticity"]): x for x in rows if x["arm"] == "floor"}
    b = {(x["f2i"], x["elasticity"]): x
         for x in rows if x["arm"] == "floor payroll kept"}
    cells = sorted(set(a) & set(b))
    if not cells:
        return None
    if any("returns" not in b[c] or "in_graph_close" not in b[c] for c in cells):
        return {"cells": len(cells), "recorded": False}
    gap, worst = max((abs(b[c]["gini_close"] - a[c]["gini_close"]), c)
                     for c in cells)
    return {
        "cells": len(cells),
        "recorded": True,
        "returns": sum(b[c]["returns"] for c in cells),
        "cells_with_returns": sum(1 for c in cells if b[c]["returns"] > 0),
        "cells_closing_membership_differs": sum(
            1 for c in cells if a[c]["in_graph_close"] != b[c]["in_graph_close"]),
        "cells_all_four_differs": sum(
            1 for c in cells if a[c]["all_four"] != b[c]["all_four"]),
        "gini_close_gap_max": r(gap),
        "gini_close_gap_cell": {"f2i": worst[0], "elasticity": worst[1]},
        "in_graph_close_at_that_cell": {
            "floor": a[worst]["in_graph_close"],
            "floor payroll kept": b[worst]["in_graph_close"]},
    }


def _not_evaluated(name: str, cov: dict) -> Criterion:
    return Criterion(
        name, False,
        f"Not evaluated: the rows are not the registered grid "
        f"({cov['runs']} of {cov['expected_runs']} expected, "
        f"{len(cov['missing'])} missing, {len(cov['outside_grid'])} outside it, "
        f"{cov['duplicates']} repeated). A verdict on part of the grid is a "
        f"verdict on that part.",
        void=True,
    )


def build_criteria(rows: list[dict], arms: dict, carrier: Carrier,
                   rounds: int, seed: int, a8: dict | None,
                   a8_name: str) -> list[Criterion]:
    """The seven criteria. A pure function of the rows and the A8 record, so a
    test can hand it a damaged grid and check that the flags move."""
    criteria = []
    base = base_config(1, 0.0, rounds, seed, carrier)
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

    cov = coverage(rows, arms, carrier)
    names = (
        "A12-2  the identity holds with destruction in it",
        "A12-3  the both-off arm reproduces A8",
        "A12-4  the coverage result survives each mechanism",
        "A12-5  the transfer channel, and who is left in circulation",
        "A12-6  which of the exit floor's two booleans carries the "
        "construction artefact",
        "A12-7  every write-off-bearing arm fired in at least one cell",
    )
    if not cov["complete"]:
        return criteria + [_not_evaluated(n, cov) for n in names]

    hits = hits_of(rows, arms)
    fired = fired_of(rows, arms)

    conserved = sum(1 for x in rows if x["claims_conserved"])
    criteria.append(Criterion(
        names[0],
        conserved == len(rows),
        f"{conserved}/{len(rows)} runs, below {SFC_TOLERANCE:.0e}",
    ))

    # A8's record on **this** carrier, not on whichever one happens to be in
    # results/. Comparing an off arm at one size against a record at another
    # would be a criterion whose scope and whose object do not coincide, and
    # the answer it returned would be about the carrier rather than about the
    # two mechanisms this stage is testing.
    #
    # **What is compared, added 2026-10-14**: the set of edges carrying all
    # four surfaces, and nothing else. A8's record ran 600 rounds and this
    # stage runs 300, so the quantities under the two sets differ (a few
    # hundred of each record's shared values) while the sets agree. The detail
    # says so, so that a match on the set is not read as a match on the values.
    if a8 is not None:
        a8_hits = sorted(
            {x["f2i"] for x in a8["grid_runs"] if x["all_four"]})
        criteria.append(Criterion(
            names[1],
            hits["off"] == a8_hits,
            f"this stage {hits['off']} against {a8_name} {a8_hits}. The edge "
            f"sets are compared, not the quantities under them: {a8_name} ran "
            f"{a8.get('rounds')} rounds and this run {rounds}",
        ))
    else:
        criteria.append(Criterion(
            names[1],
            False,
            f"this stage {hits['off']}; {a8_name} does not exist, so "
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
        names[2],
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
        g = [x for x in rows if x["arm"] == arm]
        return float(np.median([x[key] for x in g])) if g else float("nan")

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
    #
    # 2026-10-14: the detail used to say "the reversible boolean moves
    # nothing". It leaves the edge sets and the median alone and moves nodes
    # and closing Ginis underneath them, so the sentence is now printed off the
    # rows (``reversible_reading``). The verdict reads the payroll arm and did
    # not change.
    floor_arms = ("floor", "floor payroll severed", "floor payroll kept",
                  "floor drawdown")
    rev = reversible_reading(rows)
    if rev is None:
        rev_text = "The reversible boolean has no pair on these rows"
    elif not rev["recorded"]:
        rev_text = ("Whether the reversible boolean moves anything underneath "
                    "the edge sets is not recorded on these rows")
    elif (rev["returns"] == 0 and rev["cells_closing_membership_differs"] == 0
          and rev["gini_close_gap_max"] == 0.0):
        rev_text = (
            f"The reversible boolean moves nothing on this carrier, cell by "
            f"cell as well as in the edge sets: no node comes back in any of "
            f"the {rev['cells']} cells, and every cell closes with the same "
            f"nodes in the graph and the same closing gini")
    else:
        cell = rev["gini_close_gap_cell"]
        at = rev["in_graph_close_at_that_cell"]
        rev_text = (
            f"The reversible boolean leaves the edge sets carrying all four "
            f"surfaces as they are ({rev['cells_all_four_differs']} of "
            f"{rev['cells']} cells differ on that flag) and is not inert under "
            f"them: {rev['returns']} returns in {rev['cells_with_returns']} "
            f"cells, {rev['cells_closing_membership_differs']} cells close with "
            f"a different number of nodes in the graph, largest closing-gini "
            f"gap {rev['gini_close_gap_max']:.6f} at f2i {cell['f2i']}, "
            f"elasticity {cell['elasticity']} (in the graph {at['floor']} "
            f"without returns, {at['floor payroll kept']} with)")
    criteria.append(Criterion(
        names[4],
        bool(hits["floor payroll severed"]),
        "Cutting payroll is what stops the accumulation. "
        + rev_text
        + ". Edges carrying all four surfaces: "
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

    # A count rather than a median, for the reason in ``fired_of``. An arm
    # that never fires passes every criterion by never running.
    wo_arms = [arm for arm, (_f, w, _r) in arms.items() if w.active]
    criteria.append(Criterion(
        names[5],
        all(fired[arm] > 0 for arm in wo_arms),
        "; ".join(f"{arm} {fired[arm]}/{len(carrier.edges) * len(ELASTICITIES)}"
                  for arm in wo_arms),
    ))
    return criteria


def exit_code(criteria: list[Criterion]) -> int:
    """Zero when every criterion passed or had no object. An undecidable
    criterion is not a failure; a void one means the grid was not there."""
    ok = all(c.passed or (c.undecidable and not c.void) for c in criteria)
    return 0 if ok else 1


def record_name(carrier: Carrier, rounds: int, seed: int) -> str:
    stem = f"a12_mechanisms{carrier.tag}"
    if rounds == REGISTERED_ROUNDS and seed == REGISTERED_SEED:
        return f"{stem}.json"
    return f"{stem}.offparam_s{seed}x{rounds}.json"


def _one(task: tuple) -> dict:
    arm, f2i, e, rounds, seed, arms, carrier = task
    return one_run(arm, f2i, e, rounds, seed, arms, carrier,
                   clocks=True, paths=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    parser.add_argument("--seed", type=int, default=REGISTERED_SEED)
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
    parser.add_argument(
        "--workers", type=int, default=1,
        help="processes to spread the grid over. The record does not depend "
        "on it.",
    )
    args = parser.parse_args(argv)

    carrier = carrier_at(args.nodes, asset=args.asset)
    arms = arms_for(need_for(carrier))
    dropped = [k for k, (_f, _w, rate) in arms.items()
               if rate > 0.0 and carrier.asset]
    for k in dropped:
        del arms[k]
    registered = (args.rounds == REGISTERED_ROUNDS
                  and args.seed == REGISTERED_SEED)

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

    tasks = [(arm, f2i, e, args.rounds, args.seed, arms, carrier)
             for arm, f2i, e in expected_cells(arms, carrier)]
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            rows = list(pool.map(_one, tasks, chunksize=4))
    else:
        rows = [_one(t) for t in tasks]

    hits = hits_of(rows, arms)
    fired = fired_of(rows, arms)
    print(f"{'arm':>24s} | {'edges carrying all four surfaces':<44s} | "
          f"{'starved':>7s} {'fired':>6s} {'med destroyed':>13s} {'gini':>7s}")
    for arm in arms:
        g = [x for x in rows if x["arm"] == arm]
        print(f"{arm:>24s} | {str(hits[arm]):<44s} | "
              f"{float(np.median([x['starved'] for x in g])):7.0f} "
              f"{fired[arm]:>4d}/{len(g):<2d} "
              f"{float(np.median([x['written_off_total'] for x in g])):13.1f} "
              f"{float(np.median([x['gini_close'] for x in g])):7.4f}")

    a8_path = RESULTS / f"a8_coverage{carrier.tag}.json"
    a8 = (json.loads(a8_path.read_text(encoding="utf-8"))
          if a8_path.exists() else None)
    criteria = build_criteria(rows, arms, carrier, args.rounds, args.seed,
                              a8, a8_path.name)
    cov = coverage(rows, arms, carrier)

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    n_pass = sum(c.passed for c in criteria)
    n_undecidable = sum(c.undecidable and not c.void for c in criteria)
    n_void = sum(c.void for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed"
          + (f", {n_undecidable} undecidable" if n_undecidable else "")
          + (f", {n_void} not evaluated" if n_void else ""))
    code = exit_code(criteria)

    reasons = []
    if carrier.rescaled and carrier.nodes != _A8.BASE_NODES:
        reasons.append(
            f"Carrier at {carrier.nodes} nodes rather "
            f"than the {_A8.BASE_NODES} this stage is "
            f"registered at; the edge grid is solved for "
            f"equal autonomous share and the floor need is "
            f"the resource pool over the node count, so the "
            f"readings are comparable in shape and not in "
            f"level.")
    if carrier.asset:
        reasons.append(
            "A3's asset layer is on this carrier and "
            "the registered one has no asset layer, so the "
            "two are two channels and not two settings of "
            "one. Reported beside the registered run, never "
            "in place of it.")
    if not registered:
        reasons.append(
            f"Run at {args.rounds} rounds and seed {args.seed}; the registered "
            f"run is {REGISTERED_ROUNDS} rounds at seed {REGISTERED_SEED}.")
    if not cov["complete"]:
        reasons.append("The rows are not the registered grid.")
    if code != 0:
        reasons.append("Criteria outstanding on this run.")

    RESULTS.mkdir(parents=True, exist_ok=True)
    # Same reason as A8's: a run on another carrier writes its own file
    # instead of overwriting this stage's record, because the two carry the
    # same field names over different definitions.
    path = RESULTS / record_name(carrier, args.rounds, args.seed)
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
        "coverage": cov,
        "definitions": DEFINITIONS,
        "transfer_by_state": transfer_reading(rows),
        "reversible_switch": reversible_reading(rows),
        "runs": rows,
        # Closed when every criterion holds on the registered carrier at the
        # registered rounds and seed. Anything else stays diagnostic whatever
        # it reads, because its numbers are a second channel or a second
        # setting rather than the registered one.
        **(
            {}
            if not reasons
            else {"diagnostic_only": True,
                  "diagnostic_reason": " ".join(reasons)}
        ),
        "criteria": [{"name": c.name, "passed": bool(c.passed),
                      "detail": c.detail,
                      **({"undecidable": True} if c.undecidable else {}),
                      **({"void": True} if c.void else {})}
                     for c in criteria],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {path.relative_to(ROOT)}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
