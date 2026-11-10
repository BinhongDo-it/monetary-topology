"""A11: the subsistence floor, and whether position decides who starves.

Volume One section 8 draws the line this stage is built to test: **MPC is a
property of an agent; this framework talks about the edges of the graph. An
agent with a high marginal propensity and no in-edge starves anyway.** That is
falsifiable here, because the repository already carries the arm that erases the
topology while leaving every configuration field alone: ``uniform_access``
puts every node on a complete graph and, with the layers gone, collapses what
the model assigns by layer, who pays and receives payroll, which spending
propensity a node draws, the routing mask and the opening split, holding the
aggregate propensity and the claim stock where they were. If starvation still
lands on the same set of nodes there, the claim does not hold on this carrier.
``--arms`` moves the adjacency and the propensities one at a time and prints
what each does.

The floor itself is derived rather than transcribed; the derivation is in
``SubsistenceSpec``. Leaving is absorbing and it destroys nothing: a node that
drops out freezes, and the claim total is untouched.

Each record carries the rows, a ``coverage`` block that checks the rows are the
registered grid, a ``structure`` block that names what the one switch between
the two graphs collapses, a ``path_reading`` block, and ``definitions``, which
says what each field counts under each exit rule and which sampling point it is
read at. The asset carrier's sampling point and the three accounts it can be
read on are described in ``monetary_topology.asset.carrier_model``.

Usage::

    python experiments/a11_subsistence.py
    python experiments/a11_subsistence.py --rounds 300 --seeds 5
    python experiments/a11_subsistence.py --drawdown
    python experiments/a11_subsistence.py --asset
    python experiments/a11_subsistence.py --arms

Writes ``results/a11_subsistence.json`` (``_drawdown``, ``_asset``). ``--arms``
writes ``results/a11_subsistence_arms.json``, printed and not scored. The record
names are reserved for the registered 300 rounds and 5 seeds; any other length
or seed count writes ``<name>.offparam_<seeds>x<rounds>.json`` and marks it
diagnostic. Exits non-zero if any criterion fails or the rows are not the
registered grid.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.config import LAYER_1, LAYER_2, SpendRule
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

#: The registered length and seed count. Only these two write the record names.
REGISTERED_ROUNDS = 300
REGISTERED_SEEDS = 5

#: Multiples of the resource pool per node. Both the pool and the node count are
#: existing construction quantities, so the scale introduces no new number. The
#: multiples are spacing and carry no verdict.
NEED_MULTIPLES = (0.05, 0.20, 0.50, 1.00)
GRACES = (1, 5)
GRAPHS = ("stratified", "complete")

#: Fields the path is read from. A row without them is a row whose path was
#: not recorded, which is a different statement from a path with nothing in it.
PATH_FIELDS = ("below_floor_peak", "round_gap_max")

DEFINITIONS = {
    "starved": (
        "Under `exit`: nodes out of the market at the close, a membership "
        "state; in the registered corner nobody comes back. Under `drawdown` "
        "nobody leaves and all nodes stay in the graph and keep trading: it "
        "counts nodes below the floor in the closing round, a state re-read "
        "every round."
    ),
    "below_floor_close": "The same count as `starved`, read the same way under each rule.",
    "below_floor_peak": (
        "The largest per-round count of that state over the run, from the "
        "model's own per-round column."
    ),
    "below_rounds": (
        "Rounds in which at least one node is out (`exit`) or below the floor "
        "(`drawdown`)."
    ),
    "below_node_rounds_financial, below_node_rounds_production": (
        "Node-rounds spent out or below the floor, in each of the two sets."
    ),
    "ever_below_financial, ever_below_production": (
        "Nodes out or below the floor in at least one round, in each set."
    ),
    "returns": (
        "Node-round transitions from out or below the floor back into the "
        "market or above it."
    ),
    "round_gap_max": (
        "The largest per-round absolute difference between the production "
        "set's rate and the financial set's rate."
    ),
    "path_rate_financial, path_rate_production": (
        "Node-rounds out or below the floor over nodes times rounds."
    ),
    "frozen_holdings": (
        "Claims settled held at the close by the nodes counted in `starved`. "
        "Under `drawdown` those nodes are still trading and this is what the "
        "nodes below the floor hold."
    ),
    "frozen_share_close": (
        "`frozen_holdings` over the claim total in the last history row, so "
        "claims settled over claims recorded. Under `drawdown` it is the "
        "share held below the floor."
    ),
    "frozen_share_claims_recorded, frozen_share_claims_settled": (
        "The same share with numerator and denominator on one account."
    ),
    "gini_close_trading": (
        "The Gini of the last history row over the nodes not counted in "
        "`starved`. Under `drawdown` every node is still trading and this is "
        "the Gini over the nodes above the floor at the close."
    ),
    "accrued_after_leaving": (
        "Under `exit`: over the nodes out at the close, holdings in the last "
        "history row less holdings in the history row of the round each last "
        "left, summed. On the plain carrier all of it is payroll, since a "
        "departed node neither spends nor trades; on the asset carrier it "
        "also carries each round's asset settlement. Null under `drawdown`, "
        "where nobody leaves."
    ),
    "gini_close_less_accrual": (
        "Under `exit`: the Gini of the last history row with each node out at "
        "the close set back to what it held in the round it last left. Null "
        "under `drawdown`."
    ),
    "claims_recorded": (
        "The last history row, written before that round's asset settlement, "
        "units held not included. Read by `gini_close`, `gini_close_trading`, "
        "`mr_close`, `mara_close`, `support_ratio`, `claims_conserved`, "
        "`frozen_share_claims_recorded` and the denominator of "
        "`frozen_share_close`."
    ),
    "claims_settled": (
        "The model's claims after the last round's asset settlement. Read by "
        "`gini_claims_settled`, `frozen_holdings`, the numerator of "
        "`frozen_share_close` and `frozen_share_claims_settled`."
    ),
    "net_worth": (
        "Claims settled plus units held at the closing price. Read by "
        "`gini_net_worth`."
    ),
    "claims_moved_after_record": (
        "The largest per-node difference between claims settled and claims "
        "recorded. On the plain carrier there is no settlement step and no "
        "units, the three accounts are one vector and this is 0.0."
    ),
    "coverage": (
        "Whether the rows are the registered grid: both graphs, the floor off "
        "and every floor and grace, each at every seed, once. When they are "
        "not, A11-2 to A11-4 are not evaluated."
    ),
    "structure": (
        "Configuration fields each floor arm differs in from its graph's own "
        "control, the fields the two controls differ in, and per seed what the "
        "model builds on each graph before the first round, on this record's "
        "carrier."
    ),
    "path_reading": (
        "Printed and not scored. The criteria read the close; this reads the "
        "path on the same rows."
    ),
}


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


def _floor(base: NetworkConfig, need_mult: float, grace: int, mode: str,
           sub_kw: dict | None) -> SubsistenceSpec:
    scale = base.total_resources / base.spec.size
    if need_mult > 0:
        return SubsistenceSpec(need=need_mult * scale, grace=grace, mode=mode,
                               **(sub_kw or {}))
    return SubsistenceSpec()


def _last_left(out: np.ndarray) -> np.ndarray:
    """Per node, the round it last moved from in to out; -1 if it never did."""
    rounds = out.shape[0]
    entered = out.copy()
    entered[1:] &= ~out[:-1]
    idx = np.where(entered, np.arange(rounds)[:, None], -1)
    return idx.max(axis=0)


def _run(need_mult: float, grace: int, seed: int, rounds: int, uniform: bool,
         asset: bool, mode: str, base: NetworkConfig | None,
         sub_kw: dict | None, opening: np.ndarray | None):
    """One run, returning the row, the model and the per-round out-of-market masks."""
    if base is None:
        base = base_config(seed, rounds, uniform)
    assert base.seed == seed and base.rounds == rounds
    n = base.spec.size
    spec = _floor(base, need_mult, grace, mode, sub_kw)
    cfg = dataclasses.replace(base, subsistence=spec)
    net = carrier_model(cfg, asset=asset)
    if opening is not None:
        opening = np.asarray(opening, dtype=float)
        assert abs(float(opening.sum()) - float(net.holdings.sum())) < SFC_TOLERANCE
        net.holdings[:] = opening

    # The out-of-market set every round, read at the point the round loop
    # yields, which is after the round's books close. `run()` is this same loop
    # drained, so nothing about the run changes.
    out_by_round = np.zeros((cfg.rounds, n), dtype=bool)
    for t in net._run_steps():
        out_by_round[t] = net._below if spec.mode == "drawdown" else ~net._alive
    h = net._history
    assert h is not None
    # Tied to the model's own per-round count, every round, so the path fields
    # read the same object the history records.
    assert np.array_equal(out_by_round.sum(axis=1), np.asarray(h.starved, dtype=float))

    # The set that is out of the market, read from whichever object this exit
    # rule populates. `exit` moves a membership flag and `drawdown` moves none,
    # so reading `_alive` under `drawdown` returns the empty set for every arm
    # and every rate comes back nan. That is not a reading, it is the criterion
    # looking at an object the arm never touches. `network.py` already carries
    # this same expression where it records the per-round count.
    dead = net._below if spec.mode == "drawdown" else ~net._alive
    assert np.array_equal(dead, out_by_round[-1])
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

    row = {
        "need_multiple": need_mult,
        "grace": grace,
        "seed": seed,
        "graph": "complete" if uniform else "stratified",
        "need": r(spec.need),
        "starved": int(dead.sum()),
        "below_floor_close": int(dead.sum()),
        "below_floor_peak": int(np.asarray(h.starved, dtype=float).max()),
        "starved_financial": int(dead[fin].sum()),
        "starved_production": int(dead[prod].sum()),
        "financial_nodes": int(fin.size),
        "production_nodes": int(prod.size),
        "starved_rate_financial": r(dead[fin].mean()),
        "starved_rate_production": r(dead[prod].mean()),
        "frozen_holdings": r(float(net.holdings[dead].sum())),
        # **The decomposition this stage said it needed and could not do.**
        # Its own text records that the closing Gini falls as the floor rises
        # and that the fall is not the economy levelling: under `exit` with
        # `cut_payroll` false a node that has left goes on drawing a wage and
        # never spends, so the set that left accumulates, and a large pile in
        # the hands of the many reads as a *better* Gini. How much of the fall
        # is that rather than the exit was left open.
        #
        # These two separate it, and both come off state the run already has:
        # the share of every claim sitting with nodes that have left, and the
        # Gini computed over the nodes still in circulation. **A Gini read on
        # the traders only cannot be moved by the frozen pile at all**, so the
        # gap between the two columns is the artefact and what is left is the
        # exit.
        "frozen_share_close": (
            r(float(net.holdings[dead].sum() / m[-1])) if m[-1] > 0 else 0.0),
        "gini_close_trading": (
            r(gini(h.holdings[-1][~dead])) if (~dead).any() else 0.0),
        "mr_close": r(h.total_ratio[-1]),
        "mara_close": r(float(np.asarray(h.active_ratio, dtype=float)[-TAIL:].mean())),
        "gini_close": r(gini(h.holdings[-1])),
        "support_ratio": r(support[-TAIL:].mean() / support[0]),
        "claims_conserved": bool(gap < SFC_TOLERANCE),
    }

    # The path, beside the close. The criteria read the close; these read every
    # round of the same run.
    per_round = out_by_round.sum(axis=1)
    gap_by_round = np.abs(out_by_round[:, prod].mean(axis=1)
                          - out_by_round[:, fin].mean(axis=1))
    row.update({
        "below_rounds": int((per_round > 0).sum()),
        "below_node_rounds_financial": int(out_by_round[:, fin].sum()),
        "below_node_rounds_production": int(out_by_round[:, prod].sum()),
        "ever_below_financial": int(out_by_round[:, fin].any(axis=0).sum()),
        "ever_below_production": int(out_by_round[:, prod].any(axis=0).sum()),
        "returns": int((out_by_round[:-1] & ~out_by_round[1:]).sum()),
        "round_gap_max": r(gap_by_round.max()),
        "path_rate_financial": r(out_by_round[:, fin].mean()),
        "path_rate_production": r(out_by_round[:, prod].mean()),
    })

    # What reached the departed after they left, read inside this run. Under
    # `drawdown` nobody leaves, so the two have no object and are null.
    held = np.asarray(h.holdings, dtype=float)
    if spec.mode == "drawdown":
        accrued, less_accrual = None, None
    else:
        left = _last_left(out_by_round)
        idx = np.flatnonzero(dead)
        at_leaving = held[left[idx], idx] if idx.size else np.zeros(0)
        set_back = held[-1].copy()
        set_back[idx] = at_leaving
        accrued = r(float((held[-1][idx] - at_leaving).sum()))
        less_accrual = r(gini(set_back))
    row.update({
        "accrued_after_leaving": accrued,
        "gini_close_less_accrual": less_accrual,
    })

    # The three accounts at the close. The history row is written before the
    # round's settlement step; the asset carrier settles there and the plain
    # carrier does nothing, so on the plain carrier these repeat `gini_close`.
    settled = np.asarray(net.holdings, dtype=float)
    worth = (np.asarray(net.net_worth(), dtype=float) if hasattr(net, "net_worth")
             else settled)
    recorded = held[-1]
    row.update({
        "gini_claims_settled": r(gini(settled)),
        "gini_net_worth": r(gini(worth)),
        "claims_moved_after_record": r(float(np.abs(settled - recorded).max())),
        "frozen_share_claims_recorded": (
            r(float(recorded[dead].sum() / recorded.sum())) if recorded.sum() > 0 else 0.0),
        "frozen_share_claims_settled": (
            r(float(settled[dead].sum() / settled.sum())) if settled.sum() > 0 else 0.0),
    })
    return row, net, out_by_round


def one_run(need_mult: float, grace: int, seed: int, rounds: int,
            uniform: bool, asset: bool = False, mode: str = "exit",
            base: NetworkConfig | None = None, sub_kw: dict | None = None,
            opening: np.ndarray | None = None) -> dict:
    """One run's row. The last three are for the printed arms: a configuration
    built elsewhere, extra ``SubsistenceSpec`` fields, and an opening vector put
    in place of the one the model builds. All default to the registered run."""
    row, _, _ = _run(need_mult, grace, seed, rounds, uniform, asset, mode,
                     base, sub_kw, opening)
    return row


def expected_cells() -> list[tuple[float, int]]:
    return [(0.0, 1)] + [(m, g) for m in NEED_MULTIPLES for g in GRACES]


def coverage(rows: list[dict], seeds: int) -> dict:
    """Whether ``rows`` are the registered grid at ``seeds`` seeds, and if not,
    what is missing, repeated or outside it."""
    want = {(graph, m, g, s) for graph in GRAPHS
            for m, g in expected_cells() for s in range(seeds)}
    got = [(row["graph"], row["need_multiple"], row["grace"], row["seed"]) for row in rows]
    missing = sorted(want - set(got))
    outside = sorted(set(got) - want)
    duplicates = len(got) - len(set(got))
    by_key = {(row["graph"], row["need_multiple"], row["grace"], row["seed"]): row
              for row in rows}
    lonely = sum(
        1 for (graph, m, g, s), row in by_key.items()
        if graph == "complete" and row["starved"] > 0
        and by_key.get(("stratified", m, g, s), {"starved": 0})["starved"] == 0
    )
    return {
        "seeds_expected": seeds,
        "registered_seeds": REGISTERED_SEEDS,
        "expected_runs": len(want),
        "runs": len(rows),
        "missing": [list(k) for k in missing],
        "outside_grid": [list(k) for k in outside],
        "duplicates": duplicates,
        "stratified_runs": sum(k[0] == "stratified" for k in got),
        "complete_runs": sum(k[0] == "complete" for k in got),
        "complete_firing_without_firing_twin": lonely,
        "complete": not missing and not outside and duplicates == 0,
    }


def evaluate(rows: list[dict], shared: tuple[bool, str], seeds: int) -> list[Criterion]:
    out = [Criterion("A11-1  one structure, the subsistence field only", shared[0], shared[1])]

    cov = coverage(rows, seeds)
    if not cov["complete"]:
        why = (f"not evaluated: the rows are not the registered grid "
               f"({cov['runs']} of {cov['expected_runs']} runs, "
               f"{len(cov['missing'])} missing, {cov['duplicates']} duplicated, "
               f"{len(cov['outside_grid'])} outside the grid)")
        for name in ("A11-2  leaving destroys nothing",
                     "A11-3  on the stratified graph starvation lands on the production side",
                     "A11-4  erasing the topology closes the gap"):
            out.append(Criterion(name, False, why, void=True))
        return out

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
    # topology should close it. The two graphs share every configuration field
    # but ``spec.uniform_access``; what that switch collapses is in the record's
    # ``structure`` block, and ``--arms`` moves the adjacency on its own.
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
    # Two branches, because "narrower" cannot express the case where the
    # complete graph has nobody below the floor at the close. Under the
    # registered rule that happens at four of the five settings and at the
    # fifth all two hundred leave. Under `drawdown` the same four settings never
    # put anybody below the floor at any round, and at the fifth the whole
    # population crosses and comes back together, so the close reads zero or
    # two hundred according to the phase the last round lands on. Either way
    # the two sets are below at the same rate in every round, and the rows carry
    # that (`below_floor_peak`, `below_rounds`, `round_gap_max`).
    strat_gap = (med(strat, "starved_rate_production")
                 - med(strat, "starved_rate_financial")) if strat else float("nan")
    if not comp:
        out.append(
            Criterion(
                "A11-4  erasing the topology closes the gap",
                bool(strat),
                f"at the close the complete graph has nobody below the floor at "
                f"any floor on this grid, so there is no closing gap there to "
                f"narrow. {path_sentence(rows)}. On the stratified graph the same "
                f"parameters put {len(strat)} runs below the floor at the close "
                f"with a median gap of {strat_gap:+.3f}. Read: a pass here is a "
                f"control with its rows present and no gap in them, not an "
                f"absence of data",
            )
        )
    else:
        out.append(
            Criterion(
                "A11-4  erasing the topology closes the gap",
                bool(paired) and len(closed) == len(paired),
                f"paired by seed, floor and grace: the gap between the two sets' "
                f"starvation rates is narrower on the complete graph in "
                f"{len(closed)}/{len(paired)} pairs. Median gap "
                f"{med(comp, 'starved_rate_production') - med(comp, 'starved_rate_financial'):+.3f} "
                f"complete against {strat_gap:+.3f} stratified. The complete graph "
                f"fires on {len(comp)} of the runs on this grid; where it fires on "
                f"none the reading is the other branch of this criterion",
            )
        )
    return out


def path_sentence(rows: list[dict]) -> str:
    """What the complete graph's path says, computed from the rows.

    Each clause stands on the field it reads: a row without the path fields is
    reported as not recorded, never as a zero."""
    comp_all = [row for row in rows if row["graph"] == "complete"]
    if not comp_all or any(any(k not in row for k in PATH_FIELDS) for row in comp_all):
        return "The path is not recorded on these rows"
    crossed = [row for row in comp_all if row["below_floor_peak"] > 0]
    peak = max((row["below_floor_peak"] for row in crossed), default=0)
    gap = max(row["round_gap_max"] for row in comp_all)
    text = (f"{len(crossed)} of its {len(comp_all)} runs put nodes below the floor "
            f"at some round, {peak} at the peak, and the largest gap between the "
            f"two sets' rates in any round of any of its runs is {gap:.3f}")
    if gap == 0.0 and crossed:
        text += (": when it crosses, it crosses whole. Erasing the topology removes "
                 "the question of who rather than narrowing a gap, which is this "
                 "criterion's claim in its strongest form")
    elif gap == 0.0:
        text += (": nobody is below the floor in any round. Erasing the topology "
                 "removes the question of who rather than narrowing a gap, which "
                 "is this criterion's claim in its strongest form")
    return text


def path_reading(rows: list[dict]) -> dict:
    """The criteria read the close; this reads the path on the same rows."""
    strat = {(row["need_multiple"], row["grace"], row["seed"]): row
             for row in rows if row["graph"] == "stratified"}
    narrower = equal = wider = 0
    below = {}
    for row in rows:
        if row["graph"] != "complete" or row["need_multiple"] == 0:
            continue
        key = (row["need_multiple"], row["grace"], row["seed"])
        twin = strat.get(key)
        if twin is None:
            continue
        c = abs(row["path_rate_production"] - row["path_rate_financial"])
        s = abs(twin["path_rate_production"] - twin["path_rate_financial"])
        narrower += c < s
        equal += c == s
        wider += c > s
        if row["below_rounds"] > 0:
            below.setdefault(f"{row['need_multiple']:g}/g{row['grace']}", []).append(
                row["below_rounds"])
    comp = [row for row in rows if row["graph"] == "complete"]
    return {
        "path_gap_against_stratified": {
            "pairs": narrower + equal + wider, "narrower": int(narrower),
            "equal": int(equal), "wider": int(wider)},
        "complete_round_gap_max": r(max((row["round_gap_max"] for row in comp), default=0.0)),
        "complete_runs_with_a_round_below": sum(row["below_rounds"] > 0 for row in comp),
        "complete_rounds_below_by_cell": below,
    }


def _config_diff(a, b, cls) -> list[str]:
    return sorted(f.name for f in dataclasses.fields(cls)
                  if getattr(a, f.name) != getattr(b, f.name))


def judge_structure(within: dict, between_config: list[str],
                    between_spec: list[str]) -> bool:
    """One structure on each graph, and one switch between the two graphs."""
    return (set(within) == set(GRAPHS)
            and all(set(v) <= {"subsistence"} for v in within.values())
            and between_config == ["spec"]
            and between_spec == ["uniform_access"])


def structure_check(seed: int, rounds: int, mode: str = "exit",
                    controls: dict | None = None) -> tuple[bool, str, dict]:
    """Every floor arm against its own graph's control, and the two controls
    against each other. ``controls`` defaults to the registered pair."""
    if controls is None:
        controls = {g: base_config(seed, rounds, g == "complete") for g in GRAPHS}
    within: dict[str, list[str]] = {}
    for graph, base in controls.items():
        differing: set[str] = set()
        for mult in NEED_MULTIPLES:
            for grace in GRACES:
                a = dataclasses.replace(base, subsistence=_floor(base, mult, grace, mode, None))
                differing |= set(_config_diff(a, base, NetworkConfig))
        within[graph] = sorted(differing)
    a, b = controls["stratified"], controls["complete"]
    between_config = _config_diff(a, b, NetworkConfig)
    between_spec = _config_diff(a.spec, b.spec, NetworkSpec)
    union = sorted(set().union(*within.values()))
    flag = judge_structure(within, between_config, between_spec)
    return flag, f"fields differing from the control across all arms: {union}", {
        "within_graph": within,
        "between_graphs_config": between_config,
        "between_graphs_spec": between_spec,
    }


def structure_is_shared(seed: int, rounds: int, mode: str = "exit") -> tuple[bool, str]:
    flag, detail, _ = structure_check(seed, rounds, mode)
    return flag, detail


def _values(x: np.ndarray) -> list[float]:
    return sorted({r(v) for v in np.asarray(x, dtype=float)})


def primitives(net: Network, cfg: NetworkConfig) -> dict:
    """What the model has built before the first round, read off the model."""
    fin = cfg.spec.financial_nodes
    prod = cfg.spec.household_nodes
    adj = np.asarray(net.adjacency) > 0
    route = np.asarray(net._route) > 0
    hold = np.asarray(net.holdings, dtype=float)
    return {
        "edges_initial": int(adj.sum()),
        "routes_financial_to_production_initial": int(route[np.ix_(fin, prod)].sum()),
        "wage_payers_initial": int(len(net._wage_payers)),
        "wage_receivers_initial": int(len(net._wage_receivers)),
        "propensity_low_initial": {"financial": _values(net._p_low[fin]),
                                   "production": _values(net._p_low[prod])},
        "propensity_high_initial": {"financial": _values(net._p_high[fin]),
                                    "production": _values(net._p_high[prod])},
        "holdings_initial_min": r(hold.min()),
        "holdings_initial_max": r(hold.max()),
        "holdings_initial_financial_share": r(hold[fin].sum() / hold.sum()),
    }


def structure_block(seeds: int, rounds: int, mode: str, asset: bool) -> dict:
    """The structure check, plus what the switch collapses, built on the
    carrier this record runs on. Construction only."""
    _, _, diffs = structure_check(0, rounds, mode)
    per_seed = []
    for seed in range(seeds):
        entry = {"seed": seed}
        for graph in GRAPHS:
            cfg = base_config(seed, rounds, graph == "complete")
            entry[graph] = primitives(carrier_model(cfg, asset=asset), cfg)
        per_seed.append(entry)
    return {"carrier": "asset" if asset else "plain", **diffs,
            "collapsed_with_the_adjacency": per_seed}


def exit_code(criteria: list[Criterion], cov: dict) -> int:
    live = [c for c in criteria if not c.void]
    ok = all(c.passed for c in live) and cov["complete"]
    return 0 if ok else 1


def record_name(asset: bool, drawdown: bool, arms: bool, rounds: int, seeds: int) -> str:
    if arms:
        stem = "a11_subsistence_arms"
    elif not (asset or drawdown):
        stem = "a11_subsistence"
    elif asset and not drawdown:
        stem = "a11_subsistence_asset"
    elif not asset:
        stem = "a11_subsistence_drawdown"
    else:
        stem = "a11_subsistence_drawdown_asset"
    if rounds == REGISTERED_ROUNDS and seeds == REGISTERED_SEEDS:
        return f"{stem}.json"
    return f"{stem}.offparam_{seeds}x{rounds}.json"


# ---------------------------------------------------------------------------
# --arms: one switch at a time, printed and not scored
# ---------------------------------------------------------------------------

#: What each printed arm differs from the stratified arm in.
ARM_NOTES = {
    "adjacency_complete": (
        "the adjacency only: `shortcut_rate = 1`, A7's s = 1 endpoint. The "
        "payroll incidence, routing rule, propensities and opening rule stay "
        "stratified and run on the complete adjacency"
    ),
    "adjacency_complete_opening_held": (
        "the adjacency, with the stratified arm's opening vector put back node "
        "for node after construction; same total"
    ),
    "propensity_flat": (
        "the propensities only: every node gets the one claim-weighted pair "
        "`uniform_access` assigns, on the stratified edges"
    ),
    "uniform_access_same_marginal": (
        "`uniform_access` with the stratified opening vector permuted in place "
        "of the flat opening"
    ),
}
ARMS = tuple(ARM_NOTES)

#: The corners of the exit rule, on the stratified graph.
CORNERS = {
    "registered": {},
    "cut_payroll": {"cut_payroll": True},
    "reversible": {"reversible": True},
    "cut_payroll_reversible": {"cut_payroll": True, "reversible": True},
}


def flat_spend(cfg: NetworkConfig) -> SpendRule:
    """The one propensity pair ``uniform_access`` gives every node."""
    lo = np.asarray(cfg.spend.low, dtype=float)
    hi = np.asarray(cfg.spend.high, dtype=float)
    w1 = float(cfg.layer1_initial_share)
    low = w1 * lo[list(LAYER_1)].mean() + (1.0 - w1) * lo[list(LAYER_2)].mean()
    high = w1 * hi[list(LAYER_1)].mean() + (1.0 - w1) * hi[list(LAYER_2)].mean()
    return SpendRule(low=(float(low),) * len(lo), high=(float(high),) * len(hi))


def arm_config(arm: str, seed: int, rounds: int) -> NetworkConfig:
    """Built directly rather than through ``NetworkSpec.replace``."""
    if arm == "stratified":
        return NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds)
    if arm in ("adjacency_complete", "adjacency_complete_opening_held"):
        return NetworkConfig(spec=NetworkSpec(seed=seed, shortcut_rate=1.0),
                             seed=seed, rounds=rounds)
    if arm == "propensity_flat":
        return NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds,
                             spend=flat_spend(NetworkConfig()))
    if arm == "uniform_access_same_marginal":
        return NetworkConfig(
            spec=NetworkSpec(seed=seed, uniform_access=True,
                             uniform_opening="same_marginal"),
            seed=seed, rounds=rounds)
    raise ValueError(f"unknown arm: {arm}")


_OPENINGS: dict = {}


def arm_opening(arm: str, seed: int, rounds: int) -> np.ndarray | None:
    """The stratified arm's opening vector, for the arm that holds it."""
    if arm != "adjacency_complete_opening_held":
        return None
    if (seed, rounds) not in _OPENINGS:
        cfg = arm_config("stratified", seed, rounds)
        _OPENINGS[(seed, rounds)] = np.asarray(
            carrier_model(cfg, asset=False).holdings, dtype=float).copy()
    return _OPENINGS[(seed, rounds)].copy()


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    sx = x[order]
    ranks = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks


