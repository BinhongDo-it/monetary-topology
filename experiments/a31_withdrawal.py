"""A31: the issuance rule's other side, and whose accounts it comes out of.

Ruled 2026-09-11. The endogenous rule issues the Layer 2 inflow's shortfall
below its opening level and has no branch that takes anything back, so A30 read
a one-round freeze settling a healthy economy permanently larger, and a
destruction issued back only down to that level. This station gives the rule
its other half and asks the question that half opens: the rule pins one
aggregate, the floor is read per node, so whose accounts the claims come out of
decides who ends up below the floor while the aggregate is pinned either way.

Three positions, each a set this model already names: the financial layer, the
layer the issuance lands in; every live node; and every live node outside the
financial layer, the set the sovereign's pass-down pays into. Two gains, 1.0
and 0.5.

Four shocks at round 150, on A30's driver and carrier:

    freeze    a share of every live node's balance leaves the accounts at the
              close of round 149 and comes back at the close of round 150
    destroy   the same removal, never returned
    release   a share of the parked stock returns to the accounts that parked
              it, the latent pool coming back at once. Only where parking is
              latent claims and nothing else, which is the plain leak: on the
              recycled leak the parked stock is the sovereign's bonds and
              returning it would be a repayment, another object, and the
              healthy structure parks nothing.
    none      the twin every other row is read against

Three steps, one at a time and in this order:

    python experiments/a31_withdrawal.py --gate            # rule 19
    python experiments/a31_withdrawal.py --time            # seconds per cell
    python experiments/a31_withdrawal.py --run --seeds 5   # the grid

``--run`` does not start until ``--gate`` has passed on the module and this
script as they are now. ``--run --smoke`` is a reduced grid that checks the
code runs, gates itself on its own configurations and writes nothing;
``--no-write`` prints and writes nothing on any step.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.machinery
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

import monetary_topology.network as _NET  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkHistory,
    WITHDRAW_FIELDS,
    WithdrawSpec,
)

RECORD = RESULTS / "a31_withdrawal.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()

#: The module as it stood before ``WithdrawSpec``, kept beside it under the
#: repository's backup convention.
PRE_MODULE = SRC / "network.py.expired_20260911_pre_A31"
#: A30's record, whose rows this module and this driver have to reproduce.
A30_RECORD = RESULTS / "a30_shock.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A29's helpers and A30's, taken rather than restated: the record format, the
#: bit-for-bit comparison, the criterion type, the carrier, the floors and the
#: absorption and block readings.
_A29 = _load(ROOT / "experiments" / "a29_sovereign.py", "_a29_for_a31")
_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a31")

r = _A30.r
_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_same = _A30._same
_tally = _A30._tally
_num = _A30._num
_median = _A30._median
_range = _A30._range
_col_median = _A30._col_median
_default_workers = _A30._default_workers
_print_criteria = _A30._print_criteria
_rng_digest = _A30._rng_digest
Criterion = _A30.Criterion

ROUNDS = _A30.ROUNDS
SEEDS = _A30.SEEDS
TAIL = _A30.TAIL
FLOOR_MULTIPLE = _A30.FLOOR_MULTIPLE
LEDGER_TOL = _A30.LEDGER_TOL
SHOCK_ROUND = _A30.SHOCK_ROUND
WINDOW = _A30.WINDOW
BLOCK = _A30.BLOCK
HORIZON_K = _A30.HORIZON_K
NEEDS = _A30.NEEDS
STRESSES = _A30.STRESSES
STRESS_SPECS = _A30.STRESS_SPECS
ELASTICITIES = _A30.ELASTICITIES
ABSORB_STATES = _A30.ABSORB_STATES
FLIP_STATES = _A30.FLIP_STATES
absorption = _A30.absorption
flip = _A30.flip
CODES = _A30.CODES

#: The rule needs a target to overshoot, so every cell issues endogenously.
AUTHORITY = "endogenous"
#: Whose accounts the claims come out of, and how much of the overshoot is
#: taken each round. ``("none", None)`` is A30's one-sided rule, the reference
#: every other row is read against.
POSITIONS: tuple[str, ...] = ("financial", "proportional", "production")
GAINS: tuple[float, ...] = (1.0, 0.5)
RULES: tuple[tuple, ...] = (("none", None),) + tuple(
    (p, g) for p in POSITIONS for g in GAINS)
#: (kind, share). Every strain runs the first three; the plain leak runs the
#: releases as well, for the reason in the module docstring.
SHOCKS: tuple[tuple[str, float], ...] = (
    ("none", 0.0), ("freeze", 0.3), ("destroy", 0.1))
RELEASES: tuple[tuple[str, float], ...] = (("release", 0.1), ("release", 0.3))
SHOCK_KINDS: tuple[str, ...] = ("none", "freeze", "destroy", "release")
#: The strain whose parked stock is latent claims and nothing else.
RELEASE_STRESS = "leak"
#: Windows the ringing reading is printed over: before the shock, and the tail.
RING_WINDOWS: tuple[tuple[int, int], ...] = ((100, 150), (250, 300))
#: The reduced grid ``--smoke`` runs: every strain, rule and shock at the
#: bistable floor, one elasticity, two seeds.
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def shocks_for(stress: str) -> tuple:
    return SHOCKS + (RELEASES if stress == RELEASE_STRESS else ())


def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, rules=RULES) -> list:
    keys = []
    for need in needs:
        for stress in stresses:
            for e in elasticities:
                for position, gain in rules:
                    for kind, size in shocks_for(stress):
                        for seed in seeds:
                            keys.append({"need": need, "stress": stress,
                                         "elasticity": e, "position": position,
                                         "gain": gain, "shock": kind,
                                         "size": size, "seed": seed})
    return keys


def cell_config(key: dict) -> NetworkConfig:
    """A30's carrier, plus this cell's rule. The shock is not in the config:
    the driver applies it."""
    cfg = _A30.cell_config({"need": key["need"], "stress": key["stress"],
                            "elasticity": key["elasticity"],
                            "authority": AUTHORITY, "seed": key["seed"]})
    if key["position"] == "none":
        return cfg
    return dataclasses.replace(
        cfg, withdraw=WithdrawSpec(position=key["position"], gain=key["gain"]))


# ---------------------------------------------------------------------------
# The driver. A30's, with the release added.
# ---------------------------------------------------------------------------

def drive(cfg: NetworkConfig, shock: str, size: float) -> tuple:
    """Run one configuration through ``_run_steps``, acting only at the yield.

    Returns the network, whose ``_history`` is the run's history, and what the
    driver saw: what was removed or released, whether the claim total stayed
    equal to held plus parked at every yield, and whether a freeze came back
    node for node.
    """
    if shock not in SHOCK_KINDS:
        raise ValueError("shock must be one of %s, got %r" % (SHOCK_KINDS, shock))
    net = Network(cfg)
    frozen = None
    removed = 0.0
    released = 0.0
    books = True
    returned = None
    for t in net._run_steps():
        if shock in ("freeze", "destroy") and t == SHOCK_ROUND - 1:
            take = size * np.maximum(net.holdings, 0.0) * net._alive
            net.holdings -= take
            removed = float(take.sum())
            net._total_claims -= removed
            if shock == "freeze":
                frozen = take
        elif shock == "release" and t == SHOCK_ROUND - 1:
            # The latent pool comes back at once, to the accounts that parked
            # it, which is the shape ``_return_claims`` already uses. Nothing
            # is created: the claim total counts parked claims, so this moves
            # the stock between two columns the round's assertion sums.
            back = size * np.maximum(net._parked, 0.0)
            net._parked -= back
            net.holdings += back
            released = float(back.sum())
        elif frozen is not None and t == SHOCK_ROUND:
            before = net.holdings.copy()
            net.holdings += frozen
            net._total_claims += float(frozen.sum())
            tol = LEDGER_TOL * max(1.0, float(np.abs(before).max())
                                   / cfg.initial_claims)
            returned = bool(np.abs((net.holdings - before) - frozen).max()
                            <= tol)
            frozen = None
        stock = float(net.holdings.sum()) + float(net._parked.sum())
        tol = LEDGER_TOL * max(1.0, stock / cfg.initial_claims)
        if abs(net._total_claims - stock) > tol:
            books = False
    return net, {"removed": removed, "released": released, "books": books,
                 "returned": returned}


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net, seen = drive(cfg, key["shock"], key["size"])
    h = net._history
    zeros = np.zeros(ROUNDS)
    row = dict(key)
    row.update({
        "removed": r(seen["removed"]),
        "released": r(seen["released"]),
        # Booleans and not the residuals: those are machine rounding and would
        # differ in the last digit between two builds.
        "books_close": seen["books"],
        "returned_exact": seen["returned"],
        "below_close": int(net._below.sum()),
        # Private: read by the analysis, stripped before anything is written.
        "_flow": np.asarray(h.total_volume, dtype=float),
        "_circ": np.asarray(h.holdings, dtype=float).sum(axis=1),
        "_below": np.asarray(h.starved, dtype=float),
        "_parked": np.asarray(h.parked, dtype=float),
        "_issued": np.asarray(h.issuance, dtype=float),
        "_l2": np.asarray(h.layer2_inflow, dtype=float),
        "_target": float(net._baseline_active or 0.0),
        "_withdrawn": (zeros if h.withdrawn is None
                       else np.asarray(h.withdrawn, dtype=float)),
        "_withdrawn_l2": (zeros if h.withdrawn_l2 is None
                          else np.asarray(h.withdrawn_l2, dtype=float)),
        "_withdrawn_unmet": (zeros if h.withdrawn_unmet is None
                             else np.asarray(h.withdrawn_unmet, dtype=float)),
        "_rng": _rng_digest(net),
    })
    return row


def _rule_index(key: dict) -> int:
    return RULES.index((key["position"], key["gain"]))


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            _rule_index(x), SHOCK_KINDS.index(x["shock"]), x["size"],
            x["seed"])


def run_cells(keys: list, workers: int) -> list:
    if workers <= 1:
        rows = [one_cell(k) for k in keys]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one_cell, keys, chunksize=8))
    return sorted(rows, key=_row_key)


# ---------------------------------------------------------------------------
# Readings. Objects first; every state below is printed beside the numbers it
# came from, and a state that is not a reading says so.
# ---------------------------------------------------------------------------

def _carrier(x: dict) -> tuple:
    return (x["need"], x["stress"], x["elasticity"])


def _rule(x: dict) -> tuple:
    return (x["position"], x["gain"])


def _base(x: dict) -> tuple:
    return _carrier(x) + _rule(x)


def _gkey(x: dict) -> tuple:
    return _base(x) + (x["shock"], x["size"])


def _gsort(g: tuple) -> tuple:
    return (g[0], STRESSES.index(g[1]), g[2], RULES.index((g[3], g[4])),
            SHOCK_KINDS.index(g[5]), g[6])


def rule_label(position, gain) -> str:
    return "one-sided" if position == "none" else "%s gain %.1f" % (position,
                                                                    gain)


def _shock_label(kind: str, size: float) -> str:
    return "none" if kind == "none" else "%s %.1f" % (kind, size)


def _sign_changes(v: np.ndarray) -> int:
    s = np.sign(v)
    s = s[s != 0]
    return int(np.count_nonzero(np.diff(s) != 0)) if s.size > 1 else 0


def twins_and_bands(rows: list) -> tuple:
    """Each base cell's unshocked run by seed, and the floor under a shocked
    cell's flow: the twin's dispersion across seeds, round by round (gate six),
    times the stage's multiple."""
    twins = {}
    for x in rows:
        if x["shock"] == "none":
            twins.setdefault(_base(x), {})[x["seed"]] = x
    bands = {}
    for b, by in twins.items():
        if len(by) >= 2:
            flows = np.array([by[s]["_flow"] for s in sorted(by)])
            bands[b] = FLOOR_MULTIPLE * flows.std(axis=0, ddof=1)
    return twins, bands


