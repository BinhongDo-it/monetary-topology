"""A54: a fine, a cap on size and the loss of relationships, on one node, and
which of the three is still there at the end.

Ruled 2026-10-06. The reading this station exists for: a fine on a large node
does little unless it is very large, a cap on its size works, and removing
people works or does not depending on whom. On the graph these are three
different operations, and no station on disk puts them on the same node.

    fine   claims taken from the node's account. A change of the state.
    cap    a ceiling on what the node may hold: the part of its inflow that
           would take it over the ceiling goes to its payers' other
           counterparties. A change of one column of the routing.
    cut    edges of the node removed: the people who carried those
           relationships are gone. A change of the edge set.

Every penalised cell is read against its twin, the same configuration and seed
with no penalty. On this carrier the only draws inside a round are the spending
propensities, one per node per round whatever the state, so the two runs draw
the same numbers and their difference is the penalty's. Every run checks that.

The model is not changed. ``PenaltyNetwork`` adds one thing to it, at the step
where the model's own capacity rule sits (``_greedy_reroute``: a node's budget
is known there, and capacity is an amount): the cap. Beside it are taps that
read and never write. Fines and cuts are applied by the driver at the yield of
``_run_steps``, where one round's books are closed and the next has not opened.
With no penalty the class and the driver are ``Network.run()`` bit for bit,
and ``--gate`` runs that comparison.

**The fine.** At the close of round 149 a share of what the target holds is
taken, once; or the same total in ten instalments ten rounds apart; or a
multiple of the target's own inflow per round, collected at every close until
paid, which leaves the node nothing to spend while it lasts. What is taken
leaves the graph and the claim total. Where the sovereign's pool exists it can
instead be paid into the pool and passed down again by the model's own rule.

**The cap.** A level, as a multiple of what the target holds at the close of
round 149. In every later round the routed inflow the target may take is what
keeps its closing balance at the level; the rest is spent by the same payers on
their other counterparties, in the proportions they already use. Claims that
enter without an edge (issuance, the sovereign's pass-down) are not routed and
are not stopped; every close above the level is counted.

**The cut.** In-edges (who pays the target) or out-edges (whom it pays) of the
discretionary routing, a share of them, picked at random or from the largest
flow of round 149 down. The payroll channel is a separate list in the model and
is left as it is; it is never among the candidates, so every cut edge is one
whose flow stops. One arm puts the edges back twenty rounds later: the person
is replaced.

Two targets per graph: the node with the most in-edges inside the financial
layer and outside it, by the expression ``injection_node`` uses.

Steps, one at a time and in this order:

    python experiments/a54_penalty.py --gate            # the driver is the model
    python experiments/a54_penalty.py --selftest        # seeded faults
    python experiments/a54_penalty.py --time            # seconds per run
    python experiments/a54_penalty.py --run --seeds 5   # the grid
    python experiments/a54_tables.py                    # the record, as tables

``--run`` does not start until ``--gate`` has passed on the module and this
script as they are now. ``--run --smoke`` is a reduced grid that gates itself
and writes nothing; ``--no-write`` prints and writes nothing on any step.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SRC = ROOT / "src" / "monetary_topology"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkHistory,
)

RECORD = RESULTS / "a54_penalty.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A30's carrier and helpers, taken rather than restated: the three strains,
#: the record format, the bit-for-bit comparison, the criterion type.
_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a54")
_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_same = _A30._same
_tally = _A30._tally
_default_workers = _A30._default_workers
_print_criteria = _A30._print_criteria
_rng_digest = _A30._rng_digest
Criterion = _A30.Criterion
flip = _A30.flip
FLIP_STATES = _A30.FLIP_STATES
CLOSING = _A30.CLOSING

ROUNDS = _A30.ROUNDS
SEEDS = _A30.SEEDS
TAIL = _A30.TAIL
FLOOR_MULTIPLE = _A30.FLOOR_MULTIPLE
LEDGER_TOL = _A30.LEDGER_TOL
BLOCK = _A30.BLOCK
STRESSES = _A30.STRESSES
STRESS_SPECS = _A30.STRESS_SPECS

#: The penalty starts at the close of this round: A30's shock round less one.
PENALTY_ROUND = _A30.SHOCK_ROUND - 1
#: The first round whose flow the penalty reaches. "n rounds after the
#: penalty" is round ``PENALTY_ROUND + n`` everywhere below, so n = 1 is this.
FIRST = PENALTY_ROUND + 1
#: Far from the absorbing edge, and A30's bistable floor.
NEEDS: tuple[float, ...] = (0.05, 0.20)
ELASTICITIES: tuple[float, ...] = (0.0, 0.5)
AUTHORITIES: tuple[str, ...] = ("endogenous", "none")
TARGETS: tuple[str, ...] = ("financial", "production")

#: Fines as a share of what the target holds at the close of the penalty round.
FINE_SHARES: tuple[float, ...] = (0.05, 0.2, 0.5, 0.9)
INSTALMENTS = 10
INSTALMENT_GAP = 10
#: Fines as rounds of the target's own inflow, collected until paid. Nine
#: tenths of the balance is under two rounds of inflow for either target, so
#: these are the sizes a share of the balance cannot reach.
GARNISH_ROUNDS: tuple[int, ...] = (2, 4, 8)
#: The rounds whose mean inflow is "one round of the target's inflow".
REVENUE_FROM = PENALTY_ROUND - 9
#: Caps as a multiple of the balance at the close of the penalty round. On a
#: graph that is not growing a cap at or above the balance has nothing to hold
#: down, so the main grid sets it at and below, and the growing block at and
#: above.
CAP_LEVELS: tuple[float, ...] = (0.5, 0.8, 1.0)
CUT_SHARES: tuple[float, ...] = (0.1, 0.3, 0.6)
CUT_SIDES: tuple[str, ...] = ("in", "out")
CUT_PICKS: tuple[str, ...] = ("random", "flow")
#: The replaced person: the cut edges come back this many rounds later.
RESTORE_AFTER = 20
RESTORE_SHARES: tuple[float, ...] = (0.3, 0.6)
#: The growing block: A30's healthy strain with a fixed issuance per round at
#: the model's own entry point, so that a cap has growth to act on.
GROWTH_ISSUE = 1.0
GROWTH_CAPS: tuple[float, ...] = (1.0, 1.2, 1.5)
GROWTH_FINES: tuple[float, ...] = (0.5, 0.9)

#: Rounds after the penalty at which the deviation is printed per cell.
HORIZON_N: tuple[int, ...] = (1, 2, 3, 5, 10, 20, 50, 100, 150)
#: Rounds after the penalty at which who carries a fine is printed.
INCIDENCE_N: tuple[int, ...] = (1, 5, 20)
#: A node holding less than this in the twin is not a denominator.
EPS_HOLD = 1e-9
#: Where no switch differs from the twin's the model is the same affine map in
#: both runs, so a fine's effect per unit taken is the same whatever its size,
#: to rounding. Measured before the grid: 3e-14 to 1e-13 where it holds and
#: 7e-6 or more where a switch has flipped.
PROPORTIONAL_TOL = 1e-9
#: The driver's own stream for a random pick of edges, kept off the model's.
_PICK_STREAM = 5454
#: The reduced grid ``--smoke`` runs.
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}

SWITCHES: tuple[str, ...] = ("floor", "floor spending", "payroll", "issuance")
SWITCH_TEXT = (
    "floor = which nodes are below the subsistence floor; floor spending = "
    "which of those hold less than the floor amount and spend all they have; "
    "payroll = which payers hold less than their share of the wage bill; "
    "issuance = whether the authority issues this round")


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def base_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, authorities=AUTHORITIES,
              growth: bool = True) -> list:
    """One entry per configuration and seed: one twin, and every arm on both
    targets read against it."""
    keys = []
    for need in needs:
        for stress in stresses:
            for e in elasticities:
                for auth in authorities:
                    for seed in seeds:
                        keys.append({"block": "main", "need": need,
                                     "stress": stress, "elasticity": e,
                                     "authority": auth, "seed": seed})
    if growth:
        for need in needs:
            for e in elasticities:
                for seed in seeds:
                    keys.append({"block": "growth", "need": need,
                                 "stress": "healthy", "elasticity": e,
                                 "authority": "fixed", "seed": seed})
    return keys


def base_config(base: dict) -> NetworkConfig:
    """A30's cell, which is A18's ``config_for`` in drawdown with no write-off
    and no rescue plus the strain. The growing block swaps the authority for a
    fixed issuance and changes nothing else."""
    auth = base["authority"]
    key = {"need": base["need"], "stress": base["stress"],
           "elasticity": base["elasticity"],
           "authority": "none" if auth == "fixed" else auth,
           "shock": "none", "size": 0.0, "seed": base["seed"]}
    cfg = _A30.cell_config(key)
    if auth == "fixed":
        cfg = dataclasses.replace(cfg, authority=MonetaryAuthority(
            rule="fixed", fixed_amount=GROWTH_ISSUE))
    return cfg


def _fine(mode: str, size: float, sink: str = "destroy") -> dict:
    return {"kind": "fine", "mode": mode, "size": size, "sink": sink}


def _cap(level: float) -> dict:
    return {"kind": "cap", "size": level}


def _cut(side: str, share: float, pick: str, restore=None) -> dict:
    return {"kind": "cut", "side": side, "size": share, "pick": pick,
            "restore": restore}


def arms_for(base: dict) -> list:
    if base["block"] == "growth":
        return ([_fine("once", f) for f in GROWTH_FINES]
                + [_cap(c) for c in GROWTH_CAPS])
    arms = []
    sinks = ("destroy", "return") if base["stress"] == "leak_recycled" \
        else ("destroy",)
    for sink in sinks:
        arms += [_fine("once", f, sink) for f in FINE_SHARES]
        arms += [_fine("instalments", f, sink) for f in FINE_SHARES]
        arms += [_fine("garnish", m, sink) for m in GARNISH_ROUNDS]
    arms += [_cap(c) for c in CAP_LEVELS]
    for side in CUT_SIDES:
        for s in CUT_SHARES:
            for pick in CUT_PICKS:
                arms.append(_cut(side, s, pick))
    arms += [_cut("in", s, "flow", RESTORE_AFTER) for s in RESTORE_SHARES]
    return arms


def arm_label(a: dict) -> str:
    if a["kind"] == "fine":
        return "fine %s %g%s" % (a["mode"], a["size"],
                                 " returned" if a["sink"] == "return" else "")
    if a["kind"] == "cap":
        return "cap %g" % a["size"]
    return "cut %s %g %s%s" % (a["side"], a["size"], a["pick"],
                               " restored" if a.get("restore") else "")


def _all_labels() -> list:
    """Every arm label in the order the grid makes them, for sorting."""
    seen, out = set(), []
    for base in ({"block": "main", "stress": "leak_recycled"},
                 {"block": "growth", "stress": "healthy"}):
        for a in arms_for(base):
            lab = arm_label(a)
            if lab not in seen:
                seen.add(lab)
                out.append(lab)
    return out


ARM_ORDER: list = _all_labels()


# ---------------------------------------------------------------------------
# The model, with the cap at its own capacity step and taps beside it.
# ---------------------------------------------------------------------------

class PenaltyNetwork(Network):
    """``Network`` with a ceiling on one node's balance, and read-only taps.

    With ``pen_cap`` unset nothing here writes anything the round reads, so a
    run is ``Network.run()`` bit for bit; ``--gate`` runs that.

    **Where the cap sits.** ``_greedy_reroute`` is the model's capacity step:
    it is handed the routing fractions and each payer's budget, which is the
    one place an amount a node may take in can be turned into fractions. The
    cap is such an amount, so it is applied there and nowhere else. The
    target's own spending is untouched, every payer still spends what it was
    going to spend, and the rows still sum to one, so the round's stock-flow
    assertion holds as it stands.
    """

    def __init__(self, config: NetworkConfig) -> None:
        super().__init__(config)
        if (config.greedy.enabled or config.industry.enabled
                or config.rewire.active or config.edge_cut.active):
            raise ValueError(
                "A54 reads a carrier with no rank-and-fill, no industries, no "
                "rewiring and no cut of the model's own: the hook assumes the "
                "routing it is handed is the routing the round will use")
        n = self._n
        self.pen_target: int | None = None
        self.pen_cap: float | None = None
        #: A seeded fault, set only by ``--selftest``.
        self.pen_fault: str | None = None
        #: What the round just computed: each node's budget and the routing
        #: it was spent along. References, never copies and never written to.
        self.tap_spent: np.ndarray | None = None
        self.tap_route: np.ndarray | None = None
        #: The three switches the round consulted, each a mask over nodes.
        self.tap_below = np.zeros(n, dtype=bool)
        self.tap_floor_capped = np.zeros(n, dtype=bool)
        self.tap_short = np.zeros(n, dtype=bool)
        #: The cap's books: this round, and summed over the run.
        self.cap_raw = 0.0
        self.cap_blocked = 0.0
        self.cap_blocked_from = np.zeros(n)
        self.cap_diverted_to = np.zeros(n)

    def _wage_flow(self):
        payers = self._wage_payers
        held = np.maximum(self.holdings[payers], 0.0)
        out = super()._wage_flow()
        short = np.zeros(self._n, dtype=bool)
        if payers.size and self._last_bill_owed > 0.0:
            # The model pays ``min(share of the bill, balance)``: a payer is
            # short exactly when its balance is the smaller of the two.
            short[payers] = held < self._last_bill_owed / payers.size
        self.tap_short = short
        return out

    def _greedy_reroute(self, route: np.ndarray, spent: np.ndarray) -> np.ndarray:
        route = super()._greedy_reroute(route, spent)
        if self.pen_cap is not None:
            route = self._cap_route(route, spent)
        self.tap_spent, self.tap_route = spent, route
        below = self._below
        self.tap_below = below
        self.tap_floor_capped = below & (
            np.maximum(self.holdings, 0.0) < self.config.subsistence.need)
        return route

    def _cap_route(self, route: np.ndarray, spent: np.ndarray) -> np.ndarray:
        """Scale the target's column so its closing balance stops at the cap.

        ``room`` is what the target can still take in this round: the cap less
        what it holds after its own spending. If the routed inflow fits,
        nothing changes. If not, every payer sends the same share ``theta`` of
        what it was sending, and the rest of that payment is spread over the
        payer's other counterparties in the proportions the row already has,
        so the row still sums to one.
        """
        target = self.pen_target
        col = route[:, target]
        raw = float(spent @ col)
        room = self.pen_cap - (float(self.holdings[target]) - float(spent[target]))
        self.cap_raw = raw
        self.cap_blocked = 0.0
        if raw <= 0.0 or raw <= room:
            return route
        if self.pen_fault == "cap_on_outflow":
            # Seeded: the cap stops what the target pays and leaves what it is
            # paid alone. The guard at the yield has to report this.
            spent[target] = 0.0
            return route
        theta = max(room, 0.0) / raw
        payers = col > 0.0
        if (col[payers] >= 1.0).any():
            raise RuntimeError(
                "a payer of the capped node has no other counterparty to "
                "spend on; this carrier has none, so the branch is not built")
        scale = np.ones(self._n)
        scale[payers] = (1.0 - theta * col[payers]) / (1.0 - col[payers])
        gain = (spent * (scale - 1.0)) @ route
        gain[target] = 0.0
        capped = route * scale[:, None]
        capped[:, target] = theta * col
        self.cap_blocked = (1.0 - theta) * raw
        self.cap_blocked_from += spent * col * (1.0 - theta)
        self.cap_diverted_to += gain
        return capped


# ---------------------------------------------------------------------------
# The graph around a target.
# ---------------------------------------------------------------------------

def target_nodes(net: Network) -> dict:
    """The node with the most in-edges inside the financial layer and outside
    it, by ``adjacency.sum(axis=0)``, the expression ``injection_node`` and the
    hub obligation use. Ties go to the lowest index, and are counted."""
    indeg = net.adjacency.sum(axis=0)
    fin = np.asarray(net._l1)
    rest = np.setdiff1d(np.arange(net._n), fin)
    out = {}
    for kind, nodes in (("financial", fin), ("production", rest)):
        d = indeg[nodes]
        top = np.sort(d)[::-1]
        out[kind] = {
            "node": int(nodes[np.argmax(d)]),
            "in_degree": float(top[0]),
            "second_in_degree": float(top[1]),
            "distinct_in_degrees": int(np.unique(d).size),
            "tied_first": int((d == top[0]).sum()),
        }
    return out


def layers_of(net: Network) -> np.ndarray:
    """fin, mid (the intermediate block, which pays the wages), hhw (households
    on a payroll), hh0 (households on none)."""
    lab = np.full(net._n, "hh0", dtype=object)
    lab[np.asarray(net._l1)] = "fin"
    lab[np.asarray(net._mid, dtype=int)] = "mid"
    on_payroll = np.zeros(net._n, dtype=bool)
    on_payroll[np.asarray(net._wage_receivers)] = True
    lab[on_payroll & (lab == "hh0")] = "hhw"
    return lab


LAYERS: tuple[str, ...] = ("fin", "mid", "hhw", "hh0")
STEP_GROUPS: tuple[str, ...] = ("1", "2", "3+", "none")


def steps_from(adj: np.ndarray, src: int, reverse: bool = False) -> np.ndarray:
    """Hops from ``src`` along the edges (row pays column), or against them.
    -1 where there is no path."""
    a = adj.T if reverse else adj
    n = a.shape[0]
    d = np.full(n, -1, dtype=int)
    d[src] = 0
    frontier = [src]
    while frontier:
        nxt = []
        for u in frontier:
            for v in np.flatnonzero(a[u]):
                if d[v] < 0:
                    d[v] = d[u] + 1
                    nxt.append(int(v))
        frontier = nxt
    return d


def step_groups(d: np.ndarray) -> np.ndarray:
    """1, 2, 3+ or none; the source itself is its own group."""
    g = np.full(d.size, "none", dtype=object)
    g[d == 0] = "target"
    g[d == 1] = "1"
    g[d == 2] = "2"
    g[d >= 3] = "3+"
    return g


# ---------------------------------------------------------------------------
# The driver.
# ---------------------------------------------------------------------------

def _books(net: Network, cfg: NetworkConfig) -> bool:
    stock = float(net.holdings.sum()) + float(net._parked.sum())
    tol = LEDGER_TOL * max(1.0, stock / cfg.initial_claims)
    return abs(net._total_claims - stock) <= tol


def drive(cfg: NetworkConfig, node: int | None = None, arm: dict | None = None,
          twin: dict | None = None, fault: str | None = None) -> tuple:
    """Run one configuration through ``_run_steps``, acting only at the yield.

    With no arm this is a twin: nothing is done, and what its arms will be
    read against is kept. With an arm, ``twin`` is that record and ``node``
    the target. Returns the network, whose ``_history`` is the run's history,
    and what the driver saw.
    """
    if (arm is None) != (twin is None):
        raise ValueError("an arm needs its twin, and a twin has no arm")
    net = PenaltyNetwork(cfg)
    net.pen_fault = fault
    n = net._n
    kind = None if arm is None else arm["kind"]
    span = ROUNDS - FIRST
    seen: dict = {"books": True}
    if kind is None:
        seen["inflow_window"] = np.zeros((PENALTY_ROUND - REVENUE_FROM + 1, n))
        seen["sig"] = {k: np.zeros((span, n), dtype=bool)
                       for k in ("below", "floor_capped", "short")}
    else:
        if node is None:
            raise ValueError("an arm needs a target")
        net.pen_target = node
        sig = twin["sig"]
        seen.update({
            "switch": np.zeros((span, len(SWITCHES)), dtype=bool),
            "ever_extra": np.zeros(n, dtype=bool),
            "ever_fewer": np.zeros(n, dtype=bool),
            "peak_extra": 0, "peak_extra_n": None,
        })
    if kind == "fine":
        if arm["sink"] == "return" and (not cfg.sovereign.active
                                        or cfg.sovereign.serves_debt):
            raise ValueError(
                "a returned fine goes through the sovereign's pool and its "
                "pass-down, on a carrier where the pool's receipts book is "
                "read by its own guard and by nothing else")
        seen.update({"asked": 0.0, "takes": [], "take_rounds": [],
                     "fines_to_pool": 0.0, "first_take_ok": None,
                     "ledger": True if arm["sink"] == "return" else None,
                     "remaining": 0.0})
    if kind == "cap":
        seen.update({"bites": 0, "first_bite": None, "last_bite": None,
                     "bites_tail": 0, "blocked_total": 0.0,
                     "blocked_tail": 0.0, "raw_tail": 0.0,
                     "over_cap_closes": 0, "over_cap_max": 0.0,
                     "over_cap_tail": 0, "guard": True})
    if kind == "cut":
        seen.update({"chosen": None, "restored": None})
    saved_route = None

    def take(amount: float) -> float:
        have = max(float(net.holdings[node]), 0.0)
        got = min(amount, have)
        held0, total0 = float(net.holdings.sum()), float(net._total_claims)
        net.holdings[node] -= got
        if fault != "unbooked_fine":
            net._total_claims -= got
        if arm["sink"] == "return":
            # A fine paid into the pool is a receipt. The model's guard reads
            # the pool against one receipts book, ``_bonds_bought``, so the
            # fine is booked there; what was booked is kept beside it, and
            # bonds outstanding, which the fine never touches, has to equal
            # receipts less fines at every yield.
            net._sovereign_pool += got
            if fault != "pool_only":
                net._bonds_bought += got
            seen["fines_to_pool"] += got
        if seen["first_take_ok"] is None:
            tol = LEDGER_TOL * max(1.0, held0 / cfg.initial_claims)
            seen["first_take_ok"] = bool(
                abs((held0 - float(net.holdings.sum())) - got) <= tol
                and abs((total0 - float(net._total_claims)) - got) <= tol)
        seen["takes"].append(got)
        seen["take_rounds"].append(t)
        return got

    for t in net._run_steps():
        # -- the round that just closed ------------------------------------
        if kind is None:
            if REVENUE_FROM <= t <= PENALTY_ROUND:
                seen["inflow_window"][t - REVENUE_FROM] = net._last_inflow
            if t >= FIRST:
                i = t - FIRST
                seen["sig"]["below"][i] = net.tap_below
                seen["sig"]["floor_capped"][i] = net.tap_floor_capped
                seen["sig"]["short"][i] = net.tap_short
        elif t >= FIRST:
            i = t - FIRST
            sw = seen["switch"][i]
            sw[0] = bool((net.tap_below != sig["below"][i]).any())
            sw[1] = bool((net.tap_floor_capped != sig["floor_capped"][i]).any())
            sw[2] = bool((net.tap_short != sig["short"][i]).any())
            extra = net.tap_below & ~sig["below"][i]
            seen["ever_extra"] |= extra
            seen["ever_fewer"] |= sig["below"][i] & ~net.tap_below
            count = int(extra.sum())
            if count > seen["peak_extra"]:
                seen["peak_extra"], seen["peak_extra_n"] = count, t - PENALTY_ROUND
        if t == PENALTY_ROUND:
            seen["at"] = {
                "holdings": net.holdings.copy(),
                "parked": net._parked.copy(),
                "total": float(net._total_claims),
                "spent": net.tap_spent, "route": net.tap_route,
                "adjacency": net.adjacency > 0,
            }
        if kind == "cap" and t >= FIRST:
            routed = float(net.tap_spent @ net.tap_route[:, node])
            if net.cap_blocked > 0.0:
                seen["bites"] += 1
                seen["last_bite"] = t - PENALTY_ROUND
                if seen["first_bite"] is None:
                    seen["first_bite"] = t - PENALTY_ROUND
                seen["blocked_total"] += net.cap_blocked
                if t >= ROUNDS - TAIL:
                    seen["bites_tail"] += 1
                    seen["blocked_tail"] += net.cap_blocked
            if t >= ROUNDS - TAIL:
                seen["raw_tail"] += net.cap_raw
            excess = float(net.holdings[node]) - seen["cap_level"]
            edge = 1e-9 * max(1.0, seen["cap_level"])
            if net.cap_blocked > 0.0 and routed > 0.0 and abs(excess) > edge:
                # It turned some inflow away and let some in: what it let in
                # has to be exactly what fills the balance to the level.
                seen["guard"] = False
            if excess > edge:
                seen["over_cap_closes"] += 1
                seen["over_cap_max"] = max(seen["over_cap_max"], excess)
                if t >= ROUNDS - TAIL:
                    seen["over_cap_tail"] += 1
                # Above the cap at a close is allowed in one case only: the
                # column was shut, and what put the balance there did not
                # come along an edge.
                if routed != 0.0:
                    seen["guard"] = False
        if kind == "cut" and t == FIRST and seen["chosen"] is not None:
            ch = seen["chosen"]
            if arm["side"] == "in":
                left = float(net.tap_spent[ch] @ net.tap_route[ch, node])
            else:
                left = float(net.tap_spent[node] * net.tap_route[node, ch].sum())
            seen["residual_flow"] = left
        # -- act at the close: never at the last one, which no round follows --
        if t == ROUNDS - 1:
            pass
        elif kind == "fine" and t >= PENALTY_ROUND:
            if t == PENALTY_ROUND:
                if arm["mode"] == "garnish":
                    seen["asked"] = arm["size"] * float(
                        twin["inflow_window"][:, node].mean())
                else:
                    seen["asked"] = arm["size"] * float(net.holdings[node])
                seen["remaining"] = seen["asked"]
            due = None
            if arm["mode"] == "once":
                if t == PENALTY_ROUND:
                    due = seen["asked"]
            elif arm["mode"] == "instalments":
                j, rem = divmod(t - PENALTY_ROUND, INSTALMENT_GAP)
                if rem == 0 and j < INSTALMENTS:
                    due = seen["asked"] / INSTALMENTS
            elif (t == PENALTY_ROUND
                  or seen["remaining"] > 1e-12 * max(seen["asked"], 1.0)):
                due = seen["remaining"]
            if due is not None:
                got = take(due)
                if arm["mode"] == "garnish":
                    # Collected until paid: what was not there is still owed.
                    seen["remaining"] -= got
                else:
                    # A share of the balance that is not there is written
                    # off: an instalment is not carried forward.
                    seen["remaining"] -= due
                    seen["shortfall"] = seen.get("shortfall", 0.0) + due - got
        elif kind == "cap" and t == PENALTY_ROUND:
            seen["cap_level"] = arm["size"] * float(net.holdings[node])
            net.pen_cap = seen["cap_level"]
        elif kind == "cut":
            if t == PENALTY_ROUND:
                at = seen["at"]
                route = net._route
                if arm["side"] == "in":
                    cand = np.flatnonzero(route[:, node] > 0.0)
                    flows = at["spent"][cand] * at["route"][cand, node]
                else:
                    cand = np.flatnonzero(route[node] > 0.0)
                    flows = at["spent"][node] * at["route"][node, cand]
                k = int(round(arm["size"] * cand.size))
                if arm["pick"] == "flow":
                    order = np.argsort(-flows, kind="stable")
                else:
                    # A permutation, so the random pick at a larger share
                    # contains the pick at a smaller one: a path in the share.
                    rng = net.rng if fault == "cut_draws_main" else \
                        np.random.default_rng(
                            [cfg.seed, _PICK_STREAM, node,
                             CUT_SIDES.index(arm["side"])])
                    order = rng.permutation(cand.size)
                chosen = cand[order[:k]]
                seen.update({
                    "edges": int(cand.size), "cut": int(k),
                    "flow_total": float(flows.sum()),
                    "flow_cut": float(flows[order[:k]].sum()),
                    "adjacency_edges": int(
                        (net.adjacency[:, node] > 0).sum() if arm["side"] == "in"
                        else (net.adjacency[node] > 0).sum()),
                })
                if k > 0:
                    if arm.get("restore"):
                        saved_route = route.copy()
                    if arm["side"] == "in":
                        net.adjacency[chosen, node] = 0.0
                    else:
                        net.adjacency[node, chosen] = 0.0
                    # The model's own cut ends the same way: the routing is
                    # rebuilt from the adjacency, payroll list untouched.
                    net._rebuild_route()
                    seen["chosen"] = chosen
                    after = net._route[:, node] if arm["side"] == "in" \
                        else net._route[node]
                    seen["edges_after"] = int((after > 0.0).sum())
                else:
                    seen["edges_after"] = int(cand.size)
            elif (arm.get("restore") and seen["chosen"] is not None
                  and t == PENALTY_ROUND + arm["restore"]):
                ch = seen["chosen"]
                if arm["side"] == "in":
                    net.adjacency[ch, node] = 1.0
                else:
                    net.adjacency[node, ch] = 1.0
                net._rebuild_route()
                seen["restored"] = bool(np.array_equal(net._route, saved_route))
        # -- the books, after whatever was done ------------------------------
        if not _books(net, cfg):
            seen["books"] = False
        if kind == "fine" and arm["sink"] == "return":
            tol = LEDGER_TOL * max(1.0, net._bonds_bought / cfg.initial_claims)
            bonds = net._bonds_bought - seen["fines_to_pool"]
            if (abs(net._bond_stock - bonds) > tol
                    or abs(net._sovereign_pool
                           - (net._bonds_bought - net._passed_total)) > tol):
                seen["ledger"] = False
    seen["rng"] = _rng_digest(net)
    seen["below_close"] = net._below.copy()
    return net, seen


def make_twin(cfg: NetworkConfig) -> dict:
    """The unpenalised run, and everything its arms are read against."""
    net, seen = drive(cfg)
    h = net._history
    hold = np.asarray(h.holdings, dtype=float)
    circ = hold.sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    at = seen["at"]
    nodes = target_nodes(net)
    twin = {
        "cfg": cfg, "net": net, "H": hold, "circ": circ, "parked": parked,
        "starved": np.asarray(h.starved, dtype=float),
        "flow": np.asarray(h.total_volume, dtype=float),
        "issued": np.asarray(h.issuance, dtype=float),
        "wage_paid": np.asarray(h.wage_paid, dtype=float),
        "sig": seen["sig"], "below_close": seen["below_close"],
        "inflow_window": seen["inflow_window"], "at": at,
        "books": seen["books"], "rng": seen["rng"],
        "nodes": nodes, "layers": layers_of(net),
        "tail_mean": hold[-TAIL:].mean(axis=0),
        "down": {}, "up": {}, "jitter": {},
    }
    for kind, info in nodes.items():
        node = info["node"]
        twin["down"][kind] = step_groups(steps_from(at["adjacency"], node))
        twin["up"][kind] = step_groups(steps_from(at["adjacency"], node, True))
        twin["jitter"][kind] = share_jitter(hold[-TAIL:, node], circ[-TAIL:])
    return twin


# ---------------------------------------------------------------------------
# Readings. Objects first; every state is printed beside the numbers it came
# from, and a state that is not a reading says so.
# ---------------------------------------------------------------------------

def _num(x):
    """A finite float, or None."""
    if x is None:
        return None
    x = float(x)
    return x if np.isfinite(x) else None


def shares(held_target, held_all, parked_all) -> tuple:
    """The target's balance over the claims in the trading accounts, and over
    all claims, parked ones included. Two readings and never one ratio: a
    fine comes out of the first denominator, and the parked stock in the
    second neither trades nor is fined."""
    held_target = np.asarray(held_target, dtype=float)
    held_all = np.asarray(held_all, dtype=float)
    parked_all = np.asarray(parked_all, dtype=float)
    return held_target / held_all, held_target / (held_all + parked_all)


def share_jitter(target_tail: np.ndarray, circ_tail: np.ndarray):
    """How far the twin's share of the trading accounts wanders from round to
    round over the tail: the spread of its log about a straight line, so a
    twin that is running down is not read as noisy. None where the share
    touches zero."""
    s = np.asarray(target_tail, dtype=float) / np.asarray(circ_tail, dtype=float)
    if not np.isfinite(s).all() or (s <= 0.0).any():
        return None
    x = np.arange(s.size, dtype=float)
    logs = np.log(s)
    slope, level = np.polyfit(x, logs, 1)
    return float(np.std(logs - (level + slope * x), ddof=2))


def log_slope(path: np.ndarray):
    """The slope of the log of a positive path, per round. None otherwise."""
    p = np.asarray(path, dtype=float)
    if not np.isfinite(p).all() or (p <= 0.0).any():
        return None
    return float(np.polyfit(np.arange(p.size, dtype=float), np.log(p), 1)[0])


#: The rounds run after the penalty: the unit "still closing" is read in.
SPAN = ROUNDS - FIRST

TAIL_STATES: tuple[tuple[str, str], ...] = (
    ("inside", "the tail's mean deviation is inside the twin's band: the "
     "target's share is back"),
    ("outside, closing", "outside the band, and shrinking between the last "
     "two windows of %d rounds at a pace that would bring it inside within "
     "another %d rounds, the span already run after the penalty: not settled "
     "inside this window, and no reading of where it settles" % (TAIL, SPAN)),
    ("outside, settled", "outside the band, and not shrinking at that pace: "
     "the share has settled off its twin's"),
    ("no band", "the twin's share touches zero in the tail, so there is no "
     "band: no reading"))


def rounds_to_band(tail, prev, band):
    """At the pace of the last two windows, how many more rounds until the
    deviation is inside the band: zero if it already is, None if it is not
    shrinking or has changed sides. A geometric pace, which is what a linear
    mode that has not finished mixing follows."""
    if band is None or tail is None or prev is None:
        return None
    a, b = abs(tail), abs(prev)
    if a <= band:
        return 0.0
    if tail * prev <= 0.0 or a >= b:
        return None
    rate = (a / b) ** (1.0 / TAIL)
    return float(np.log(band / a) / np.log(rate))


def tail_state(tail, prev, band) -> str:
    if band is None or tail is None or prev is None:
        return "no band"
    if abs(tail) <= band:
        return "inside"
    more = rounds_to_band(tail, prev, band)
    return ("outside, closing" if more is not None and more <= SPAN
            else "outside, settled")


PERMANENCE_STATES: tuple[tuple[str, str], ...] = (
    ("kept", "first round and tail both outside the band on the same side: "
     "the ratio is printed; near 1 none of it has gone, above 1 it has "
     "widened"),
    ("gone", "first round outside the band and tail inside: the ratio is "
     "printed, and it is zero to within the band"),
    ("reversed", "first round and tail outside the band on opposite sides: "
     "the ratio is negative, and both numbers are printed"),
    ("late", "first round inside the band and tail outside: the effect "
     "arrives after the first round, the ratio has no denominator and is not "
     "formed; the tail stands alone"),
    ("nothing", "first round and tail both inside the band: nothing here to "
     "be kept or lost, the ratio is not formed. An arm that was never "
     "applied (a cap that never bit, a cut of no edge) is this state too, "
     "and is told apart by its own columns"),
    ("no band", "no band: no reading"))


def permanence(early, tail, band) -> tuple:
    """The tail's deviation over the first round's, and the state that says
    whether that ratio means anything."""
    if band is None or early is None or tail is None:
        return None, "no band"
    big_early, big_tail = abs(early) > band, abs(tail) > band
    if not big_early:
        return None, ("late" if big_tail else "nothing")
    ratio = tail / early
    if not big_tail:
        return ratio, "gone"
    return ratio, ("kept" if ratio > 0.0 else "reversed")


CAP_STATES: tuple[tuple[str, str], ...] = (
    ("above its cap to the end", "the target closed above the level in every "
     "one of the last %d rounds with its column shut: claims that arrive "
     "without an edge keep it there, the cap has no routed inflow left to "
     "turn away, and this cell is not a reading of the cap" % TAIL),
    ("biting to the end", "the cap turned inflow away in every one of the "
     "last %d rounds" % TAIL),
    ("biting on and off", "it turned inflow away in some of the last %d "
     "rounds and not in others" % TAIL),
    ("let go", "it bit, and not once in the last %d rounds: the target fell "
     "below its cap by itself" % TAIL),
    ("never bit", "the target never reached the cap: nothing was done, and "
     "this cell is not read"))


def cap_state(bites: int, bites_tail: int, over_tail: int = 0) -> str:
    if over_tail == TAIL:
        return "above its cap to the end"
    if bites == 0:
        return "never bit"
    if bites_tail == 0:
        return "let go"
    return "biting to the end" if bites_tail == TAIL else "biting on and off"


def _spread(values: np.ndarray) -> dict:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return {"count": 0, "median": None, "q25": None, "q75": None,
                "min": None, "max": None}
    return {"count": int(v.size), "median": float(np.median(v)),
            "q25": float(np.quantile(v, 0.25)),
            "q75": float(np.quantile(v, 0.75)),
            "min": float(v.min()), "max": float(v.max())}


def _by(values: np.ndarray, ok: np.ndarray, labels: np.ndarray,
        names: tuple) -> dict:
    out = {}
    for name in names:
        m = ok & (labels == name)
        out[name] = float(np.median(values[m])) if m.any() else None
    return out


def incidence(twin: dict, hold: np.ndarray, kind: str) -> dict:
    """Who carries it: every node's balance against its twin's, over the tail
    and at a few rounds after the penalty, by layer and by steps down and up
    the graph from the target. The target is its own row elsewhere and is in
    none of the groups."""
    node = twin["nodes"][kind]["node"]
    not_target = np.ones(hold.shape[1], dtype=bool)
    not_target[node] = False
    ok = twin["tail_mean"] > EPS_HOLD
    ratio = np.full(hold.shape[1], np.nan)
    ratio[ok] = hold[-TAIL:].mean(axis=0)[ok] / twin["tail_mean"][ok]
    out = {
        "tail_all": _spread(ratio[ok]),
        "tail_layer": _by(ratio, ok & not_target, twin["layers"], LAYERS),
        "tail_down": _by(ratio, ok & not_target, twin["down"][kind], STEP_GROUPS),
        "tail_up": _by(ratio, ok & not_target, twin["up"][kind], STEP_GROUPS),
        "at": {},
    }
    for n_after in INCIDENCE_N:
        idx = PENALTY_ROUND + n_after
        base = twin["H"][idx]
        live = base > EPS_HOLD
        rel = np.full(hold.shape[1], np.nan)
        rel[live] = hold[idx][live] / base[live] - 1.0
        out["at"][str(n_after)] = {
            "layer": _by(rel, live & not_target, twin["layers"], LAYERS),
            "down": _by(rel, live & not_target, twin["down"][kind], STEP_GROUPS),
            "up": _by(rel, live & not_target, twin["up"][kind], STEP_GROUPS),
        }
    return out


def _where(mask: np.ndarray, twin: dict, kind: str) -> dict:
    """A set of nodes by where they sit from the target: the target itself,
    one step down from it, further down, anywhere else."""
    down = twin["down"][kind]
    return {"target": int((mask & (down == "target")).sum()),
            "down_1": int((mask & (down == "1")).sum()),
            "down_further": int((mask & ((down == "2") | (down == "3+"))).sum()),
            "elsewhere": int((mask & (down == "none")).sum())}


TRIGGERS: tuple[tuple[str, str], ...] = (
    ("block", "%d or more nodes more below the floor than the twin in some "
     "round" % BLOCK),
    ("target", "the target itself went below the floor in a round its twin "
     "did not"),
    ("one step down", "a node the target pays did"),
    ("elsewhere", "some other node did"),
    ("none", "no node was below the floor in a round its twin was not"))


def trigger(where: dict, peak: int) -> str:
    if peak >= BLOCK:
        return "block"
    if where["target"]:
        return "target"
    if where["down_1"]:
        return "one step down"
    if where["down_further"] or where["elsewhere"]:
        return "elsewhere"
    return "none"


def read_arm(twin: dict, base: dict, kind: str, arm: dict, net: Network,
             seen: dict) -> dict:
    """One penalised run against its twin. ``kind`` is the target's."""
    info = twin["nodes"][kind]
    node = info["node"]
    h = net._history
    hold = np.asarray(h.holdings, dtype=float)
    circ = hold.sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    at = twin["at"]
    held149 = float(at["holdings"][node])
    circ149 = float(at["holdings"].sum())
    s_c, s_t = shares(hold[:, node], circ, parked)
    b_c, b_t = shares(twin["H"][:, node], twin["circ"], twin["parked"])
    with np.errstate(divide="ignore", invalid="ignore"):
        dev = s_c / b_c - 1.0
        dev_total = s_t / b_t - 1.0
    jitter = twin["jitter"][kind]
    band = None if jitter is None else FLOOR_MULTIPLE * jitter
    early = _num(dev[FIRST])
    tail = _num(dev[-TAIL:].mean())
    prev = _num(dev[-2 * TAIL:-TAIL].mean())
    after = dev[FIRST:]
    peak_i = int(np.nanargmax(np.abs(after))) if np.isfinite(after).any() else 0
    peak = _num(after[peak_i])
    ratio, perm_state = permanence(early, tail, band)
    # The switches, with the authority's own added: whether it issued.
    switch = seen["switch"].copy()
    issued = np.asarray(h.issuance, dtype=float)
    switch[:, 3] = (issued[FIRST:] > 0.0) != (twin["issued"][FIRST:] > 0.0)
    rounds_off = np.flatnonzero(switch.any(axis=1))
    first_switch = None
    first_switch_n = None
    if rounds_off.size:
        i = int(rounds_off[0])
        first_switch = " + ".join(s for s, on in zip(SWITCHES, switch[i]) if on)
        first_switch_n = i + 1
    bd = np.asarray(h.starved, dtype=float) - twin["starved"]
    bd_after = bd[FIRST:]
    close_extra = seen["below_close"] & ~twin["below_close"]
    where_ever = _where(seen["ever_extra"], twin, kind)
    flow = np.asarray(h.total_volume, dtype=float)
    twin_flow_tail = float(twin["flow"][-TAIL:].mean())
    twin_circ_tail = float(twin["circ"][-TAIL:].mean())
    extra_issued = float(issued[FIRST:].sum() - twin["issued"][FIRST:].sum())
    row = dict(base)
    row.update({
        "target": kind, "node": node, "arm": arm_label(arm),
        "kind": arm["kind"], "size": arm["size"],
        "held_at_penalty": held149, "circulating_at_penalty": circ149,
        "share_at_penalty": held149 / circ149,
        "share_of_all_claims_at_penalty": held149 / float(at["total"]),
        "inflow_per_round": float(twin["inflow_window"][:, node].mean()),
        "books_close": bool(seen["books"]),
        "same_draws_as_twin": seen["rng"] == twin["rng"],
        "band": _num(band),
        "first_round": early, "tail": tail, "tail_before": prev,
        "peak": peak, "peak_n": peak_i + 1,
        "tail_over_peak": (_num(tail / peak) if tail is not None and peak
                           else None),
        "permanence": _num(ratio), "permanence_state": perm_state,
        # The same ratio wherever the first round is not zero to rounding,
        # band or no band: the paired difference carries no noise of its own.
        "permanence_unbanded": (
            _num(tail / early) if tail is not None and early is not None
            and abs(early) > PROPORTIONAL_TOL else None),
        "tail_state": tail_state(tail, prev, band),
        "rounds_to_band": _num(rounds_to_band(tail, prev, band)),
        "tail_on_all_claims": _num(dev_total[-TAIL:].mean()),
        "deviation_at": {str(k): _num(dev[PENALTY_ROUND + k])
                         for k in HORIZON_N},
        "first_switch": first_switch, "first_switch_n": first_switch_n,
        "switch_rounds": int(rounds_off.size),
        "switch_in_last_round": bool(switch[-1].any()),
        "switches_as_twin": not bool(rounds_off.size),
        "below_diff_at": {str(k): int(bd[PENALTY_ROUND + k])
                          for k in INCIDENCE_N},
        "below_diff_close": int(seen["below_close"].sum()
                                - twin["below_close"].sum()),
        "below_diff_peak": int(bd_after.max()),
        "below_diff_peak_n": int(np.argmax(bd_after)) + 1,
        "rounds_block_under": int((bd_after >= BLOCK).sum()),
        "flip": flip(int(seen["below_close"].sum()
                         - twin["below_close"].sum())),
        "extra_below_ever": where_ever,
        "extra_below_close": _where(close_extra, twin, kind),
        "fewer_below_ever": int(seen["ever_fewer"].sum()),
        "trigger": trigger(where_ever, seen["peak_extra"]),
        "flow_tail_ratio": (_num(flow[-TAIL:].mean() / twin_flow_tail)
                            if twin_flow_tail > 0 else None),
        "circulating_tail_ratio": (_num(circ[-TAIL:].mean() / twin_circ_tail)
                                   if twin_circ_tail > 0 else None),
        "extra_issued_after": extra_issued,
        "log_slope_tail": log_slope(hold[-TAIL:, node]),
        "twin_log_slope_tail": log_slope(twin["H"][-TAIL:, node]),
    })
    if arm["kind"] == "fine":
        taken = float(sum(seen["takes"]))
        first = float(seen["takes"][0]) if seen["takes"] else 0.0
        row.update({
            "mode": arm["mode"], "sink": arm["sink"],
            "asked": float(seen["asked"]), "taken": taken,
            "shortfall": float(seen.get("shortfall", 0.0)
                               + (seen["remaining"]
                                  if arm["mode"] == "garnish" else 0.0)),
            "takes": int(len(seen["takes"])),
            "rounds_to_collect": (
                int(seen["take_rounds"][-1] - PENALTY_ROUND + 1)
                if seen["takes"] else 0),
            "first_take": first,
            "first_take_ok": seen["first_take_ok"],
            "ledger_close": seen["ledger"],
            "fine_over_circulating": taken / circ149,
            "fine_in_rounds_of_inflow": (
                taken / row["inflow_per_round"]
                if row["inflow_per_round"] > 0 else None),
            # The share ratio at the yield itself, before any round has run.
            "impact": (_num(((held149 - first) / (circ149 - first))
                            / (held149 / circ149) - 1.0)
                       if circ149 > first else None),
            "extra_issued_share_of_fine": (_num(extra_issued / taken)
                                           if taken > 0 else None),
            "target_loss_over_fine_tail": (
                _num(-(hold[-TAIL:, node].mean()
                       - twin["tail_mean"][node]) / taken)
                if taken > 0 else None),
            "uniform_prediction": 1.0 - taken / circ149,
            "incidence": incidence(twin, hold, kind),
        })
    elif arm["kind"] == "cap":
        div = net.cap_diverted_to
        total = float(div.sum())
        up = twin["up"][kind]
        row.update({
            "cap_level": float(seen["cap_level"]),
            "held_close": float(hold[-1, node]),
            "bites": int(seen["bites"]), "first_bite_n": seen["first_bite"],
            "last_bite_n": seen["last_bite"],
            "bites_tail": int(seen["bites_tail"]),
            "blocked_total": float(seen["blocked_total"]),
            "blocked_share_of_inflow_tail": (
                _num(seen["blocked_tail"] / seen["raw_tail"])
                if seen["raw_tail"] > 0 else None),
            "diverted_to_layer": {
                L: (float(div[twin["layers"] == L].sum() / total)
                    if total > 0 else None) for L in LAYERS},
            "diverted_to_payers_of_target": (
                float(div[up == "1"].sum() / total) if total > 0 else None),
            "over_cap_closes": int(seen["over_cap_closes"]),
            "over_cap_max": float(seen["over_cap_max"]),
            "cap_guard": bool(seen["guard"]),
            "over_cap_closes_tail": int(seen["over_cap_tail"]),
            "cap_state": cap_state(seen["bites"], seen["bites_tail"],
                                   seen["over_cap_tail"]),
        })
    else:
        ch = seen["chosen"]
        lay = twin["layers"]
        ok = twin["tail_mean"] > EPS_HOLD
        ratio_tail = np.full(hold.shape[1], np.nan)
        ratio_tail[ok] = hold[-TAIL:].mean(axis=0)[ok] / twin["tail_mean"][ok]
        route149 = at["route"]
        others = np.flatnonzero((route149[:, node] if arm["side"] == "in"
                                 else route149[node]) > 0.0)
        kept = np.setdiff1d(others, ch if ch is not None else [])
        row.update({
            "side": arm["side"], "pick": arm["pick"],
            "restore": arm.get("restore"),
            "edges": seen["edges"], "cut": seen["cut"],
            "edges_after": seen["edges_after"],
            "adjacency_edges": seen["adjacency_edges"],
            "edge_share": (seen["cut"] / seen["edges"]
                           if seen["edges"] else None),
            "flow_share": (seen["flow_cut"] / seen["flow_total"]
                           if seen["flow_total"] > 0 else None),
            "cut_by_layer": {L: (int((lay[ch] == L).sum())
                                 if ch is not None else 0) for L in LAYERS},
            "residual_flow_next_round": _num(seen.get("residual_flow")),
            "wage_paid_next_round_as_twin": bool(
                np.asarray(h.wage_paid, dtype=float)[FIRST]
                == twin["wage_paid"][FIRST]),
            "restored_exactly": seen["restored"],
            # Who is at the other end: the nodes whose edge was cut, and the
            # ones whose edge was kept, each against its twin over the tail.
            "other_end_cut_tail": (
                _num(np.nanmedian(ratio_tail[ch]))
                if ch is not None and np.isfinite(ratio_tail[ch]).any()
                else None),
            "other_end_kept_tail": (
                _num(np.nanmedian(ratio_tail[kept]))
                if kept.size and np.isfinite(ratio_tail[kept]).any()
                else None),
        })
    row["_dev"] = dev[FIRST:].copy()
    row["_effect"] = hold[FIRST:] - twin["H"][FIRST:]
    return row


