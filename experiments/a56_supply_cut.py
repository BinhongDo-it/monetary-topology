"""A56: when a cut of out-edges falls on the node that was cut off.

A54 cut a node's out-edges, the payments it makes, and read the loss on the
other end: the payees that lost the payer hold less, the payer itself is
untouched. That is a reading of a payment graph. A node on that carrier needs
no particular input, so what it cannot pay one payee it pays the others, and
what it is paid does not depend on what it bought.

This stage adds the one condition under which the cut reaches the payer: an
input constraint at the node.

    classes     a node's counterparties are of two kinds, the financial layer
                and everyone else. Within a kind they stand in for each other,
                which is how the routing already behaves; across kinds they do
                not, which is the min of a Leontief technology.
    fill        a kind a node bought from before the cut is filled as long as
                one counterparty of that kind that can itself deliver is still
                connected. The node's fill is the smaller of its kinds'.
    strength    ``e``. A node takes in ``1 - e * (1 - fill)`` of its routed
                inflow: 0 is off, which is A54's cut; 1 is the strict min.

A node that cannot deliver is a missing supplier to its own payers, so the
fill is taken to its fixed point. The limit sits where A55 put a ceiling, at
the model's capacity step: a ceiling is a limit on what a node takes in set
by its balance, and this is one set by its inputs. What a limited node cannot
take is spent by its payers on their other counterparties. Wages are a
separate channel and are not touched.

    python experiments/a56_supply_cut.py --gate
    python experiments/a56_supply_cut.py --selftest
    python experiments/a56_supply_cut.py --time
    python experiments/a56_supply_cut.py --run [--seeds N] [--workers N]
    python experiments/a56_supply_cut.py --tables
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
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

RECORD = RESULTS / "a56_supply_cut.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
A55_SCRIPT = ROOT / "experiments" / "a55_cap_lift_layer.py"
A54_SCRIPT = ROOT / "experiments" / "a54_penalty.py"
STAGE = "A56"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A55's class with limits on any number of columns, and through it A54's
#: carrier, twin, readings and record format.
_A55 = _load(A55_SCRIPT, "_a55_for_a56")
_A54 = _A55._A54
LimitNetwork = _A55.LimitNetwork
Criterion = _A54.Criterion
_fmt = _A54._fmt
_num = _A54._num
_same = _A54._same
_module_sha = _A54._module_sha
_median = _A55._median
_count = _A55._count
_fmt_count = _A55._fmt_count

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
STRESSES = _A55.STRESSES

#: The two kinds of counterparty: the financial layer, and everyone else.
CLASSES: tuple[str, ...] = ("F", "P")
CLASS_TEXT = {"F": "the financial layer", "P": "the production side"}
#: Strengths of the constraint. Zero is off.
STRENGTHS: tuple[float, ...] = (0.0, 0.5, 1.0)
#: A replacement found: the cut edges come back this many rounds later.
RESTORE_AFTER = _A54.RESTORE_AFTER
#: Rounds after the cut at which the deviation is printed.
AT: tuple[int, ...] = (1, 2, 5, 10, 20, 50)
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def base_keys(seeds=SEEDS, needs=NEEDS, elasticities=ELASTICITIES,
              authorities=AUTHORITIES) -> list:
    return _A55.base_keys(seeds=seeds, needs=needs, elasticities=elasticities,
                          authorities=authorities, growth=False)


base_config = _A54.base_config


def _arm(cls: str, part: str, e: float, restore=None) -> dict:
    return {"kind": "cut", "cls": cls, "part": part, "size": e,
            "restore": restore}


def arms_for(base: dict) -> list:
    arms = []
    for cls in CLASSES:
        arms += [_arm(cls, "all", e) for e in STRENGTHS]
    # Half of the kind the target has more suppliers of: a cut that leaves a
    # stand-in for everything it removes.
    arms += [_arm("larger", "half", e) for e in (0.0, 1.0)]
    arms += [_arm(cls, "all", 1.0, RESTORE_AFTER) for cls in CLASSES]
    return arms


def arm_label(a: dict) -> str:
    return "cut %s %s e %g%s" % (a["part"], a["cls"], a["size"],
                                 " restored" if a.get("restore") else "")


ARM_ORDER: list = [arm_label(a) for a in arms_for({})]


def runs_of(base: dict) -> int:
    return 1 + len(TARGETS) * len(arms_for(base))


# ---------------------------------------------------------------------------
# The constraint.
# ---------------------------------------------------------------------------

def needs_of(pays: np.ndarray, cls: np.ndarray) -> np.ndarray:
    """Which kinds each node buys from: a column per kind."""
    return np.column_stack([pays[:, cls == k].any(axis=1)
                            for k in range(len(CLASSES))])


def deliverable(pays: np.ndarray, cls: np.ndarray, needs: np.ndarray,
                e: float, fault: str | None = None,
                before: np.ndarray | None = None) -> np.ndarray:
    """The share of its routed inflow each node can take in, at the fixed
    point: ``1 - e * (1 - fill)``, where a node's fill is the smallest, over
    the kinds it needs, of the best ``deliverable`` among the counterparties
    of that kind it still pays. A kind with nobody left fills to zero.

    Starts from one everywhere and only falls, so the loop ends.
    """
    n = pays.shape[0]
    d = np.ones(n)
    if e <= 0.0:
        return d
    for _ in range(n + 1):
        fill = np.ones(n)
        for k in range(len(CLASSES)):
            sub = pays[:, cls == k]
            if fault == "bite_with_substitutes" and before is not None:
                # Seeded: a kind counts as short as soon as any one of the
                # counterparties it had is gone, stand-ins or not.
                was = before[:, cls == k]
                best = np.where(was.sum(axis=1) > 0,
                                sub.sum(axis=1) / np.maximum(was.sum(axis=1), 1),
                                0.0)
            else:
                best = (sub * d[cls == k][None, :]).max(axis=1, initial=0.0)
            fill = np.where(needs[:, k], np.minimum(fill, best), fill)
        new = 1.0 - e * (1.0 - fill)
        if np.allclose(new, d, rtol=0.0, atol=1e-15):
            return new
        d = new
    return d


def pick_edges(spent: np.ndarray, route: np.ndarray, node: int,
               cls: np.ndarray, arm: dict) -> dict:
    """The out-edges an arm removes, read off the routing at the yield."""
    out = np.flatnonzero(route[node] > 0.0)
    flows = spent[node] * route[node, out]
    kinds = cls[out]
    sizes = [int((kinds == k).sum()) for k in range(len(CLASSES))]
    if arm["cls"] == "larger":
        k = int(np.argmax(sizes))
    else:
        k = CLASSES.index(arm["cls"])
    members = out[kinds == k]
    m_flows = flows[kinds == k]
    if arm["part"] == "all":
        chosen = members
    else:
        order = np.argsort(-m_flows, kind="stable")
        chosen = members[order[:int(round(0.5 * members.size))]]
    total = float(flows.sum())
    return {
        "chosen": chosen, "kept": np.setdiff1d(out, chosen),
        "class": CLASSES[k], "edges": int(out.size),
        "of_class": int(members.size), "cut": int(chosen.size),
        "by_class": dict(zip(CLASSES, sizes)),
        "flow_share_cut": (float(spent[node] * route[node, chosen].sum())
                           / total if total > 0 else None),
    }


# ---------------------------------------------------------------------------
# The driver.
# ---------------------------------------------------------------------------

def drive(cfg: NetworkConfig, arm: dict, twin: dict, node: int,
          fault: str | None = None) -> tuple:
    """One cut, with the constraint at strength ``arm['size']``."""
    net = LimitNetwork(cfg)
    lay = twin["layers"]
    cls = (lay != "fin").astype(int)
    sig = twin["sig"]
    span = ROUNDS - FIRST
    seen: dict = {
        "books": True, "switch": np.zeros(span, dtype=bool),
        "raw": np.zeros(ROUNDS), "blocked": np.zeros(ROUNDS),
        "target_routed": np.zeros(ROUNDS),
        "target_short": 0, "target_below": 0, "restored": None,
    }
    saved = None
    needs = None
    for t in net._run_steps():
        if t >= FIRST:
            i = t - FIRST
            seen["switch"][i] = bool(
                (net.tap_below != sig["below"][i]).any()
                or (net.tap_floor_capped != sig["floor_capped"][i]).any()
                or (net.tap_short != sig["short"][i]).any())
            r = net.lim_round
            seen["raw"][t], seen["blocked"][t] = r["raw"], r["blocked"]
            seen["target_routed"][t] = float(net.tap_spent
                                             @ net.tap_route[:, node])
            seen["target_short"] += int(net.tap_short[node])
            seen["target_below"] += int(net.tap_below[node])
        if t == ROUNDS - 1:
            pass
        elif t == PENALTY_ROUND:
            before = net._route > 0.0
            needs = needs_of(before, cls)
            pick = pick_edges(net.tap_spent, net.tap_route, node, cls, arm)
            seen.update(pick)
            if pick["cut"] > 0:
                saved = net._route.copy()
                net.adjacency[node, pick["chosen"]] = 0.0
                net._rebuild_route()
            d = deliverable(net._route > 0.0, cls, needs, arm["size"],
                            fault, before)
            seen["deliverable"] = d
            if fault != "no_bite" and (d < 1.0).any():
                net.lim_theta = d
        elif (arm.get("restore") and seen.get("cut", 0) > 0
              and t == PENALTY_ROUND + arm["restore"]):
            net.adjacency[node, seen["chosen"]] = 1.0
            net._rebuild_route()
            seen["restored"] = bool(np.array_equal(net._route, saved))
            d = deliverable(net._route > 0.0, cls, needs, arm["size"])
            net.lim_theta = d if (d < 1.0).any() else None
        if not _A54._books(net, cfg):
            seen["books"] = False
    seen["rng"] = _A54._rng_digest(net)
    seen["below_close"] = net._below.copy()
    seen["blocked_by"] = net.lim_blocked_by.copy()
    seen["diverted_to"] = net.lim_diverted_to.copy()
    return net, seen


def reference_cut(cfg: NetworkConfig, node: int, chosen: np.ndarray) -> Network:
    """The same cut on the model's own class, with nothing of this script in
    the loop: what a strength of zero has to reproduce."""
    net = Network(cfg)
    for t in net._run_steps():
        if t == PENALTY_ROUND and chosen.size:
            net.adjacency[node, chosen] = 0.0
            net._rebuild_route()
    return net


# ---------------------------------------------------------------------------
# Readings.
# ---------------------------------------------------------------------------

def _digest(net: Network) -> str:
    h = net._history
    m = hashlib.sha256()
    for name in ("holdings", "total_volume", "wage_paid", "issuance"):
        m.update(np.ascontiguousarray(
            np.asarray(getattr(h, name), dtype=float)).tobytes())
    m.update(np.ascontiguousarray(net.holdings).tobytes())
    return m.hexdigest()[:16]


def _ratio_tail(hold: np.ndarray, twin_h: np.ndarray, nodes) -> float | None:
    nodes = np.asarray(nodes, dtype=int)
    if not nodes.size:
        return None
    theirs = twin_h[-TAIL:, nodes].mean(axis=0)
    mine = hold[-TAIL:, nodes].mean(axis=0)
    ok = theirs > _A54.EPS_HOLD
    return float(np.mean(mine[ok] / theirs[ok])) if ok.any() else None


def read_arm(twin: dict, base: dict, kind: str, arm: dict, net: Network,
             seen: dict) -> dict:
    info = twin["nodes"][kind]
    node = info["node"]
    h = net._history
    hold = np.asarray(h.holdings, dtype=float)
    circ = hold.sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    flow = np.asarray(h.total_volume, dtype=float)
    wage = np.asarray(h.wage_paid, dtype=float)
    issued = np.asarray(h.issuance, dtype=float)
    lay = twin["layers"]
    s_c, _ = _A54.shares(hold[:, node], circ, parked)
    b_c, _ = _A54.shares(twin["H"][:, node], twin["circ"], twin["parked"])
    with np.errstate(divide="ignore", invalid="ignore"):
        dev = s_c / b_c - 1.0
    jitter = twin["jitter"][kind]
    band = None if jitter is None else FLOOR_MULTIPLE * jitter
    early, tail = _num(dev[FIRST]), _num(dev[-TAIL:].mean())
    ratio, state = _A54.permanence(early, tail, band)
    switch = seen["switch"] | ((issued[FIRST:] > 0.0)
                               != (twin["issued"][FIRST:] > 0.0))
    d = seen["deliverable"]
    others = np.setdiff1d(np.flatnonzero(d < 1.0), [node])
    sells = (twin["at"]["route"] > 0.0).any(axis=0)
    below_diff = int(seen["below_close"].sum() - twin["below_close"].sum())
    t_flow = float(twin["flow"][-TAIL:].mean())
    t_circ = float(twin["circ"][-TAIL:].mean())
    t_wage = float(twin["wage_paid"][-TAIL:].mean())
    payers = np.flatnonzero(twin["at"]["route"][:, node] > 0.0)
    on = slice(FIRST, ROUNDS) if not arm.get("restore") else slice(
        FIRST, PENALTY_ROUND + arm["restore"] + 1)
    twin_routed = twin["at"]["spent"] @ twin["at"]["route"][:, node]
    # What the target could have been paid this stretch, with the limit off:
    # the limit's own books hold it only for the rounds it bit.
    raw_on = float(seen["raw"][on].sum())
    total = float(seen["blocked_by"].sum())
    row = dict(base)
    row.update({
        "target": kind, "node": node, "arm": arm_label(arm), "kind": "cut",
        "cls": arm["cls"], "part": arm["part"], "size": arm["size"],
        "restore": arm.get("restore"),
        "class_cut": seen["class"], "edges": seen["edges"],
        "of_class": seen["of_class"], "cut": seen["cut"],
        "suppliers_by_class": seen["by_class"],
        "flow_share_cut": _num(seen["flow_share_cut"]),
        "books_close": bool(seen["books"]),
        "same_draws_as_twin": seen["rng"] == twin["rng"],
        "restored_exactly": seen["restored"],
        "digest": _digest(net),
        "target_deliverable": float(d[node]),
        "followers": int(others.size),
        "followers_by_layer": {L: int((lay[others] == L).sum())
                               for L in LAYERS},
        "followers_that_are_paid": int(sells[others].sum()),
        "turned_away_share": (_num(float(seen["blocked"][on].sum()) / raw_on)
                              if raw_on > 0 else None),
        "target_turned_away_share": (
            _num(float(seen["blocked_by"][node])
                 / float(seen["blocked_by"][node]
                         + seen["target_routed"][on].sum()))
            if seen["blocked_by"][node] > 0 else 0.0),
        "target_routed_first_round": float(seen["target_routed"][FIRST]),
        "twin_routed_at_penalty": float(twin_routed),
        "target_rounds_short_of_wages": int(seen["target_short"]),
        "target_rounds_below_floor": int(seen["target_below"]),
        "band": _num(band), "first_round": early, "tail": tail,
        "permanence": _num(ratio), "state": state,
        "deviation_at": {str(k): _num(dev[PENALTY_ROUND + k]) for k in AT},
        "target_balance_tail": _ratio_tail(hold, twin["H"], [node]),
        "cut_end_tail": _ratio_tail(hold, twin["H"], seen["chosen"]),
        "kept_end_tail": _ratio_tail(hold, twin["H"], seen["kept"]),
        "payers_tail": _ratio_tail(hold, twin["H"], payers),
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
        "_path": dev[FIRST:].copy(),
    })
    if total > 0.0:
        row["turned_away_to"] = {
            L: float(seen["diverted_to"][lay == L].sum() / total)
            for L in LAYERS}
    return row


def twin_row(base: dict, twin: dict) -> dict:
    lay = twin["layers"]
    cls = (lay != "fin").astype(int)
    pays = twin["at"]["route"] > 0.0
    row = dict(base)
    row.update({"target": "twin", "arm": "twin", "kind": "twin",
                "books_close": bool(twin["books"]),
                "below_close": int(twin["below_close"].sum()),
                "targets": {}})
    for kind in TARGETS:
        node = twin["nodes"][kind]["node"]
        k = int(cls[node])
        # Payers that have this node as their one supplier of its kind: the
        # ones a stopped node takes with it.
        only = (pays[:, cls == k].sum(axis=1) == 1) & pays[:, node]
        row["targets"][kind] = {
            "node": node, "layer": str(lay[node]),
            "held_at_penalty": float(twin["at"]["holdings"][node]),
            "inflow_per_round": float(twin["inflow_window"][:, node].mean()),
            "suppliers": {c: int(pays[node, cls == j].sum())
                          for j, c in enumerate(CLASSES)},
            "payers": int(pays[:, node].sum()),
            "payers_with_it_as_only_supplier_of_its_kind": {
                L: int((only & (lay == L)).sum()) for L in LAYERS},
            "on_payroll_list": bool(node in set(
                np.asarray(twin["net"]._wage_payers).tolist())),
        }
    return row


def one_base(base: dict, arms=None, faults=None) -> list:
    cfg = base_config(base)
    twin = _A54.make_twin(cfg)
    rows = [twin_row(base, twin)]
    for kind in TARGETS:
        node = twin["nodes"][kind]["node"]
        for arm in (arms_for(base) if arms is None else arms):
            fault = None if faults is None else faults.get(arm_label(arm))
            net, seen = drive(cfg, arm, twin, node, fault)
            rows.append(read_arm(twin, base, kind, arm, net, seen))
    return rows


def _row_sort(x: dict) -> tuple:
    return _A54._base_sort(x) + (
        TARGETS.index(x["target"]) if x["target"] in TARGETS else -1,
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


def groups(rows: list) -> list:
    keyed: dict = {}
    for x in _arms(rows):
        keyed.setdefault(_A55._cell(x) + (x["target"], x["arm"]),
                         []).append(x)
    out = []
    for key in sorted(keyed, key=lambda k: _row_sort(keyed[k][0])):
        xs = keyed[key]
        first = xs[0]
        g = {k: first[k] for k in ("block", "need", "stress", "elasticity",
                                   "authority", "target", "arm", "kind",
                                   "cls", "part", "size", "restore")}
        paths = np.vstack([x["_path"] for x in xs])
        with np.errstate(all="ignore"):
            med = np.nanmedian(paths, axis=0)
        g.update({
            "seeds": sorted(x["seed"] for x in xs),
            "band_median": _median(x["band"] for x in xs),
            "tail_median": _median(x["tail"] for x in xs),
            "cut_end_tail_median": _median(x["cut_end_tail"] for x in xs),
            "kept_end_tail_median": _median(x["kept_end_tail"] for x in xs),
            "flow_tail_ratio_median": _median(x["flow_tail_ratio"]
                                              for x in xs),
            "states": _count(x["state"] for x in xs),
            "flips": _count(x["flip"] for x in xs),
            "median_path": [None if not np.isfinite(v) else float(v)
                            for v in med],
        })
        out.append(g)
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def _gate_section():
    if not RECORD.exists():
        return None
    return json.loads(RECORD.read_text(encoding="utf-8")).get(
        "sections", {}).get("gate")


_SHAS = (("module_sha", MODULE, "network.py"), ("script_sha", SCRIPT,
                                                 "this script"),
         ("a55_sha", A55_SCRIPT, "a55_cap_lift_layer.py"),
         ("a54_sha", A54_SCRIPT, "a54_penalty.py"))


def _gate_allows(g) -> tuple:
    if not g:
        return False, "no gate section in the record: run --gate first"
    for key, path, what in _SHAS:
        if g.get(key) != _module_sha(path):
            return False, "%s has changed since the gate ran: run --gate again" % what
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and these scripts"


def _g(v) -> str:
    return "n/a" if v is None else "%.4g" % v


def _pct(v) -> str:
    return "n/a" if v is None else "%+.1f%%" % (100.0 * v)


def criterion_a56_0(g, rows: list) -> Criterion:
    name = "A56-0 with the constraint off the cut is the model's own"
    if g is None:
        return Criterion(name, "instrument", False,
                         "not evaluated: no gate section", evaluated=False)
    ok, why = _gate_allows(g)
    books = sum(1 for x in rows if x["books_close"])
    arms = _arms(rows)
    draws = sum(1 for x in arms if x["same_draws_as_twin"])
    put = [x for x in arms if x["restore"]]
    exact = sum(1 for x in put if x["restored_exactly"])
    good = (ok and not g.get("differ") and books == len(rows)
            and draws == len(arms) and exact == len(put))
    return Criterion(
        name, "instrument", bool(good),
        "%d configurations, %d runs: a cut of a whole kind at strength zero "
        "against the same cut on Network, and the constraint at full strength "
        "with nothing cut against the twin, %s. %s. Grid: claim total equal "
        "to held plus parked at every yield in %d of %d runs; generators end "
        "where the twin's do in %d of %d; edges put back restore the routing "
        "to the bit in %d of %d"
        % (len(g.get("configs", [])), g.get("runs", 0),
           "identical" if not g.get("differ") else
           "DIFFER in %d" % len(g["differ"]), why, books, len(rows), draws,
           len(arms), exact, len(put)))


def criterion_a56_1(rows: list) -> Criterion:
    """The constraint binds exactly when a kind is gone."""
    arms = _arms(rows)
    half = {}
    for x in arms:
        if x["part"] == "half":
            half[_A55._cell(x) + (x["seed"], x["target"], x["size"])] = x
    pairs = same = 0
    for k, off in half.items():
        if k[-1] != 0.0:
            continue
        on = half.get(k[:-1] + (1.0,))
        if on is None:
            continue
        pairs += 1
        same += int(on["digest"] == off["digest"]
                    and on["target_deliverable"] == 1.0
                    and on["followers"] == 0)
    whole = [x for x in arms if x["part"] == "all" and not x["restore"]]
    right = sum(1 for x in whole
                if abs(x["target_deliverable"] - (1.0 - x["size"])) < 1e-12
                and abs((x["target_turned_away_share"] or 0.0)
                        - x["size"]) < 1e-9)
    stopped = [x for x in whole if x["size"] == 1.0]
    dry = sum(1 for x in stopped if x["target_routed_first_round"] == 0.0)
    ok = (pairs > 0 and same == pairs and bool(whole)
          and right == len(whole) and dry == len(stopped))
    return Criterion(
        "A56-1 the constraint binds when a whole kind is gone and not before",
        "known_answer", ok,
        "half of a kind cut, a stand-in left for every edge removed: the run "
        "at full strength is the run at strength zero to the bit, with "
        "nobody's inflow limited, in %d of %d pairs. A whole kind cut: the "
        "target takes in 1 - e of its routed inflow, and the share turned "
        "away over the run is e to 1e-9, in %d of %d; at e = 1 its routed "
        "inflow in the first round is exactly zero in %d of %d"
        % (same, pairs, right, len(whole), dry, len(stopped)))


def criterion_a56_2(rows: list) -> Criterion:
    """Whom a cut of a whole kind falls on, by strength. The target's own
    column is implied (A54: what a node cannot take in, it loses) and is
    printed, not judged. The registered reading is the kept end: with the
    constraint off the payees the target still has gain what the cut ones
    lost; with it on the target stops buying and they lose too."""
    whole = [x for x in _arms(rows) if x["part"] == "all"
             and not x["restore"]]
    by = {}
    for x in whole:
        by.setdefault((x["target"], x["cls"], x["size"]), []).append(x)
    parts = []
    for (kind, cls, e), xs in sorted(by.items(), key=lambda kv: (
            TARGETS.index(kv[0][0]), CLASSES.index(kv[0][1]), kv[0][2])):
        parts.append(
            "%s target, %s cut, e %g (%d cells): own share %s, payees cut off "
            "%s of the twin's balance, payees kept %s, its payers %s" % (
                kind, CLASS_TEXT[cls], e, len(xs),
                _pct(_median(x["tail"] for x in xs)),
                _g(_median(x["cut_end_tail"] for x in xs)),
                _g(_median(x["kept_end_tail"] for x in xs)),
                _g(_median(x["payers_tail"] for x in xs))))
    keyed = {(_A55._cell(x) + (x["seed"], x["target"], x["cls"], x["size"])): x
             for x in whole}
    pairs = down = up_off = 0
    for k, off in keyed.items():
        if k[-1] != 0.0:
            continue
        on = keyed.get(k[:-1] + (1.0,))
        if on is None or off["kept_end_tail"] is None \
                or on["kept_end_tail"] is None:
            continue
        pairs += 1
        down += int(on["kept_end_tail"] < off["kept_end_tail"])
        up_off += int(off["kept_end_tail"] > 1.0)
    off_med = _median(x["kept_end_tail"] for x in whole if x["size"] == 0.0)
    on_med = _median(x["kept_end_tail"] for x in whole if x["size"] == 1.0)
    ok = (pairs > 0 and off_med is not None and on_med is not None
          and off_med > 1.0 > on_med)
    return Criterion(
        "A56-2 a whole kind cut: with the constraint the kept payees lose too",
        "own_reading", ok,
        "payees the target keeps, balance over the twin's: median %s with the "
        "constraint off and %s at full strength; lower at full strength in %d "
        "of %d pairs of the same cell, seed, target and kind, and above the "
        "twin's with it off in %d of %d. %s"
        % (_g(off_med), _g(on_med), down, pairs, up_off, pairs,
           "; ".join(parts)))


def criterion_a56_3(rows: list) -> Criterion:
    """Who else: the nodes that follow, where the target's payers spend
    instead, and the totals."""
    on = [x for x in _arms(rows) if x["part"] == "all" and not x["restore"]
          and x["size"] > 0.0]
    if not on:
        return Criterion("A56-3 who else", "own_reading", False, "no cell")
    landed = [x for x in on if x.get("turned_away_to")]
    closes = max((abs(sum(x["turned_away_to"].values()) - 1.0)
                  for x in landed), default=1.0)
    read = sum(1 for x in on if x["flow_tail_ratio"] is not None
               and x["circulating_tail_ratio"] is not None)
    parts = []
    for kind in TARGETS:
        for e in STRENGTHS[1:]:
            xs = [x for x in on if x["target"] == kind and x["size"] == e]
            if not xs:
                continue
            to = {L: _median(x["turned_away_to"][L] for x in xs
                             if x.get("turned_away_to")) for L in LAYERS}
            parts.append(
                "%s target, e %g (%d cells): other nodes limited %s (of them "
                "paid by anyone %s); what it could not take went to fin %s, "
                "mid %s; total flow %s of the twin's, claims %s, wages %s; "
                "rounds short of its wages %s; nodes below the floor less the "
                "twin's %s, %s" % (
                    kind, e, len(xs),
                    _g(_median(x["followers"] for x in xs)),
                    _g(_median(x["followers_that_are_paid"] for x in xs)),
                    _g(to["fin"]), _g(to["mid"]),
                    _g(_median(x["flow_tail_ratio"] for x in xs)),
                    _g(_median(x["circulating_tail_ratio"] for x in xs)),
                    _g(_median(x["wage_tail_ratio"] for x in xs)),
                    _g(_median(x["target_rounds_short_of_wages"]
                               for x in xs)),
                    _g(_median(x["below_diff_close"] for x in xs)),
                    _fmt_count(_count(x["flip"] for x in xs))))
    ok = (len(landed) == len(on) and closes < 1e-9 and read == len(on))
    return Criterion(
        "A56-3 who else is reached", "own_reading", ok,
        "%d cells with a whole kind cut and the constraint on; where the "
        "target's turned-away inflow landed is on the books in %d and adds to "
        "one within %.1e; totals read in %d. %s"
        % (len(on), len(landed), closes, read, "; ".join(parts)))


def criterion_a56_4(rows: list) -> Criterion:
    """A replacement found after twenty rounds."""
    xs = [x for x in _arms(rows) if x["restore"]]
    names = {s for s, _ in _A54.PERMANENCE_STATES}
    mapped = all(x["state"] in names for x in xs)
    plain = [x for x in xs if x["switches_as_twin"]]
    left = [x for x in plain if x["state"] in ("kept", "reversed", "late")]
    parts = []
    for kind in TARGETS:
        ks = [x for x in xs if x["target"] == kind]
        if ks:
            parts.append("%s target: %s; deepest at 20 rounds %s, tail %s; "
                         "nodes below the floor less the twin's at the close "
                         "%s" % (
                             kind, _fmt_count(_count(x["state"] for x in ks)),
                             _pct(_median(x["deviation_at"]["20"]
                                          for x in ks)),
                             _pct(_median(x["tail"] for x in ks)),
                             _fmt_count(_count(x["flip"] for x in ks))))
    ok = bool(xs) and mapped and not left
    return Criterion(
        "A56-4 the edges put back after %d rounds" % RESTORE_AFTER,
        "own_reading", ok,
        "%d cells at full strength. With every switch as the twin's, %d of %d "
        "leave nothing in the tail; with one flipped, %d of %d. %s"
        % (len(xs), len(plain) - len(left), len(plain),
           sum(1 for x in xs if not x["switches_as_twin"]
               and x["state"] in ("gone", "nothing")),
           len(xs) - len(plain), "; ".join(parts)))


def criterion_a56_5(grp: list) -> Criterion:
    span = ROUNDS - FIRST
    names = {s for s, _ in _A54.PERMANENCE_STATES}
    paths = sum(1 for g in grp if len(g.get("median_path") or []) == span)
    mapped = sum(1 for g in grp if set(g["states"]) <= names)
    ok = bool(grp) and paths == len(grp) and mapped == len(grp)
    return Criterion(
        "A56-5 every group carries its path and its states", "bookkeeping",
        ok, "%d groups: the median path over all %d rounds after the cut in "
        "%d, states from the map in %d" % (len(grp), span, paths, mapped))


def analyse(rows: list, gate_section) -> tuple:
    grp = groups(rows)
    crits = [criterion_a56_0(gate_section, rows), criterion_a56_1(rows),
             criterion_a56_2(rows), criterion_a56_3(rows),
             criterion_a56_4(rows), criterion_a56_5(grp)]
    sections = {
        "criteria": [c.as_dict() for c in crits],
        "layout": "every section below criteria is a table: fields names the "
                  "columns once, nested readings as dotted names, and rows "
                  "holds one record per line in that order",
        "states": {"permanence": dict(_A54.PERMANENCE_STATES),
                   "flip": dict(_A54.FLIP_STATES)},
        "groups": _A54._table(grp),
        "rows": {"twin": _A54._table([x for x in rows
                                      if x["kind"] == "twin"]),
                 "cut": _A54._table(_arms(rows))},
    }
    return crits, sections


# ---------------------------------------------------------------------------
# Rule 19.
# ---------------------------------------------------------------------------

def gate_configs(bases=None) -> list:
    out = []
    for b in (base_keys(seeds=SEEDS[:1]) if bases is None else bases):
        out.append(("%s need %.2f %s e %.1f %s" % (
            b["block"], b["need"], b["stress"], b["elasticity"],
            b["authority"]), base_config(b)))
    return out


def gate(configs: list) -> dict:
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    closing = _A54.CLOSING

    def differs(ref, ref_rng, net, rng) -> list:
        bad = [n for n in names if not _same(getattr(ref._history, n),
                                             getattr(net._history, n))]
        bad += [n for n in closing if not _same(getattr(ref, n),
                                                getattr(net, n))]
        if ref_rng != rng:
            bad.append("generators")
        return bad

    differ, labels, runs = [], [], 0
    for label, cfg in configs:
        t0 = time.perf_counter()
        twin = _A54.make_twin(cfg)
        tnet = twin["net"]
        runs += 1
        off = 0
        for kind in TARGETS:
            node = twin["nodes"][kind]["node"]
            for cls in CLASSES:
                net, seen = drive(cfg, _arm(cls, "all", 0.0), twin, node)
                ref = reference_cut(cfg, node, seen["chosen"])
                bad = differs(ref, _A54._rng_digest(ref), net, seen["rng"])
                if not seen["books"]:
                    bad.append("claim total against held plus parked")
                runs += 2
                if bad:
                    off += 1
                    differ.append({"run": "%s, %s target, %s cut at strength "
                                   "zero" % (label, kind, cls), "fields": bad})
            # Full strength, an arm that removes no edge: nothing may move.
            none = {"kind": "cut", "cls": "F", "part": "none", "size": 1.0,
                    "restore": None}
            net, seen = drive_none(cfg, none, twin, node)
            bad = differs(tnet, twin["rng"], net, seen["rng"])
            runs += 1
            if bad:
                off += 1
                differ.append({"run": "%s, %s target, full strength and no "
                               "cut" % (label, kind), "fields": bad})
        labels.append(label)
        print("   %-44s against Network and the twin: %s  (%.1f s)" % (
            label, "identical" if not off else "%d DIFFER" % off,
            time.perf_counter() - t0))
    return {"module_sha": _module_sha(MODULE),
            "script_sha": _module_sha(SCRIPT),
            "a55_sha": _module_sha(A55_SCRIPT),
            "a54_sha": _module_sha(A54_SCRIPT),
            "configs": labels,
            "fields_compared": len(names) + len(closing) + 1,
            "runs": runs, "differ": differ,
            "verdict": "pass" if not differ else "fail"}


def drive_none(cfg: NetworkConfig, arm: dict, twin: dict, node: int) -> tuple:
    """The constraint switched on with no edge removed."""
    net = LimitNetwork(cfg)
    cls = (twin["layers"] != "fin").astype(int)
    seen = {"books": True}
    for t in net._run_steps():
        if t == PENALTY_ROUND:
            pays = net._route > 0.0
            d = deliverable(pays, cls, needs_of(pays, cls), arm["size"])
            if (d < 1.0).any():
                net.lim_theta = d
        if not _A54._books(net, cfg):
            seen["books"] = False
    seen["rng"] = _A54._rng_digest(net)
    return net, seen


# ---------------------------------------------------------------------------
# Seeded faults.
# ---------------------------------------------------------------------------

def selftest() -> dict:
    checks: list = []

    def note(what: str, held: bool, detail: str = "") -> None:
        checks.append({"check": what, "held": bool(held), "detail": detail})
        print("   [%s] %s%s" % ("ok" if held else "MISSED", what,
                                " : " + detail if detail else ""))

    # -- the fixed point on a graph small enough to do by hand ---------------
    # 0, 1 financial; 2, 3, 4 on the production side.
    cls = np.array([0, 0, 1, 1, 1])
    full = np.zeros((5, 5), dtype=bool)
    for i, js in {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2, 4],
                  4: [0, 2]}.items():
        full[i, js] = True
    needs = needs_of(full, cls)
    note("fixed point: nothing cut, nobody limited at any strength",
         bool((deliverable(full, cls, needs, 1.0) == 1.0).all()))
    cut = full.copy()
    cut[3, [2, 4]] = False          # node 3 loses its whole production side
    d1 = deliverable(cut, cls, needs, 1.0)
    dh = deliverable(cut, cls, needs, 0.5)
    # Nodes 1 and 2 buy the production side from 3 alone, so they follow; 4
    # buys it from 2 alone and follows 2; 0 buys the financial side from 1
    # alone and follows 1.
    note("fixed point: a kind gone stops the node, and the nodes that had it "
         "as their one supplier of a kind follow, one after another",
         d1.tolist() == [0.0, 0.0, 0.0, 0.0, 0.0], "%s" % d1.tolist())
    note("fixed point: at half strength each step down the chain is half as "
         "deep", abs(dh[3] - 0.5) < 1e-12 and abs(dh[2] - 0.75) < 1e-12
         and abs(dh[4] - 0.875) < 1e-12, "%s" % dh.round(4).tolist())
    part = full.copy()
    part[3, 4] = False              # one of two production suppliers gone
    note("fixed point: a stand-in left, nobody limited",
         bool((deliverable(part, cls, needs, 1.0) == 1.0).all())
         and not bool((deliverable(part, cls, needs, 1.0,
                                   "bite_with_substitutes", full)
                       == 1.0).all()))
    note("fixed point: strength zero is off",
         bool((deliverable(cut, cls, needs, 0.0) == 1.0).all()))

    # -- the driver, on one configuration ------------------------------------
    base = {"block": "main", "need": 0.20, "stress": "healthy",
            "elasticity": 0.5, "authority": "none", "seed": SEEDS[0]}
    arms = arms_for(base)
    good = one_base(base, arms=arms)
    g_ok = dict({k: _module_sha(p) for k, p, _ in _SHAS}, verdict="pass",
                differ=[], configs=["x"], runs=1, fields_compared=1)

    def crit(rs, index, g=g_ok):
        return analyse(rs, g)[0][index]

    clean = analyse(good, g_ok)[0]
    note("the clean configuration passes A56-0, A56-1 and A56-5",
         all(clean[i].passed for i in (0, 1, 5)),
         "; ".join("%s %s" % (c.name.split()[0], c.passed) for c in clean))
    half_on = arm_label(_arm("larger", "half", 1.0))
    early = one_base(base, arms=arms, faults={half_on: "bite_with_substitutes"})
    note("a constraint that binds with a stand-in left is reported by A56-1",
         not crit(early, 1).passed)
    whole_on = arm_label(_arm("P", "all", 1.0))
    idle = one_base(base, arms=arms, faults={whole_on: "no_bite"})
    note("a constraint that never binds is reported by A56-1",
         not crit(idle, 1).passed)

    def broken(change):
        rs = copy.deepcopy(good)
        change(rs)
        return rs

    def pick(rs, **want):
        return [x for x in rs if all(x.get(k) == v for k, v in want.items())]

    note("A56-0 fails when a script changed after the gate, and on an open "
         "ledger",
         not crit(good, 0, dict(g_ok, a55_sha="0" * 16)).passed
         and not crit(broken(lambda rs: pick(rs, kind="cut")[0].update(
             books_close=False)), 0).passed)
    note("A56-0 fails when edges put back do not restore the routing",
         not crit(broken(lambda rs: [x for x in pick(rs, kind="cut")
                                     if x["restore"]][0].update(
                                         restored_exactly=False)), 0).passed)

    def lift_kept(rs):
        for x in pick(rs, part="all", size=1.0):
            if not x["restore"]:
                x["kept_end_tail"] = 1.5

    note("A56-2 fails when the kept payees gain at full strength",
         not crit(broken(lift_kept), 2).passed)

    def lose_books(rs):
        for x in pick(rs, part="all", size=1.0):
            x.pop("turned_away_to", None)

    note("A56-3 fails when where the turned-away inflow landed is missing",
         not crit(broken(lose_books), 3).passed)

    def stay(rs):
        for x in pick(rs, kind="cut"):
            if x["restore"]:
                x["switches_as_twin"], x["state"] = True, "kept"

    note("A56-4 fails when a cell with no switch flipped keeps the loss",
         not crit(broken(stay), 4).passed)

    def cut_path(rs):
        pick(rs, kind="cut")[0]["_path"] = pick(rs, kind="cut")[0]["_path"][:5]

    try:
        short = not crit(broken(cut_path), 5).passed
    except ValueError:
        short = True
    note("A56-5 fails on a path that is not the whole span", short)
    held = sum(1 for c in checks if c["held"])
    return {"module_sha": _module_sha(MODULE), "script_sha": _module_sha(SCRIPT),
            "checks": checks, "held": held, "of": len(checks),
            "verdict": "pass" if held == len(checks) else "fail"}


# ---------------------------------------------------------------------------
# D38, the record, the tables, the entry point.
# ---------------------------------------------------------------------------

def time_bases(workers: int) -> None:
    probes = [
        {"block": "main", "need": 0.20, "stress": "healthy",
         "elasticity": 0.5, "authority": "endogenous", "seed": SEEDS[0]},
        {"block": "main", "need": 0.20, "stress": "leak_recycled",
         "elasticity": 0.5, "authority": "none", "seed": SEEDS[0]},
    ]
    _A54.make_twin(base_config(probes[0]))  # warm-up, not timed
    per = {}
    for b in probes:
        t0 = time.perf_counter()
        rows = one_base(b)
        dt = time.perf_counter() - t0
        per[b["stress"]] = dt
        print("   %-14s %-10s %3d runs  %.1f s  (%.3f s a run)" % (
            b["stress"], b["authority"], len(rows), dt, dt / len(rows)))
    eff = max(1, min(workers, os.cpu_count() or 1))
    for count in (2, len(SEEDS)):
        bases = base_keys(seeds=SEEDS[:count])
        total = sum(per[b["stress"]] for b in bases)
        print("   %d seeds: %d configurations, %d runs, %.0f s serial, about "
              "%.0f s on %d workers" % (
                  count, len(bases), sum(runs_of(b) for b in bases), total,
                  total / eff, eff))


def station_config() -> dict:
    return {
        "carrier": "A54's main block in the two strains whose twin is not "
                   "itself running down",
        "rounds": ROUNDS, "cut_at_close_of_round": PENALTY_ROUND,
        "classes": dict(CLASS_TEXT),
        "constraint": "a node takes in 1 - e * (1 - fill) of its routed "
                      "inflow; fill is the smallest, over the kinds it bought "
                      "from before the cut, of the best such share among the "
                      "counterparties of that kind it still pays, at the fixed "
                      "point; applied at the model's capacity step, wages "
                      "untouched",
        "grid": {
            "need_multiples": list(NEEDS),
            "stresses": {s: _A54.STRESS_SPECS[s] for s in STRESSES},
            "elasticities": list(ELASTICITIES),
            "authorities": list(AUTHORITIES),
            "seeds": list(SEEDS),
            "strengths": list(STRENGTHS),
            "cuts": {"all F": "every out-edge into the financial layer",
                     "all P": "every out-edge into the production side",
                     "half larger": "half, by flow, of the kind the target "
                                    "has more suppliers of"},
            "restore_after": RESTORE_AFTER,
        },
        "tail": TAIL, "at": list(AT), "floor_multiple": FLOOR_MULTIPLE,
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
    rows = _A55._records(run["rows"]["cut"])
    twins = _A55._records(run["rows"]["twin"])
    print("### the two targets\n")
    out = []
    for kind in TARGETS:
        p = "targets.%s." % kind
        out.append([kind, twins[0][p + "layer"],
                    _m((t[p + "suppliers.F"] for t in twins), 0),
                    _m((t[p + "suppliers.P"] for t in twins), 0),
                    _m((t[p + "payers"] for t in twins), 0),
                    _m((t[p + "held_at_penalty"] for t in twins), 3),
                    _m((t[p + "inflow_per_round"] for t in twins), 3),
                    " / ".join(_m((t[p + "payers_with_it_as_only_supplier_"
                                     "of_its_kind." + L] for t in twins), 0)
                               for L in LAYERS)])
    _A55._md(["target", "layer", "suppliers in the financial layer",
              "on the production side", "payers", "balance",
              "inflow a round", "payers with it as their one supplier of its "
              "kind: fin / mid / hhw / hh0"], out)
    print("### a whole kind cut, by strength of the constraint\n")
    out = []
    for kind in TARGETS:
        for cls in CLASSES:
            for e in STRENGTHS:
                xs = [x for x in rows if x["target"] == kind
                      and x["cls"] == cls and x["part"] == "all"
                      and x["size"] == e and not x["restore"]]
                if not xs:
                    continue
                out.append([
                    kind, CLASS_TEXT[cls], "%g" % e, len(xs),
                    _m((x["cut"] for x in xs), 0),
                    _m((x["flow_share_cut"] for x in xs), 3),
                    *(_m(x["deviation_at.%d" % k] for x in xs)
                      for k in (1, 5, 20)),
                    _m(x["tail"] for x in xs),
                    _fmt_count(_count(x["state"] for x in xs)),
                    _m((x["cut_end_tail"] for x in xs), 3),
                    _m((x["kept_end_tail"] for x in xs), 3),
                    _m((x["payers_tail"] for x in xs), 3),
                    _m(x["flow_tail_ratio"] for x in xs),
                    _m(x["circulating_tail_ratio"] for x in xs),
                    _m(x["wage_tail_ratio"] for x in xs),
                    _m((x["followers_that_are_paid"] for x in xs), 0),
                    _m((x.get("turned_away_to.fin") for x in xs), 3),
                    _m((x.get("turned_away_to.mid") for x in xs), 3),
                    _m((x["target_rounds_short_of_wages"] for x in xs), 0),
                    _m((x["below_diff_close"] for x in xs), 0),
                    _fmt_count(_count(x["flip"] for x in xs))])
    _A55._md(["target", "kind cut", "e", "cells", "edges cut",
              "share of its spending", "own share after 1", "after 5",
              "after 20", "tail", "states", "payees cut off",
              "payees kept", "its payers", "total flow", "claims",
              "wages paid", "other limited nodes that are paid",
              "turned away to fin", "to mid", "rounds short of its wages",
              "nodes below the floor less the twin's", "flips"], out)
    print("### half of a kind cut, and the edges put back\n")
    out = []
    for kind in TARGETS:
        for arm in ARM_ORDER:
            xs = [x for x in rows if x["target"] == kind and x["arm"] == arm
                  and (x["part"] == "half" or x["restore"])]
            if not xs:
                continue
            out.append([kind, arm, len(xs), _m((x["cut"] for x in xs), 0),
                        _m(x["deviation_at.20"] for x in xs),
                        _m(x["tail"] for x in xs),
                        _fmt_count(_count(x["state"] for x in xs)),
                        _m((x["cut_end_tail"] for x in xs), 3),
                        _m((x["kept_end_tail"] for x in xs), 3),
                        _m(x["flow_tail_ratio"] for x in xs),
                        sum(1 for x in xs if not x["switches_as_twin"]),
                        _fmt_count(_count(x["flip"] for x in xs))])
    _A55._md(["target", "arm", "cells", "edges cut", "own share after 20",
              "tail", "states", "payees cut off", "payees kept", "total flow",
              "cells with a switch flipped", "flips"], out)
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
        print("stage %s, rule 19: a cut at strength zero against the same cut "
              "on Network, and full strength with nothing cut against the "
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