def block_class(diff: int) -> str:
    """A30-3's six states, read at the block level only: what this station asks
    of the count below the floor is whether a block moved."""
    state = flip(diff)
    return state if state in ("block under", "block lifted") else "no block"


BLOCK_CLASSES: tuple[tuple[str, str], ...] = (
    ("block under", "%d or more nodes more below the floor than the reference "
     "at the close" % BLOCK),
    ("block lifted", "%d or more fewer" % BLOCK),
    ("no block", "everything else, printed as A30-3's own six states beside "
     "it"))

POSITION_STATES: tuple[tuple[str, str], ...] = (
    ("position decides", "the three positions do not all leave the same "
     "block state"),
    ("the aggregate decides", "all three leave the same block state, so on "
     "this cell pinning the aggregate settles it"),
    ("split, no reading", "one position's seeds disagree with each other"))


def read_cells(rows: list, twins: dict, bands: dict) -> list:
    """Every cell's own numbers, and for a shocked cell its readings against
    its twin. Private arrays are carried along for the group paths and are
    stripped before anything is written."""
    k0 = SHOCK_ROUND
    out = []
    for x in rows:
        c = {k: v for k, v in x.items() if not k.startswith("_")}
        flow, circ, parked = x["_flow"], x["_circ"], x["_parked"]
        w, wl2 = x["_withdrawn"], x["_withdrawn_l2"]
        taken = float(w.sum())
        target = x["_target"]
        dev = (np.divide(x["_l2"] - target, target,
                         out=np.full(ROUNDS, np.nan), where=target > 0)
               if target > 0 else np.full(ROUNDS, np.nan))
        c.update({
            "flow_at_shock_round": _num(flow[k0]),
            "flow_tail": _num(flow[-TAIL:].mean()),
            "circulating_tail": _num(circ[-TAIL:].mean()),
            "parked_tail": _num(parked[-TAIL:].mean()),
            "issued_total": _num(x["_issued"].sum()),
            "withdrawn_total": _num(taken),
            "withdrawn_unmet_total": _num(x["_withdrawn_unmet"].sum()),
            "withdrawn_l2_share": _num(float(wl2.sum()) / taken)
                                  if taken > 0 else None,
            "rounds_withdrawing": int((w > 0.0).sum()),
            # Where the Layer 2 inflow sits against the rule's own target.
            "l2_over_target_before_shock": _num(dev[k0 - 1]),
            "l2_over_target_tail": _num(np.nanmean(dev[-TAIL:]))
                                   if target > 0 else None,
            # The ringing object: how often the gap changes sign, and how big
            # it is before the shock and in the tail.
            "target_gap_sign_changes": _sign_changes(dev[1:])
                                       if target > 0 else None,
            "target_gap_size": {
                "%d_%d" % w0w1: _num(float(np.nanmean(np.abs(dev[w0w1[0]:w0w1[1]]))))
                for w0w1 in RING_WINDOWS} if target > 0 else None,
        })
        c["is_twin"] = x["shock"] == "none"
        tw = twins.get(_base(x), {}).get(x["seed"])
        if x["shock"] == "none" or tw is None:
            if x["shock"] != "none":
                c["has_twin"] = False
            out.append(c)
            continue
        base_flow = tw["_flow"]
        d = flow - base_flow
        rel = np.divide(d, base_flow, out=np.full_like(d, np.nan),
                        where=base_flow > 0)
        band = bands.get(_base(x))
        tau, state = absorption(d, band)
        bd = x["_below"] - tw["_below"]
        after = bd[k0:]
        hit = np.flatnonzero(np.abs(after) >= BLOCK)
        diff_close = int(x["below_close"] - tw["below_close"])
        twin_flow_tail = float(base_flow[-TAIL:].mean())
        twin_circ_tail = float(tw["_circ"][-TAIL:].mean())
        tail_ratio = (float(flow[-TAIL:].mean()) / twin_flow_tail
                      if twin_flow_tail > 0 else None)
        moved = float(x["removed"] or 0.0) + float(x["released"] or 0.0)
        extra_w = float(w[k0 + 1:].sum() - tw["_withdrawn"][k0 + 1:].sum())
        extra_i = float(x["_issued"][k0 + 1:].sum()
                        - tw["_issued"][k0 + 1:].sum())
        c.update({
            "has_twin": True,
            "flow_below_twin_at_shock_round": bool(d[k0] < 0.0),
            "drop_at_shock_round": _num(rel[k0]),
            "band_share_at_shock_round": (
                None if band is None or base_flow[k0] <= 0 else
                _num(band[k0] / float(np.mean(
                    [twins[_base(x)][s]["_flow"][k0]
                     for s in sorted(twins[_base(x)])])))),
            "tau": tau,
            "absorption": state,
            "deviation_at": {str(k): _num(rel[k0 + k]) for k in HORIZON_K},
            "below_diff_at": {str(k): int(bd[k0 + k]) for k in HORIZON_K},
            "below_diff_close": diff_close,
            "twin_below_close": int(tw["below_close"]),
            "flip": flip(diff_close),
            "block_first_k": int(hit[0]) if hit.size else None,
            "below_diff_peak": int(after.max()),
            "below_diff_peak_k": int(np.argmax(after)),
            "rounds_block_under": int((after >= BLOCK).sum()),
            "rounds_block_lifted": int((after <= -BLOCK).sum()),
            "flow_tail_ratio": _num(tail_ratio),
            "circulating_tail_ratio": (
                _num(circ[-TAIL:].mean() / twin_circ_tail)
                if twin_circ_tail > 0 else None),
            "recovered": (_num(1.0 - (tail_ratio - 1.0) / float(rel[k0]))
                          if tail_ratio is not None and np.isfinite(rel[k0])
                          and rel[k0] != 0.0 else None),
            # What the rule did about this shock, over what its twin did.
            "withdrawn_after_shock": _num(extra_w),
            "issued_after_shock": _num(extra_i),
            "withdrawn_after_over_moved": (_num(extra_w / moved)
                                           if moved > 0 else None),
            "issued_after_over_moved": (_num(extra_i / moved)
                                        if moved > 0 else None),
            "same_draws_as_twin": x["_rng"] == tw["_rng"],
        })
        c["_rel"] = rel
        out.append(c)
    return out