def proportionality(rows: list) -> None:
    """Among one target's one-off fines that leave the graph: the effect on
    every node in every round, per unit taken, against the smallest fine's.
    Where every switch stayed as the twin's the two have to agree to rounding.
    Written into the rows."""
    fines = sorted((x for x in rows if x["kind"] == "fine"
                    and x["mode"] == "once" and x["sink"] == "destroy"),
                   key=lambda x: x["size"])
    if not fines:
        return
    ref = fines[0]
    unit = ref["_effect"] / ref["taken"] if ref["taken"] > 0 else None
    for x in fines:
        x["proportional_reference"] = ref["size"]
        if unit is None or x["taken"] <= 0:
            x["proportional_gap"] = None
        else:
            x["proportional_gap"] = float(
                np.abs(x["_effect"] / x["taken"] - unit).max())
        x["reference_switches_as_twin"] = ref["switches_as_twin"]


def one_base(base: dict, arms=None, faults=None) -> list:
    """One configuration and seed: the twin, then every arm on both targets.
    Returns the twin's row and one row per arm, private arrays included."""
    cfg = base_config(base)
    twin = make_twin(cfg)
    rows = []
    trow = dict(base)
    trow.update({
        "arm": "twin", "kind": "twin",
        "books_close": bool(twin["books"]),
        "below_close": int(twin["below_close"].sum()),
        "circulating_at_penalty": float(twin["at"]["holdings"].sum()),
        "parked_at_penalty": float(twin["at"]["parked"].sum()),
        "circulating_close": float(twin["circ"][-1]),
        "issued_after": float(twin["issued"][FIRST:].sum()),
        "payers_short_at_penalty": int(twin["sig"]["short"][0].sum()),
        "targets": {},
    })
    lay = twin["layers"]
    for kind in TARGETS:
        info = dict(twin["nodes"][kind])
        node = info["node"]
        at = twin["at"]
        inflow = at["spent"] * at["route"][:, node]
        payers = inflow > 0.0
        ordered = np.sort(inflow[payers])[::-1]
        info.update({
            "layer": str(lay[node]),
            "held_at_penalty": float(at["holdings"][node]),
            "share_at_penalty": float(at["holdings"][node]
                                      / at["holdings"].sum()),
            "inflow_per_round": float(twin["inflow_window"][:, node].mean()),
            "jitter": twin["jitter"][kind],
            "routing_in_edges": int((at["route"][:, node] > 0).sum()),
            "routing_out_edges": int((at["route"][node] > 0).sum()),
            "in_edges_carrying_flow": int(payers.sum()),
            "inflow_by_payer_layer": {
                L: float(inflow[lay == L].sum()) for L in LAYERS},
            "top_tenth_of_in_edges_share_of_inflow": (
                float(ordered[:max(1, int(round(0.1 * ordered.size)))].sum()
                      / ordered.sum()) if ordered.size else None),
            "on_payroll_list": bool(node in set(
                np.asarray(twin["net"]._wage_payers).tolist())),
            "is_issuance_entry": bool(node == twin["net"].injection_node),
            "log_slope_tail": log_slope(twin["H"][-TAIL:, node]),
            "holds_by_layer_at_penalty": {
                L: float(at["holdings"][lay == L].sum()) for L in LAYERS},
        })
        trow["targets"][kind] = info
    trow["_flow"] = twin["flow"]
    rows.append(trow)
    for kind in TARGETS:
        node = twin["nodes"][kind]["node"]
        mine = []
        for arm in (arms_for(base) if arms is None else arms):
            net, seen = drive(cfg, node, arm, twin,
                              None if faults is None else faults.get(arm_label(arm)))
            mine.append(read_arm(twin, base, kind, arm, net, seen))
        proportionality(mine)
        for x in mine:
            x.pop("_effect", None)
        rows += mine
    return rows