def rank_correlation(a: np.ndarray, b: np.ndarray) -> float | None:
    ra, rb = _ranks(np.asarray(a, float)), _ranks(np.asarray(b, float))
    if ra.std() == 0 or rb.std() == 0:
        return None
    return r(float(np.corrcoef(ra, rb)[0, 1]))


def _jaccard(a, b) -> float:
    a, b = {int(x) for x in a}, {int(x) for x in b}
    return r(len(a & b) / len(a | b)) if a | b else 1.0


class Runner:
    """Each (arm, rule, floor, grace, seed, corner) run once per invocation, so
    every block reads the same rows."""

    def __init__(self, rounds: int):
        self.rounds = rounds
        self.cache: dict = {}

    def get(self, arm: str, mode: str, mult: float, grace: int, seed: int,
            corner: str = "registered") -> dict:
        sub_kw = CORNERS[corner] if mult > 0 else {}
        key = (arm, mode, mult, grace, seed, corner if mult > 0 else "registered")
        if key in self.cache:
            return self.cache[key]
        base = arm_config(arm, seed, self.rounds)
        row, net, out = _run(mult, grace, seed, self.rounds, False, False, mode,
                             base, sub_kw, arm_opening(arm, seed, self.rounds))
        row["graph"] = arm
        h = net._history
        held = np.asarray(h.holdings, dtype=float)
        recv = np.zeros(base.spec.size, dtype=bool)
        recv[np.asarray(net._wage_receivers, dtype=int)] = True
        stay = out[:-1] & out[1:]
        step = np.diff(held, axis=0)
        on_recv = step[stay & recv[None, :]]
        on_other = step[stay & ~recv[None, :]]
        digest = hashlib.sha256()
        digest.update(np.ascontiguousarray(held).tobytes())
        digest.update(np.ascontiguousarray(out).tobytes())
        extra = {
            "close_out": np.flatnonzero(out[-1]),
            "receivers": np.flatnonzero(recv),
            "arrival_receivers": ([r(on_recv.min()), r(on_recv.max())]
                                  if on_recv.size else None),
            "arrival_non_receivers": ([r(on_other.min()), r(on_other.max())]
                                      if on_other.size else None),
            "receivers_ever_out": int((out.any(axis=0) & recv).sum()),
            "issued_total": float(np.asarray(h.issuance, dtype=float).sum()),
            "digest": digest.hexdigest(),
        }
        self.cache[key] = {"row": row, "extra": extra}
        return self.cache[key]