def groups(cells: list) -> list:
    """Every shocked group (need, strain, elasticity, rule, shock) over its
    seeds, never pooled across groups."""
    by = {}
    for c in cells:
        if c["shock"] != "none" and c.get("has_twin"):
            by.setdefault(_gkey(c), []).append(c)
    out = []
    for g in sorted(by, key=_gsort):
        cs = sorted(by[g], key=lambda c: c["seed"])
        states = [c["absorption"] for c in cs]
        taus = [c["tau"] for c in cs]
        out.append({
            "need": g[0], "stress": g[1], "elasticity": g[2],
            "position": g[3], "gain": g[4], "shock": g[5], "size": g[6],
            "seeds": [c["seed"] for c in cs],
            "absorption": states,
            "absorption_state": states[0] if len(set(states)) == 1 else "split",
            "tau": taus,
            "tau_median": _median([t for t in taus if t is not None]),
            "flip": [c["flip"] for c in cs],
            "below_diff_close": [c["below_diff_close"] for c in cs],
            "twin_below_close": [c["twin_below_close"] for c in cs],
            "block_came_back": sum(
                1 for c in cs if c["flip"] not in ("block under",
                                                   "block lifted")
                and (c["rounds_block_under"] or c["rounds_block_lifted"])),
            "drop_at_shock_round_median": _median(
                [c["drop_at_shock_round"] for c in cs]),
            "band_share_at_shock_round": cs[0]["band_share_at_shock_round"],
            "flow_tail_ratio_median": _median([c["flow_tail_ratio"]
                                               for c in cs]),
            "circulating_tail_ratio_median": _median(
                [c["circulating_tail_ratio"] for c in cs]),
            "recovered_median": _median([c["recovered"] for c in cs]),
            "withdrawn_after_over_moved_median": _median(
                [c["withdrawn_after_over_moved"] for c in cs]),
            "issued_after_over_moved_median": _median(
                [c["issued_after_over_moved"] for c in cs]),
            "withdrawn_l2_share_median": _median([c["withdrawn_l2_share"]
                                                  for c in cs]),
            "median_deviation_path_from_shock_round": _col_median(
                np.array([c["_rel"][SHOCK_ROUND:] for c in cs])),
        })
    return out