# ---------------------------------------------------------------------------
# Running the grid.
# ---------------------------------------------------------------------------

_AUTH_ORDER: tuple[str, ...] = ("endogenous", "none", "fixed")


def _base_sort(b: dict) -> tuple:
    return (0 if b["block"] == "main" else 1, b["need"],
            STRESSES.index(b["stress"]), b["elasticity"],
            _AUTH_ORDER.index(b["authority"]), b.get("seed", 0))


def _row_sort(x: dict) -> tuple:
    return _base_sort(x) + (
        TARGETS.index(x["target"]) if "target" in x else -1,
        ARM_ORDER.index(x["arm"]) if x["arm"] in ARM_ORDER else -1)


def run_bases(bases: list, workers: int) -> list:
    if workers <= 1:
        parts = [one_base(b) for b in bases]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parts = list(pool.map(one_base, bases, chunksize=1))
    return sorted((x for part in parts for x in part), key=_row_sort)


def _arms(rows: list) -> list:
    return [x for x in rows if x["kind"] != "twin"]


def _cell(x: dict) -> tuple:
    """A configuration and seed: what one twin serves."""
    return (x["block"], x["need"], x["stress"], x["elasticity"],
            x["authority"], x["seed"])


def _gkey(x: dict) -> tuple:
    return (x["block"], x["need"], x["stress"], x["elasticity"],
            x["authority"], x["target"], x["arm"])


