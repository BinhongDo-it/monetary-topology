"""A55: a cap taken off again, and a cap on every node of a layer.

A54 read a ceiling on one node's balance for as long as it stays, and found
that two thirds of what the ceiling turns away from a financial node lands on
other financial nodes. Two things it left unread, and this stage reads them on
the same carrier:

    lift    the ceiling comes off again after L rounds. Does the node's share
            of the trading accounts come back, and at what pace?
    layer   every node of the financial layer has a ceiling at once, each at a
            multiple of its own balance, so the way out along the layer is
            shut. Where does what is turned away go?

The ceiling stays where A54 put it, at the model's own capacity step. This
script writes A54's one column as many: a column with a ceiling takes in what
fits under it, its payers spend the rest on their counterparties that have no
ceiling, in the proportions their rows already have. With one node capped that
is A54's arithmetic expression for expression, and ``--gate`` compares the two
classes bit for bit.

    python experiments/a55_cap_lift_layer.py --gate
    python experiments/a55_cap_lift_layer.py --selftest
    python experiments/a55_cap_lift_layer.py --time
    python experiments/a55_cap_lift_layer.py --run [--seeds N] [--workers N]
    python experiments/a55_cap_lift_layer.py --tables

``--run`` does not start until ``--gate`` has passed on the module and on this
script and A54's as they are now. ``--tables`` reads the record and prints
Markdown tables; it runs nothing. ``--no-write`` prints and writes nothing.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SRC = ROOT / "src" / "monetary_topology"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkHistory,
)

RECORD = RESULTS / "a55_cap_lift_layer.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
A54_SCRIPT = ROOT / "experiments" / "a54_penalty.py"
STAGE = "A55"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A54's carrier, twin, readings and record format, taken and not restated.
_A54 = _load(A54_SCRIPT, "_a54_for_a55")
Criterion = _A54.Criterion
_fmt = _A54._fmt
_num = _A54._num
_same = _A54._same
_module_sha = _A54._module_sha

ROUNDS = _A54.ROUNDS
SEEDS = _A54.SEEDS
TAIL = _A54.TAIL
PENALTY_ROUND = _A54.PENALTY_ROUND
FIRST = _A54.FIRST
TARGETS = _A54.TARGETS
LAYERS = _A54.LAYERS
NEEDS = _A54.NEEDS
ELASTICITIES = _A54.ELASTICITIES
AUTHORITIES = _A54.AUTHORITIES
FLOOR_MULTIPLE = _A54.FLOOR_MULTIPLE
BLOCK = _A54.BLOCK

#: The two strains whose twin is not itself running down.
STRESSES: tuple[str, ...] = ("healthy", "leak_recycled")

#: (ceiling as a multiple of the balance at the penalty round, rounds it stays).
#: On a graph that is not growing a ceiling has to sit below the balance to
#: hold anything down; on the growing block it sits at the balance and the gap
#: opens with time, so the lift comes later there.
LIFT_MAIN: tuple[tuple[float, int], ...] = ((0.5, 20), (0.5, 50), (0.8, 50))
KEPT_MAIN: tuple[float, ...] = (0.5,)
LAYER_MAIN: tuple[tuple[float, int | None], ...] = ((0.8, None), (1.0, None),
                                                    (0.8, 50))
LIFT_GROWTH: tuple[tuple[float, int], ...] = ((1.0, 50), (1.0, 100))
KEPT_GROWTH: tuple[float, ...] = (1.0,)
LAYER_GROWTH: tuple[tuple[float, int | None], ...] = ((1.0, None), (1.2, None),
                                                      (1.0, 50))

#: Rounds after the lift at which the deviation is printed.
AFTER_LIFT: tuple[int, ...] = (1, 2, 3, 5, 10, 20, 50)
#: The last rounds of the run, whose mean is "where it ended" for a lifted arm.
END = 10
#: Rounds after the penalty at which a kept ceiling is printed.
AT: tuple[int, ...] = (20, 50, 100)
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}

LIFT_STATES: tuple[tuple[str, str], ...] = (
    ("back", "the mean deviation over the last %d rounds is inside the twin's "
     "band: the share is back where the twin's is" % END),
    ("not back", "outside the band at the end, on the side it was on when the "
     "ceiling came off"),
    ("reversed", "outside the band at the end, on the other side"),
    ("nothing to give back", "inside the band when the ceiling came off: the "
     "ceiling had moved nothing, so nothing is read"),
    ("no band", "the twin's share touches zero in the tail: no reading"))


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def base_keys(seeds=SEEDS, needs=NEEDS, elasticities=ELASTICITIES,
              authorities=AUTHORITIES, growth: bool = True) -> list:
    return _A54.base_keys(seeds=seeds, needs=needs, stresses=STRESSES,
                          elasticities=elasticities, authorities=authorities,
                          growth=growth)


base_config = _A54.base_config


def _arm(scope: str, level: float, lift=None) -> dict:
    return {"kind": "cap", "scope": scope, "size": level, "lift": lift}


def arms_for(base: dict) -> list:
    growth = base["block"] == "growth"
    arms = [_arm("node", c) for c in (KEPT_GROWTH if growth else KEPT_MAIN)]
    arms += [_arm("node", c, L) for c, L in (LIFT_GROWTH if growth
                                             else LIFT_MAIN)]
    arms += [_arm("layer", c, L) for c, L in (LAYER_GROWTH if growth
                                              else LAYER_MAIN)]
    return arms


def arm_label(a: dict) -> str:
    return "%scap %g%s" % ("layer " if a["scope"] == "layer" else "",
                           a["size"],
                           " lifted %d" % a["lift"] if a.get("lift") else "")


def _all_labels() -> list:
    out = []
    for block in ("main", "growth"):
        for a in arms_for({"block": block}):
            if arm_label(a) not in out:
                out.append(arm_label(a))
    return out


ARM_ORDER: list = _all_labels()
WHO: tuple[str, ...] = TARGETS + ("layer",)


def runs_of(base: dict) -> int:
    return 1 + sum(len(TARGETS) if a["scope"] == "node" else 1
                   for a in arms_for(base))


# ---------------------------------------------------------------------------
# The model, with ceilings on any number of columns at its own capacity step.
# ---------------------------------------------------------------------------

_ZERO_ROUND = {"raw": 0.0, "blocked": 0.0, "columns": 0}


class LimitNetwork(_A54.PenaltyNetwork):
    """A54's class with the one ceiling written as many.

    ``lim_cap`` is a level per node, infinite where there is none. ``lim_theta``
    is the share of its routed inflow a node can take in for a reason other
    than a ceiling; this stage never sets it, the next one does. With neither
    set nothing here writes anything the round reads.

    **Who takes what is turned away.** Only a node with no ceiling and no limit
    of its own. So a ceiling can never be overrun by what another ceiling
    turned away, and one pass settles every column: no column's routed inflow
    depends on another column's share.
    """

    def __init__(self, config: NetworkConfig) -> None:
        super().__init__(config)
        n = self._n
        self.lim_cap: np.ndarray | None = None
        self.lim_theta: np.ndarray | None = None
        #: A seeded fault, set only by ``--selftest``.
        self.lim_fault: str | None = None
        #: This round: the share each column took in (None when no column was
        #: held back), and the totals over the columns that carry a limit.
        self.lim_theta_used: np.ndarray | None = None
        self.lim_round = dict(_ZERO_ROUND)
        #: Summed over the run: turned away from each column, landed on each.
        self.lim_blocked_by = np.zeros(n)
        self.lim_diverted_to = np.zeros(n)

    def _greedy_reroute(self, route: np.ndarray, spent: np.ndarray) -> np.ndarray:
        # The model's own step, then the limits, then A54's taps. A54's single
        # ceiling (``pen_cap``) is never set on this class.
        route = Network._greedy_reroute(self, route, spent)
        self.lim_theta_used = None
        self.lim_round = dict(_ZERO_ROUND)
        if self.lim_cap is not None or self.lim_theta is not None:
            route = self._limit(route, spent)
        self.tap_spent, self.tap_route = spent, route
        below = self._below
        self.tap_below = below
        self.tap_floor_capped = below & (
            np.maximum(self.holdings, 0.0) < self.config.subsistence.need)
        return route

    def _limit(self, route: np.ndarray, spent: np.ndarray) -> np.ndarray:
        """Scale every limited column to what it can take, and spread the rest
        of each payment over the payer's counterparties that carry no limit.

        For one capped column this is A54's ``_cap_route`` term for term: the
        same ``room``, the same ``theta``, the same row scale
        ``(1 - theta * col) / (1 - col)``.
        """
        n = self._n
        theta = np.ones(n)
        closed = np.zeros(n, dtype=bool)
        if self.lim_theta is not None:
            theta = np.minimum(theta, self.lim_theta)
            closed |= theta < 1.0
        capped = np.zeros(0, dtype=int)
        routed = 0.0
        if self.lim_cap is not None:
            capped = np.flatnonzero(np.isfinite(self.lim_cap))
            if self.lim_fault != "divert_to_capped":
                closed[capped] = True
            for c in capped:
                raw = float(spent @ route[:, c])
                routed += raw
                room = float(self.lim_cap[c]) - (float(self.holdings[c])
                                                 - float(spent[c]))
                if raw <= 0.0 or theta[c] * raw <= room:
                    continue
                theta[c] = max(room, 0.0) / raw
                closed[c] = True
        if not (theta < 1.0).any():
            # Nothing held back this round: the routed inflow of the capped
            # columns still counts in what a ceiling could have turned away.
            self.lim_round = {"raw": routed, "blocked": 0.0, "columns": 0}
            return route
        cols = np.flatnonzero(closed)
        sub = route[:, cols]
        t_cols = theta[cols]
        closed_w = sub.sum(axis=1)
        adm_w = (sub * t_cols[None, :]).sum(axis=1)
        payers = closed_w > 0.0
        if (closed_w[payers] >= 1.0 - 1e-12).any():
            raise RuntimeError(
                "a payer of a limited node has no counterparty without a limit "
                "to spend on; this carrier has none, so the branch is not built")
        scale = np.ones(n)
        scale[payers] = (1.0 - adm_w[payers]) / (1.0 - closed_w[payers])
        out = route * scale[:, None]
        out[:, cols] = sub * t_cols[None, :]
        # The books of the limits; none of this is read by the round.
        flows = spent[:, None] * sub
        blocked = (flows * (1.0 - t_cols)[None, :]).sum(axis=0)
        gain = (spent * (scale - 1.0)) @ route
        gain[cols] = 0.0
        self.lim_theta_used = theta
        self.lim_blocked_by[cols] += blocked
        self.lim_diverted_to += gain
        self.lim_round = {"raw": float(flows.sum()),
                          "blocked": float(blocked.sum()),
                          "columns": int((theta < 1.0).sum())}
        return out


# ---------------------------------------------------------------------------
# The driver.
# ---------------------------------------------------------------------------

def drive(cfg: NetworkConfig, arm: dict, twin: dict, node: int | None = None,
          fault: str | None = None) -> tuple:
    """One capped run, acting only at the yield, read against ``twin``."""
    net = LimitNetwork(cfg)
    if fault in ("divert_to_capped",):
        net.lim_fault = fault
    n = net._n
    if arm["scope"] == "node":
        if node is None:
            raise ValueError("a ceiling on one node needs the node")
        nodes = np.array([node], dtype=int)
    else:
        nodes = np.flatnonzero(twin["layers"] == "fin")
    sig = twin["sig"]
    span = ROUNDS - FIRST
    seen = {
        "books": True, "guard": True, "nodes": nodes,
        "raw": np.zeros(ROUNDS), "blocked": np.zeros(ROUNDS),
        "columns": np.zeros(ROUNDS, dtype=int),
        "over_closes": 0, "over_max": 0.0, "lifted_at": None,
        "blocked_after_lift": 0.0,
        "switch": np.zeros(span, dtype=bool),
    }
    level = None
    for t in net._run_steps():
        # -- the round that just closed ------------------------------------
        if t >= FIRST:
            i = t - FIRST
            seen["switch"][i] = bool(
                (net.tap_below != sig["below"][i]).any()
                or (net.tap_floor_capped != sig["floor_capped"][i]).any()
                or (net.tap_short != sig["short"][i]).any())
            r = net.lim_round
            seen["raw"][t], seen["blocked"][t] = r["raw"], r["blocked"]
            seen["columns"][t] = r["columns"]
            if seen["lifted_at"] is not None and t > seen["lifted_at"]:
                seen["blocked_after_lift"] += r["blocked"]
            if net.lim_cap is not None and level is not None:
                lev = level[nodes]
                excess = net.holdings[nodes] - lev
                edge = 1e-9 * np.maximum(1.0, lev)
                routed = net.tap_spent @ net.tap_route[:, nodes]
                used = (np.ones(nodes.size) if net.lim_theta_used is None
                        else net.lim_theta_used[nodes])
                # A column that turned some inflow away and let some in has
                # to close exactly at its level.
                if ((used < 1.0) & (routed > 0.0)
                        & (np.abs(excess) > edge)).any():
                    seen["guard"] = False
                over = excess > edge
                if over.any():
                    seen["over_closes"] += int(over.sum())
                    seen["over_max"] = max(seen["over_max"],
                                           float(excess[over].max()))
                    # Above the level at a close is allowed in one case: the
                    # column was shut, and what put it there came along no edge.
                    if (routed[over] != 0.0).any():
                        seen["guard"] = False
        # -- act at the close: never at the last one -------------------------
        if t == ROUNDS - 1:
            pass
        elif t == PENALTY_ROUND:
            level = np.full(n, np.inf)
            level[nodes] = arm["size"] * net.holdings[nodes]
            net.lim_cap = level
            seen["level"] = level
        elif (arm.get("lift") and t == PENALTY_ROUND + arm["lift"]
              and fault != "lift_never"):
            net.lim_cap = None
            seen["lifted_at"] = t
        if arm.get("lift") and t == PENALTY_ROUND + arm["lift"] \
                and fault == "lift_never":
            seen["lifted_at"] = t
        if not _A54._books(net, cfg):
            seen["books"] = False
    seen["rng"] = _A54._rng_digest(net)
    seen["below_close"] = net._below.copy()
    seen["diverted_to_capped"] = float(net.lim_diverted_to[nodes].sum())
    seen["blocked_by"] = net.lim_blocked_by.copy()
    seen["diverted_to"] = net.lim_diverted_to.copy()
    return net, seen


# ---------------------------------------------------------------------------
# Readings.
# ---------------------------------------------------------------------------

def lift_state(at_lift, end, band) -> str:
    if band is None or at_lift is None or end is None:
        return "no band"
    if abs(at_lift) <= band:
        return "nothing to give back"
    if abs(end) <= band:
        return "back"
    return "not back" if end * at_lift > 0.0 else "reversed"


def back_after(dev: np.ndarray, start: int, band) -> int | None:
    """The first m >= 1 with every round from ``start + m`` on inside the
    band. None if the last round is outside it."""
    if band is None:
        return None
    inside = np.abs(dev[start + 1:]) <= band
    if not inside.size or not inside[-1]:
        return None
    out = np.flatnonzero(~inside)
    return int(out[-1]) + 2 if out.size else 1


def _layer_shares(hold: np.ndarray, lay: np.ndarray) -> dict:
    circ = hold.sum(axis=1)
    return {L: hold[:, lay == L].sum(axis=1) / circ for L in LAYERS}


def read_arm(twin: dict, base: dict, who: str, arm: dict, net: Network,
             seen: dict) -> dict:
    """One capped run against its twin. ``who`` is the target, or ``layer``."""
    h = net._history
    hold = np.asarray(h.holdings, dtype=float)
    circ = hold.sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    flow = np.asarray(h.total_volume, dtype=float)
    wage = np.asarray(h.wage_paid, dtype=float)
    issued = np.asarray(h.issuance, dtype=float)
    lay = twin["layers"]
    nodes = seen["nodes"]
    lift = arm.get("lift")
    switch = seen["switch"] | ((issued[FIRST:] > 0.0)
                               != (twin["issued"][FIRST:] > 0.0))
    below_diff = int(seen["below_close"].sum() - twin["below_close"].sum())
    t_flow = float(twin["flow"][-TAIL:].mean())
    t_circ = float(twin["circ"][-TAIL:].mean())
    t_wage = float(twin["wage_paid"][-TAIL:].mean())
    on = slice(FIRST, ROUNDS) if not lift else slice(FIRST,
                                                     PENALTY_ROUND + lift + 1)
    raw_on = float(seen["raw"][on].sum())
    row = dict(base)
    row.update({
        "who": who, "arm": arm_label(arm), "kind": "cap",
        "scope": arm["scope"], "size": arm["size"], "lift": lift,
        "capped_nodes": int(nodes.size),
        "books_close": bool(seen["books"]),
        "same_draws_as_twin": seen["rng"] == twin["rng"],
        "guard": bool(seen["guard"]),
        "rounds_bitten": int((seen["columns"][on] > 0).sum()),
        "rounds_on": int(on.stop - on.start),
        "turned_away_share": (_num(float(seen["blocked"][on].sum()) / raw_on)
                              if raw_on > 0 else None),
        "over_closes": int(seen["over_closes"]),
        "over_max": float(seen["over_max"]),
        "diverted_to_capped": float(seen["diverted_to_capped"]),
        "blocked_after_lift": (float(seen["blocked_after_lift"])
                               if lift else None),
        "lifted": (seen["lifted_at"] is not None) if lift else None,
        "switch_rounds": int(switch.sum()),
        "switches_as_twin": not bool(switch.any()),
        "flow_tail_ratio": (_num(flow[-TAIL:].mean() / t_flow)
                            if t_flow > 0 else None),
        "circulating_tail_ratio": (_num(circ[-TAIL:].mean() / t_circ)
                                   if t_circ > 0 else None),
        "wage_tail_ratio": (_num(wage[-TAIL:].mean() / t_wage)
                            if t_wage > 0 else None),
        "below_diff_close": below_diff, "flip": _A54.flip(below_diff),
        "extra_issued_after": float(issued[FIRST:].sum()
                                    - twin["issued"][FIRST:].sum()),
    })
    total = float(seen["blocked_by"].sum())
    if total > 0.0:
        row["turned_away_to"] = {
            L: float(seen["diverted_to"][lay == L].sum() / total)
            for L in LAYERS}
    # The path this arm is read on: one node's share, or the layer's.
    if arm["scope"] == "node":
        node = int(nodes[0])
        s_c, _ = _A54.shares(hold[:, node], circ, parked)
        b_c, _ = _A54.shares(twin["H"][:, node], twin["circ"], twin["parked"])
        jitter = twin["jitter"][who]
        row["node"] = node
        row["log_slope_tail"] = _A54.log_slope(hold[-TAIL:, node])
        row["twin_log_slope_tail"] = _A54.log_slope(twin["H"][-TAIL:, node])
    else:
        s_c = hold[:, nodes].sum(axis=1) / circ
        b_c = twin["H"][:, nodes].sum(axis=1) / twin["circ"]
        jitter = _A54.share_jitter(twin["H"][-TAIL:, nodes].sum(axis=1),
                                   twin["circ"][-TAIL:])
        mine, theirs = _layer_shares(hold, lay), _layer_shares(twin["H"], lay)
        diff = {L: mine[L] - theirs[L] for L in LAYERS}
        row.update({
            # Shares of the trading accounts by layer, less the twin's: the
            # four add to zero, so what the capped layer gives up is read off
            # the other three.
            "layer_share_twin_tail": {L: float(theirs[L][-TAIL:].mean())
                                      for L in LAYERS},
            "layer_diff_tail": {L: float(diff[L][-TAIL:].mean())
                                for L in LAYERS},
            "layer_diff_at": {str(k): {L: float(diff[L][PENALTY_ROUND + k])
                                       for L in LAYERS} for k in AT},
            "layer_diff_sum_tail": float(sum(diff[L][-TAIL:].mean()
                                             for L in LAYERS)),
            "layer_slope_tail": {
                L: _A54.log_slope(hold[-TAIL:, lay == L].sum(axis=1))
                for L in LAYERS},
            "twin_layer_slope_tail": {
                L: _A54.log_slope(twin["H"][-TAIL:, lay == L].sum(axis=1))
                for L in LAYERS},
            "balance_ratio_tail": {
                L: (_num(hold[-TAIL:, lay == L].mean()
                         / twin["H"][-TAIL:, lay == L].mean())
                    if twin["H"][-TAIL:, lay == L].mean() > 0 else None)
                for L in LAYERS},
        })
    with np.errstate(divide="ignore", invalid="ignore"):
        dev = s_c / b_c - 1.0
    band = None if jitter is None else FLOOR_MULTIPLE * jitter
    row.update({
        "band": _num(band),
        "first_round": _num(dev[FIRST]),
        "tail": _num(dev[-TAIL:].mean()),
        "deviation_at": {str(k): _num(dev[PENALTY_ROUND + k]) for k in AT},
        "_path": dev[FIRST:].copy(),
    })
    if lift:
        at_i = PENALTY_ROUND + lift
        at_lift = _num(dev[at_i])
        end = _num(dev[-END:].mean())
        nxt = _num(dev[at_i + 1])
        row.update({
            "at_lift": at_lift, "end": end,
            "after_lift": {str(m): _num(dev[at_i + m]) for m in AFTER_LIFT
                           if at_i + m < ROUNDS},
            "rounds_after_lift": ROUNDS - 1 - at_i,
            "back_after": back_after(dev, at_i, band),
            "first_step": (_num(nxt / at_lift) if at_lift is not None
                           and nxt is not None and band is not None
                           and abs(at_lift) > band else None),
            "state": lift_state(at_lift, end, band),
        })
    else:
        ratio, state = _A54.permanence(_num(dev[FIRST]), row["tail"], band)
        row.update({"permanence": _num(ratio), "state": state})
    return row


def twin_row(base: dict, twin: dict) -> dict:
    lay = twin["layers"]
    at = twin["at"]
    R = at["route"] > 0.0
    fin = lay == "fin"
    shares = _layer_shares(twin["H"], lay)
    row = dict(base)
    row.update({
        "who": "twin", "arm": "twin", "kind": "twin",
        "books_close": bool(twin["books"]),
        "below_close": int(twin["below_close"].sum()),
        "circulating_at_penalty": float(at["holdings"].sum()),
        "issued_after": float(twin["issued"][FIRST:].sum()),
        "injection_node_layer": str(lay[twin["net"].injection_node]),
        "layer_share_at_penalty": {
            L: float(at["holdings"][lay == L].sum() / at["holdings"].sum())
            for L in LAYERS},
        "layer_share_tail": {L: float(shares[L][-TAIL:].mean())
                             for L in LAYERS},
        "layer_slope_tail": {
            L: _A54.log_slope(twin["H"][-TAIL:, lay == L].sum(axis=1))
            for L in LAYERS},
        # What the layer ceiling leans on: who pays into the financial layer,
        # and whether each of them has somewhere else to spend.
        "payers_of_financial_layer": int(R[:, fin].any(axis=1).sum()),
        "of_them_with_no_other_counterparty": int(
            (R[:, fin].any(axis=1) & ~R[:, ~fin].any(axis=1)).sum()),
        "routing_edges_into_households": int(
            R[:, (lay == "hhw") | (lay == "hh0")].sum()),
        "wage_tail": float(twin["wage_paid"][-TAIL:].mean()),
    })
    return row


def one_base(base: dict, arms=None, faults=None) -> list:
    """One configuration and seed: the twin, then every arm."""
    cfg = base_config(base)
    twin = _A54.make_twin(cfg)
    rows = [twin_row(base, twin)]
    for arm in (arms_for(base) if arms is None else arms):
        fault = None if faults is None else faults.get(arm_label(arm))
        if arm["scope"] == "node":
            for kind in TARGETS:
                node = twin["nodes"][kind]["node"]
                net, seen = drive(cfg, arm, twin, node, fault)
                rows.append(read_arm(twin, base, kind, arm, net, seen))
        else:
            net, seen = drive(cfg, arm, twin, None, fault)
            rows.append(read_arm(twin, base, "layer", arm, net, seen))
    return rows


# ---------------------------------------------------------------------------
# Running the grid, and the groups.
# ---------------------------------------------------------------------------

def _row_sort(x: dict) -> tuple:
    return _A54._base_sort(x) + (
        WHO.index(x["who"]) if x["who"] in WHO else -1,
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


def _median(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.median(vals)) if vals else None


def _count(items) -> dict:
    out: dict = {}
    for it in items:
        key = "none" if it is None else str(it)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _cell(x: dict) -> tuple:
    return (x["block"], x["need"], x["stress"], x["elasticity"],
            x["authority"])


def groups(rows: list) -> list:
    """Medians over seeds of every cell, target and arm, with the path."""
    keyed: dict = {}
    for x in _arms(rows):
        keyed.setdefault(_cell(x) + (x["who"], x["arm"]), []).append(x)
    out = []
    for key in sorted(keyed, key=lambda k: _row_sort(keyed[k][0])):
        xs = keyed[key]
        first = xs[0]
        g = {k: first[k] for k in ("block", "need", "stress", "elasticity",
                                   "authority", "who", "arm", "kind", "scope",
                                   "size", "lift")}
        paths = np.vstack([x["_path"] for x in xs])
        with np.errstate(all="ignore"):
            med_path = np.nanmedian(paths, axis=0)
        g.update({
            "seeds": sorted(x["seed"] for x in xs),
            "band_median": _median(x["band"] for x in xs),
            "tail_median": _median(x["tail"] for x in xs),
            "states": _count(x["state"] for x in xs),
            "flips": _count(x["flip"] for x in xs),
            "flow_tail_ratio_median": _median(x["flow_tail_ratio"]
                                              for x in xs),
            "wage_tail_ratio_median": _median(x["wage_tail_ratio"]
                                              for x in xs),
            "turned_away_share_median": _median(x["turned_away_share"]
                                                for x in xs),
            "median_path": [None if not np.isfinite(v) else float(v)
                            for v in med_path],
        })
        if first["lift"]:
            g.update({
                "at_lift_median": _median(x["at_lift"] for x in xs),
                "end_median": _median(x["end"] for x in xs),
                "back_after_median": _median(x["back_after"] for x in xs),
                "first_step_median": _median(x["first_step"] for x in xs),
            })
        if first["scope"] == "layer":
            g["layer_diff_tail_median"] = {
                L: _median(x["layer_diff_tail"][L] for x in xs)
                for L in LAYERS}
        out.append(g)
    return out


# ---------------------------------------------------------------------------
# Criteria. Each flag is computed from the rows, and --selftest feeds each one
# a wrong input.
# ---------------------------------------------------------------------------

def _gate_section():
    if not RECORD.exists():
        return None
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    return doc.get("sections", {}).get("gate")


def _gate_allows(g) -> tuple:
    if not g:
        return False, "no gate section in the record: run --gate first"
    for key, path, what in (("module_sha", MODULE, "network.py"),
                            ("script_sha", SCRIPT, "this script"),
                            ("a54_sha", A54_SCRIPT, "a54_penalty.py")):
        if g.get(key) != _module_sha(path):
            return False, "%s has changed since the gate ran: run --gate again" % what
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and these scripts"


def criterion_a55_0(g) -> Criterion:
    name = ("A55-0 the class is the model, and with one ceiling it is A54's "
            "class")
    if g is None:
        return Criterion(name, "instrument", False,
                         "not evaluated: no gate section", evaluated=False)
    ok, why = _gate_allows(g)
    detail = ("%d configurations, %d runs: with no ceiling the class and "
              "Network.run() agree on %d fields in %s; one ceiling on either "
              "target against A54's class, and every arm with an infinite "
              "ceiling against the twin, %s. %s"
              % (len(g.get("configs", [])), g.get("runs", 0),
                 g.get("fields_compared", 0),
                 "every run" if not g.get("differ") else
                 "all but %d" % len(g["differ"]),
                 "identical" if not g.get("differ") else "DIFFER", why))
    return Criterion(name, "instrument", bool(ok and not g.get("differ")),
                     detail)


def criterion_a55_1(rows: list) -> Criterion:
    arms = _arms(rows)
    twins = [x for x in rows if x["kind"] == "twin"]
    books = sum(1 for x in rows if x["books_close"])
    draws = sum(1 for x in arms if x["same_draws_as_twin"])
    guard = sum(1 for x in arms if x["guard"])
    clean = sum(1 for x in arms if x["diverted_to_capped"] == 0.0)
    lifted = [x for x in arms if x["lift"]]
    done = sum(1 for x in lifted if x["lifted"]
               and x["blocked_after_lift"] == 0.0)
    bit = sum(1 for x in arms if x["rounds_bitten"] > 0)
    over = sum(1 for x in arms if x["over_closes"] > 0)
    nowhere = sum(x["of_them_with_no_other_counterparty"] for x in twins)
    ok = (bool(arms) and books == len(rows) and draws == len(arms)
          and guard == len(arms) and clean == len(arms)
          and done == len(lifted))
    return Criterion(
        "A55-1 the ceilings hold, and what they turn away goes where the rule "
        "says", "instrument", ok,
        "claim total equal to held plus parked at every yield in %d of %d "
        "runs; generators end where the twin's do in %d of %d; no capped node "
        "closes above its level with inflow let in, and a column that turned "
        "some away and let some in closes at its level, in %d of %d (%d runs "
        "had a close above the level with the column shut); nothing turned "
        "away landed on a capped node in %d of %d; a lifted ceiling was "
        "lifted and turned nothing away afterwards in %d of %d. The ceiling "
        "bit in %d of %d runs. Payers of the financial layer with no "
        "counterparty outside it, over all twins: %d"
        % (books, len(rows), draws, len(arms), guard, len(arms), over, clean,
           len(arms), done, len(lifted), bit, len(arms), nowhere))


def criterion_a55_2(rows: list) -> Criterion:
    """Lifted ceilings on one node. The registered reading: where no switch
    left the twin's setting the two runs are one affine map, so the share
    comes back."""
    xs = [x for x in _arms(rows) if x["lift"] and x["scope"] == "node"]
    names = {s for s, _ in LIFT_STATES}
    mapped = all(x["state"] in names for x in xs)
    moved = ("back", "not back", "reversed")
    read = [x for x in xs if x["state"] in moved]
    unread = [x for x in xs if x["state"] not in moved]
    plain = [x for x in read if x["switches_as_twin"]]
    stuck = [x for x in plain if x["state"] != "back"]
    flipped = [x for x in read if not x["switches_as_twin"]]
    parts = []
    for kind in TARGETS:
        ks = [x for x in read if x["who"] == kind]
        if not ks:
            continue
        parts.append(
            "%s target: %s; share against the twin's when the ceiling came "
            "off %s (median), one round later that gap times %s, back inside "
            "the band for good after %s rounds" % (
                kind, _fmt_count(_count(x["state"] for x in ks)),
                _pct(_median(x["at_lift"] for x in ks)),
                _g(_median(x["first_step"] for x in ks)),
                _g(_median(x["back_after"] for x in ks))))
    ok = bool(xs) and mapped and bool(plain) and not stuck
    return Criterion(
        "A55-2 a ceiling taken off: the share comes back", "own_reading", ok,
        "%d lifted cells, %d read (the rest: %s). Where every switch stayed "
        "as the twin's, %d of %d are back; where one flipped, %d of %d. %s"
        % (len(xs), len(read),
           _fmt_count(_count(x["state"] for x in unread)) or "none",
           len(plain) - len(stuck), len(plain),
           sum(1 for x in flipped if x["state"] == "back"), len(flipped),
           "; ".join(parts)))


def criterion_a55_3(rows: list) -> Criterion:
    """A ceiling on every financial node, kept. The registered reading: what
    the layer gives up lands on the intermediate layer, and households see it
    only as far as wages follow sales."""
    bit = [x for x in _arms(rows) if x["scope"] == "layer" and not x["lift"]
           and x["rounds_bitten"] > 0]
    # Read where the layer's own share has left its band: a ceiling at the
    # balance on a graph that is not growing bites on jitter and moves nothing.
    xs = [x for x in bit if x["band"] is not None and x["tail"] is not None
          and abs(x["tail"]) > x["band"]]
    if not xs:
        return Criterion("A55-3 a ceiling on the whole layer: where its "
                         "share goes", "own_reading", False,
                         "no layer cell in which the layer's share left its "
                         "band (%d in which the ceiling bit)" % len(bit))
    closes = max(abs(x["layer_diff_sum_tail"]) for x in xs)
    mid_up = sum(1 for x in xs if x["layer_diff_tail"]["mid"] > 0.0)
    fin_down = sum(1 for x in xs if x["layer_diff_tail"]["fin"] < 0.0)
    keyed = {}
    for x in xs:
        keyed[(x["block"], x["need"], x["stress"], x["authority"], x["seed"],
               x["arm"], x["elasticity"])] = x
    pairs = []
    for k, rigid in keyed.items():
        if k[-1] != 0.0:
            continue
        elastic = keyed.get(k[:-1] + (0.5,))
        if elastic is not None:
            pairs.append(elastic["layer_diff_tail"]["hhw"]
                         - rigid["layer_diff_tail"]["hhw"])
    more = sum(1 for d in pairs if d > 0.0)
    med_pair = _median(pairs)
    parts = []
    for block in ("main", "growth"):
        for arm in ARM_ORDER:
            ks = [x for x in xs if x["block"] == block and x["arm"] == arm]
            if not ks:
                continue
            parts.append(
                "%s %s (%d cells): share of the trading accounts against the "
                "twin's, in points, financial %s, intermediate %s, households "
                "on a payroll %s, off it %s; total flow %s of the twin's, "
                "wages %s" % (
                    block, arm, len(ks),
                    *(_pts(_median(x["layer_diff_tail"][L] for x in ks))
                      for L in LAYERS),
                    _g(_median(x["flow_tail_ratio"] for x in ks)),
                    _g(_median(x["wage_tail_ratio"] for x in ks))))
    ok = (closes < 1e-9 and fin_down == len(xs) and mid_up > len(xs) / 2.0
          and med_pair is not None and med_pair > 0.0)
    return Criterion(
        "A55-3 a ceiling on the whole layer: where its share goes",
        "own_reading", ok,
        "%d cells in which the layer's share left its band; the four layers' "
        "differences add to zero within %.1e. Financial layer lower in %d of "
        "%d, intermediate "
        "layer higher in %d of %d. Households on a payroll, elastic wages "
        "less rigid wages in the same cell and seed: higher in %d of %d "
        "pairs, median %s points. %s"
        % (len(xs), closes, fin_down, len(xs), mid_up, len(xs), more,
           len(pairs), _pts(med_pair), "; ".join(parts)))


def criterion_a55_4(grp: list) -> Criterion:
    span = ROUNDS - FIRST
    names = ({s for s, _ in LIFT_STATES}
             | {s for s, _ in _A54.PERMANENCE_STATES})
    paths = sum(1 for g in grp if len(g.get("median_path") or []) == span)
    mapped = sum(1 for g in grp if set(g["states"]) <= names)
    ok = bool(grp) and paths == len(grp) and mapped == len(grp)
    return Criterion(
        "A55-4 every group carries its path and its states", "bookkeeping", ok,
        "%d groups: the median path over all %d rounds after the penalty in "
        "%d, states from the two maps in %d" % (len(grp), span, paths, mapped))


def _pct(v) -> str:
    return "n/a" if v is None else "%+.1f%%" % (100.0 * v)


def _pts(v) -> str:
    return "n/a" if v is None else "%+.2f" % (100.0 * v)


def _g(v) -> str:
    return "n/a" if v is None else "%.4g" % v


def _fmt_count(c: dict) -> str:
    return ", ".join("%s %d" % kv for kv in c.items())


def analyse(rows: list, gate_section) -> tuple:
    grp = groups(rows)
    crits = [criterion_a55_0(gate_section), criterion_a55_1(rows),
             criterion_a55_2(rows), criterion_a55_3(rows),
             criterion_a55_4(grp)]
    arms = _arms(rows)
    sections = {
        "criteria": [c.as_dict() for c in crits],
        "layout": "every section below criteria is a table: fields names the "
                  "columns once, nested readings as dotted names, and rows "
                  "holds one record per line in that order",
        "states": {"lifted": dict(LIFT_STATES),
                   "kept": dict(_A54.PERMANENCE_STATES),
                   "flip": dict(_A54.FLIP_STATES)},
        "groups": _A54._table(grp),
        "rows": {"twin": _A54._table([x for x in rows if x["kind"] == "twin"]),
                 "node": _A54._table([x for x in arms if x["scope"] == "node"]),
                 "layer": _A54._table([x for x in arms
                                       if x["scope"] == "layer"])},
    }
    return crits, sections


# ---------------------------------------------------------------------------
# Rule 19: the class against the model, and against A54's class.
# ---------------------------------------------------------------------------

def _plain(cfg: NetworkConfig) -> LimitNetwork:
    net = LimitNetwork(cfg)
    for _ in net._run_steps():
        pass
    return net


def gate_configs(bases=None) -> list:
    out = [("library default", NetworkConfig(), None)]
    for b in (base_keys(seeds=SEEDS[:1]) if bases is None else bases):
        out.append(("%s need %.2f %s e %.1f %s" % (
            b["block"], b["need"], b["stress"], b["elasticity"],
            b["authority"]), base_config(b), b))
    return out


def gate(configs: list) -> dict:
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    closing = _A54.CLOSING

    def differs(ref_hist, ref_net, ref_rng, hist, net, rng) -> list:
        bad = [n for n in names if not _same(getattr(ref_hist, n),
                                             getattr(hist, n))]
        bad += [n for n in closing if not _same(getattr(ref_net, n),
                                                getattr(net, n))]
        if ref_rng != rng:
            bad.append("generators")
        return bad

    differ, labels, runs = [], [], 0
    for label, cfg, base in configs:
        t0 = time.perf_counter()
        ref = Network(cfg)
        h_ref = ref.run()
        mine = _plain(cfg)
        bad = differs(h_ref, ref, _A54._rng_digest(ref), mine._history, mine,
                      _A54._rng_digest(mine))
        runs += 2
        if bad:
            differ.append({"run": "%s, no ceiling" % label, "fields": bad})
        off = 0
        if base is not None:
            twin = _A54.make_twin(cfg)
            tnet = twin["net"]
            runs += 1
            level = (KEPT_GROWTH if base["block"] == "growth"
                     else KEPT_MAIN)[0]
            checks = []
            for kind in TARGETS:
                node = twin["nodes"][kind]["node"]
                theirs, t_seen = _A54.drive(cfg, node, _A54._cap(level), twin)
                net, seen = drive(cfg, _arm("node", level), twin, node)
                checks.append(("%s target, one ceiling at %g against A54's "
                               "class" % (kind, level),
                               differs(theirs._history, theirs, t_seen["rng"],
                                       net._history, net, seen["rng"])))
                z, zs = drive(cfg, _arm("node", float("inf")), twin, node)
                checks.append(("%s target, infinite ceiling" % kind,
                               differs(tnet._history, tnet, twin["rng"],
                                       z._history, z, zs["rng"])))
                runs += 3
            for lift in (None, 50):
                z, zs = drive(cfg, _arm("layer", float("inf"), lift), twin)
                checks.append(("layer, infinite ceiling%s"
                               % (" lifted" if lift else ""),
                               differs(tnet._history, tnet, twin["rng"],
                                       z._history, z, zs["rng"])))
                runs += 1
            for what, zbad in checks:
                if zbad:
                    off += 1
                    differ.append({"run": "%s, %s" % (label, what),
                                   "fields": zbad})
        labels.append(label)
        print("   %-44s %s; against A54 and at infinity: %s  (%.1f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "identical" if not off else "%d DIFFER" % off,
            time.perf_counter() - t0))
    return {
        "module_sha": _module_sha(MODULE),
        "script_sha": _module_sha(SCRIPT),
        "a54_sha": _module_sha(A54_SCRIPT),
        "configs": labels,
        "fields_compared": len(names) + len(closing) + 1,
        "runs": runs,
        "differ": differ,
        "verdict": "pass" if not differ else "fail",
    }


# ---------------------------------------------------------------------------
# Seeded faults.
# ---------------------------------------------------------------------------

def selftest() -> dict:
    checks: list = []

    def note(what: str, held: bool, detail: str = "") -> None:
        checks.append({"check": what, "held": bool(held), "detail": detail})
        print("   [%s] %s%s" % ("ok" if held else "MISSED", what,
                                " : " + detail if detail else ""))

    # -- pure functions ----------------------------------------------------
    note("lift_state: back, not back, reversed, nothing, no band",
         [lift_state(-0.3, 0.001, 0.01), lift_state(-0.3, -0.2, 0.01),
          lift_state(-0.3, 0.2, 0.01), lift_state(0.001, 0.5, 0.01),
          lift_state(-0.3, 0.0, None)]
         == ["back", "not back", "reversed", "nothing to give back",
             "no band"])
    d = np.array([0.0, -0.5, -0.2, 0.004, -0.02, 0.003, 0.001])
    note("back_after: the first round from which every round is inside",
         back_after(d, 1, 0.01) == 4 and back_after(d, 1, 0.0005) is None
         and back_after(d, 4, 0.01) == 1,
         "%s %s %s" % (back_after(d, 1, 0.01), back_after(d, 1, 0.0005),
                       back_after(d, 4, 0.01)))

    # -- the limiter on a hand-made round ------------------------------------
    base = {"block": "main", "need": 0.20, "stress": "healthy",
            "elasticity": 0.5, "authority": "none", "seed": SEEDS[0]}
    cfg = base_config(base)
    net = LimitNetwork(cfg)
    n = net._n
    rng = np.random.default_rng(55)
    route = np.zeros((n, n))
    for i in range(n):
        js = rng.choice([j for j in range(n) if j != i], size=5, replace=False)
        route[i, js] = 0.2
    # One payer that pays both a column that will be full and one that will
    # have room, so the seeded fault below has something to spill.
    route[0] = 0.0
    route[0, [3, 19, 50, 51, 52]] = 0.2
    spent = rng.uniform(0.1, 1.0, n)
    net.holdings = rng.uniform(1.0, 2.0, n)
    capped = np.array([3, 7, 11])
    net.lim_cap = np.full(n, np.inf)
    inflow = spent @ route
    net.lim_cap[capped] = (net.holdings - spent)[capped] + 0.5 * inflow[capped]
    out = net._limit(route, spent)
    got = spent @ out
    note("limiter: rows still sum to one",
         bool(np.allclose(out.sum(axis=1), 1.0, atol=1e-12)))
    note("limiter: each capped column takes in exactly its room",
         bool(np.allclose(got[capped], 0.5 * inflow[capped], rtol=1e-12)),
         "%s" % (got[capped] / inflow[capped]))
    others = np.setdiff1d(np.arange(n), capped)
    note("limiter: what is turned away lands on the columns with no ceiling",
         bool(abs((got[others] - inflow[others]).sum()
                  - 0.5 * inflow[capped].sum()) < 1e-10)
         and float(net.lim_diverted_to[capped].sum()) == 0.0)
    roomy = LimitNetwork(cfg)
    roomy.holdings = net.holdings.copy()
    roomy.lim_cap = net.lim_cap.copy()
    roomy.lim_cap[7] = np.inf
    roomy.lim_cap[19] = (roomy.holdings - spent)[19] + 1.0001 * inflow[19]
    ok_out = roomy._limit(route, spent)
    roomy2 = LimitNetwork(cfg)
    roomy2.holdings = net.holdings.copy()
    roomy2.lim_cap = roomy.lim_cap.copy()
    roomy2.lim_fault = "divert_to_capped"
    bad_out = roomy2._limit(route, spent)
    room19 = 1.0001 * inflow[19]
    note("limiter: a capped column with room to spare takes none of what "
         "another turned away",
         float(spent @ ok_out[:, 19]) <= room19 * (1 + 1e-12)
         and float(spent @ bad_out[:, 19]) > room19 * (1 + 1e-9),
         "with the fault the column takes %.6f against a room of %.6f"
         % (float(spent @ bad_out[:, 19]), room19))
    one = LimitNetwork(cfg)
    one.holdings = net.holdings.copy()
    one.lim_cap = np.full(n, np.inf)
    one.lim_cap[3] = net.lim_cap[3]
    theirs = _A54.PenaltyNetwork(cfg)
    theirs.holdings = net.holdings.copy()
    theirs.pen_target, theirs.pen_cap = 3, float(net.lim_cap[3])
    note("limiter: one ceiling is A54's _cap_route to the bit",
         _same(one._limit(route, spent), theirs._cap_route(route, spent)))
    lone = route.copy()
    lone[0] = 0.0
    lone[0, 3] = 1.0
    try:
        one._limit(lone, spent)
        raised = False
    except RuntimeError:
        raised = True
    note("limiter: a payer with nowhere else to spend is refused, not "
         "silently absorbed", raised)

    # -- the driver, on one configuration ------------------------------------
    arms = arms_for(base)
    good = one_base(base, arms=arms)
    g_ok = {"module_sha": _module_sha(MODULE), "script_sha": _module_sha(SCRIPT),
            "a54_sha": _module_sha(A54_SCRIPT), "verdict": "pass",
            "differ": [], "configs": ["x"], "runs": 1, "fields_compared": 1}

    def crit(rs, index, g=g_ok):
        return analyse(rs, g)[0][index]

    note("the clean configuration passes A55-0, A55-1 and A55-4",
         all(crit(good, i).passed for i in (0, 1, 4)),
         "; ".join("%s %s" % (c.name.split()[0], c.passed)
                   for c in analyse(good, g_ok)[0]))
    lifted_label = arm_label(_arm("node", *LIFT_MAIN[0]))
    never = one_base(base, arms=arms, faults={lifted_label: "lift_never"})
    note("a ceiling that is never taken off is reported by A55-1",
         not crit(never, 1).passed)
    # At the balance some capped nodes are full and others have room in the
    # same round, which is the case the rule exists for; below the balance
    # every one of them is full and there is nothing to spill onto.
    layer_label = arm_label(_arm("layer", LAYER_MAIN[1][0]))
    spill = one_base(base, arms=arms, faults={layer_label: "divert_to_capped"})
    hit = [x for x in spill if x["arm"] == layer_label][0]
    note("what is turned away landing on capped nodes is reported by A55-1",
         not crit(spill, 1).passed,
         "landed on capped nodes %.4f, closes above a level %d, guard %s"
         % (hit["diverted_to_capped"], hit["over_closes"], hit["guard"]))

    # -- every criterion on a wrong input ------------------------------------
    def broken(change):
        rs = copy.deepcopy(good)
        change(rs)
        return rs

    def pick(rs, **want):
        return [x for x in rs if all(x.get(k) == v for k, v in want.items())]

    note("A55-0 fails when a script changed after the gate",
         not crit(good, 0, dict(g_ok, a54_sha="0" * 16)).passed
         and not crit(good, 0, dict(g_ok, differ=[{"run": "x"}])).passed)
    note("A55-1 fails on an open ledger",
         not crit(broken(lambda rs: pick(rs, kind="cap")[0].update(
             books_close=False)), 1).passed)
    note("A55-1 fails on a level overrun with inflow let in",
         not crit(broken(lambda rs: pick(rs, kind="cap")[0].update(
             guard=False)), 1).passed)

    def stay_out(rs):
        for x in pick(rs, scope="node"):
            if x["lift"] and x["switches_as_twin"] and x["state"] == "back":
                x["state"] = "not back"
                return
        raise AssertionError("no lifted cell with its switches as the twin's")

    lifted_ok = crit(good, 2)
    note("A55-2 fails when a cell with no switch flipped stays out",
         lifted_ok.passed and not crit(broken(stay_out), 2).passed,
         "clean: %s" % lifted_ok.passed)
    note("A55-2 fails on a state that is not in the map",
         not crit(broken(lambda rs: [x for x in pick(rs, scope="node")
                                     if x["lift"]][0].update(state="gone")),
                  2).passed)
    two = [b for b in base_keys(needs=(0.20,), authorities=("none",),
                                seeds=SEEDS[:1], growth=False)
           if b["stress"] == "healthy"]
    layered = [x for b in two for x in one_base(
        b, arms=[_arm("layer", LAYER_MAIN[0][0])])]
    layer_ok = crit(layered, 3)

    def swap(rs):
        for x in pick(rs, scope="layer"):
            x["layer_diff_tail"]["hhw"] = -x["layer_diff_tail"]["hhw"] \
                if x["elasticity"] == 0.5 else 1.0

    def leak(rs):
        pick(rs, scope="layer")[0]["layer_diff_sum_tail"] = 1e-3

    note("A55-3 fails when households gain more under rigid wages, and when "
         "the layers do not add to zero",
         layer_ok.passed and not crit(broken_from(layered, swap), 3).passed
         and not crit(broken_from(layered, leak), 3).passed,
         "clean: %s" % layer_ok.passed)

    def cut_path(rs):
        pick(rs, kind="cap")[0]["_path"] = pick(rs, kind="cap")[0]["_path"][:5]

    try:
        short = not crit(broken(cut_path), 4).passed
    except ValueError:
        short = True
    note("A55-4 fails on a path that is not the whole span", short)
    held = sum(1 for c in checks if c["held"])
    return {"module_sha": _module_sha(MODULE), "script_sha": _module_sha(SCRIPT),
            "checks": checks, "held": held, "of": len(checks),
            "verdict": "pass" if held == len(checks) else "fail"}


def broken_from(rows: list, change) -> list:
    rs = copy.deepcopy(rows)
    change(rs)
    return rs


# ---------------------------------------------------------------------------
# D38, the record, the tables, the entry point.
# ---------------------------------------------------------------------------

def time_bases(workers: int) -> None:
    probes = [
        {"block": "main", "need": 0.20, "stress": "healthy",
         "elasticity": 0.5, "authority": "endogenous", "seed": SEEDS[0]},
        {"block": "main", "need": 0.20, "stress": "leak_recycled",
         "elasticity": 0.5, "authority": "none", "seed": SEEDS[0]},
        {"block": "growth", "need": 0.05, "stress": "healthy",
         "elasticity": 0.0, "authority": "fixed", "seed": SEEDS[0]},
    ]
    _A54.make_twin(base_config(probes[0]))  # warm-up, not timed
    per = {}
    for b in probes:
        t0 = time.perf_counter()
        rows = one_base(b)
        dt = time.perf_counter() - t0
        per[(b["block"], b["stress"])] = dt
        print("   %-6s %-14s %-10s %3d runs  %.1f s  (%.3f s a run)" % (
            b["block"], b["stress"], b["authority"], len(rows), dt,
            dt / len(rows)))
    eff = max(1, min(workers, os.cpu_count() or 1))
    for count in (2, len(SEEDS)):
        bases = base_keys(seeds=SEEDS[:count])
        total = sum(per[(b["block"], b["stress"])] for b in bases)
        print("   %d seeds: %d configurations, %d runs, %.0f s serial, about "
              "%.0f s on %d workers" % (
                  count, len(bases), sum(runs_of(b) for b in bases), total,
                  total / eff, eff))
    gates = gate_configs()
    print("   --gate: %d configurations, about %d runs, serial"
          % (len(gates), 2 + 11 * (len(gates) - 1)))


def station_config() -> dict:
    return {
        "carrier": "A54's: A30's cells in the two strains whose twin is not "
                   "itself running down, and A54's growing block",
        "rounds": ROUNDS,
        "penalty_at_close_of_round": PENALTY_ROUND,
        "ceiling": "a multiple of each capped node's own balance at the close "
                   "of the penalty round, applied at the model's capacity "
                   "step; what a capped column cannot take is spent by its "
                   "payers on their counterparties that carry no ceiling",
        "grid": {
            "need_multiples": list(NEEDS),
            "stresses": {s: _A54.STRESS_SPECS[s] for s in STRESSES},
            "elasticities": list(ELASTICITIES),
            "authorities": list(AUTHORITIES),
            "seeds": list(SEEDS),
            "one_node_kept": list(KEPT_MAIN),
            "one_node_lifted": [list(x) for x in LIFT_MAIN],
            "layer": [list(x) for x in LAYER_MAIN],
        },
        "growing_block": {
            "strain": "healthy", "authority": "fixed",
            "issued_per_round": _A54.GROWTH_ISSUE,
            "one_node_kept": list(KEPT_GROWTH),
            "one_node_lifted": [list(x) for x in LIFT_GROWTH],
            "layer": [list(x) for x in LAYER_GROWTH],
        },
        "layer": "every node of the financial layer",
        "tail": TAIL, "end": END,
        "after_lift": list(AFTER_LIFT), "kept_at": list(AT),
        "block": BLOCK, "floor_multiple": FLOOR_MULTIPLE,
        "band": "floor_multiple times the spread of the log of the twin's "
                "share of the trading accounts about a straight line over the "
                "tail: one node's share for a ceiling on one node, the "
                "layer's for a ceiling on the layer",
        "non_default_fields": _A54.station_config()["non_default_fields"],
    }


def write_record(section: str, payload: dict) -> None:
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = STAGE
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(_A54._dump(doc), encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def _records(t: dict) -> list:
    return [dict(zip(t["fields"], row)) for row in t["rows"]]


def _md(head: list, rows: list) -> None:
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join("---" for _ in head) + "|")
    for r in rows:
        print("| " + " | ".join(str(v) for v in r) + " |")
    print()


def _m(values, digits: int = 4) -> str:
    v = _median(values)
    return "-" if v is None else "%.*f" % (digits, v)


def tables() -> int:
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    run = doc["sections"]["run"]
    print("record %s, stage %s, seeds %s; criteria: %s\n" % (
        RECORD.name, doc["stage"], run["seeds_run"], ", ".join(
            "%s %s" % (c["name"].split()[0], "PASS" if c["passed"] else "FAIL")
            for c in run["criteria"])))
    node = _records(run["rows"]["node"])
    layer = _records(run["rows"]["layer"])
    print("### lifted: a ceiling on one node, taken off again\n")
    out = []
    for block in ("main", "growth"):
        for kind in TARGETS:
            for arm in ARM_ORDER:
                xs = [x for x in node if x["block"] == block
                      and x["who"] == kind and x["arm"] == arm and x["lift"]]
                if not xs:
                    continue
                read = [x for x in xs if x["state"] != "nothing to give back"
                        and x["state"] != "no band"]
                out.append([
                    block, kind, arm, len(xs),
                    _fmt_count(_count(x["state"] for x in xs)),
                    _m(x["at_lift"] for x in read),
                    *(_m(x.get("after_lift.%d" % m) for x in read)
                      for m in (1, 2, 3, 5, 10, 20)),
                    _m(x["end"] for x in read),
                    _m((x["first_step"] for x in read), 3),
                    _m((x["back_after"] for x in read), 0),
                    sum(1 for x in read if not x["switches_as_twin"])])
    _md(["block", "target", "arm", "cells", "states", "when it came off",
         "1 round after", "2", "3", "5", "10", "20", "last %d rounds" % END,
         "gap after one round over gap before", "rounds until inside for good",
         "cells with a switch flipped"], out)
    print("### kept: the same ceilings left on, for reference\n")
    out = []
    for block in ("main", "growth"):
        for kind in TARGETS:
            for arm in ARM_ORDER:
                xs = [x for x in node if x["block"] == block
                      and x["who"] == kind and x["arm"] == arm
                      and not x["lift"]]
                if xs:
                    out.append([block, kind, arm, len(xs),
                                _fmt_count(_count(x["state"] for x in xs)),
                                *(_m(x["deviation_at.%d" % k] for x in xs)
                                  for k in AT),
                                _m(x["tail"] for x in xs)])
    _md(["block", "target", "arm", "cells", "states"]
        + ["after %d" % k for k in AT] + ["tail"], out)
    print("### layer: a ceiling on every financial node\n")
    out = []
    for block in ("main", "growth"):
        for arm in ARM_ORDER:
            for e in ELASTICITIES:
                xs = [x for x in layer if x["block"] == block
                      and x["arm"] == arm and x["elasticity"] == e]
                if not xs:
                    continue
                out.append([
                    block, arm, "%g" % e, len(xs),
                    sum(1 for x in xs if x["rounds_bitten"] > 0),
                    _m((x["turned_away_share"] for x in xs), 3),
                    *(_m((100.0 * x["layer_diff_tail.%s" % L] for x in xs), 2)
                      for L in LAYERS),
                    *(_m((x.get("turned_away_to.%s" % L) for x in xs), 3)
                      for L in ("mid", "hhw")),
                    _m(x["flow_tail_ratio"] for x in xs),
                    _m(x["wage_tail_ratio"] for x in xs),
                    _m(x["balance_ratio_tail.hhw"] for x in xs),
                    _m((x["below_diff_close"] for x in xs), 0),
                    _fmt_count(_count(x["flip"] for x in xs)),
                    _fmt_count(_count(x["state"] for x in xs))])
    _md(["block", "arm", "wage elasticity", "cells", "bit in",
         "routed inflow turned away", "fin, points", "mid, points",
         "households on a payroll, points", "off it, points",
         "turned away to mid", "to households", "total flow", "wages paid",
         "balance of a household on a payroll", "nodes below the floor less "
         "the twin's", "flips", "states"], out)
    grow = [x for x in layer if x["block"] == "growth" and not x["lift"]]
    if grow:
        print("growing block, slope of the log of each layer's holdings over "
              "the tail, capped run and twin\n")
        out = []
        for arm in ARM_ORDER:
            xs = [x for x in grow if x["arm"] == arm]
            if xs:
                out.append([arm, len(xs)] + [
                    "%s / %s" % (_m((x.get("layer_slope_tail.%s" % L)
                                     for x in xs), 5),
                                 _m((x.get("twin_layer_slope_tail.%s" % L)
                                     for x in xs), 5)) for L in LAYERS])
        _md(["arm", "cells"] + ["%s, capped / twin" % L for L in LAYERS], out)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--gate", "--selftest", "--time", "--run", "--tables"):
        mode.add_argument(flag, action="store_true")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--workers", type=int, default=_A54._default_workers())
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.tables:
        return tables()
    if args.gate:
        print("stage %s, rule 19: the class against Network.run(), one "
              "ceiling against A54's class, infinite ceilings against the "
              "twin\n" % STAGE)
        g = gate(gate_configs())
        print("\n   %d runs, verdict: %s" % (g["runs"], g["verdict"]))
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1
    if args.selftest:
        print("stage %s, seeded faults\n" % STAGE)
        s = selftest()
        print("\n   %d of %d held, verdict: %s" % (s["held"], s["of"],
                                                  s["verdict"]))
        if not args.no_write:
            write_record("selftest", s)
        return 0 if s["verdict"] == "pass" else 1
    if args.time:
        print("stage %s, D38: seconds per configuration, measured here\n"
              % STAGE)
        time_bases(args.workers)
        return 0

    if args.smoke:
        bases = base_keys(needs=SMOKE["needs"],
                          elasticities=SMOKE["elasticities"],
                          seeds=SMOKE["seeds"])
        gate_section = None
        print("stage %s, smoke: %d configurations and seeds, nothing "
              "written\n" % (STAGE, len(bases)))
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage %s: not starting. %s." % (STAGE, why))
            return 2
        bases = base_keys(seeds=SEEDS[:args.seeds])
        print("stage %s: %d configurations and seeds, %d runs, %d workers. "
              "%s.\n" % (STAGE, len(bases), sum(runs_of(b) for b in bases),
                         args.workers, why))
    t0 = time.perf_counter()
    rows = run_bases(bases, args.workers)
    print("   ran %d runs in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections = analyse(rows, gate_section)
    _A54._print_criteria(crits)
    failed = [c.name for c in crits if c.evaluated and not c.passed]
    if args.smoke or args.no_write:
        return 0 if not failed else 1
    sections["seeds_run"] = sorted({x["seed"] for x in rows})
    write_record("run", sections)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