def rule_pairs(cells: list) -> list:
    """A31-3: each two-sided twin against the one-sided twin on the same
    carrier and seed, then the three positions against each other."""
    twins = {}
    for c in cells:
        if c["shock"] == "none":
            twins.setdefault(_carrier(c) + (c["seed"],), {})[_rule(c)] = c
    by = {}
    for key, rules in twins.items():
        ref = rules.get(("none", None))
        if ref is None:
            continue
        for (position, gain), c in rules.items():
            if position == "none":
                continue
            entry = by.setdefault(key[:3] + (gain,), {}).setdefault(
                position, {"seeds": [], "below_diff": [], "class": [],
                           "circulating_ratio": [], "flow_ratio": [],
                           "withdrawn": [], "withdrawn_l2_share": [],
                           "l2_over_target_tail": [], "issued": []})
            diff = int(c["below_close"] - ref["below_close"])
            entry["seeds"].append(key[3])
            entry["below_diff"].append(diff)
            entry["class"].append(block_class(diff))
            entry["circulating_ratio"].append(
                _num(c["circulating_tail"] / ref["circulating_tail"])
                if ref["circulating_tail"] else None)
            entry["flow_ratio"].append(_num(c["flow_tail"] / ref["flow_tail"])
                                       if ref["flow_tail"] else None)
            entry["withdrawn"].append(c["withdrawn_total"])
            entry["withdrawn_l2_share"].append(c["withdrawn_l2_share"])
            entry["l2_over_target_tail"].append(c["l2_over_target_tail"])
            entry["issued"].append(c["issued_total"])
    out = []
    for key in sorted(by, key=lambda k: (k[0], STRESSES.index(k[1]), k[2],
                                         -(k[3] or 0.0))):
        positions = {}
        for position in POSITIONS:
            e = by[key].get(position)
            if e is None:
                continue
            classes = set(e["class"])
            positions[position] = {
                "seeds": e["seeds"], "below_diff": e["below_diff"],
                "class": e["class"],
                "state": e["class"][0] if len(classes) == 1 else "split",
                "circulating_ratio_median": _median(e["circulating_ratio"]),
                "flow_ratio_median": _median(e["flow_ratio"]),
                "withdrawn_median": _median(e["withdrawn"]),
                "withdrawn_l2_share_median": _median(e["withdrawn_l2_share"]),
                "l2_over_target_tail_median": _median(e["l2_over_target_tail"]),
                "issued_median": _median(e["issued"]),
            }
        states = {p["state"] for p in positions.values()}
        reading = ("split, no reading" if "split" in states else
                   "the aggregate decides" if len(states) == 1 else
                   "position decides")
        refs = [c for c in cells if c["shock"] == "none"
                and _carrier(c) == key[:3] and _rule(c) == ("none", None)]
        out.append({
            "need": key[0], "stress": key[1], "elasticity": key[2],
            "gain": key[3],
            "one_sided": {
                "below_close": [c["below_close"] for c in refs],
                "l2_over_target_tail_median": _median(
                    [c["l2_over_target_tail"] for c in refs]),
                "issued_median": _median([c["issued_total"] for c in refs]),
                "circulating_tail_median": _median([c["circulating_tail"]
                                                    for c in refs]),
            },
            "positions": positions,
            "reading": reading,
        })
    return out


def ringing(cells: list) -> list:
    """A31-6: how often the gap against the rule's target changes sign, and how
    big it is before the shock and in the tail. Read on the twins."""
    by = {}
    for c in cells:
        if c["shock"] == "none":
            by.setdefault(_rule(c), []).append(c)
    out = []
    for rule in sorted(by, key=lambda k: RULES.index(k)):
        cs = by[rule]
        entry = {"position": rule[0], "gain": rule[1], "cells": len(cs),
                 "sign_changes_median": _median(
                     [c["target_gap_sign_changes"] for c in cs]),
                 "sign_changes_range": _range(
                     [c["target_gap_sign_changes"] for c in cs]),
                 "rounds_withdrawing_median": _median(
                     [c["rounds_withdrawing"] for c in cs]),
                 "withdrawn_median": _median([c["withdrawn_total"] for c in cs]),
                 "issued_median": _median([c["issued_total"] for c in cs])}
        for w0, w1 in RING_WINDOWS:
            entry["gap_size_%d_%d_median" % (w0, w1)] = _median(
                [(c["target_gap_size"] or {}).get("%d_%d" % (w0, w1))
                 for c in cs])
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def _shocked(cells: list) -> list:
    return [c for c in cells if c["shock"] != "none" and c.get("has_twin")]


def _two_sided(cells: list) -> list:
    return [c for c in cells if c["position"] != "none"]


A31_0 = "A31-0 the switch off is the module before it, and the driver is the model"


def criterion_a31_0(g, cells: list) -> Criterion:
    shocked = _shocked(cells)
    freezes = [c for c in shocked if c["shock"] == "freeze"]
    books = sum(1 for c in cells if c["books_close"])
    back = sum(1 for c in freezes if c["returned_exact"])
    draws = sum(1 for c in shocked if c.get("same_draws_as_twin"))
    rows_ok = (books == len(cells) and back == len(freezes)
               and draws == len(shocked))
    part = (
        "In every cell the claim total equals held plus parked at every yield, "
        "to %.0e of the opening stock: %d of %d. Every freeze comes back node "
        "for node: %d of %d. Every shocked cell's generators end where its "
        "twin's end: %d of %d. The round loop's own asserts, the withdrawal's "
        "among them, did not fire: all %d cells completed."
        % (LEDGER_TOL, books, len(cells), back, len(freezes), draws,
           len(shocked), len(cells)))
    state_map = (
        "State map: the module with the switch off identical to the module "
        "before it, the driver with no shock identical to Network.run(), "
        "A30's rows reproduced, and the three checks above holding -> PASS; "
        "anything else -> FAIL; no gate section -> not judged, and --run does "
        "not start.")
    if not g:
        return Criterion(A31_0, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + part + " " + state_map, evaluated=False)
    a30 = g.get("a30_rows", {})
    head = (
        "With the switch off, the module before it and the module now ran %d "
        "configurations in one process (the library default, A18's exit arm "
        "with and without write-off, A18_E twice, A23, A18_F, A29's control "
        "and treated cells with the debt served, and every base cell of A30's "
        "grid): %d history fields and the closing state compared bit for bit, "
        "%d differ, and the three new fields are None in every run. The "
        "driver with no shock against Network.run() on the same "
        "configurations: %d differ. A30's recorded rows recomputed through "
        "this driver: %d rows, %d fields differ.%s"
        % (len(g["configs"]), g["fields_compared"], len(g["differ"]),
           len(g["driver_differ"]), a30.get("rows", 0),
           len(a30.get("differ", [])),
           "" if not g["differ"] else " First: %s" % g["differ"][:3]))
    return Criterion(A31_0, "instrument", g["verdict"] == "pass" and rows_ok,
                     "%s %s Gate verdict: %s. %s" % (head, part, g["verdict"],
                                                     state_map))