def _median(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.median(vals)) if vals else None


def _range(values) -> str:
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not vals:
        return "none"
    return "%.4g to %.4g" % (min(vals), max(vals))


def _count(items) -> dict:
    out = {}
    for it in items:
        key = "none" if it is None else str(it)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _g(x) -> str:
    return "-" if x is None else "%.4g" % x


def _col_median(a: np.ndarray) -> list:
    out = []
    for col in np.asarray(a, dtype=float).T:
        f = col[np.isfinite(col)]
        out.append(float(np.median(f)) if f.size else None)
    return out


def burden(x: dict) -> dict:
    """A fine row's incidence by layer as a multiple of pro rata: the fall of
    the layer's median balance over the fall of the claims in the trading
    accounts. 1 is the layer carrying its share, 0 none of it."""
    f = x["fine_over_circulating"]
    tail = x["incidence"]["tail_layer"]
    return {L: ((1.0 - tail[L]) / f
                if tail.get(L) is not None and f > 0 else None)
            for L in LAYERS}


def groups(rows: list) -> list:
    """Every arm on one target of one configuration, over its seeds. Never
    pooled across configurations."""
    by = {}
    for x in _arms(rows):
        by.setdefault(_gkey(x), []).append(x)

    def order(g: tuple) -> tuple:
        return (_base_sort({"block": g[0], "need": g[1], "stress": g[2],
                            "elasticity": g[3], "authority": g[4]}),
                TARGETS.index(g[5]), ARM_ORDER.index(g[6]))

    out = []
    for g in sorted(by, key=order):
        cs = sorted(by[g], key=lambda x: x["seed"])
        first = cs[0]
        d = {
            "block": g[0], "need": g[1], "stress": g[2], "elasticity": g[3],
            "authority": g[4], "target": g[5], "arm": g[6],
            "kind": first["kind"], "size": first["size"],
            "seeds": [x["seed"] for x in cs],
            "band_median": _median(x["band"] for x in cs),
            "first_round_median": _median(x["first_round"] for x in cs),
            "tail_median": _median(x["tail"] for x in cs),
            "tail": [x["tail"] for x in cs],
            "peak_median": _median(x["peak"] for x in cs),
            "tail_over_peak_median": _median(x["tail_over_peak"] for x in cs),
            "permanence_median": _median(x["permanence"] for x in cs),
            "permanence_unbanded_median": _median(
                x["permanence_unbanded"] for x in cs),
            "permanence_states": _count(x["permanence_state"] for x in cs),
            "tail_states": _count(x["tail_state"] for x in cs),
            "first_switch": _count(x["first_switch"] for x in cs),
            "switches_as_twin": sum(1 for x in cs if x["switches_as_twin"]),
            "triggers": _count(x["trigger"] for x in cs),
            "flips": _count(x["flip"] for x in cs),
            "below_diff_close": [x["below_diff_close"] for x in cs],
            "below_diff_peak": [x["below_diff_peak"] for x in cs],
            "flow_tail_ratio_median": _median(x["flow_tail_ratio"] for x in cs),
            "median_deviation_path": _col_median(
                np.array([x["_dev"] for x in cs])),
        }
        if first["kind"] == "fine":
            bur = [burden(x) for x in cs]
            d.update({
                "mode": first["mode"], "sink": first["sink"],
                "fine_over_circulating_median": _median(
                    x["fine_over_circulating"] for x in cs),
                "fine_in_rounds_of_inflow_median": _median(
                    x["fine_in_rounds_of_inflow"] for x in cs),
                "rounds_to_collect": [x["rounds_to_collect"] for x in cs],
                "shortfall_max": max(x["shortfall"] for x in cs),
                "impact_median": _median(x["impact"] for x in cs),
                "target_loss_over_fine_median": _median(
                    x["target_loss_over_fine_tail"] for x in cs),
                "share_at_penalty_median": _median(
                    x["share_at_penalty"] for x in cs),
                "uniform_prediction_median": _median(
                    x["uniform_prediction"] for x in cs),
                "tail_by_layer_median": {
                    L: _median(x["incidence"]["tail_layer"].get(L)
                               for x in cs) for L in LAYERS},
                "burden_by_layer_median": {
                    L: _median(b[L] for b in bur) for L in LAYERS},
                "extra_issued_share_of_fine_median": _median(
                    x["extra_issued_share_of_fine"] for x in cs),
            })
            gaps = [x.get("proportional_gap") for x in cs]
            if any(v is not None for v in gaps):
                d["proportional_gap_max"] = max(v for v in gaps if v is not None)
        elif first["kind"] == "cap":
            d.update({
                "cap_states": _count(x["cap_state"] for x in cs),
                "bites": [x["bites"] for x in cs],
                "bites_tail": [x["bites_tail"] for x in cs],
                "first_bite_n": [x["first_bite_n"] for x in cs],
                "last_bite_n": [x["last_bite_n"] for x in cs],
                "blocked_share_of_inflow_tail_median": _median(
                    x["blocked_share_of_inflow_tail"] for x in cs),
                "diverted_to_layer_median": {
                    L: _median(x["diverted_to_layer"][L] for x in cs)
                    for L in LAYERS},
                "diverted_to_payers_of_target_median": _median(
                    x["diverted_to_payers_of_target"] for x in cs),
                "over_cap_closes": [x["over_cap_closes"] for x in cs],
                "log_slope_tail_median": _median(
                    x["log_slope_tail"] for x in cs),
                "twin_log_slope_tail_median": _median(
                    x["twin_log_slope_tail"] for x in cs),
            })
        else:
            d.update({
                "side": first["side"], "pick": first["pick"],
                "restore": first["restore"],
                "edges": [x["edges"] for x in cs],
                "cut": [x["cut"] for x in cs],
                "edge_share_median": _median(x["edge_share"] for x in cs),
                "flow_share_median": _median(x["flow_share"] for x in cs),
                "flow_share": [x["flow_share"] for x in cs],
                "other_end_cut_tail_median": _median(
                    x["other_end_cut_tail"] for x in cs),
                "other_end_kept_tail_median": _median(
                    x["other_end_kept_tail"] for x in cs),
            })
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Readings across arms.
# ---------------------------------------------------------------------------

LINEAR_STATES: tuple[tuple[str, str], ...] = (
    ("back", "no switch differs from the twin's in any round and the "
     "target's share is back inside the band: on this cell the fine is a fee"),
    ("closing", "no switch differs, the share is outside the band and still "
     "closing: a linear mode that has not finished mixing inside this window, "
     "which says nothing either way about a lasting effect"),
    ("settled off", "no switch differs and the share has settled outside the "
     "band: the same affine map in both runs, so this is its fixed nominal "
     "amounts (the wage bill, the floor) weighing differently on a smaller "
     "claim stock, in proportion to the fine"),
    ("switch", "a switch differs from the twin's in some round: outside the "
     "linear segment, and read in A54-4"),
    ("no band", "no band: no reading"))

_LINEAR_FROM_TAIL = {"inside": "back", "outside, closing": "closing",
                     "outside, settled": "settled off", "no band": "no band"}


def linear_state(x: dict):
    if not x["switches_as_twin"]:
        return "switch"
    return _LINEAR_FROM_TAIL.get(x["tail_state"])


def thresholds(rows: list) -> list:
    """Per configuration, seed, target and mode, among fines that leave the
    graph: the smallest size whose tail is outside the band, the smallest at
    which a switch differs from the twin's, and the smallest at which a block
    goes below the floor, each with what that fine was in the target's own
    terms."""
    by = {}
    for x in _arms(rows):
        if (x["kind"] == "fine" and x["sink"] == "destroy"
                and x["block"] == "main"):
            by.setdefault(_cell(x) + (x["target"], x["mode"]), []).append(x)

    def brief(x):
        if x is None:
            return None
        return {"size": x["size"], "tail": x["tail"],
                "tail_state": x["tail_state"],
                "fine_over_circulating": x["fine_over_circulating"],
                "fine_in_rounds_of_inflow": x["fine_in_rounds_of_inflow"],
                "first_switch": x["first_switch"],
                "first_switch_n": x["first_switch_n"],
                "trigger": x["trigger"],
                "below_diff_peak": x["below_diff_peak"],
                "below_diff_close": x["below_diff_close"]}

    out = []
    for key in sorted(by, key=lambda k: (_base_sort(dict(zip(
            ("block", "need", "stress", "elasticity", "authority", "seed"),
            k[:6]))), TARGETS.index(k[6]), k[7])):
        xs = sorted(by[key], key=lambda x: x["size"])
        out.append({
            "block": key[0], "need": key[1], "stress": key[2],
            "elasticity": key[3], "authority": key[4], "seed": key[5],
            "target": key[6], "mode": key[7],
            "sizes": [x["size"] for x in xs],
            "band": xs[0]["band"],
            "outside_band": brief(next(
                (x for x in xs if x["tail_state"].startswith("outside")), None)),
            "switch": brief(next(
                (x for x in xs if not x["switches_as_twin"]), None)),
            "block_under": brief(next(
                (x for x in xs if x["trigger"] == "block"), None)),
            "block_under_at_close": brief(next(
                (x for x in xs if x["flip"] == "block under"), None)),
        })
    return out


def _rank(v: np.ndarray) -> np.ndarray:
    order = np.argsort(v, kind="mergesort")
    rk = np.empty(v.size)
    rk[order] = np.arange(1, v.size + 1)
    _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    return (np.bincount(inv, weights=rk) / cnt)[inv]