def _cells():
    return [(m, g) for m in NEED_MULTIPLES for g in GRACES]


def _paired_sign_summary(xs: list[float]) -> dict:
    a = np.asarray(xs, dtype=float)
    return {"mean": r(a.mean()), "sd": r(a.std(ddof=1)) if a.size > 1 else None,
            "signs": [int(np.sign(x)) for x in a]}


def graph_arm_summary(rows: list[dict], strat: list[dict]) -> dict:
    """One arm under one rule, read against the stratified arm under the same rule."""
    twin = {(x["need_multiple"], x["grace"], x["seed"]): x for x in strat}
    on = [x for x in rows if x["need_multiple"] > 0]
    firing = [x for x in on if x["starved"] > 0]
    lower = [x for x in firing if x["starved_rate_financial"] < x["starved_rate_production"]]
    higher = [x for x in firing if x["starved_rate_financial"] > x["starved_rate_production"]]
    close = {"pairs": 0, "narrower": 0, "equal": 0, "wider": 0}
    path = {"pairs": 0, "narrower": 0, "equal": 0, "wider": 0}
    for x in on:
        s = twin[(x["need_multiple"], x["grace"], x["seed"])]
        if x["starved"] > 0 and s["starved"] > 0:
            a = abs(x["starved_rate_production"] - x["starved_rate_financial"])
            b = abs(s["starved_rate_production"] - s["starved_rate_financial"])
            close["pairs"] += 1
            close["narrower" if a < b else "equal" if a == b else "wider"] += 1
        a = abs(x["path_rate_production"] - x["path_rate_financial"])
        b = abs(s["path_rate_production"] - s["path_rate_financial"])
        path["pairs"] += 1
        path["narrower" if a < b else "equal" if a == b else "wider"] += 1
    under = [x for x in on if x["need_multiple"] < 1.0]
    pool = [x for x in on if x["need_multiple"] == 1.0]
    cells = {}
    for m, g in _cells():
        c = [x for x in on if x["need_multiple"] == m and x["grace"] == g]
        cells[f"{m:g}/g{g}"] = {
            "starved_mean": r(np.mean([x["starved"] for x in c])),
            "starved_financial_mean": r(np.mean([x["starved_financial"] for x in c])),
            "starved_production_mean": r(np.mean([x["starved_production"] for x in c])),
            "runs_with_a_round_below": sum(x["below_floor_peak"] > 0 for x in c),
        }
    med = (lambda xs, k: r(np.median([x[k] for x in xs])) if xs else None)
    return {
        "firing_runs": len(firing),
        "financial_rate_below_production": len(lower),
        "financial_rate_equal_production": len(firing) - len(lower) - len(higher),
        "financial_rate_above_production": len(higher),
        "median_rate_financial_firing": med(firing, "starved_rate_financial"),
        "median_rate_production_firing": med(firing, "starved_rate_production"),
        "floors_under_pool_runs_never_below": sum(x["below_floor_peak"] == 0 for x in under),
        "floors_under_pool_runs": len(under),
        "at_pool_close": [[x["grace"], x["seed"], x["starved_financial"],
                           x["starved_production"]] for x in pool],
        "closing_gap_against_stratified": close,
        "path_gap_against_stratified": path,
        "round_gap_max": r(max((x["round_gap_max"] for x in on), default=0.0)),
        "cells": cells,
    }