def criterion_a31_1(cells: list) -> Criterion:
    two = _two_sided(cells)
    asked = [(c["withdrawn_total"] or 0.0) + (c["withdrawn_unmet_total"] or 0.0)
             for c in two]
    unmet = [(c["withdrawn_unmet_total"] or 0.0) / a if a > 0 else 0.0
             for c, a in zip(two, asked)]
    short = [c for c, u in zip(two, unmet) if u > 1e-9]
    books = sum(1 for c in cells if c["books_close"])
    ok = books == len(cells) and bool(two)
    return Criterion(
        "A31-1 the withdrawal's books close", "instrument", ok,
        "Every round, in the loop: what leaves held plus parked equals what "
        "was taken, no account is taken below zero, and what the cap leaves "
        "uncollected is recorded and not carried. Read back here: %d of %d "
        "cells close their claim total against held plus parked. Of %d "
        "two-sided cells, %d left anything uncollected; the largest share of "
        "what was asked that went uncollected is %s. State map: every cell "
        "closing -> PASS; any cell open -> FAIL, and nothing after this reads."
        % (books, len(cells), len(two), len(short),
           _median([max(unmet)]) if unmet else None))


def criterion_a31_2(cells: list, rp: list) -> Criterion:
    two = _two_sided(cells)
    live = [e for e in rp if (e["one_sided"]["l2_over_target_tail_median"] or 0.0) > 0]
    dead = []
    for e in live:
        for position, p in e["positions"].items():
            if not (p["withdrawn_median"] or 0.0) > 0:
                dead.append((e["need"], e["stress"], position))
    parts = []
    for position in POSITIONS:
        xs = [c for c in two if c["position"] == position]
        parts.append("%s: Layer 2 share of what was taken, median %s, %s; "
                     "rounds withdrawing, median %s of %d" % (
                         position,
                         _median([c["withdrawn_l2_share"] for c in xs]),
                         _range([c["withdrawn_l2_share"] for c in xs]),
                         _median([c["rounds_withdrawing"] for c in xs]),
                         ROUNDS))
    return Criterion(
        "A31-2 the switch carries something, and to the position it names "
        "(D28)", "instrument", not dead,
        "Wherever the one-sided reference ends above the rule's target, every "
        "position takes something: %d of %d carrier-and-gain cells, %d with a "
        "position that took nothing%s. Where it came from: %s. State map: "
        "every such cell withdrawing -> PASS; any taking nothing -> FAIL, and "
        "the readings after this have no object there."
        % (len(live) - len({(d[0], d[1]) for d in dead}), len(live),
           len(dead), "" if not dead else " %s" % dead[:5], "; ".join(parts)))


def criterion_a31_3(rp: list) -> Criterion:
    tally = _tally(e["reading"] for e in rp)
    decided = [e for e in rp if e["reading"] == "position decides"]
    lines = []
    for e in decided[:12]:
        lines.append("need %.2f %s e %.1f gain %s: %s; one-sided below the "
                     "floor %s" % (
                         e["need"], e["stress"], e["elasticity"], e["gain"],
                         ", ".join("%s %s (below %s, circulating %s)"
                                   % (p, e["positions"][p]["state"],
                                      e["positions"][p]["below_diff"],
                                      e["positions"][p]["circulating_ratio_median"])
                                   for p in POSITIONS if p in e["positions"]),
                         e["one_sided"]["below_close"]))
    if len(decided) > 12:
        lines.append("%d more in the rule_pairs section" % (len(decided) - 12))
    pinned = [p["l2_over_target_tail_median"] for e in rp
              for p in e["positions"].values()]
    one = [e["one_sided"]["l2_over_target_tail_median"] for e in rp]
    return Criterion(
        "A31-3 the aggregate is pinned either way, so who is below the floor "
        "is the reading", "own_reading", True,
        "Printed, not judged. Each two-sided twin against the one-sided twin "
        "on the same carrier and seed, at the close. Block states: %s. "
        "Reading per carrier and gain: %s. The Layer 2 inflow over the rule's "
        "target in the tail: one-sided median %s, %s; two-sided median %s, "
        "%s. Carrier and gain cells by reading: %s. Where the position "
        "decides: %s."
        % ("; ".join("%s = %s" % s for s in BLOCK_CLASSES),
           "; ".join("%s = %s" % s for s in POSITION_STATES),
           _median(one), _range(one), _median(pinned), _range(pinned),
           tally, "; ".join(lines) if lines else "nowhere"))


def _by_rule(groups_list: list, kinds: tuple) -> dict:
    by = {}
    for g in groups_list:
        if g["shock"] in kinds:
            by.setdefault((g["position"], g["gain"], g["shock"], g["size"]),
                          []).append(g)
    return by


def criterion_a31_4(grp: list) -> Criterion:
    by = _by_rule(grp, ("release",))
    lines = []
    for k in sorted(by, key=lambda k: (RULES.index(k[:2]), k[3])):
        gs = by[k]
        lines.append(
            "%s, %s: %s; tau median %s; flow tail %s, circulating %s; taken "
            "back over what was released %s, of it outside Layer 1 %s; issued "
            "over it %s; below the floor at the close %s" % (
                rule_label(k[0], k[1]), _shock_label(k[2], k[3]),
                _tally(s for g in gs for s in g["absorption"]),
                _median([g["tau_median"] for g in gs]),
                _median([g["flow_tail_ratio_median"] for g in gs]),
                _median([g["circulating_tail_ratio_median"] for g in gs]),
                _median([g["withdrawn_after_over_moved_median"] for g in gs]),
                _median([g["withdrawn_l2_share_median"] for g in gs]),
                _median([g["issued_after_over_moved_median"] for g in gs]),
                _tally(f for g in gs for f in g["flip"])))
    return Criterion(
        "A31-4 the latent pool comes back, and the tightening lands somewhere",
        "own_reading", True,
        "Printed, not judged. The parked stock returns to the accounts that "
        "parked it at the close of round %d, on the plain leak only. Read "
        "against the twin under the same rule: A30-2's absorption states (%s), "
        "the tail against the twin, what the rule took back after the shock "
        "over what came back, and where it took it. The one-sided rule has no "
        "withdrawal and answers a return by issuing less. By rule and size, "
        "over floors, elasticities and seeds: %s."
        % (SHOCK_ROUND - 1, "; ".join("%s = %s" % s for s in ABSORB_STATES),
           "; ".join(lines)))