def spearman(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.size < 3:
        return None
    ra, rb = _rank(a), _rank(b)
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    return float((ra * rb).sum() / den) if den > 0 else None


PAIR_STATES: tuple[tuple[str, str], ...] = (
    ("flow pick loses more", "the pick from the largest flow down costs the "
     "target more share than the random pick of as many edges, by more than "
     "the band"),
    ("inside the band", "the two picks cost the same to within the band"),
    ("random pick loses more", "the random pick costs more, by more than the "
     "band"),
    ("no band", "no band: no reading"))


def cut_readings(rows: list) -> tuple:
    """Cuts that are not put back. Pairs: the two picks at the same share on
    the same side of the same target. Sets: all six cuts on one side of one
    target, for the rank correlations of the share lost with the share of the
    flow cut and with the share of the edges cut."""
    cuts = [x for x in _arms(rows) if x["kind"] == "cut" and not x["restore"]]
    idx = {(_cell(x), x["target"], x["side"], x["size"], x["pick"]): x
           for x in cuts}
    pairs, sets = [], []
    for (cell, target, side, size, pick), x in sorted(
            idx.items(), key=lambda kv: (_row_sort(kv[1]))):
        if pick != "flow":
            continue
        y = idx.get((cell, target, side, size, "random"))
        if y is None:
            continue
        band = x["band"]
        if band is None or x["tail"] is None or y["tail"] is None:
            state, diff = "no band", None
        else:
            diff = (-x["tail"]) - (-y["tail"])
            state = ("flow pick loses more" if diff > band else
                     "random pick loses more" if diff < -band else
                     "inside the band")
        pairs.append({
            "block": cell[0], "need": cell[1], "stress": cell[2],
            "elasticity": cell[3], "authority": cell[4], "seed": cell[5],
            "target": target, "side": side, "size": size,
            "edges_cut": x["cut"],
            "flow_share_by_flow": x["flow_share"],
            "flow_share_at_random": y["flow_share"],
            "loss_by_flow": None if x["tail"] is None else -x["tail"],
            "loss_at_random": None if y["tail"] is None else -y["tail"],
            "difference": diff, "band": band, "state": state})
    by = {}
    for x in cuts:
        by.setdefault((_cell(x), x["target"], x["side"]), []).append(x)
    for (cell, target, side), xs in sorted(
            by.items(), key=lambda kv: _row_sort(kv[1][0])):
        ok = [x for x in xs if x["tail"] is not None
              and x["flow_share"] is not None and x["cut"] > 0]
        loss = [-x["tail"] for x in ok]
        sets.append({
            "block": cell[0], "need": cell[1], "stress": cell[2],
            "elasticity": cell[3], "authority": cell[4], "seed": cell[5],
            "target": target, "side": side, "cuts": len(ok),
            "rank_loss_with_flow_share": spearman(
                loss, [x["flow_share"] for x in ok]),
            "rank_loss_with_edge_share": spearman(
                loss, [x["edge_share"] for x in ok]),
            "loss_over_flow_share_median": _median(
                (-x["tail"]) / x["flow_share"] for x in ok
                if x["flow_share"] > 0),
        })
    return pairs, sets


def headline(rows: list) -> list:
    """Each arm on each target, by block, authority and strain, over floors,
    elasticities and seeds: a first look, and nothing a reading rests on."""
    by = {}
    for x in _arms(rows):
        by.setdefault((x["block"], x["target"], x["authority"], x["stress"],
                       x["arm"]), []).append(x)
    out = []
    for key in sorted(by, key=lambda k: (
            0 if k[0] == "main" else 1, TARGETS.index(k[1]),
            _AUTH_ORDER.index(k[2]), STRESSES.index(k[3]),
            ARM_ORDER.index(k[4]))):
        xs = by[key]
        out.append({
            "block": key[0], "target": key[1], "authority": key[2],
            "stress": key[3], "arm": key[4], "cells": len(xs),
            "first_round_median": _median(x["first_round"] for x in xs),
            "tail_median": _median(x["tail"] for x in xs),
            "permanence_unbanded_median": _median(
                x["permanence_unbanded"] for x in xs),
            "permanence_states": _count(x["permanence_state"] for x in xs),
            "blocks_under_at_close": sum(
                1 for x in xs if x["flip"] == "block under"),
            "blocks_under_in_some_round": sum(
                1 for x in xs if x["rounds_block_under"] > 0),
        })
    return out


# ---------------------------------------------------------------------------
# Criteria. A flag is computed from the rows it is about; ``--selftest`` feeds
# each one a wrong input and checks that it fails.
# ---------------------------------------------------------------------------

def _states(states: tuple) -> str:
    return "; ".join("%s = %s" % s for s in states)


def _names(states: tuple) -> set:
    return {s[0] for s in states}


A54_0 = "A54-0 the driver is the model, and its books close"


def criterion_a54_0(g, rows: list) -> Criterion:
    arms = _arms(rows)
    returned = [x for x in arms if x["kind"] == "fine" and x["sink"] == "return"]
    books = sum(1 for x in rows if x["books_close"])
    draws = sum(1 for x in arms if x["same_draws_as_twin"])
    ledger = sum(1 for x in returned if x["ledger_close"])
    rows_ok = (bool(rows) and books == len(rows) and draws == len(arms)
               and ledger == len(returned))
    part = (
        "In every run the claim total equals held plus parked at every yield, "
        "to %.0e of the opening stock: %d of %d. Every penalised run's "
        "generators end where its twin's end, so the two draw the same numbers "
        "and their difference is the penalty's: %d of %d. Where a fine is paid "
        "into the sovereign's pool it is booked as a receipt beside the bonds, "
        "and at every yield the pool equals receipts less everything passed "
        "down and the bonds outstanding equal receipts less fines: %d of %d. "
        "The round loop's own assertions did not fire: all %d runs completed."
        % (LEDGER_TOL, books, len(rows), draws, len(arms), ledger,
           len(returned), len(rows)))
    state_map = (
        "State map: the gate identical on every configuration and the three "
        "counts above complete -> PASS; anything else -> FAIL; no gate section "
        "-> not judged, and --run does not start.")
    if not g:
        return Criterion(A54_0, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + part + " " + state_map, evaluated=False)
    differ = g["differ"]
    head = (
        "With no penalty the class and the driver touch nothing: on %d "
        "configurations (the library default and every configuration of this "
        "grid at seed %d), %d history fields and the closing state (claim "
        "total, holdings, parked, below the floor, and where every generator "
        "got to) compared bit for bit against Network.run(); and every arm at "
        "size zero (%s) on both targets against that twin, %d runs: %d "
        "differ%s."
        % (len(g["configs"]), SEEDS[0], g["fields_compared"],
           ", ".join(g["zero_arms"]), g["runs"], len(differ),
           "" if not differ else ": " + "; ".join(
               "%s in %s" % (x["run"], x["fields"]) for x in differ[:5])))
    return Criterion(A54_0, "instrument", g["verdict"] == "pass" and rows_ok,
                     "%s %s Gate verdict: %s. %s" % (head, part, g["verdict"],
                                                    state_map))


def _expected_first_take(x: dict) -> float:
    if x["mode"] == "once":
        return x["asked"]
    if x["mode"] == "instalments":
        return x["asked"] / INSTALMENTS
    return min(x["asked"], x["held_at_penalty"])


#: The closes a collection can act at: from the penalty to the last but one.
_COLLECTING_CLOSES = ROUNDS - 1 - PENALTY_ROUND


def _fine_moved(x: dict) -> bool:
    want = _expected_first_take(x)
    if not (x["first_take_ok"]
            and abs(x["first_take"] - want) <= 1e-9 * max(1.0, want)):
        return False
    edge = 1e-9 * max(1.0, x["asked"])
    if abs(x["taken"] + x["shortfall"] - x["asked"]) > edge:
        return False
    if x["mode"] == "once":
        return x["takes"] == 1
    if x["mode"] == "instalments":
        return x["takes"] == INSTALMENTS
    # Collected until paid: either it was paid, or it was still collecting at
    # the last close it could act at.
    return x["shortfall"] <= edge or x["takes"] == _COLLECTING_CLOSES


def _cut_moved(x: dict) -> bool:
    if x["edges"] - x["edges_after"] != x["cut"]:
        return False
    if x["cut"] != int(round(x["size"] * x["edges"])):
        return False
    if x["cut"] == 0:
        return True
    if x["residual_flow_next_round"] != 0.0:
        return False
    if not x["wage_paid_next_round_as_twin"]:
        return False
    return bool(x["restored_exactly"]) if x["restore"] else True


def criterion_a54_1(rows: list) -> Criterion:
    arms = _arms(rows)
    fines = [x for x in arms if x["kind"] == "fine"]
    caps = [x for x in arms if x["kind"] == "cap"]
    cuts = [x for x in arms if x["kind"] == "cut"]
    fine_ok = sum(1 for x in fines if _fine_moved(x))
    cap_ok = sum(1 for x in caps if x["cap_guard"])
    cut_ok = sum(1 for x in cuts if _cut_moved(x))
    ok = (bool(fines) and bool(caps) and bool(cuts) and fine_ok == len(fines)
          and cap_ok == len(caps) and cut_ok == len(cuts))
    short = [x for x in fines if x["shortfall"] > 1e-12]
    over = [x for x in caps if x["over_cap_closes"] > 0]
    idle_caps = sum(1 for x in caps if x["bites"] == 0)
    idle_cuts = sum(1 for x in cuts if x["cut"] == 0)
    restored = [x for x in cuts if x["restore"] and x["cut"] > 0]
    wage_edges = sorted({x["adjacency_edges"] - x["edges"] for x in cuts
                         if x["side"] == "out" and x["target"] == "production"})
    return Criterion(
        "A54-1 each penalty moves what it says and nothing else (D28)",
        "instrument", ok,
        "Fines: the first amount taken is the amount due (the share of the "
        "balance, a tenth of it, or the multiple of inflow up to the balance) "
        "and the trading accounts and the claim total both fall by exactly "
        "it; what was taken and what was not add up to what was asked; a "
        "one-off is one take, instalments are %d, and a collection either "
        "ends paid or is still taking at the last close: %d of %d. %d fines "
        "could not collect in full (an instalment the "
        "balance did not cover, written off; or a multiple of inflow still "
        "owed at the end), largest shortfall %s. Caps: at no close does the "
        "target stand above its cap in a round in which it took any routed "
        "inflow: %d of %d. %d caps closed above the level in some round, "
        "%d closes in all, each with the column shut that round: claims "
        "that came without an edge (issuance, the pass-down) or the balance "
        "the target already had; largest excess %s. %d caps never bit and are "
        "not read. Cuts: the target's routing edges fall by exactly the "
        "number picked, which is the share of them rounded; next round the "
        "flow on the cut edges is exactly zero and the wage bill paid is the "
        "twin's to the bit: %d of %d. Only routing edges are candidates: the "
        "production target also pays wages along %s edges that are in the "
        "adjacency and not in the routing, and no cut touches them. %d cuts "
        "of a share that rounds to no edge did nothing and are not read. "
        "Edges put back restore the routing bit for bit: %d of %d. State "
        "map: all three counts complete -> PASS; any short -> FAIL, and the "
        "readings below cannot be read in those cells."
        % (INSTALMENTS, fine_ok, len(fines), len(short),
           _g(max((x["shortfall"] for x in short), default=None)),
           cap_ok, len(caps), len(over),
           sum(x["over_cap_closes"] for x in over),
           _g(max((x["over_cap_max"] for x in over), default=None)),
           idle_caps, cut_ok, len(cuts), wage_edges or "no", idle_cuts,
           sum(1 for x in restored if x["restored_exactly"]), len(restored)))


def _once(rows: list) -> list:
    return [x for x in _arms(rows) if x["kind"] == "fine"
            and x["mode"] == "once" and x["sink"] == "destroy"]


def criterion_a54_2a(rows: list) -> Criterion:
    name = ("A54-2a where no switch flips, a fine's effect is proportional "
            "to the fine")
    judged = [x for x in _once(rows) if x.get("proportional_gap") is not None
              and x["size"] != x["proportional_reference"]]
    stable = [x for x in judged if x["switches_as_twin"]
              and x["reference_switches_as_twin"]]
    moved = [x for x in judged if not (x["switches_as_twin"]
                                       and x["reference_switches_as_twin"])]
    bad = [x for x in stable if x["proportional_gap"] > PROPORTIONAL_TOL]
    apart = [x for x in moved if x["proportional_gap"] > PROPORTIONAL_TOL]
    text = (
        "The model has four switches on this carrier (%s). Where all four "
        "sit as the twin's in every round, both runs apply the same affine "
        "map, so the effect of a fine on every node in every round, per unit "
        "taken, cannot depend on its size. Read on the one-off fines that "
        "leave the graph, each against the smallest fine on the same target: "
        "%d cells with every switch as the twin's in both, largest gap %s "
        "against a tolerance of %.0e, %d above it. Beside them, %d cells "
        "where a switch flipped in one of the two: %d of those are apart by "
        "more than the tolerance, smallest gap among them %s. State map: no "
        "stable cell above the tolerance -> PASS, the four switches are all "
        "of this carrier's non-linearity; any above -> FAIL, a channel this "
        "stage has not named, and A54-2's reading does not stand; no stable "
        "cell -> not judged."
        % (SWITCH_TEXT, len(stable),
           _g(max((x["proportional_gap"] for x in stable), default=None)),
           PROPORTIONAL_TOL, len(bad), len(moved), len(apart),
           _g(min((x["proportional_gap"] for x in apart), default=None))))
    if not stable:
        return Criterion(name, "known_answer", False,
                         "Not evaluated: no cell with every switch as the "
                         "twin's. " + text, evaluated=False)
    return Criterion(name, "known_answer", not bad, text)


def criterion_a54_2(rows: list) -> Criterion:
    scoped = [x for x in _once(rows) if x["block"] == "main"
              and x["authority"] == "none"]
    names = _names(LINEAR_STATES)
    mapped = [x for x in scoped if linear_state(x) in names]
    whole = [x for x in mapped if linear_state(x) == "no band" or (
        x["tail"] is not None and x["target_loss_over_fine_tail"] is not None
        and x["incidence"]["tail_all"]["median"] is not None)]
    ok = bool(scoped) and len(whole) == len(scoped)
    lines = []
    for kind in TARGETS:
        xs = [x for x in mapped if x["target"] == kind]
        lin = [x for x in xs if linear_state(x) in ("back", "closing",
                                                    "settled off")]
        lines.append(
            "%s target: %s; where no switch flipped, the target's own lasting "
            "loss per unit taken, median %s (%s) beside its share of the "
            "trading accounts %s, and the tail of its share against the "
            "twin's %s (%s) with a band of %s"
            % (kind, _tally(linear_state(x) for x in xs),
               _g(_median(x["target_loss_over_fine_tail"] for x in lin)),
               _range(x["target_loss_over_fine_tail"] for x in lin),
               _g(_median(x["share_at_penalty"] for x in lin)),
               _g(_median(x["tail"] for x in lin)),
               _range(x["tail"] for x in lin),
               _g(_median(x["band"] for x in lin))))
    lay = []
    lin_all = [x for x in mapped if linear_state(x) != "switch"
               and linear_state(x) != "no band"]
    for e in ELASTICITIES:
        xs = [x for x in lin_all if x["elasticity"] == e]
        b = [burden(x) for x in xs]
        lay.append("elasticity %.1f: %s" % (e, ", ".join(
            "%s %s" % (L, _g(_median(v[L] for v in b)))
            for L in ("fin", "mid", "hhw"))))
    back = [x for x in _arms(rows) if x["kind"] == "fine"
            and x["sink"] == "return" and x["mode"] == "once"
            and x["authority"] == "none"]
    return Criterion(
        "A54-2 the linear segment: a fine where no switch flips",
        "own_reading", ok,
        "Printed with its state. Scope: one-off fines that leave the graph, "
        "authority off, the main block; %d cells, %d with a state from the "
        "map and their numbers whole. State map: %s. %s. Who carries it over "
        "the tail, where no switch flipped, as a multiple of pro rata (the "
        "fall of a layer's median balance over the fall of the claims in the "
        "trading accounts; 1 is its share): %s. Every node falling by the "
        "same share would read 1 in every layer. The same fine paid into the "
        "sovereign's pool and passed down again (%d cells): the median "
        "node's balance against its twin's over the tail %s (%s), and the "
        "target's share %s (%s). The flag: every cell in scope has a state "
        "from the map, and unless that state is 'no band' its tail, its "
        "lasting loss and its incidence are numbers -> PASS; a cell with "
        "none -> FAIL, reprint."
        % (len(scoped), len(whole), _states(LINEAR_STATES), "; ".join(lines),
           "; ".join(lay), len(back),
           _g(_median(x["incidence"]["tail_all"]["median"] for x in back)),
           _range(x["incidence"]["tail_all"]["median"] for x in back),
           _g(_median(x["tail"] for x in back)),
           _range(x["tail"] for x in back)))


def criterion_a54_3(rows: list) -> Criterion:
    fines = [x for x in _arms(rows) if x["kind"] == "fine"
             and x["sink"] == "destroy" and x["block"] == "main"]
    names = _names(TRIGGERS)
    whole = [x for x in fines if x["trigger"] in names
             and set(x["incidence"]["tail_layer"]) == set(LAYERS)
             and set(x["incidence"]["at"]) == {str(n) for n in INCIDENCE_N}]
    ok = bool(fines) and len(whole) == len(fines)
    first = []
    for kind in TARGETS:
        xs = [x for x in fines if x["target"] == kind and x["mode"] == "once"]
        at1 = [x["incidence"]["at"]["1"]["down"] for x in xs]
        at20 = [x["incidence"]["at"]["20"]["down"] for x in xs]
        first.append(
            "%s target, one-off, by steps down from it: after one round %s, "
            "after twenty %s" % (
                kind,
                ", ".join("%s %s" % (s, _g(_median(v[s] for v in at1)))
                          for s in STEP_GROUPS),
                ", ".join("%s %s" % (s, _g(_median(v[s] for v in at20)))
                          for s in STEP_GROUPS)))
    lay = []
    for auth in AUTHORITIES:
        for e in ELASTICITIES:
            xs = [x for x in fines if x["authority"] == auth
                  and x["elasticity"] == e and x["mode"] == "once"]
            b = [burden(x) for x in xs]
            lay.append("authority %s, elasticity %.1f: %s" % (auth, e, ", ".join(
                "%s %s" % (L, _g(_median(v[L] for v in b)))
                for L in ("fin", "mid", "hhw"))))
    trig = []
    for need in NEEDS:
        xs = [x for x in fines if x["need"] == need]
        trig.append("floor %.2f: %s" % (need, _tally(x["trigger"] for x in xs)))
    under = [x for x in fines if x["flip"] == "block under"]
    passing = [x for x in fines if x["rounds_block_under"] > 0
               and x["flip"] != "block under"]
    return Criterion(
        "A54-3 who carries a fine", "own_reading", ok,
        "Printed with its state. Fines that leave the graph, the main block, "
        "%d cells, %d with their incidence whole. The first round is forced "
        "(the fine cuts only what the target itself spends) and is printed, "
        "not read: each group's median balance against its twin's, %s. Over "
        "the tail, by layer, as a multiple of pro rata (one-off fines, median "
        "over cells): %s. Where the nodes that went below the floor in a "
        "round their twin did not are, by floor (state map: %s): %s. A block "
        "below the floor at the close: %d cells (by strain, authority and "
        "floor: %s). A block below in some round and back by the close: %d "
        "cells (%s). Cell by cell in the rows section. The flag: every cell "
        "carries its incidence by layer and by step at every horizon, and a "
        "trigger from the map -> PASS; any missing -> FAIL, reprint."
        % (len(fines), len(whole), "; ".join(first), "; ".join(lay),
           _states(TRIGGERS), "; ".join(trig), len(under),
           _tally("%s %s, floor %.2f" % (x["stress"], x["authority"],
                                         x["need"]) for x in under),
           len(passing),
           _tally("%s %s, floor %.2f" % (x["stress"], x["authority"],
                                         x["need"]) for x in passing)))


def criterion_a54_4(rows: list, thr: list) -> Criterion:
    want = {"once": len(FINE_SHARES), "instalments": len(FINE_SHARES),
            "garnish": len(GARNISH_ROUNDS)}
    whole = [t for t in thr if len(t["sizes"]) == want[t["mode"]]]
    cells = {(_cell(x), x["target"]) for x in _arms(rows)
             if x["block"] == "main"}
    ok = bool(thr) and len(whole) == len(thr) and len(thr) == 3 * len(cells)
    lines = []
    for kind in TARGETS:
        for mode in ("once", "instalments", "garnish"):
            ts = [t for t in thr if t["target"] == kind and t["mode"] == mode]
            out = [t["outside_band"] for t in ts]
            sw = [t["switch"] for t in ts]
            blk = [t["block_under"] for t in ts]
            lines.append(
                "%s target, %s: smallest size with the tail outside the band "
                "%s (in rounds of the target's inflow, median %s; over the "
                "claims in the trading accounts, median %s); smallest size at "
                "which a switch flips %s, the switch being %s; smallest size "
                "that puts a block below the floor in some round %s, and one "
                "that leaves it there at the close %s"
                % (kind, mode,
                   _tally("none" if t is None else "%g" % t["size"]
                          for t in out),
                   _g(_median(t["fine_in_rounds_of_inflow"]
                              for t in out if t)),
                   _g(_median(t["fine_over_circulating"] for t in out if t)),
                   _tally("none" if t is None else "%g" % t["size"]
                          for t in sw),
                   _tally(t["first_switch"] for t in sw if t),
                   _tally("none" if t is None else "%g" % t["size"]
                          for t in blk),
                   _tally("none" if t["block_under_at_close"] is None
                          else "%g" % t["block_under_at_close"]["size"]
                          for t in ts)))
    return Criterion(
        "A54-4 how large a fine has to be before something stays",
        "own_reading", ok,
        "Printed with its state. Per configuration, seed, target and mode, "
        "among fines that leave the graph, sizes %s as a share of the "
        "balance (one-off and in %d instalments) and %s rounds of the "
        "target's inflow (collected until paid): %d sets, %d complete. Each "
        "count below is over configurations and seeds; 'none' is a set in "
        "which no size did it. %s. Set by set in the thresholds section. "
        "The flag: every configuration, seed and target carries all three "
        "modes at every size -> PASS; a set short -> FAIL, reprint."
        % (list(FINE_SHARES), INSTALMENTS, list(GARNISH_ROUNDS), len(thr),
           len(whole), ". ".join(lines)))


def criterion_a54_5(rows: list) -> Criterion:
    caps = [x for x in _arms(rows) if x["kind"] == "cap"]
    names = _names(CAP_STATES)
    whole = [x for x in caps if x["cap_state"] in names and (
        x["cap_state"] == "never bit" or x["band"] is None
        or x["tail"] is not None)]
    ok = bool(caps) and len(whole) == len(caps)
    lines = []
    for block in ("main", "growth"):
        for kind in TARGETS:
            for level in sorted({x["size"] for x in caps
                                 if x["block"] == block}):
                xs = [x for x in caps if x["block"] == block
                      and x["target"] == kind and x["size"] == level]
                if not xs:
                    continue
                bit = [x for x in xs if x["cap_state"] not in (
                    "never bit", "above its cap to the end")]
                lines.append(
                    "%s block, %s target, cap %g: %s; where it bit, the "
                    "share against the twin's after 20, 50, 100 rounds and "
                    "over the tail %s, %s, %s, %s; share of routed inflow "
                    "turned away in the tail %s; slope of the log balance "
                    "over the tail %s against the twin's %s; turned away to "
                    "fin %s, mid %s, households %s, and to nodes that "
                    "themselves pay the target %s"
                    % (block, kind, level,
                       _tally(x["cap_state"] for x in xs),
                       _g(_median(x["deviation_at"]["20"] for x in bit)),
                       _g(_median(x["deviation_at"]["50"] for x in bit)),
                       _g(_median(x["deviation_at"]["100"] for x in bit)),
                       _g(_median(x["tail"] for x in bit)),
                       _g(_median(x["blocked_share_of_inflow_tail"]
                                  for x in bit)),
                       _g(_median(x["log_slope_tail"] for x in bit)),
                       _g(_median(x["twin_log_slope_tail"] for x in bit)),
                       _g(_median(x["diverted_to_layer"]["fin"] for x in bit)),
                       _g(_median(x["diverted_to_layer"]["mid"] for x in bit)),
                       _g(_median(
                           (x["diverted_to_layer"]["hhw"] or 0.0)
                           + (x["diverted_to_layer"]["hh0"] or 0.0)
                           if x["diverted_to_layer"]["fin"] is not None
                           else None for x in bit)),
                       _g(_median(x["diverted_to_payers_of_target"]
                                  for x in bit))))
    held_up = [x for x in caps if x["cap_state"] == "above its cap to the end"]
    grow = []
    for kind in TARGETS:
        xs = [x for x in _arms(rows) if x["block"] == "growth"
              and x["kind"] == "fine" and x["target"] == kind]
        grow.append(
            "%s target: slope %s against the twin's %s, first round %s, "
            "tail %s" % (kind, _g(_median(x["log_slope_tail"] for x in xs)),
                         _g(_median(x["twin_log_slope_tail"] for x in xs)),
                         _g(_median(x["first_round"] for x in xs)),
                         _g(_median(x["tail"] for x in xs))))
    return Criterion(
        "A54-5 the cap", "own_reading", ok,
        "Printed with its state. %d cells, %d with a state from the map. The "
        "main block is not growing, so its caps sit at and below the balance "
        "(%s times it); the growing block issues %g a round and its caps sit "
        "at and above (%s). State map: %s. The medians below are over the "
        "cells that are a reading of the cap. %s. Above its cap to the end: "
        "%d cells (%s); there the authority issues into the capped node, a "
        "node with no routed inflow is below the floor by the model's rule "
        "and spends the floor amount only, so what is issued stays on it: "
        "balance over the cap at the close, median %s. In the growing "
        "block, a one-off fine of %s of the balance beside the caps: %s. The "
        "flag: every cap cell has a state from the map, and one that bit has "
        "its tail unless the twin gives no band -> PASS; otherwise FAIL, "
        "reprint."
        % (len(caps), len(whole), list(CAP_LEVELS), GROWTH_ISSUE,
           list(GROWTH_CAPS), _states(CAP_STATES), ". ".join(lines),
           len(held_up),
           _tally("%s target, cap %g, %s %s" % (
               x["target"], x["size"], x["stress"], x["authority"])
               for x in held_up),
           _g(_median((x["held_close"] / x["cap_level"]) for x in held_up)),
           list(GROWTH_FINES), "; ".join(grow)))


def criterion_a54_6(rows: list, pairs: list, sets: list) -> Criterion:
    cuts = [x for x in _arms(rows) if x["kind"] == "cut" and not x["restore"]]
    want = {(_cell(x), x["target"], x["side"], x["size"]) for x in cuts}
    names = _names(PAIR_STATES)
    ranked = [s for s in sets if s["rank_loss_with_flow_share"] is not None
              and s["rank_loss_with_edge_share"] is not None]
    ok = (bool(pairs) and len(pairs) == len(want)
          and all(p["state"] in names for p in pairs) and bool(ranked))
    lines = []
    for kind in TARGETS:
        ps = [p for p in pairs if p["target"] == kind and p["side"] == "in"]
        ss = [s for s in sets if s["target"] == kind and s["side"] == "in"]
        by_size = []
        for size in CUT_SHARES:
            q = [p for p in ps if p["size"] == size]
            by_size.append(
                "share %g: flow carried by the edges cut %s by flow and %s at "
                "random, share lost %s and %s, %s"
                % (size, _g(_median(p["flow_share_by_flow"] for p in q)),
                   _g(_median(p["flow_share_at_random"] for p in q)),
                   _g(_median(p["loss_by_flow"] for p in q)),
                   _g(_median(p["loss_at_random"] for p in q)),
                   _tally(p["state"] for p in q)))
        lines.append(
            "%s target, in-edges. %s. Rank correlation of the share lost "
            "across the six cuts of a cell with the share of the flow cut, "
            "median %s (%s), and with the share of the edges cut, median %s "
            "(%s). Share lost over share of flow cut, median %s (%s)"
            % (kind, "; ".join(by_size),
               _g(_median(s["rank_loss_with_flow_share"] for s in ss)),
               _range(s["rank_loss_with_flow_share"] for s in ss),
               _g(_median(s["rank_loss_with_edge_share"] for s in ss)),
               _range(s["rank_loss_with_edge_share"] for s in ss),
               _g(_median(s["loss_over_flow_share_median"] for s in ss)),
               _range(s["loss_over_flow_share_median"] for s in ss)))
    outs = []
    for kind in TARGETS:
        xs = [x for x in cuts if x["side"] == "out" and x["target"] == kind
              and x["cut"] > 0]
        outs.append(
            "%s target, out-edges: its own share %s, tail median %s (%s); the "
            "nodes at the other end of a cut edge hold %s of their twin's "
            "over the tail, and those whose edge was kept %s"
            % (kind, _tally(x["tail_state"] for x in xs),
               _g(_median(x["tail"] for x in xs)),
               _range(x["tail"] for x in xs),
               _g(_median(x["other_end_cut_tail"] for x in xs)),
               _g(_median(x["other_end_kept_tail"] for x in xs))))
    back = [x for x in _arms(rows) if x["kind"] == "cut" and x["restore"]
            and x["cut"] > 0]
    under = [x for x in cuts if x["flip"] == "block under"]
    return Criterion(
        "A54-6 the cut: how many, and which", "own_reading", ok,
        "Printed with its state. Cuts that are not put back, %d cells; %d "
        "pairs of the same share on the same side of the same target, one "
        "picked from the largest flow down and one at random. Pair state map: "
        "%s. %s. %s. Put back after %d rounds (in-edges, by flow, shares %s; "
        "%d cells): %s, tail median %s; the deepest point median %s. A block "
        "below the floor at the close after a cut: %d cells (by target, cut, "
        "strain and floor: %s). Rank correlations are formed on %d of %d "
        "sides; the rest have fewer than three cuts with a band, or every "
        "cut costing the same. The flag: every share on every side of every "
        "target has both picks and a state from the map, and the rank "
        "correlations exist -> PASS; otherwise FAIL, reprint."
        % (len(cuts), len(pairs), _states(PAIR_STATES), ". ".join(lines),
           ". ".join(outs), RESTORE_AFTER, list(RESTORE_SHARES), len(back),
           _tally(x["permanence_state"] for x in back),
           _g(_median(x["tail"] for x in back)),
           _g(_median(x["peak"] for x in back)), len(under),
           _tally("%s %s, %s, floor %.2f" % (
               x["target"], x["arm"], x["stress"], x["need"])
               for x in under), len(ranked), len(sets)))


def criterion_a54_7(grp: list) -> Criterion:
    key = "median_deviation_path"
    full = [g for g in grp if len(g[key]) == SPAN and (
        all(v is not None for v in g[key])
        or set(g["permanence_states"]) == {"no band"})]
    names = _names(PERMANENCE_STATES)
    mapped = [g for g in grp if set(g["permanence_states"]) <= names]
    by_kind = []
    for label, pick in (
            ("fines that leave the graph", lambda g: g["kind"] == "fine"
             and g["sink"] == "destroy"),
            ("fines returned", lambda g: g["kind"] == "fine"
             and g["sink"] == "return"),
            ("caps", lambda g: g["kind"] == "cap"),
            ("in-edge cuts", lambda g: g["kind"] == "cut"
             and g["side"] == "in" and not g["restore"]),
            ("in-edge cuts put back", lambda g: g["kind"] == "cut"
             and bool(g["restore"])),
            ("out-edge cuts", lambda g: g["kind"] == "cut"
             and g["side"] == "out")):
        for kind in TARGETS:
            gs = [g for g in grp if pick(g) and g["target"] == kind]
            if not gs:
                continue
            states = {}
            for g in gs:
                for k, v in g["permanence_states"].items():
                    states[k] = states.get(k, 0) + v
            by_kind.append(
                "%s, %s target: %s; first round median %s, tail median %s, "
                "tail over first round where the first round is not zero, "
                "median %s, tail over the deepest point %s"
                % (label, kind,
                   ", ".join("%s %d" % kv for kv in sorted(states.items())),
                   _g(_median(g["first_round_median"] for g in gs)),
                   _g(_median(g["tail_median"] for g in gs)),
                   _g(_median(g["permanence_unbanded_median"] for g in gs)),
                   _g(_median(g["tail_over_peak_median"] for g in gs))))
    return Criterion(
        "A54-7 the three penalties side by side", "bookkeeping",
        bool(grp) and len(full) == len(grp) and len(mapped) == len(grp),
        "One number for all three: the target's share of the claims in the "
        "trading accounts against its twin's, less one; permanence is its "
        "mean over the last %d rounds over its value in the first round the "
        "penalty reaches. 0 is all of it gone, 1 none of it, above 1 a gap "
        "that widened. The ratio is formed only where the first round is "
        "outside the twin's band; the state beside it says what the pair of "
        "numbers is. State map: %s. By penalty and target, counts over cells "
        "and medians over groups: %s. Every group's median path, round by "
        "round from %d to %d, is in the groups section: %d of %d full, %d of "
        "%d with states from the map. State map of the flag: every group "
        "full and mapped -> PASS; a path short, or with a round missing in a "
        "group that has a band -> FAIL, reprint."
        % (TAIL, _states(PERMANENCE_STATES), "; ".join(by_kind), FIRST,
           ROUNDS - 1, len(full), len(grp), len(mapped), len(grp)))


def _flatten(d: dict, prefix: str = "") -> dict:
    """Nested readings as dotted names: ``incidence.tail_layer.fin``."""
    out = {}
    for k, v in d.items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, dict):
            out.update(_flatten(v, "%s%s." % (prefix, k)))
        else:
            out[prefix + str(k)] = v
    return out