def run_arms(rounds: int, seeds: int) -> dict:
    run = Runner(rounds)
    grid = [(0.0, 1)] + _cells()
    # The stratified baseline is the registered row, field for field.
    for seed in range(seeds):
        assert arm_config("stratified", seed, rounds) == base_config(seed, rounds, False)

    strat_rows = {}
    for mode in ("exit", "drawdown"):
        rows = []
        for m, g in grid:
            for seed in range(seeds):
                rec = run.get("stratified", mode, m, g, seed)["row"]
                ref = one_run(m, g, seed, rounds, False, mode=mode)
                assert {**rec, "graph": "stratified"} == ref
                rows.append(rec)
        strat_rows[mode] = rows

    strat_prims = []
    for seed in range(seeds):
        cfg = arm_config("stratified", seed, rounds)
        net = carrier_model(cfg, asset=False)
        strat_prims.append({"primitives": primitives(net, cfg),
                            "payers": np.asarray(net._wage_payers),
                            "receivers": np.asarray(net._wage_receivers),
                            "opening": np.asarray(net.holdings, dtype=float).copy()})

    graph_arms = {}
    for arm in ARMS:
        prims, drift = [], []
        for seed in range(seeds):
            cfg = arm_config(arm, seed, rounds)
            net = carrier_model(cfg, asset=False)
            opening = arm_opening(arm, seed, rounds)
            if opening is not None:
                net.holdings[:] = opening
            prims.append({"seed": seed, **primitives(net, cfg)})
            s = strat_prims[seed]
            drift.append({
                "seed": seed,
                "payer_jaccard": _jaccard(net._wage_payers, s["payers"]),
                "receiver_jaccard": _jaccard(net._wage_receivers, s["receivers"]),
                "opening_rank_correlation": rank_correlation(net.holdings, s["opening"]),
            })
        entry = {"differs_from_stratified_in": ARM_NOTES[arm],
                 "primitives": prims, "drift_against_stratified": drift}
        for mode in ("exit", "drawdown"):
            rows = [run.get(arm, mode, m, g, seed)["row"]
                    for m, g in grid for seed in range(seeds)]
            summary = graph_arm_summary(rows, strat_rows[mode])
            if mode == "drawdown":
                # Only where payroll reaches some nodes and not others; where
                # every node receives it the comparison has no object.
                same, cases = 0, 0
                for g in GRACES:
                    for seed in range(seeds):
                        got = run.get(arm, mode, 1.0, g, seed)
                        n = got["row"]["financial_nodes"] + got["row"]["production_nodes"]
                        recv = {int(i) for i in got["extra"]["receivers"]}
                        if len(recv) == n:
                            continue
                        above = set(range(n)) - {int(i) for i in got["extra"]["close_out"]}
                        same += above == recv
                        cases += 1
                summary["above_floor_at_pool_is_payroll_receivers"] = (
                    f"{same}/{cases}" if cases else None)
            entry[mode] = {"summary": summary, "rows": rows}
        graph_arms[arm] = entry

    baselines = {mode: graph_arm_summary(strat_rows[mode], strat_rows[mode])
                 for mode in ("exit", "drawdown")}
    baselines["primitives"] = [{"seed": s, **strat_prims[s]["primitives"]}
                               for s in range(seeds)]

    off = {seed: run.get("stratified", "exit", 0.0, 1, seed)["row"]["gini_close"]
           for seed in range(seeds)}
    off_issued = r(np.mean([run.get("stratified", "exit", 0.0, 1, s)["extra"]["issued_total"]
                            for s in range(seeds)]))
    corners = {"control_issued_total_mean": off_issued, "corners": {}}
    for label in list(CORNERS) + ["drawdown"]:
        mode = "drawdown" if label == "drawdown" else "exit"
        corner = "registered" if label == "drawdown" else label
        per_cell = {}
        for m, g in _cells():
            got = [run.get("stratified", mode, m, g, s, corner) for s in range(seeds)]
            rows = [x["row"] for x in got]
            firing = [x for x in rows if x["starved"] > 0]
            cell = {
                "dgini": _paired_sign_summary(
                    [x["gini_close"] - off[x["seed"]] for x in rows]),
                "frozen_share_close_mean": r(np.mean([x["frozen_share_close"] for x in rows])),
                "starved_financial_mean": r(np.mean([x["starved_financial"] for x in rows])),
                "starved_production_mean": r(np.mean([x["starved_production"] for x in rows])),
                "median_rate_financial": r(np.median([x["starved_rate_financial"] for x in rows])),
                "median_rate_production": r(np.median([x["starved_rate_production"] for x in rows])),
                "financial_rate_below_production": (
                    f"{sum(x['starved_rate_financial'] < x['starved_rate_production'] for x in firing)}"
                    f"/{len(firing)}"),
                "mr_close_mean": r(np.mean([x["mr_close"] for x in rows])),
                "returns_mean": r(np.mean([x["returns"] for x in rows])),
                "claims_conserved": f"{sum(x['claims_conserved'] for x in rows)}/{len(rows)}",
                "issued_total_mean": r(np.mean([x["extra"]["issued_total"] for x in got])),
            }
            if mode == "exit":
                cell["alive_close_mean"] = r(np.mean(
                    [x["financial_nodes"] + x["production_nodes"] - x["starved"] for x in rows]))
                cell["dgini_less_accrual"] = _paired_sign_summary(
                    [x["gini_close_less_accrual"] - off[x["seed"]] for x in rows])
                recv = [x["extra"]["arrival_receivers"] for x in got if x["extra"]["arrival_receivers"]]
                other = [x["extra"]["arrival_non_receivers"] for x in got
                         if x["extra"]["arrival_non_receivers"]]
                cell["arrival_per_round_on_departed_receivers"] = (
                    [min(v[0] for v in recv), max(v[1] for v in recv)] if recv else None)
                cell["arrival_per_round_on_departed_non_receivers"] = (
                    [min(v[0] for v in other), max(v[1] for v in other)] if other else None)
                cell["receivers_ever_departed"] = [x["extra"]["receivers_ever_out"] for x in got]
                if label in ("reversible", "cut_payroll_reversible"):
                    absorbing = "registered" if label == "reversible" else "cut_payroll"
                    same = sum(
                        x["extra"]["digest"]
                        == run.get("stratified", "exit", m, g, s, absorbing)["extra"]["digest"]
                        for s, x in enumerate(got))
                    cell["identical_to_absorbing_corner"] = f"{same}/{len(got)}"
            per_cell[f"{m:g}/g{g}"] = cell
        corners["corners"][label] = per_cell

    overlap = {}
    drawdown_only_total = 0
    for m, g in _cells():
        sizes = []
        for s in range(seeds):
            e = set(run.get("stratified", "exit", m, g, s)["extra"]["close_out"].tolist())
            d = set(run.get("stratified", "drawdown", m, g, s)["extra"]["close_out"].tolist())
            sizes.append((len(e), len(d), len(e & d), len(d - e), len(e - d)))
            drawdown_only_total += len(d - e)
        a = np.asarray(sizes, dtype=float)
        overlap[f"{m:g}/g{g}"] = {
            "exit_out_mean": r(a[:, 0].mean()),
            "drawdown_below_mean": r(a[:, 1].mean()),
            "both_mean": r(a[:, 2].mean()),
            "drawdown_only_mean": r(a[:, 3].mean()),
            "exit_only_mean": r(a[:, 4].mean()),
        }
    rule_overlap = {"cells": overlap, "drawdown_only_nodes_over_grid": drawdown_only_total}

    # Under `drawdown` the complete graph at the pool per node is all below the
    # floor every other round, so the close is a phase. One round either side.
    phase = {}
    for length in (rounds - 1, rounds + 1):
        rows = [one_run(m, g, s, length, uniform, mode="drawdown")
                for uniform in (False, True) for m, g in grid for s in range(seeds)]
        crit = evaluate(rows, structure_is_shared(0, length, "drawdown"), seeds)
        phase[str(length)] = {
            "complete_at_pool_close": [
                [x["grace"], x["seed"], x["below_floor_close"]] for x in rows
                if x["graph"] == "complete" and x["need_multiple"] == 1.0],
            "criteria": [{"name": c.name, "passed": bool(c.passed), "void": bool(c.void),
                          "detail": c.detail} for c in crit],
        }

    return {
        "drawdown_phase": phase,
        "baselines_stratified": baselines,
        "graph_arms": graph_arms,
        "exit_corners": corners,
        "rule_overlap": rule_overlap,
        "runs_made": len(run.cache),
    }