def criterion_a31_5(grp: list) -> Criterion:
    by = _by_rule(grp, ("freeze", "destroy"))
    lines = []
    for k in sorted(by, key=lambda k: (k[2], RULES.index(k[:2]))):
        gs = by[k]
        lines.append(
            "%s, %s: %s; tau median %s; flow tail %s, recovered %s; taken "
            "back over what was moved %s; blocks at the close %s" % (
                rule_label(k[0], k[1]), _shock_label(k[2], k[3]),
                _tally(s for g in gs for s in g["absorption"]),
                _median([g["tau_median"] for g in gs]),
                _median([g["flow_tail_ratio_median"] for g in gs]),
                _median([g["recovered_median"] for g in gs]),
                _median([g["withdrawn_after_over_moved_median"] for g in gs]),
                _tally(f for g in gs for f in g["flip"])))
    return Criterion(
        "A31-5 A30's two shocks under a rule that also takes back",
        "own_reading", True,
        "Printed, not judged. Freeze and destruction read as in A30-2, A30-3 "
        "and A30-4, with the one-sided rows here as the reference A30 "
        "measured: a freeze settled a structure without a chronic gap "
        "permanently above its twin, by the amount the rule issued into the "
        "dip. By rule and shock, over floors, strains, elasticities and "
        "seeds: %s." % "; ".join(lines))


def criterion_a31_6(ring: list) -> Criterion:
    lines = []
    for e in ring:
        lines.append(
            "%s: sign changes of the gap against the target, median %s (%s); "
            "rounds withdrawing median %s; gap size %s before the shock and "
            "%s in the tail; issued median %s, taken back median %s" % (
                rule_label(e["position"], e["gain"]), e["sign_changes_median"],
                e["sign_changes_range"], e["rounds_withdrawing_median"],
                e.get("gap_size_100_150_median"), e.get("gap_size_250_300_median"),
                e["issued_median"], e["withdrawn_median"]))
    return Criterion(
        "A31-6 whether a rule that moves both ways rings", "own_reading", True,
        "Printed, not judged, and no line drawn on it. On the twins, with no "
        "shock: how often the Layer 2 inflow's gap against the rule's target "
        "changes sign over rounds 1 to %d, and the mean absolute gap over "
        "rounds %d to %d and %d to %d. A rule that answers a gap one round "
        "later can cross its own target, and the two gains are printed side "
        "by side because that is what would damp it. %s."
        % (ROUNDS - 1, RING_WINDOWS[0][0], RING_WINDOWS[0][1] - 1,
           RING_WINDOWS[1][0], RING_WINDOWS[1][1] - 1, "; ".join(lines)))


def criterion_a31_7(grp: list) -> Criterion:
    want = ROUNDS - SHOCK_ROUND
    key = "median_deviation_path_from_shock_round"
    full = [g for g in grp if len(g[key]) == want
            and all(v is not None for v in g[key])]
    return Criterion(
        "A31-7 the paths and the shares are on the record", "bookkeeping",
        bool(grp) and len(full) == len(grp),
        "The median over seeds of the flow's deviation from its twin, every "
        "round from %d to %d: %d of %d shocked groups carry a full path, each "
        "beside the share of what the rule took that came from outside Layer "
        "1. They are in the groups section, one per need, strain, elasticity, "
        "rule and shock. State map: every group full -> PASS; a group short or "
        "with a missing round -> FAIL, reprint."
        % (SHOCK_ROUND, ROUNDS - 1, len(full), len(grp)))


# ---------------------------------------------------------------------------
# Console tables: printed, never written.
# ---------------------------------------------------------------------------

def _axes(items: list) -> tuple:
    needs = sorted({x["need"] for x in items})
    stresses = [s for s in STRESSES if any(x["stress"] == s for x in items)]
    es = sorted({x["elasticity"] for x in items})
    return needs, stresses, es


def print_rule_pairs(rp: list) -> None:
    needs, stresses, es = _axes(rp)
    gains = sorted({e["gain"] for e in rp}, reverse=True)
    index = {(e["need"], e["stress"], e["elasticity"], e["gain"]): e for e in rp}
    print("\n   twins under a rule that also takes back, against the "
          "one-sided twin on the same seed")
    print("   each entry: block state, the count below the floor against the "
          "one-sided twin, circulating stock over its own")
    for e_val in es:
        for gain in gains:
            print("\n   elasticity %.1f, gain %.1f" % (e_val, gain))
            print("   %-26s%s" % ("", "".join("%-30s" % p for p in POSITIONS)))
            for need in needs:
                for s in stresses:
                    entry = index.get((need, s, e_val, gain))
                    txt = []
                    for p in POSITIONS:
                        q = (entry or {}).get("positions", {}).get(p)
                        if q is None:
                            txt.append("%-30s" % "-")
                            continue
                        txt.append("%-30s" % ("%s %s %s" % (
                            q["state"], q["below_diff"],
                            "-" if q["circulating_ratio_median"] is None
                            else "%.3f" % q["circulating_ratio_median"])))
                    print("   %-26s%s" % ("need %.2f %s" % (need, s),
                                          "".join(txt)))