def _table(dicts: list) -> dict:
    """Rows that share their fields as one table: the names once, in the
    order they first appear, then one row of values per record. Eight
    thousand runs written as objects repeat every name eight thousand times.
    A field no row fills is left out."""
    flat = [_flatten(d) for d in dicts]
    fields = []
    for f in flat:
        for k in f:
            if k not in fields:
                fields.append(k)
    fields = [k for k in fields if any(f.get(k) is not None for f in flat)]
    return {"fields": fields, "rows": [[f.get(k) for k in fields]
                                       for f in flat]}


def _by_kind(dicts: list, kinds: tuple) -> dict:
    return {k: _table([d for d in dicts if d["kind"] == k]) for k in kinds}


def analyse(rows: list, gate_section) -> tuple:
    grp = groups(rows)
    thr = thresholds(rows)
    pairs, sets = cut_readings(rows)
    crits = [criterion_a54_0(gate_section, rows), criterion_a54_1(rows),
             criterion_a54_2a(rows), criterion_a54_2(rows),
             criterion_a54_3(rows), criterion_a54_4(rows, thr),
             criterion_a54_5(rows), criterion_a54_6(rows, pairs, sets),
             criterion_a54_7(grp)]
    head = headline(rows)
    sections = {
        "criteria": [c.as_dict() for c in crits],
        "layout": "every section below criteria is a table or a set of "
                  "tables by kind of row: fields names the columns once, "
                  "nested readings as dotted names, and rows holds one "
                  "record per line in that order",
        "headline": _table(head),
        "groups": _by_kind(grp, ("fine", "cap", "cut")),
        "thresholds": _table(thr),
        "cut_pairs": _table(pairs), "cut_sets": _table(sets),
        "rows": _by_kind(rows, ("twin", "fine", "cap", "cut")),
    }
    return crits, sections, head