ARMS_DEFINITIONS = {
    "graph_arms": (
        "Each arm under both exit rules on the registered grid, read against "
        "the stratified arm under the same rule: paired by seed, floor and "
        "grace, the closing gap where both fire and the path gap on every "
        "floor-on pair. The adjacency arms are the s = 1 endpoint of A7's "
        "continuum and a different economy from the registered complete-graph "
        "control, so no arm is read against that control."
    ),
    "drift_against_stratified": (
        "With the adjacency moved and the rules held, which nodes pay and "
        "receive payroll (Jaccard against the stratified arm) and the opening "
        "vector's rank correlation with the stratified one (null where one "
        "vector is constant)."
    ),
    "exit_corners": (
        "The exit rule's two switches on the stratified graph, each corner on "
        "the registered grid. `dgini` is the closing Gini less the stratified "
        "floor-off control, paired by seed; `dgini_less_accrual` does the same "
        "with each node out at the close set back to what it held when it last "
        "left. `arrival_per_round_*` are the smallest and largest one-round "
        "increases in holdings of a node out in both rounds. "
        "`identical_to_absorbing_corner` compares the whole holdings history "
        "and the per-round masks with the absorbing corner of the same payroll "
        "setting."
    ),
    "above_floor_at_pool_is_payroll_receivers": (
        "Under `drawdown` at the pool per node, the runs in which the nodes "
        "above the floor at the close are exactly the payroll receivers. Null "
        "where every node receives payroll."
    ),
    "drawdown_phase": (
        "The registered `drawdown` grid at one round fewer and one round more "
        "than the record, with the four criteria evaluated on each, and the "
        "closing count of the complete graph at the pool per node as "
        "[grace, seed, count]."
    ),
    "rule_overlap": (
        "Per floor and grace, the closing sets under the two rules on the "
        "stratified graph: out under `exit`, below the floor under `drawdown`, "
        "both, and each alone. Means over seeds."
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--drawdown", action="store_true",
        help="run the floor under the drawdown exit rule instead of the "
             "registered one. Under the registered rule a node below the "
             "floor leaves the graph and, with the payroll left on, goes "
             "on receiving wages it never spends, so the frozen set "
             "accumulates; A12-6 measured that. Under drawdown the node "
             "stays and spends min(need, holdings). Off is the registered "
             "arm and reproduces the record key for key.",
    )
    parser.add_argument("--rounds", type=int, default=REGISTERED_ROUNDS)
    parser.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
    parser.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    parser.add_argument(
        "--arms", action="store_true",
        help="the one-switch arms and the corners of the exit rule, printed "
             "and not scored, on the plain carrier.",
    )
    args = parser.parse_args(argv)
    if args.arms and (args.asset or args.drawdown):
        parser.error("--arms runs both rules on the plain carrier; it takes "
                     "neither --asset nor --drawdown")
    mode = "drawdown" if args.drawdown else "exit"
    registered = args.rounds == REGISTERED_ROUNDS and args.seeds == REGISTERED_SEEDS
    path = RESULTS / record_name(args.asset, args.drawdown, args.arms,
                                 args.rounds, args.seeds)
    RESULTS.mkdir(parents=True, exist_ok=True)
    offparam = ([] if registered else [
        f"run at {args.seeds} seeds and {args.rounds} rounds, which is not the "
        f"registered {REGISTERED_SEEDS} and {REGISTERED_ROUNDS}"])

    if args.arms:
        print("stage A11: one switch at a time, printed and not scored")
        print(f"  rounds={args.rounds} seeds={args.seeds}\n")
        arms = run_arms(args.rounds, args.seeds)
        reason = "; ".join(offparam + [
            "one-switch arms built from switches the shared model already "
            "carries; printed and not scored. The registered reading is "
            "results/a11_subsistence.json"])
        record = {
            "stage": "A11",
            "diagnostic_only": True,
            "diagnostic_reason": reason,
            "rounds": args.rounds,
            "seeds_tested": args.seeds,
            "need_multiples": list(NEED_MULTIPLES),
            "graces": list(GRACES),
            "definitions": {**{k: v for k, v in DEFINITIONS.items()
                               if k not in ("coverage", "structure", "path_reading")},
                            **ARMS_DEFINITIONS},
            **arms,
        }
        for arm in ARMS:
            for rule in ("exit", "drawdown"):
                s = arms["graph_arms"][arm][rule]["summary"]
                print(f"  {arm:>32s} {rule:>8s}: firing {s['firing_runs']:2d}, "
                      f"fin<prod {s['financial_rate_below_production']:2d}, "
                      f"close gap vs stratified {s['closing_gap_against_stratified']}, "
                      f"under-pool runs never below "
                      f"{s['floors_under_pool_runs_never_below']}/{s['floors_under_pool_runs']}")
        for length, ph in arms["drawdown_phase"].items():
            marks = " ".join("VOID" if c["void"] else ("PASS" if c["passed"] else "FAIL")
                             for c in ph["criteria"])
            print(f"  drawdown at {length} rounds: {marks}; complete at the pool closes "
                  f"{sorted({x[2] for x in ph['complete_at_pool_close']})}")
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
        print(f"  wrote {path.relative_to(ROOT)}")
        return 0

    print("stage A11: the subsistence floor")
    print(f"  rounds={args.rounds} seeds={args.seeds}\n")

    rows = []
    for uniform in (False, True):
        for seed in range(args.seeds):
            rows.append(one_run(0.0, 1, seed, args.rounds, uniform,
                                args.asset, mode))
        for mult in NEED_MULTIPLES:
            for grace in GRACES:
                for seed in range(args.seeds):
                    rows.append(
                        one_run(mult, grace, seed, args.rounds, uniform,
                                args.asset, mode))

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

    criteria = evaluate(rows, structure_is_shared(0, args.rounds, mode), args.seeds)
    cov = coverage(rows, args.seeds)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, {len(criteria) - len(live)} void")
    if not cov["complete"]:
        print("  the rows are not the registered grid; see the coverage block")

    reasons = offparam + (
        ["run under the drawdown exit rule, which is not this station's "
         "registered one; the registered reading is results/a11_subsistence.json"]
        if args.drawdown and not args.asset else []) + (
        ["read on A3's asset layer, which is not this station's registered "
         "carrier; the registered reading is results/a11_subsistence.json"]
        if args.asset and not args.drawdown else []) + (
        ["run under the drawdown exit rule on A3's asset layer, neither of which "
         "is this station's registered setting; the registered reading is "
         "results/a11_subsistence.json"]
        if args.asset and args.drawdown else [])
    path.write_text(
        json.dumps(
            {
                "stage": "A11",
                "exit_rule": mode,
                **({"diagnostic_only": True, "diagnostic_reason": "; ".join(reasons)}
                   if reasons else {}),
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "need_multiples": list(NEED_MULTIPLES),
                "graces": list(GRACES),
                "definitions": DEFINITIONS,
                "coverage": cov,
                "structure": structure_block(args.seeds, args.rounds, mode, args.asset),
                "path_reading": path_reading(rows),
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
    return exit_code(criteria, cov)


if __name__ == "__main__":
    raise SystemExit(main())