def print_shock_tables(grp: list) -> None:
    needs, stresses, es = _axes(grp)
    index = {(g["need"], g["stress"], g["elasticity"], g["position"],
              g["gain"], g["shock"], g["size"]): g for g in grp}
    print("\n   each entry: absorption (%s), tau median, blocks under (+) or "
          "lifted (-) at the close, flow tail over the twin's"
          % ", ".join("%s = %s" % (v, k) for k, v in CODES.items()))
    for kind, size in SHOCKS[1:] + RELEASES:
        rows = [g for g in grp if g["shock"] == kind and g["size"] == size]
        if not rows:
            continue
        for e_val in es:
            print("\n   %s, elasticity %.1f" % (_shock_label(kind, size), e_val))
            print("   %-24s%s" % ("", "".join(
                "%-22s" % rule_label(p, gn) for p, gn in RULES)))
            for need in needs:
                for s in stresses:
                    if not any(g["need"] == need and g["stress"] == s
                               for g in rows):
                        continue
                    txt = []
                    for position, gain in RULES:
                        g = index.get((need, s, e_val, position, gain, kind,
                                       size))
                        if g is None:
                            txt.append("%-22s" % "-")
                            continue
                        under = sum(1 for f in g["flip"] if f == "block under")
                        lifted = sum(1 for f in g["flip"]
                                     if f == "block lifted")
                        blk = (("+%d" % under if under else "")
                               + ("-%d" % lifted if lifted else "")) or "0"
                        tau = g["tau_median"]
                        fr = g["flow_tail_ratio_median"]
                        code = CODES.get(g["absorption_state"], "?")
                        if g["absorption_state"] == "split":
                            cnt = {}
                            for st in g["absorption"]:
                                c2 = CODES.get(st, "?")
                                cnt[c2] = cnt.get(c2, 0) + 1
                            code = "/".join("%s%d" % (c2, cnt[c2])
                                            for c2 in sorted(cnt))
                        txt.append("%-22s" % ("%s t%s b%s %s" % (
                            code, "-" if tau is None else "%g" % tau, blk,
                            "-" if fr is None else "%.3f" % fr)))
                    print("   %-24s%s" % ("need %.2f %s" % (need, s),
                                          "".join(txt)))


# ---------------------------------------------------------------------------
# Rule 19: the module before the switch against the module now, the driver
# against ``Network.run()``, and A30's record recomputed through both.
# ---------------------------------------------------------------------------

#: The closing state compared beside the history.
CLOSING: tuple[str, ...] = ("_total_claims", "holdings", "_parked", "_below",
                            "_alive")