# ---------------------------------------------------------------------------
# Console tables: printed, never written.
# ---------------------------------------------------------------------------

def print_twins(rows: list) -> None:
    tw = [x for x in rows if x["kind"] == "twin"]
    print("\n   twins, median over seeds: below the floor at the close, "
          "claims in the trading accounts at the penalty and at the close; "
          "then each target's share of them, its inflow per round, its "
          "round-to-round jitter, and its routing edges in and out")
    seen = []
    for x in tw:
        key = (x["block"], x["need"], x["stress"], x["elasticity"],
               x["authority"])
        if key not in seen:
            seen.append(key)
    for key in seen:
        xs = [x for x in tw if (x["block"], x["need"], x["stress"],
                                x["elasticity"], x["authority"]) == key]
        line = "   %-6s need %.2f %-14s e %.1f %-10s below %-5s circ %7s -> %-7s" % (
            key[0], key[1], key[2], key[3], key[4],
            _g(_median(x["below_close"] for x in xs)),
            _g(_median(x["circulating_at_penalty"] for x in xs)),
            _g(_median(x["circulating_close"] for x in xs)))
        for kind in TARGETS:
            t = [x["targets"][kind] for x in xs]
            line += " | %s: share %s inflow %s jitter %s edges %s/%s" % (
                kind[:4], _g(_median(v["share_at_penalty"] for v in t)),
                _g(_median(v["inflow_per_round"] for v in t)),
                _g(_median(v["jitter"] for v in t)),
                _g(_median(v["routing_in_edges"] for v in t)),
                _g(_median(v["routing_out_edges"] for v in t)))
        print(line)


def print_headline(head: list) -> None:
    print("\n   each arm over floors, elasticities and seeds: cells, the "
          "share's deviation from its twin in the first round and over the "
          "tail (medians), tail over first round, the permanence states, and "
          "cells with a block below the floor at the close / in some round")
    last = None
    for h in head:
        key = (h["block"], h["target"], h["authority"], h["stress"])
        if key != last:
            print("\n   %s block, %s target, authority %s, %s" % key)
            last = key
        print("      %-30s %3d  first %9s  tail %9s  ratio %8s  %-40s %d/%d" % (
            h["arm"], h["cells"], _g(h["first_round_median"]),
            _g(h["tail_median"]), _g(h["permanence_unbanded_median"]),
            ", ".join("%s %d" % kv for kv in h["permanence_states"].items()),
            h["blocks_under_at_close"], h["blocks_under_in_some_round"]))


# ---------------------------------------------------------------------------
# Rule 19. The model is not changed, so the gate is the class and the driver:
# with no penalty they have to be ``Network.run()``, and an arm at size zero
# has to be its twin. Both are run, not argued.
# ---------------------------------------------------------------------------

def zero_arms(cfg: NetworkConfig) -> list:
    arms = [_fine("once", 0.0), _fine("instalments", 0.0), _fine("garnish", 0),
            _cap(float("inf")), _cut("in", 0.0, "random"),
            _cut("out", 0.0, "flow"), _cut("in", 0.0, "flow", RESTORE_AFTER)]
    if cfg.sovereign.active and not cfg.sovereign.serves_debt:
        arms += [_fine("once", 0.0, "return"), _fine("garnish", 0, "return")]
    return arms


def gate_configs(bases=None) -> list:
    out = [("library default", NetworkConfig())]
    for b in (base_keys(seeds=SEEDS[:1]) if bases is None else bases):
        out.append(("%s need %.2f %s e %.1f %s" % (
            b["block"], b["need"], b["stress"], b["elasticity"],
            b["authority"]), base_config(b)))
    return out


def _differs(names: list, ref_hist, ref_net, hist, net, ref_rng: str,
             rng: str) -> list:
    bad = [n for n in names if not _same(getattr(ref_hist, n), getattr(hist, n))]
    bad += [n for n in CLOSING if not _same(getattr(ref_net, n),
                                            getattr(net, n))]
    if ref_rng != rng:
        bad.append("generators")
    return bad


def gate(configs: list) -> dict:
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    differ, labels, zero_labels = [], [], []
    runs = 0
    for label, cfg in configs:
        t0 = time.perf_counter()
        ref = Network(cfg)
        h_ref = ref.run()
        twin = make_twin(cfg)
        net = twin["net"]
        bad = _differs(names, h_ref, ref, net._history, net, _rng_digest(ref),
                       twin["rng"])
        if not twin["books"]:
            bad.append("claim total against held plus parked")
        runs += 1
        if bad:
            differ.append({"run": "%s, no penalty" % label, "fields": bad})
        off = 0
        for kind in TARGETS:
            node = twin["nodes"][kind]["node"]
            for arm in zero_arms(cfg):
                lab = arm_label(arm)
                if lab not in zero_labels:
                    zero_labels.append(lab)
                z, seen = drive(cfg, node, arm, twin)
                zbad = _differs(names, net._history, net, z._history, z,
                                twin["rng"], seen["rng"])
                if not seen["books"]:
                    zbad.append("claim total against held plus parked")
                if seen.get("ledger") is False:
                    zbad.append("the pool's receipts")
                runs += 1
                if zbad:
                    off += 1
                    differ.append({"run": "%s, %s target, %s" % (label, kind,
                                                                lab),
                                   "fields": zbad})
        labels.append(label)
        print("   %-44s %s; arms at zero: %s  (%.1f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "identical" if not off else "%d DIFFER" % off,
            time.perf_counter() - t0))
    return {
        "module_sha": _module_sha(MODULE),
        "script_sha": _module_sha(SCRIPT),
        "configs": labels,
        "fields_compared": len(names) + len(CLOSING) + 1,
        "zero_arms": zero_labels,
        "runs": runs,
        "differ": differ,
        "verdict": "pass" if not differ else "fail",
    }


def _gate_section():
    if not RECORD.exists():
        return None
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    return doc.get("sections", {}).get("gate")


def _gate_allows(g) -> tuple:
    if not g:
        return False, "no gate section in the record: run --gate first"
    if g.get("module_sha") != _module_sha(MODULE):
        return False, "network.py has changed since the gate ran: run --gate again"
    if g.get("script_sha") != _module_sha(SCRIPT):
        return False, ("this script has changed since the gate ran, and the "
                       "class and the driver live in it: run --gate again")
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and this script"


# ---------------------------------------------------------------------------
# Seeded faults: every check has to report the fault it is there for, and
# every criterion has to fail on a wrong input.
# ---------------------------------------------------------------------------