def load_pre_module():
    name = "monetary_topology._network_pre_a31"
    loader = importlib.machinery.SourceFileLoader(name, str(PRE_MODULE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def gate_configs(needs=NEEDS, elasticities=ELASTICITIES, full: bool = True) -> list:
    out = [("library default", NetworkConfig())]
    if full:
        out += [x for x in _A29.gate_configs() if x[0] != "library default"]
        c = _A29.config_for("drawdown", _NET.WriteOffSpec(), AUTHORITY, 0.50,
                            SEEDS[0], resupply_rate=0.0)
        park = _NET.ParkSpec(rate=0.02, target=_A30.TARGET)
        out.append(("A29 sovereign, pass-down", dataclasses.replace(
            c, park=park, sovereign=_NET.SovereignSpec(
                pass_rate=1.0, bond_share=1.0, landing="production"))))
        out.append(("A29 sovereign, debt served by a levy", dataclasses.replace(
            c, park=park, sovereign=_NET.SovereignSpec(
                pass_rate=1.0, bond_share=1.0, landing="production",
                maturity_rate=0.1, coupon_rate=0.02, funding="levy",
                levy_base="threshold"))))
    out += [x for x in _A30.gate_configs(needs=needs, elasticities=elasticities)
            if x[0] != "library default"]
    return out


def a30_rows(needs=NEEDS, seeds=(SEEDS[0],)) -> dict:
    """A30's recorded rows, recomputed on this module through this driver.

    A record on disk, produced before the switch existed, is a stronger check
    than any in-process comparison: it fixes the numbers rather than the code
    that makes them.
    """
    if not A30_RECORD.exists():
        return {"record": A30_RECORD.name, "state": "missing", "rows": 0,
                "fields_compared": 0, "differ": []}
    doc = json.loads(A30_RECORD.read_text(encoding="utf-8"))
    rows = [x for x in doc.get("sections", {}).get("run", {}).get("rows", [])
            if x["seed"] in seeds and x["need"] in needs]
    differ = []
    fields = ("below_close", "books_close", "removed", "flow_at_shock_round",
              "flow_tail", "circulating_tail", "parked_tail", "issued_total")
    for x in rows:
        cfg = _A30.cell_config({k: x[k] for k in ("need", "stress",
                                                  "elasticity", "authority",
                                                  "seed")})
        net, seen = drive(cfg, x["shock"], x["size"])
        h = net._history
        flow = np.asarray(h.total_volume, dtype=float)
        circ = np.asarray(h.holdings, dtype=float).sum(axis=1)
        got = {
            "below_close": int(net._below.sum()),
            "books_close": seen["books"],
            "removed": _num(seen["removed"]),
            "flow_at_shock_round": _num(flow[SHOCK_ROUND]),
            "flow_tail": _num(flow[-TAIL:].mean()),
            "circulating_tail": _num(circ[-TAIL:].mean()),
            "parked_tail": _num(np.asarray(h.parked, dtype=float)[-TAIL:].mean()),
            "issued_total": _num(np.asarray(h.issuance, dtype=float).sum()),
        }
        bad = [k for k in fields if k in x and _fmt(got[k]) != x[k]]
        if bad:
            differ.append({"cell": {k: x[k] for k in ("need", "stress",
                                                      "elasticity",
                                                      "authority", "shock",
                                                      "size", "seed")},
                           "fields": bad})
    return {"record": A30_RECORD.name, "state": "read", "rows": len(rows),
            "fields_compared": len(fields), "differ": differ}


def gate(configs: list, row_needs=NEEDS, row_seeds=(SEEDS[0],)) -> dict:
    old = load_pre_module()
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    differ, driver_differ, labels = [], [], []
    for label, cfg in configs:
        if cfg.withdraw.active:
            raise RuntimeError("a gate configuration has the switch on: %s"
                               % label)
        t0 = time.perf_counter()
        ref = old.Network(_A29.transplant(cfg, old))
        h_old = ref.run()
        net = Network(cfg)
        h_new = net.run()
        bad = [n for n in names if hasattr(h_old, n)
               and not _same(getattr(h_old, n), getattr(h_new, n))]
        bad += [n for n in CLOSING if not _same(getattr(ref, n),
                                                getattr(net, n))]
        if _rng_digest(ref) != _rng_digest(net):
            bad.append("generators")
        extra = [k for k in WITHDRAW_FIELDS if getattr(h_new, k) is not None]
        if extra:
            bad.append("new fields set: %s" % extra)
        drv, seen = drive(cfg, "none", 0.0)
        dbad = [n for n in names
                if not _same(getattr(h_new, n), getattr(drv._history, n))]
        dbad += [n for n in CLOSING if not _same(getattr(net, n),
                                                 getattr(drv, n))]
        if not seen["books"]:
            dbad.append("claim total against held plus parked")
        labels.append(label)
        if bad:
            differ.append({"config": label, "fields": bad})
        if dbad:
            driver_differ.append({"config": label, "fields": dbad})
        print("   %-44s %s, driver %s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "identical" if not dbad else "DIFFERS in %s" % dbad,
            time.perf_counter() - t0))
    t0 = time.perf_counter()
    rows = a30_rows(needs=row_needs, seeds=row_seeds)
    print("\n   %s: %d rows recomputed, %d fields each, %d differ  (%.0f s)"
          % (rows["record"], rows["rows"], rows["fields_compared"],
             len(rows["differ"]), time.perf_counter() - t0))
    for d in rows["differ"][:5]:
        print("     %s" % d)
    verdict = ("pass" if not differ and not driver_differ
               and rows["state"] == "read" and not rows["differ"]
               and rows["rows"] > 0 else "fail")
    return {
        "module_sha": _module_sha(MODULE),
        "pre_module_sha": _module_sha(PRE_MODULE),
        "script_sha": _module_sha(SCRIPT),
        "configs": labels,
        "fields_compared": len(names) + len(CLOSING) + 1,
        "differ": differ,
        "driver_differ": driver_differ,
        "a30_rows": rows,
        "verdict": verdict,
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
                       "driver lives in it: run --gate again")
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and this script"


# ---------------------------------------------------------------------------
# Timing (D38): measured, printed, never written.
# ---------------------------------------------------------------------------

def time_cells(repeats: int = 3, workers: int = 1) -> None:
    probes = [
        {"need": 0.20, "stress": "leak_recycled", "elasticity": 0.5,
         "position": "none", "gain": None, "shock": "none", "size": 0.0,
         "seed": SEEDS[0]},
        {"need": 0.20, "stress": "leak_recycled", "elasticity": 0.5,
         "position": "production", "gain": 1.0, "shock": "freeze", "size": 0.3,
         "seed": SEEDS[0]},
        {"need": 0.20, "stress": "leak", "elasticity": 0.0,
         "position": "financial", "gain": 0.5, "shock": "release", "size": 0.3,
         "seed": SEEDS[0]},
    ]
    one_cell(probes[0])  # warm-up, not timed
    per = []
    for k in probes:
        ts = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            one_cell(k)
            ts.append(time.perf_counter() - t0)
        per.append(float(np.mean(ts)))
        print("   %-14s %-18s %-12s %.3f s per cell (mean of %d)"
              % (k["stress"], rule_label(k["position"], k["gain"]),
                 _shock_label(k["shock"], k["size"]), per[-1], repeats))
    mean = float(np.mean(per))
    eff = max(1, min(workers, os.cpu_count() or 1))
    for n in (3, len(SEEDS)):
        cells = len(cell_keys(seeds=SEEDS[:n]))
        print("   %d seeds: %d cells, %.0f s serial, about %.0f s on %d workers"
              % (n, cells, cells * mean, cells * mean / eff, eff))
    n_gate = len(gate_configs())
    print("   --gate: %d configurations, three runs each, plus %d of A30's "
          "rows, serial, about %.0f s"
          % (n_gate, len(NEEDS) * len(STRESSES) * len(ELASTICITIES) * 2 * 6,
             (3 * n_gate + len(NEEDS) * len(STRESSES) * len(ELASTICITIES) * 2 * 6) * mean))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe = cell_config({"need": NEEDS[0], "stress": "healthy",
                         "elasticity": ELASTICITIES[0], "position": "none",
                         "gain": None, "shock": "none", "size": 0.0,
                         "seed": SEEDS[0]})
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
                   "rescue, the shock at round %d" % SHOCK_ROUND,
        "rounds": ROUNDS,
        "authority": AUTHORITY,
        "rule": ("the endogenous rule issues the Layer 2 inflow's shortfall "
                 "below its round 0 level; the switch adds the other side, "
                 "taking back gain times the overshoot from the position "
                 "named, pro rata to what each account holds, capped at each "
                 "account and never carried"),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticities": list(ELASTICITIES),
                 "rules": [list(x) for x in RULES],
                 "shocks": [list(x) for x in SHOCKS],
                 "shocks_on_%s_as_well" % RELEASE_STRESS: [list(x) for x in RELEASES],
                 "seeds": list(SEEDS)},
        "park_target": _A30.TARGET,
        "tail": TAIL,
        "window": WINDOW,
        "block": BLOCK,
        "horizons_after_shock": list(HORIZON_K),
        "ring_windows": [list(w) for w in RING_WINDOWS],
        "floor_multiple": FLOOR_MULTIPLE,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one step's payload into the station record. No wall-clock content:
    git records when a file was committed."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A31"
    # Closed 2026-09-12. The switch has three dimensions, position, base and
    # mix, each was swept once, and the three sweeps agree: only whether the
    # setpoint holds decides who falls below the floor. Nothing is registered.
    doc.pop("diagnostic_only", None)
    doc.pop("diagnostic_reason", None)
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def analyse(rows: list, gate_section) -> tuple:
    twins, bands = twins_and_bands(rows)
    cells = read_cells(rows, twins, bands)
    grp = groups(cells)
    rp = rule_pairs(cells)
    ring = ringing(cells)
    crits = [criterion_a31_0(gate_section, cells), criterion_a31_1(cells),
             criterion_a31_2(cells, rp), criterion_a31_3(rp),
             criterion_a31_4(grp), criterion_a31_5(grp),
             criterion_a31_6(ring), criterion_a31_7(grp)]
    written = [{k: v for k, v in c.items() if not k.startswith("_")}
               for c in cells]
    sections = {"criteria": [c.as_dict() for c in crits], "rule_pairs": rp,
                "ringing": ring, "groups": grp, "rows": written}
    return crits, sections, grp, rp, cells


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
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
            print("  %-22s %s" % (k, v))
        print("  %-22s %d at %d seeds" % (
            "cells", len(cell_keys(seeds=SEEDS[:args.seeds])), args.seeds))
        return 0

    if args.gate:
        print("stage A31, rule 19: the module before the switch, the driver, "
              "and A30's record\n")
        g = gate(gate_configs())
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A31, D38: seconds per cell, measured on this machine\n")
        time_cells(workers=args.workers)
        return 0

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A31, smoke: %d cells, gated in-process on its own "
              "configurations, nothing written\n" % len(keys))
        gate_section = gate(
            gate_configs(needs=SMOKE["needs"],
                         elasticities=SMOKE["elasticities"], full=False),
            row_needs=SMOKE["needs"], row_seeds=SMOKE["seeds"][:1])
        print()
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A31: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        if len(seeds) < 2:
            print("stage A31: not starting. The floor is a dispersion across "
                  "seeds, and a dispersion needs two.")
            return 2
        keys = cell_keys(seeds=seeds)
        print("stage A31: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(seeds), args.workers, why))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections, grp, rp, cells = analyse(rows, gate_section)
    print_rule_pairs(rp)
    print_shock_tables(grp)
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