def selftest() -> dict:
    import copy

    checks = []

    def note(what: str, held: bool, detail: str = "") -> None:
        checks.append({"check": what, "held": bool(held), "detail": detail})
        print("   [%s] %s%s" % ("ok" if held else "MISSED", what,
                                ("  (%s)" % detail) if detail else ""))

    base = {"block": "main", "need": 0.05, "stress": "leak_recycled",
            "elasticity": 0.0, "authority": "none", "seed": SEEDS[0]}
    cfg = base_config(base)
    twin = make_twin(cfg)
    fin = twin["nodes"]["financial"]["node"]

    # 1. A fine that is not taken off the claim total.
    arm = _fine("once", 0.2)
    _, good = drive(cfg, fin, arm, twin)
    _, bad = drive(cfg, fin, arm, twin, fault="unbooked_fine")
    note("a fine not taken off the claim total is reported by the books and "
         "by the first take",
         good["books"] and good["first_take_ok"] and not bad["books"]
         and not bad["first_take_ok"])

    # 2. A cap that stops what the target pays.
    arm = _cap(0.8)
    _, good = drive(cfg, fin, arm, twin)
    _, bad = drive(cfg, fin, arm, twin, fault="cap_on_outflow")
    note("a cap that stops the target's payments, and not its receipts, is "
         "reported by the guard at the close",
         good["guard"] and good["bites"] > 0 and not bad["guard"],
         "closes above the cap with routed inflow taken: %d against %d"
         % (bad["over_cap_closes"], good["over_cap_closes"]))

    # 3. A random pick drawn from the model's own stream.
    arm = _cut("in", 0.3, "random")
    _, good = drive(cfg, fin, arm, twin)
    _, bad = drive(cfg, fin, arm, twin, fault="cut_draws_main")
    note("a pick of edges drawn from the model's stream leaves the "
         "generators somewhere else than the twin's",
         good["rng"] == twin["rng"] and bad["rng"] != twin["rng"])

    # 3b. The pick by flow is the largest flows of the penalty round, and the
    #     band is the stage's multiple of the twin's jitter.
    arm = _cut("in", 0.3, "flow")
    net_cut, cut_seen = drive(cfg, fin, arm, twin)
    at = twin["at"]
    flows = np.sort((at["spent"] * at["route"][:, fin])[at["route"][:, fin] > 0])
    top = float(flows[::-1][:cut_seen["cut"]].sum())
    row = read_arm(twin, base, "financial", arm, net_cut, cut_seen)
    note("the pick by flow cuts the largest flows of the penalty round",
         cut_seen["cut"] > 0 and abs(cut_seen["flow_cut"] - top) <= 1e-12
         and cut_seen["flow_cut"] > 0.5 * cut_seen["flow_total"],
         "%d of %d edges carry %.3f of the inflow" % (
             cut_seen["cut"], cut_seen["edges"],
             cut_seen["flow_cut"] / cut_seen["flow_total"]))
    note("the band is the stage's multiple of the twin's own jitter",
         row["band"] == FLOOR_MULTIPLE * twin["jitter"]["financial"]
         and twin["jitter"]["financial"] > 0.0)
    # The deviation, read a second way straight off the two histories.
    hp = np.asarray(net_cut._history.holdings, dtype=float)
    second = ((hp[FIRST, fin] / hp[FIRST].sum())
              / (twin["H"][FIRST, fin] / twin["H"][FIRST].sum()) - 1.0)
    second_tail = float(np.mean(
        (hp[-TAIL:, fin] / hp[-TAIL:].sum(axis=1))
        / (twin["H"][-TAIL:, fin] / twin["H"][-TAIL:].sum(axis=1)) - 1.0))
    note("the deviation is the share of the trading accounts against the "
         "twin's, and not the share of all claims",
         abs(row["first_round"] - second) <= 1e-12
         and abs(row["tail"] - second_tail) <= 1e-12
         and abs(row["tail"] - row["tail_on_all_claims"]) > 1e-6,
         "first round %.6f, tail %.6f, tail on all claims %.6f" % (
             row["first_round"], row["tail"], row["tail_on_all_claims"]))
    # Steps along a chain a -> b -> c, and against it.
    chain = np.zeros((3, 3), dtype=bool)
    chain[0, 1] = chain[1, 2] = True
    note("steps are counted along the edges, and against them when asked",
         steps_from(chain, 0).tolist() == [0, 1, 2]
         and steps_from(chain, 2).tolist() == [-1, -1, 0]
         and steps_from(chain, 2, True).tolist() == [2, 1, 0]
         and step_groups(steps_from(chain, 0)).tolist() == ["target", "1", "2"])
    note("the trigger names the widest thing that happened",
         trigger({"target": 1, "down_1": 0, "down_further": 0,
                  "elsewhere": 0}, BLOCK) == "block"
         and trigger({"target": 1, "down_1": 3, "down_further": 0,
                      "elsewhere": 0}, 4) == "target"
         and trigger({"target": 0, "down_1": 3, "down_further": 9,
                      "elsewhere": 0}, 12) == "one step down"
         and trigger({"target": 0, "down_1": 0, "down_further": 0,
                      "elsewhere": 2}, 2) == "elsewhere"
         and trigger({"target": 0, "down_1": 0, "down_further": 0,
                      "elsewhere": 0}, 0) == "none")

    # 4. The two denominators of a share, swapped.
    over_held, over_all = shares([2.0], [10.0], [30.0])
    swapped = shares([2.0], [40.0], [-30.0])
    note("the share of the trading accounts and the share of all claims are "
         "the two they are named for",
         float(over_held[0]) == 0.2 and float(over_all[0]) == 0.05
         and float(swapped[0][0]) != 0.2)

    # 5. A returned fine booked to the pool and not to its receipts: the
    #    model's own guard has to stop the run.
    arm = _fine("once", 0.2, "return")
    _, good = drive(cfg, fin, arm, twin)
    try:
        drive(cfg, fin, arm, twin, fault="pool_only")
        stopped = False
    except AssertionError:
        stopped = True
    note("a fine added to the sovereign's pool without its receipt stops at "
         "the model's own ledger assertion, and with it the driver's ledger "
         "closes", bool(good["ledger"]) and stopped)

    # 6. A linear two-node kernel that has not finished mixing must read as
    #    closing, never as settled: 27.5 - 22.5 * 0.98 ** k against 27.5.
    k = np.arange(1, SPAN + 1, dtype=float)
    path = (27.5 - 22.5 * 0.98 ** k) / 27.5 - 1.0
    tail, prev = float(path[-TAIL:].mean()), float(path[-2 * TAIL:-TAIL].mean())
    note("a slow linear mode is read as still closing",
         94.0 < rounds_to_band(tail, prev, 0.01) < 96.0
         and tail_state(tail, prev, 0.01) == "outside, closing"
         and tail_state(tail, tail, 0.01) == "outside, settled"
         and tail_state(0.005, 0.02, 0.01) == "inside"
         and tail_state(tail, prev, None) == "no band",
         "tail %.4f, the window before %.4f, %.0f more rounds to a band of "
         "0.01" % (tail, prev, rounds_to_band(tail, prev, 0.01)))

    # 7. The classifiers, on the cases the audit of the design named.
    note("permanence: a zero first round forms no ratio, a change of sides "
         "is named, and a tail inside the band is zero",
         permanence(0.0, 0.0, 0.01) == (None, "nothing")
         and permanence(0.0, -0.2, 0.01) == (None, "late")
         and permanence(0.02, -0.2, 0.01)[1] == "reversed"
         and permanence(-0.4, 0.001, 0.01)[1] == "gone"
         and permanence(-0.25, -0.5, 0.01) == (2.0, "kept")
         and permanence(-0.25, -0.5, None) == (None, "no band"))
    note("cap states: never, let go, on and off, to the end, held above",
         [cap_state(0, 0), cap_state(40, 0), cap_state(40, 9),
          cap_state(150, TAIL), cap_state(150, TAIL, TAIL)]
         == ["never bit", "let go", "biting on and off", "biting to the end",
             "above its cap to the end"])

    # 8. Every criterion on rows that are right, then on rows made wrong.
    rows = one_base(base)
    g_ok = {"verdict": "pass", "differ": [], "configs": ["x"],
            "fields_compared": 0, "zero_arms": [], "runs": 0}

    def crit(rs, index, g=g_ok):
        return analyse(rs, g)[0][index]

    # The written form: a table gives back the records it was made from, and
    # every row of it is one line of the file.
    as_table = _table([{"a": 1, "b": {"c": 2.5, "d": None}, "_private": 9},
                       {"a": 3, "b": {"c": None, "d": None}, "e": [1, 2]}])
    text = _dump({"t": as_table, "plain": [1, 2, 3]})
    note("a table keeps every record, names nested readings by dotted "
         "names, drops what no row fills, and writes one row a line",
         as_table == {"fields": ["a", "b.c", "e"],
                      "rows": [[1, 2.5, None], [3, None, [1, 2]]]}
         and json.loads(text) == {"t": as_table, "plain": [1, 2, 3]}
         and "[1, 2.5, null]" in text and "[3, null, [1, 2]]" in text
         and "@@LINE" not in text)

    def broken(change):
        rs = copy.deepcopy(rows)
        change(rs)
        return rs

    def pick(rs, **want):
        for x in rs:
            if all(x.get(k) == v for k, v in want.items()):
                return x
        raise KeyError(want)

    right = analyse(rows, g_ok)[0]
    note("every criterion passes on one configuration's rows as run",
         all(c.passed for c in right),
         ", ".join(c.name.split()[0] for c in right if not c.passed))

    def off(field, value, **want):
        def change(rs):
            pick(rs, **want)[field] = value
        return change

    def drop(**want):
        def change(rs):
            rs.remove(pick(rs, **want))
        return change

    def spoil_path(rs):
        x = pick(rs, arm="cap 0.8", target="financial")
        x["_dev"] = x["_dev"][:-1]

    def spoil_incidence(rs):
        pick(rs, arm="fine once 0.5", target="financial")["incidence"][
            "tail_layer"].pop("mid")

    faults = [
        (0, "A54-0, a run whose books do not close",
         off("books_close", False, arm="cap 0.8", target="financial"), g_ok),
        (0, "A54-0, a run whose draws are not its twin's",
         off("same_draws_as_twin", False, arm="cut in 0.3 random",
             target="production"), g_ok),
        (0, "A54-0, a returned fine whose receipts do not close",
         off("ledger_close", False, arm="fine once 0.2 returned",
             target="financial"), g_ok),
        (0, "A54-0, a gate that failed", lambda rs: None,
         dict(g_ok, verdict="fail")),
        (1, "A54-1, a fine whose first take is not the amount due",
         off("first_take", 0.0, arm="fine once 0.2", target="financial"),
         g_ok),
        (1, "A54-1, a collection that stopped while still owed",
         lambda rs: pick(rs, arm="fine garnish 8", target="financial").update(
             taken=1.0, shortfall=pick(rs, arm="fine garnish 8",
                                       target="financial")["asked"] - 1.0,
             takes=1), g_ok),
        (1, "A54-1, a cap whose guard was broken",
         off("cap_guard", False, arm="cap 0.5", target="production"), g_ok),
        (1, "A54-1, a cut that removed another number of edges",
         off("edges_after", 0, arm="cut in 0.1 flow", target="financial"),
         g_ok),
        (1, "A54-1, a cut edge still carrying flow",
         off("residual_flow_next_round", 0.1, arm="cut out 0.6 flow",
             target="production"), g_ok),
        (1, "A54-1, edges put back onto another routing",
         off("restored_exactly", False, arm="cut in 0.6 flow restored",
             target="financial"), g_ok),
        (2, "A54-2a, a stable cell whose effect is not proportional",
         off("proportional_gap", 1e-3, arm="fine once 0.2",
             target="financial"), g_ok),
        (3, "A54-2, a cell with a tail state outside the map",
         off("tail_state", "somewhere", arm="fine once 0.2",
             target="financial"), g_ok),
        (3, "A54-2, a cell with a state and no tail",
         off("tail", None, arm="fine once 0.05", target="financial"), g_ok),
        (4, "A54-3, a fine whose incidence lacks a layer", spoil_incidence,
         g_ok),
        (4, "A54-3, a fine with a trigger outside the map",
         off("trigger", "somewhere", arm="fine garnish 4",
             target="production"), g_ok),
        (5, "A54-4, a set of fines missing a size",
         drop(arm="fine instalments 0.5", target="production"), g_ok),
        (6, "A54-5, a cap with a state outside the map",
         off("cap_state", "somewhere", arm="cap 1", target="financial"), g_ok),
        (7, "A54-6, a share with one of its two picks missing",
         drop(arm="cut in 0.3 random", target="financial"), g_ok),
        (8, "A54-7, a group whose path is a round short", spoil_path, g_ok),
        (8, "A54-7, a group with a permanence state outside the map",
         off("permanence_state", "somewhere", arm="cut out 0.1 flow",
             target="production"), g_ok),
    ]
    for index, what, change, g in faults:
        c = crit(broken(change), index, g)
        note("%s: fails" % what, c.evaluated and not c.passed)
    held = sum(1 for c in checks if c["held"])
    return {"module_sha": _module_sha(MODULE),
            "script_sha": _module_sha(SCRIPT),
            "checks": checks, "held": held, "of": len(checks),
            "verdict": "pass" if held == len(checks) else "fail"}


# ---------------------------------------------------------------------------
# Timing (D38): measured on each size of work unit, printed, never written.
# ---------------------------------------------------------------------------

def time_bases(workers: int = 1) -> None:
    probes = [
        {"block": "main", "need": 0.20, "stress": "healthy",
         "elasticity": 0.5, "authority": "endogenous", "seed": SEEDS[0]},
        {"block": "main", "need": 0.20, "stress": "leak_recycled",
         "elasticity": 0.5, "authority": "none", "seed": SEEDS[0]},
        {"block": "growth", "need": 0.05, "stress": "healthy",
         "elasticity": 0.0, "authority": "fixed", "seed": SEEDS[0]},
    ]
    make_twin(base_config(probes[0]))  # warm-up, not timed
    per = {}
    for b in probes:
        t0 = time.perf_counter()
        rows = one_base(b)
        dt = time.perf_counter() - t0
        size = ("growth" if b["block"] == "growth" else
                "returned" if b["stress"] == "leak_recycled" else "main")
        per[size] = dt
        print("   %-6s %-14s %-10s %3d runs  %.1f s  (%.3f s a run)" % (
            b["block"], b["stress"], b["authority"], len(rows), dt,
            dt / len(rows)))
    eff = max(1, min(workers, os.cpu_count() or 1))
    for n in (2, len(SEEDS)):
        bases = base_keys(seeds=SEEDS[:n])
        total = sum(per["growth" if b["block"] == "growth" else
                        "returned" if b["stress"] == "leak_recycled"
                        else "main"] for b in bases)
        runs = sum(1 + len(TARGETS) * len(arms_for(b)) for b in bases)
        print("   %d seeds: %d configurations, %d runs, %.0f s serial, about "
              "%.0f s on %d workers" % (n, len(bases), runs, total,
                                        total / eff, eff))
    gates = gate_configs()
    g_runs = sum(2 + len(TARGETS) * len(zero_arms(cfg)) for _, cfg in gates)
    print("   --gate: %d configurations, %d runs, serial, about %.0f s"
          % (len(gates), g_runs, g_runs * per["main"] / 57.0))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe = base_config({"block": "main", "need": NEEDS[0],
                         "stress": "healthy", "elasticity": ELASTICITIES[0],
                         "authority": AUTHORITIES[0], "seed": SEEDS[0]})
    cfg = _config_diff(probe)
    cfg.pop("seed", None)
    for sub, keys in (("spec", ("seed",)), ("subsistence", ("need",)),
                      ("wages", ("elasticity",)), ("authority", ("rule",))):
        if sub in cfg:
            for k in keys:
                cfg[sub].pop(k, None)
            if not cfg[sub]:
                cfg.pop(sub)
    return {
        "carrier": "A30's: A18's config_for in drawdown, no write-off, no "
                   "rescue, with A30's three strains",
        "rounds": ROUNDS,
        "penalty_at_close_of_round": PENALTY_ROUND,
        "first_round_reached": FIRST,
        "targets": "the node with the most in-edges inside the financial "
                   "layer, and outside it",
        "grid": {
            "need_multiples": list(NEEDS),
            "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
            "elasticities": list(ELASTICITIES),
            "authorities": list(AUTHORITIES),
            "seeds": list(SEEDS),
            "fine_shares_of_balance": list(FINE_SHARES),
            "instalments": INSTALMENTS, "instalment_gap": INSTALMENT_GAP,
            "fine_rounds_of_inflow": list(GARNISH_ROUNDS),
            "inflow_window": [REVENUE_FROM, PENALTY_ROUND],
            "fine_sinks": {"destroy": "every configuration",
                           "return": "leak_recycled only: paid into the "
                                     "sovereign's pool and passed down"},
            "cap_levels": list(CAP_LEVELS),
            "cut_shares": list(CUT_SHARES), "cut_sides": list(CUT_SIDES),
            "cut_picks": list(CUT_PICKS),
            "restore_after": RESTORE_AFTER,
            "restore_shares": list(RESTORE_SHARES),
        },
        "growing_block": {
            "strain": "healthy", "authority": "fixed",
            "issued_per_round": GROWTH_ISSUE,
            "cap_levels": list(GROWTH_CAPS),
            "fine_shares_of_balance": list(GROWTH_FINES),
        },
        "tail": TAIL,
        "horizons_after_penalty": list(HORIZON_N),
        "incidence_horizons": list(INCIDENCE_N),
        "block": BLOCK,
        "floor_multiple": FLOOR_MULTIPLE,
        "band": "floor_multiple times the spread of the log of the twin's "
                "share of the trading accounts about a straight line over the "
                "tail, per target and seed",
        "proportional_tolerance": PROPORTIONAL_TOL,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


_SCALAR = (r'(?:-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?|null|true|false|'
           r'"(?:[^"\\]|\\.)*")')
_FLAT_LIST = re.compile(r"\[\n\s*(%s(?:,\n\s*%s)*)\n\s*\]" % (_SCALAR, _SCALAR))
_LINE = re.compile(r'"@@LINE(\d+)@@"')


def _dump(doc: dict) -> str:
    """Sorted keys and one level of indent; a list of plain values on one
    line; and in a table, the field names on one line and each row on its
    own, whatever it holds."""
    lines: list = []

    def one_line(value) -> str:
        lines.append(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                separators=(", ", ": ")))
        return "@@LINE%d@@" % (len(lines) - 1)

    def mark(o):
        if isinstance(o, dict):
            if set(o) == {"fields", "rows"} and isinstance(o["rows"], list):
                return {"fields": one_line(o["fields"]),
                        "rows": [one_line(row) for row in o["rows"]]}
            return {k: mark(v) for k, v in o.items()}
        if isinstance(o, list):
            return [mark(v) for v in o]
        return o

    text = json.dumps(mark(doc), ensure_ascii=False, indent=1, sort_keys=True)
    text = _FLAT_LIST.sub(
        lambda m: "[" + re.sub(r",\n\s*", ", ", m.group(1)) + "]", text)
    return _LINE.sub(lambda m: lines[int(m.group(1))], text) + "\n"


def write_record(section: str, payload: dict) -> None:
    """Merge one step's payload into the station record. No wall-clock
    content: git records when a file was committed."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A54"
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(_dump(doc), encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--plan", action="store_true")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--workers", type=int, default=_default_workers())
    ap.add_argument("--smoke", action="store_true",
                    help="with --run: the reduced grid, gated on its own "
                         "configurations, nothing written")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-26s %s" % (k, v))
        bases = base_keys(seeds=SEEDS[:args.seeds])
        print("  %-26s %d configurations and seeds, %d runs at %d seeds" % (
            "work", len(bases),
            sum(1 + len(TARGETS) * len(arms_for(b)) for b in bases),
            args.seeds))
        return 0

    if args.gate:
        print("stage A54, rule 19: the class and the driver against "
              "Network.run() with no penalty, and every arm at size zero "
              "against that twin\n")
        g = gate(gate_configs())
        print("\n   %d runs, verdict: %s" % (g["runs"], g["verdict"]))
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.selftest:
        print("stage A54, seeded faults: each check has to report its own, "
              "and each criterion has to fail on a wrong input\n")
        s = selftest()
        print("\n   %d of %d held, verdict: %s" % (s["held"], s["of"],
                                                  s["verdict"]))
        if not args.no_write:
            write_record("selftest", s)
        return 0 if s["verdict"] == "pass" else 1

    if args.time:
        print("stage A54, D38: seconds per configuration, measured on this "
              "machine, one of each size\n")
        time_bases(workers=args.workers)
        return 0

    if args.smoke:
        bases = base_keys(needs=SMOKE["needs"],
                          elasticities=SMOKE["elasticities"],
                          seeds=SMOKE["seeds"])
        print("stage A54, smoke: %d configurations and seeds, gated "
              "in-process on its own configurations, nothing written\n"
              % len(bases))
        gate_section = gate(gate_configs(
            base_keys(needs=SMOKE["needs"],
                      elasticities=SMOKE["elasticities"], seeds=SEEDS[:1])))
        print()
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A54: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        if len(seeds) < 2:
            print("stage A54: not starting. The groups are medians over "
                  "seeds, and a median over one seed is that seed.")
            return 2
        bases = base_keys(seeds=seeds)
        print("stage A54: %d configurations and seeds, %d runs, seeds %s, %d "
              "workers. %s.\n"
              % (len(bases),
                 sum(1 + len(TARGETS) * len(arms_for(b)) for b in bases),
                 list(seeds), args.workers, why))
    t0 = time.perf_counter()
    rows = run_bases(bases, args.workers)
    print("   ran %d runs in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections, head = analyse(rows, gate_section)
    print_twins(rows)
    print_headline(head)
    _print_criteria(crits)
    failed = [c.name for c in crits if c.evaluated and not c.passed]
    judged = sum(1 for c in crits if c.evaluated)
    print("\n  %d/%d%s" % (judged - len(failed), judged,
                          "" if judged == len(crits) else
                          ", %d not evaluated" % (len(crits) - judged)))
    if args.smoke or args.no_write:
        return 0 if not failed else 1
    sections["seeds_run"] = sorted({x["seed"] for x in rows})
    write_record("run", sections)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
