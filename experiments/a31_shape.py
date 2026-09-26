"""A31, second round: the same pinned aggregate, taken in three shapes.

The first round moved the *position* the claims come out of and read no
difference at all: the three positions left the same integer below the floor in
300 seed comparisons. The reason is that all three take pro rata to what a node
holds while spending is pro rata to what a node holds as well, so trading puts
the distribution back within a few rounds. Measured: the per-node take share
between two positions differs by at most 1.26e-04, mean 6e-06.

This round moves the *shape* instead. ``WithdrawSpec.base`` splits the same
amount inside the same position three ways: pro rata to holdings, the same
amount from every node inside the position that holds something, and in
proportion to the part above the mean. Measured on this carrier before the
switch was written, the per-node take share between two bases differs by 0.0194
to 0.0996 at the maximum and 0.0011 to 0.0066 on average, two to three orders
of magnitude above the contrast that produced nothing.

Three things this reading has to keep apart, and each has a criterion.

**The aggregate.** A shape that cannot collect what the rule asks for changes
the aggregate, and the aggregate is what the first round already read. So every
group that reads a difference is checked against the collected totals, and the
line has a source rather than a convention: the first round's three positions
collected 17.4378, 17.5452 and 17.7710 on one cell, a spread of 1.91%, and that
spread never changed a block state in 300 comparisons. A spread at or under it
is measured not to decide; a spread above it is not adjudicated here.

**Feedback.** In a run this round's take changes next round's inflow, which
changes what the rule asks for next. A31-10 takes that out: identical history to
round 149, the base swapped at the yield, one round of difference in front, and
the same requested amount in all three.

**The denominator.** Dividing the equal share by every live node collects 0.167
to 0.614 of what is asked on this carrier, because most accounts are empty (one
cell has 50 positive accounts among 200 live nodes and a median account of
zero). The switch divides by the nodes inside the position that hold something,
and that is in its docstring with the numbers. The other denominator is a
different rule whose reading is about the aggregate, and the aggregate has been
read.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a31_shape.py --plan
    python experiments/a31_shape.py --gate
    python experiments/a31_shape.py --time
    python experiments/a31_shape.py --run --smoke
    python experiments/a31_shape.py --run --workers 8
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.machinery
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SRC = ROOT / "src" / "monetary_topology"
RESULTS = ROOT / "results"

import monetary_topology.network as _NET  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network, NetworkConfig, NetworkHistory, WithdrawSpec, WITHDRAW_BASES,
    WITHDRAW_FIELDS)

RECORD = RESULTS / "a31_shape.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
#: The module as it stood before ``base`` existed, which is the first round's.
PRE_MODULE = SRC / "network.py.expired_20260912_pre_A31B"
#: The first round's record. Numbers on disk, produced before this switch
#: existed, are a stronger check than any in-process comparison.
A31_RECORD = RESULTS / "a31_withdrawal.json"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A29 = _load(ROOT / "experiments" / "a29_sovereign.py", "_a29_for_shape")
_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_shape")
_A31 = _load(ROOT / "experiments" / "a31_withdrawal.py", "_a31_for_shape")

_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_same = _A30._same
_tally = _A30._tally
_num = _A30._num
_median = _A30._median
_range = _A30._range
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
flip = _A30.flip

AUTHORITY = _A31.AUTHORITY
POSITIONS = _A31.POSITIONS
SHOCKS = _A31.SHOCKS
RELEASES = _A31.RELEASES
SHOCK_KINDS = _A31.SHOCK_KINDS
RELEASE_STRESS = _A31.RELEASE_STRESS
RING_WINDOWS = _A31.RING_WINDOWS
block_class = _A31.block_class
BLOCK_CLASSES = _A31.BLOCK_CLASSES
drive = _A31.drive

#: Fixed. The first round read the gain as a speed knob and not a knob on the
#: block state, so a second level of it buys nothing here.
GAIN = 1.0
#: How the amount is split inside the position. ``holdings`` is the first
#: round's rule and the module default.
BASES: tuple[str, ...] = WITHDRAW_BASES
#: ``("none", "holdings")`` is the one-sided rule, the reference every other
#: row is read against; its base is inert and named only to key the tables.
RULES: tuple[tuple[str, str], ...] = (("none", "holdings"),) + tuple(
    (p, b) for p in POSITIONS for b in BASES)
#: The relative spread of collected totals at or under which a difference in
#: block state is read as shape rather than as aggregate. Source: the first
#: round's three positions on one cell collected 17.4378, 17.5452 and 17.7710,
#: a spread of 1.91%, and that spread changed no block state in 300 seed
#: comparisons. It is a measured "does not decide", not a convention.
SPREAD_LINE = 0.0191
#: A31-10 reads one application per strain, at the bistable floor where the
#: block sits on its edge.
PROBE_CARRIERS: tuple[dict, ...] = tuple(
    {"need": 0.20, "stress": s, "elasticity": 0.5, "seed": SEEDS[1]}
    for s in STRESSES)
#: The reduced grid ``--smoke`` runs.
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}

KEYS: tuple[str, ...] = ("need", "stress", "elasticity", "position", "base",
                         "gain", "shock", "size", "seed")
#: The recomputed fields the gate compares against the first round's record.
#: Every one is read off the cell's own arrays, so none of them depends on how
#: many seeds this run happens to carry.
ROW_FIELDS: tuple[str, ...] = (
    "below_close", "books_close", "removed", "released", "returned_exact",
    "flow_at_shock_round", "flow_tail", "circulating_tail", "parked_tail",
    "issued_total", "withdrawn_total", "withdrawn_unmet_total",
    "withdrawn_l2_share", "rounds_withdrawing", "l2_over_target_before_shock",
    "l2_over_target_tail", "target_gap_sign_changes")


# ---------------------------------------------------------------------------
# The first round's readers are reused, and they key a cell by its rule. Here a
# rule is a position and a base, so that key is replaced in the loaded copy.
# The patch lives in this module's copy of it and not in the file.
# ---------------------------------------------------------------------------

def _carrier(x: dict) -> tuple:
    return (x["need"], x["stress"], x["elasticity"])


def _rule(x: dict) -> tuple:
    if x["position"] == "none":
        return ("none", None)
    return ("%s/%s" % (x["position"], x["base"]), x["gain"])


_A31._rule = _rule


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            POSITIONS.index(x["position"]) if x["position"] != "none" else -1,
            BASES.index(x["base"]), -(x["gain"] or 0.0),
            SHOCK_KINDS.index(x["shock"]), x["size"], x["seed"])


def _ref_key(x: dict) -> tuple:
    return tuple(x[k] for k in KEYS if k != "base")


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
                for position, base in rules:
                    for kind, size in shocks_for(stress):
                        for seed in seeds:
                            keys.append({
                                "need": need, "stress": stress,
                                "elasticity": e, "position": position,
                                "base": base,
                                "gain": None if position == "none" else GAIN,
                                "shock": kind, "size": size, "seed": seed})
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
        cfg, withdraw=WithdrawSpec(position=key["position"],
                                   gain=key["gain"], base=key["base"]))


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net, seen = drive(cfg, key["shock"], key["size"])
    h = net._history
    zeros = np.zeros(ROUNDS)
    row = dict(key)
    row.update({
        "removed": _num(seen["removed"]),
        "released": _num(seen["released"]),
        "books_close": seen["books"],
        "returned_exact": seen["returned"],
        "below_close": int(net._below.sum()),
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


def run_cells(keys: list, workers: int) -> list:
    if workers <= 1:
        rows = [one_cell(k) for k in keys]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one_cell, keys, chunksize=8))
    return sorted(rows, key=_row_key)


# ---------------------------------------------------------------------------
# One application, no feedback (A31-10).
# ---------------------------------------------------------------------------

def take_vector(cash, alive, l1, l2, position, base, amount):
    """The three splits written out, so the probe can print the object.

    This is a second copy of what the module does, and a second copy is worth
    nothing unless it is checked: every probe cell compares its total against
    what the module itself collected in that round, and the check is reported.
    """
    holdings = np.maximum(cash, 0.0) * alive
    inside = alive.copy()
    if position in ("financial", "production"):
        keep = np.zeros(holdings.size, dtype=bool)
        keep[l1 if position == "financial" else l2] = True
        inside &= keep
    pool = np.where(inside, holdings, 0.0)
    total = float(pool.sum())
    if total <= 0.0:
        return np.zeros_like(pool), inside
    if base == "equal":
        payers = pool > 0.0
        take = np.where(payers, np.minimum(amount / int(payers.sum()), pool),
                        0.0)
    elif base == "threshold":
        mean = total / int(inside.sum())
        excess = np.where(inside, np.maximum(pool - mean, 0.0), 0.0)
        span = float(excess.sum())
        if span <= 0.0:
            return np.zeros_like(pool), inside
        take = excess * min(1.0, amount / span)
    else:
        take = np.minimum(amount * (pool / total), pool)
    return take, inside


def arm_round(cfg: NetworkConfig, prefer_from: int) -> int | None:
    """Scout one run for the round the probe arms on.

    The rule asks for nothing in the rounds where the Layer 2 inflow sits at or
    under its target, and on this carrier about half the rounds are like that.
    Worse, a strain whose graph has already collapsed can be short of its target
    for the whole tail, so from a fixed round on it never asks for anything: the
    first version of this probe read three applications of zero and called the
    three equal counts a result.

    So the round is scouted rather than fixed. Preferred: the first round from
    ``prefer_from`` on that the rule asks anything for. Failing that, the last
    round before it that does, so a carrier whose withdrawals all happen early
    is still read somewhere. ``None`` if the rule never asks for anything at
    all, and then there is nothing to apply and the probe says so.
    """
    net = Network(cfg)
    last = None
    for t in net._run_steps():
        if net._pending_withdrawal > 0.0:
            if t >= prefer_from:
                return t
            last = t
    return last


def one_application(carrier: dict, position: str) -> dict:
    """Identical history up to the armed round, the base swapped there, one
    round of difference in front, the same requested amount in all three.

    Nothing is deep-copied: the three runs share a configuration and a seed, so
    they are the same run bit for bit until the swap, and the round is scouted
    beforehand so all three arm on the same one by construction.
    """
    out = {"carrier": dict(carrier), "position": position, "bases": {}}
    key = dict(carrier, position=position, base="holdings", gain=GAIN,
               shock="none", size=0.0)
    cfg = cell_config(key)
    arm = arm_round(cfg, SHOCK_ROUND - 1)
    out["armed_at_round"] = arm
    out["armed_from_preferred_round"] = (arm is not None
                                         and arm >= SHOCK_ROUND - 1)
    if arm is None:
        out["state"] = "nothing to apply: the rule never asks for anything here"
        out["snapshot"] = None
        return out
    snap, asked, takes = None, 0.0, {}
    for base in BASES:
        swap = dataclasses.replace(
            cfg, withdraw=WithdrawSpec(position=position, gain=GAIN,
                                       base=base))
        net = Network(cfg)
        at_round = None
        for t in net._run_steps():
            if t == arm:
                at_round = t + 1
                asked = float(net._pending_withdrawal)
                if snap is None:
                    live = np.maximum(net.holdings, 0.0)[net._alive]
                    snap = {
                        "cash": np.maximum(net.holdings, 0.0).copy(),
                        "alive": net._alive.copy(),
                        "l1": net._l1, "l2": net._l2,
                        "live_nodes": int(net._alive.sum()),
                        "positive_accounts": int((live > 0.0).sum()),
                        "median_account": _num(float(np.median(live))),
                        "mean_account": _num(float(live.mean())),
                        "circulating": _num(float(live.sum())),
                        "below": int(net._below.sum()),
                        "round": t,
                    }
                if base != "holdings":
                    net.config = swap
            elif t == arm + 1:
                break
        # The run is stopped at the yield, so the history has not been
        # assembled yet; the round's own figures are still on the network,
        # where the loop reads them from to record them.
        got = float(net._withdrawn_this_round)
        unmet = float(net._withdrawn_unmet_this_round)
        take, inside = take_vector(snap["cash"], snap["alive"], snap["l1"],
                                   snap["l2"], position, base, asked)
        takes[base] = take
        out["bases"][base] = {
            "asked": _num(asked),
            "applied_at_round": at_round,
            "collected": _num(got),
            "collected_over_asked": _num(got / asked) if asked > 0 else None,
            "uncollected": _num(unmet),
            "below_close": int(net._below.sum()),
            "payers": int((take > 0.0).sum()),
            "nodes_inside": int(inside.sum()),
            "copy_matches_module": bool(
                abs(float(take.sum()) - got) <= 1e-12 * max(1.0, abs(got))),
        }
    ref = takes["holdings"]
    for base in BASES:
        v, e = takes[base], out["bases"][base]
        if float(v.sum()) > 0.0 and float(ref.sum()) > 0.0:
            d = v / v.sum() - ref / ref.sum()
            e["take_share_max_difference"] = _num(float(np.abs(d).max()))
            e["take_share_mean_difference"] = _num(float(np.abs(d).mean()))
        else:
            e["take_share_max_difference"] = None
            e["take_share_mean_difference"] = None
    states = {e["below_close"] for e in out["bases"].values()}
    rounds = {e["applied_at_round"] for e in out["bases"].values()}
    asks = {e["asked"] for e in out["bases"].values()}
    out["same_round_and_amount"] = len(rounds) == 1 and len(asks) == 1
    out["state"] = (
        "not comparable" if not out["same_round_and_amount"] else
        "nothing asked for" if asked <= 0.0 else
        "one application does not decide" if len(states) == 1 else
        "one application decides")
    out["snapshot"] = {k: v for k, v in snap.items()
                       if k not in ("cash", "alive", "l1", "l2")}
    return out


def probe(carriers=PROBE_CARRIERS, positions=POSITIONS) -> list:
    return [one_application(c, p) for c in carriers for p in positions]


# ---------------------------------------------------------------------------
# The bases against each other, at a fixed carrier and position.
# ---------------------------------------------------------------------------

SEED_STATES: tuple[tuple[str, str], ...] = (
    ("same integer on every seed", "at a fixed carrier, position and seed the "
     "three bases leave the same count below the floor"),
    ("differs at matched totals: shape decides", "they do not, and the spread "
     "of what they collected is at or under %.4f" % SPREAD_LINE),
    ("differs, and so do the totals: not adjudicated", "they do not, and the "
     "collected totals differ by more than %.4f, so the aggregate channel is "
     "open and this group is read neither way" % SPREAD_LINE))

SHAPE_STATES: tuple[tuple[str, str], ...] = (
    ("shape decides", "the three bases do not all leave the same block "
     "state, and the spread of what they collected is at or under %.4f"
     % SPREAD_LINE),
    ("the aggregate decides", "all three leave the same block state, so on "
     "this carrier and position the shape does not settle it"),
    ("confounded, not adjudicated", "the block states differ and so do the "
     "collected totals, by more than %.4f: the aggregate channel is open and "
     "this group is not read either way" % SPREAD_LINE),
    ("split, no reading", "one base's seeds disagree with each other"))


def base_pairs(cells: list) -> list:
    """A31-11 and A31-12: at a fixed carrier and position, the three bases
    against each other, each read against the one-sided twin on the same seed.
    """
    twins = {}
    for c in cells:
        if c["shock"] == "none":
            twins.setdefault(_carrier(c) + (c["seed"],), {})[
                (c["position"], c["base"])] = c
    by = {}
    for key, rules in twins.items():
        ref = rules.get(("none", "holdings"))
        if ref is None:
            continue
        for (position, base), c in rules.items():
            if position == "none":
                continue
            e = by.setdefault(key[:3] + (position,), {}).setdefault(
                base, {"seeds": [], "below_diff": [], "class": [],
                       "circulating_ratio": [], "withdrawn": [],
                       "uncollected_share": [], "l2_over_target_tail": [],
                       "withdrawn_l2_share": [], "issued": []})
            diff = int(c["below_close"] - ref["below_close"])
            asked = ((c["withdrawn_total"] or 0.0)
                     + (c["withdrawn_unmet_total"] or 0.0))
            e["seeds"].append(key[3])
            e["below_diff"].append(diff)
            e["class"].append(block_class(diff))
            e["circulating_ratio"].append(
                _num(c["circulating_tail"] / ref["circulating_tail"])
                if ref["circulating_tail"] else None)
            e["withdrawn"].append(c["withdrawn_total"])
            e["uncollected_share"].append(
                _num((c["withdrawn_unmet_total"] or 0.0) / asked)
                if asked > 0 else None)
            e["l2_over_target_tail"].append(c["l2_over_target_tail"])
            e["withdrawn_l2_share"].append(c["withdrawn_l2_share"])
            e["issued"].append(c["issued_total"])
    out = []
    for key in sorted(by, key=lambda k: (k[0], STRESSES.index(k[1]), k[2],
                                         POSITIONS.index(k[3]))):
        shapes = {}
        for base in BASES:
            e = by[key].get(base)
            if e is None:
                continue
            classes = set(e["class"])
            shapes[base] = {
                "seeds": e["seeds"], "below_diff": e["below_diff"],
                "class": e["class"],
                "state": e["class"][0] if len(classes) == 1 else "split",
                "circulating_ratio_median": _median(e["circulating_ratio"]),
                "withdrawn_median": _median(e["withdrawn"]),
                "uncollected_share_median": _median(e["uncollected_share"]),
                "l2_over_target_tail_median": _median(e["l2_over_target_tail"]),
                "withdrawn_l2_share_median": _median(e["withdrawn_l2_share"]),
                "issued_median": _median(e["issued"]),
            }
        seeds_all = sorted({sd for sh in shapes.values() for sd in sh["seeds"]})
        per_seed = []
        for sd in seeds_all:
            vals = {b: sh["below_diff"][sh["seeds"].index(sd)]
                    for b, sh in shapes.items() if sd in sh["seeds"]}
            per_seed.append({
                "seed": sd, "below_diff": vals,
                "same": len(vals) == len(shapes)
                        and len(set(vals.values())) == 1})
        differing = [x for x in per_seed if not x["same"]]
        states = {s["state"] for s in shapes.values()}
        taken = [s["withdrawn_median"] for s in shapes.values()
                 if s["withdrawn_median"]]
        spread = ((max(taken) - min(taken)) / min(taken)
                  if len(taken) == len(shapes) and taken and min(taken) > 0
                  else None)
        if not per_seed:
            seed_reading = "no seeds"
        elif not differing:
            seed_reading = "same integer on every seed"
        elif spread is None or spread > SPREAD_LINE:
            seed_reading = "differs, and so do the totals: not adjudicated"
        else:
            seed_reading = "differs at matched totals: shape decides"
        if "split" in states:
            reading = "split, no reading"
        elif len(states) == 1:
            reading = "the aggregate decides"
        elif spread is None or spread > SPREAD_LINE:
            reading = "confounded, not adjudicated"
        else:
            reading = "shape decides"
        refs = [c for c in cells if c["shock"] == "none"
                and _carrier(c) == key[:3] and c["position"] == "none"]
        out.append({
            "need": key[0], "stress": key[1], "elasticity": key[2],
            "position": key[3],
            "collected_spread": _num(spread),
            "one_sided": {
                "below_close": [c["below_close"] for c in refs],
                "l2_over_target_tail_median": _median(
                    [c["l2_over_target_tail"] for c in refs]),
                "circulating_tail_median": _median(
                    [c["circulating_tail"] for c in refs]),
            },
            "shapes": shapes,
            "reading": reading,
            "per_seed": per_seed,
            "seeds_compared": len(per_seed),
            "seeds_differing": len(differing),
            "seed_reading": seed_reading,
        })
    return out


def _two_sided(cells: list) -> list:
    return [c for c in cells if c["position"] != "none"]


# ---------------------------------------------------------------------------
# Criteria. Every state below is printed beside the numbers it came from, and a
# state that is not a reading says so.
# ---------------------------------------------------------------------------

def criterion_a31_8(g, cells: list) -> Criterion:
    name = ("A31-8 the default base reproduces the first round, bit for bit")
    state_map = (
        "State map: the module before this field identical to the module now "
        "on both the switch-off and the two-sided configurations, the driver "
        "identical to Network.run(), and the first round's recorded rows "
        "reproduced -> PASS; anything else -> FAIL; no gate section -> not "
        "judged, and --run does not start.")
    if not g:
        return Criterion(name, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + state_map, evaluated=False)
    rows = g.get("a31_rows", {})
    detail = (
        "The module before ``base`` existed and the module now ran %d "
        "configurations in one process: the first round's own off-switch set "
        "(the library default, A18's exit arm with and without write-off, "
        "A18_E twice, A23, A18_F, A29's control and treated cells, every base "
        "cell of A30's grid) and its two-sided cells with the base at its "
        "default. %d history fields and the closing state compared bit for "
        "bit, %d differ; the generators end in the same place. The driver "
        "with no shock against Network.run(): %d differ. The first round's "
        "recorded rows recomputed on this module: %d rows, %d fields each, %d "
        "differ.%s %s"
        % (len(g["configs"]), g["fields_compared"], len(g["differ"]),
           len(g["driver_differ"]), rows.get("rows", 0),
           rows.get("fields_compared", 0), len(rows.get("differ", [])),
           "" if not g["differ"] else " First: %s" % g["differ"][:3],
           state_map))
    return Criterion(name, "instrument", g["verdict"] == "pass", detail)


def criterion_a31_9(cells: list, pr: list) -> Criterion:
    two = _two_sided(cells)
    books = sum(1 for c in cells if c["books_close"])
    spill = []
    for c in two:
        share = c["withdrawn_l2_share"]
        if share is None:
            continue
        if c["position"] == "financial" and share != 0.0:
            spill.append((c["position"], c["base"], share))
        if c["position"] == "production" and share != 1.0:
            spill.append((c["position"], c["base"], share))
    copies = [(e["carrier"], e["position"], b)
              for e in pr for b, x in e["bases"].items()
              if not x["copy_matches_module"]]
    asked = [(c["withdrawn_total"] or 0.0) + (c["withdrawn_unmet_total"] or 0.0)
             for c in two]
    unmet = [((c["withdrawn_unmet_total"] or 0.0) / a) if a > 0 else 0.0
             for c, a in zip(two, asked)]
    by_base = {b: [u for c, u in zip(two, unmet) if c["base"] == b]
               for b in BASES}
    ok = books == len(cells) and not spill and not copies and bool(two)
    return Criterion(
        "A31-9 the withdrawal's books close, and nothing is taken outside the "
        "position", "instrument", ok,
        "Asserted every round in the loop: what leaves held plus parked equals "
        "what was taken, no account goes below zero, and what the cap leaves "
        "uncollected is recorded and not carried. Read back here: %d of %d "
        "cells close their claim total against held plus parked to %.0e of the "
        "opening stock. The Layer 2 share of what was taken is 0 under every "
        "financial cell and 1 under every production cell: %d cells out of "
        "place%s. The probe's own copy of the three splits matches what the "
        "module collected in that round to 1e-12: %d probe cells out of "
        "place. Uncollected over asked, median by base: %s. State map: every "
        "cell closing, nothing outside the position and the copy matching -> "
        "PASS; anything else -> FAIL, and nothing after this reads."
        % (books, len(cells), LEDGER_TOL, len(spill),
           "" if not spill else " %s" % spill[:5], len(copies),
           ", ".join("%s %s" % (b, _median(v)) for b, v in by_base.items())))


def criterion_a31_10(pr: list) -> Criterion:
    tally = _tally(e["state"] for e in pr)
    early = [(e["carrier"]["stress"], e["position"], e["armed_at_round"])
             for e in pr if e["bases"]
             and not e["armed_from_preferred_round"]]
    pr = [e for e in pr if e["bases"]]
    lines = []
    for e in pr:
        c = e["carrier"]
        lines.append(
            "need %.2f %s e %.1f seed %d, %s @%s: asked %s, below the floor %s, "
            "collected over asked %s, payers %s, take share against holdings "
            "max %s"
            % (c["need"], c["stress"], c["elasticity"], c["seed"],
               e["position"], e["armed_at_round"],
               e["bases"]["holdings"]["asked"],
               "/".join(str(e["bases"][b]["below_close"]) for b in BASES),
               "/".join(str(e["bases"][b]["collected_over_asked"])
                        for b in BASES),
               "/".join(str(e["bases"][b]["payers"]) for b in BASES),
               "/".join(str(e["bases"][b]["take_share_max_difference"])
                        for b in BASES)))
    snaps = "; ".join(
        "%s at round %d: %d live, %d holding something, median account %s, "
        "circulating %s"
        % (e["carrier"]["stress"], e["armed_at_round"],
           e["snapshot"]["live_nodes"], e["snapshot"]["positive_accounts"],
           e["snapshot"]["median_account"], e["snapshot"]["circulating"])
        for e in pr if e["position"] == POSITIONS[0])
    return Criterion(
        "A31-10 one application, with the feedback taken out", "own_reading",
        True,
        "Printed, not judged. Three runs share a configuration and a seed, so "
        "they are the same run bit for bit up to the yield they arm on. That "
        "round is scouted in a run of its own: the first from %d on that the "
        "rule asks anything for, and failing that the last before it that "
        "does, because a strain whose graph drains early is short of its "
        "target for the whole tail and asks for nothing there. The base is "
        "swapped at that yield and each takes one round. The amount asked and "
        "the round it lands in are therefore the same in all three, and that "
        "is checked rather than assumed. Values below read "
        "holdings/equal/threshold. The state at the yield: %s. Cells: %s. "
        "State map: the three bases leaving the same count below the floor -> "
        "one application does not decide; any two differing -> one application "
        "decides; the rule never asking for anything on that carrier -> "
        "nothing to apply, and the group is not read. Counts by state: %s. "
        "Armed before the preferred round because the rule asks for nothing "
        "in the tail there: %s."
        % (SHOCK_ROUND - 1, snaps, " | ".join(lines), tally,
           early if early else "nowhere"))


def criterion_a31_11(bp: list) -> Criterion:
    tally = _tally(e["reading"] for e in bp)
    seed_tally = _tally(e["seed_reading"] for e in bp)
    compared = sum(e["seeds_compared"] for e in bp)
    differing = sum(e["seeds_differing"] for e in bp)
    decided = [e for e in bp
               if e["seed_reading"] == "differs at matched totals: shape "
                                       "decides"]
    lines = []
    for e in decided[:12]:
        lines.append(
            "need %.2f %s e %.1f %s: %s; one-sided below the floor %s"
            % (e["need"], e["stress"], e["elasticity"], e["position"],
               ", ".join("%s %s (below %s, collected %s)"
                         % (b, e["shapes"][b]["state"],
                            e["shapes"][b]["below_diff"],
                            e["shapes"][b]["withdrawn_median"])
                         for b in BASES if b in e["shapes"]),
               e["one_sided"]["below_close"]))
    if len(decided) > 12:
        lines.append("%d more in the base_pairs section" % (len(decided) - 12))
    return Criterion(
        "A31-11 the same aggregate in three shapes: who is below the floor",
        "own_reading", True,
        "Printed, not judged. Each two-sided twin against the one-sided twin "
        "on the same carrier and seed, at the close, at a fixed position. "
        "**The headline is the seed-by-seed comparison**, because this "
        "carrier is bistable across seeds at the floor it was built on: %d "
        "comparisons of three bases at a fixed carrier, position and seed, %d "
        "leaving a different count below the floor. Seed states: %s. Groups "
        "by seed state: %s. Where the shape decides: %s. The first round's "
        "comparison for scale: three positions, 300 seed comparisons, 0 "
        "differing. The block-level reading beside it, which reads split "
        "wherever the carrier itself is bistable: block states %s; states %s; "
        "groups by reading %s."
        % (compared, differing,
           "; ".join("%s = %s" % x for x in SEED_STATES), seed_tally,
           "; ".join(lines) if lines else "nowhere",
           "; ".join("%s = %s" % x for x in BLOCK_CLASSES),
           "; ".join("%s = %s" % x for x in SHAPE_STATES), tally))


def criterion_a31_12(bp: list) -> Criterion:
    differing = [e for e in bp if e["reading"] in ("shape decides",
                                                   "confounded, not "
                                                   "adjudicated")]
    spreads = [e["collected_spread"] for e in differing
               if e["collected_spread"] is not None]
    over = [e for e in differing
            if e["reading"] == "confounded, not adjudicated"]
    all_spreads = [e["collected_spread"] for e in bp
                   if e["collected_spread"] is not None]
    lines = ["need %.2f %s e %.1f %s: spread %s, collected %s"
             % (e["need"], e["stress"], e["elasticity"], e["position"],
                e["collected_spread"],
                "/".join(str(e["shapes"][b]["withdrawn_median"])
                         for b in BASES if b in e["shapes"]))
             for e in over[:10]]
    return Criterion(
        "A31-12 whether a difference is the shape or the aggregate",
        "own_reading", True,
        "Printed, not judged. A base that cannot collect what the rule asks "
        "for changes the aggregate, and the aggregate is what the first round "
        "already read, so every group whose block states differ is checked "
        "against what the three bases collected over 300 rounds. The line is "
        "%.4f and it is measured rather than chosen: the first round's three "
        "positions collected 17.4378, 17.5452 and 17.7710 on one cell, a "
        "spread of 1.91%%, and that spread changed no block state in 300 seed "
        "comparisons. Relative spread of the collected totals over all %d "
        "groups: median %s, %s. Groups whose block states differ: %d, of "
        "which %d sit above the line and are not adjudicated%s. State map: "
        "block states differing and the spread at or under the line -> shape; "
        "above the line -> not adjudicated, and the group is read neither "
        "way; block states all equal -> nothing to separate."
        % (SPREAD_LINE, len(bp), _median(all_spreads), _range(all_spreads),
           len(differing), len(over),
           "" if not lines else ": %s" % "; ".join(lines)))


def criterion_a31_13(bp: list, cells: list) -> Criterion:
    two = [c for c in cells if c["position"] != "none" and c["shock"] == "none"]
    one = [c for c in cells if c["position"] == "none" and c["shock"] == "none"]
    parts = []
    for base in BASES:
        v = [c["l2_over_target_tail"] for c in two if c["base"] == base]
        parts.append("%s median %s, %s" % (base, _median(v), _range(v)))
    ref = [c["l2_over_target_tail"] for c in one]
    return Criterion(
        "A31-13 the aggregate is pinned whichever shape takes it",
        "own_reading", True,
        "Printed, not judged. The Layer 2 inflow over the rule's own target, "
        "averaged over the last %d rounds, on the two-sided twins. One-sided "
        "reference: median %s, %s. Two-sided by base: %s. The first round read "
        "-0.0001 on the same quantity. Reading: all three bases pinning says "
        "the pinning is a property of the aggregate and not of the shape that "
        "takes it; one base failing to pin says that shape cannot collect what "
        "the rule asks for, which A31-12 reads as the aggregate channel."
        % (TAIL, _median(ref), _range(ref), "; ".join(parts)))


def criterion_a31_14(cells: list, bp: list) -> Criterion:
    two = _two_sided(cells)
    parts = []
    for base in BASES:
        xs = [c for c in two if c["base"] == base]
        parts.append(
            "%s: Layer 2 share of what was taken, median %s, %s; rounds "
            "withdrawing, median %s of %d; uncollected over asked, median %s"
            % (base, _median([c["withdrawn_l2_share"] for c in xs]),
               _range([c["withdrawn_l2_share"] for c in xs]),
               _median([c["rounds_withdrawing"] for c in xs]), ROUNDS,
               _median([(((c["withdrawn_unmet_total"] or 0.0)
                          / ((c["withdrawn_total"] or 0.0)
                             + (c["withdrawn_unmet_total"] or 0.0)))
                         if ((c["withdrawn_total"] or 0.0)
                             + (c["withdrawn_unmet_total"] or 0.0)) > 0
                         else 0.0) for c in xs])))
    return Criterion(
        "A31-14 where it came from, and what the cap left", "bookkeeping",
        True, "Printed. %s. Groups: %d, over %d two-sided cells."
        % ("; ".join(parts), len(bp), len(two)))


# ---------------------------------------------------------------------------
# Printing.
# ---------------------------------------------------------------------------

def print_probe(pr: list) -> None:
    print("\n  A31-10, one application. The three runs are the same run to "
          "the yield they arm on, so the amount asked is one number. The round "
          "is scouted: the first from %d on that the rule asks anything for, "
          "and failing that the last before it that does." % (SHOCK_ROUND - 1))
    print("  %-14s %-12s %14s %8s %8s %8s %8s %8s"
          % ("strain", "position", "asked @round", "below", "got/ask",
             "payers", "max dS", "mean dS"))
    for e in pr:
        if not e["bases"]:
            print("  %-14s %-12s %s" % (e["carrier"]["stress"],
                                        e["position"], e["state"]))
            continue
        for base in BASES:
            x = e["bases"][base]
            print("  %-14s %-12s %14s %8s %8s %8s %8s %8s   %s"
                  % (e["carrier"]["stress"] if base == BASES[0] else "",
                     "%s %s" % (e["position"][:4], base),
                     ("%s @%s" % (x["asked"], x["applied_at_round"])
                      if base == BASES[0] else ""),
                     x["below_close"], x["collected_over_asked"],
                     x["payers"], x["take_share_max_difference"],
                     x["take_share_mean_difference"],
                     "" if x["copy_matches_module"] else "COPY MISMATCH"))
        print("  %-14s %s" % ("", e["state"]))


def print_base_pairs(bp: list) -> None:
    print("\n  A31-11 and A31-12, the three bases at a fixed carrier and "
          "position, each against the one-sided twin.")
    print("  %-5s %-14s %-4s %-12s %7s %8s  %s"
          % ("need", "strain", "e", "position", "differ", "spread",
             "seed reading"))
    for e in bp:
        print("  %-5.2f %-14s %-4.1f %-12s %7s %8s  %s"
              % (e["need"], e["stress"], e["elasticity"], e["position"],
                 "%d/%d" % (e["seeds_differing"], e["seeds_compared"]),
                 e["collected_spread"], e["seed_reading"]))


# ---------------------------------------------------------------------------
# Rule 19. The module before this field, and the first round's record.
# ---------------------------------------------------------------------------

CLOSING = _A31.CLOSING


def load_pre_module():
    """Loaded under the package name, because the module uses relative
    imports and a bare name has no parent package to resolve them against."""
    name = "monetary_topology._network_pre_a31b"
    loader = importlib.machinery.SourceFileLoader(name, str(PRE_MODULE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def gate_configs(needs=NEEDS, elasticities=ELASTICITIES, full: bool = True,
                 seed=None) -> list:
    """The first round's off-switch set, plus its own two-sided cells with the
    base at its default. The two-sided half is what this field could break."""
    out = list(_A31.gate_configs(needs=needs, elasticities=elasticities,
                                 full=full))
    need = needs[-1]
    for stress in STRESSES:
        for e in elasticities:
            for position in POSITIONS:
                out.append((
                    "A31 two-sided %s, need %.2f, %s, e %.1f"
                    % (position, need, stress, e),
                    cell_config({"need": need, "stress": stress,
                                 "elasticity": e, "position": position,
                                 "base": "holdings", "gain": GAIN,
                                 "shock": "none", "size": 0.0,
                                 "seed": SEEDS[0] if seed is None else seed})))
    return out


def a31_rows(needs=NEEDS, seeds=(SEEDS[0],), workers: int = 1) -> dict:
    """The first round's recorded rows, recomputed on this module.

    A record on disk, produced before this field existed, is a stronger check
    than any in-process comparison: it fixes the numbers rather than the code
    that makes them. Every field compared is read off the cell's own arrays, so
    none of them depends on how many seeds this call happens to carry.
    """
    if not A31_RECORD.exists():
        return {"record": A31_RECORD.name, "state": "missing", "rows": 0,
                "fields_compared": 0, "differ": []}
    doc = json.loads(A31_RECORD.read_text(encoding="utf-8"))
    ref_rows = [x for x in doc.get("sections", {}).get("run", {}).get("rows", [])
                if x["seed"] in seeds and x["need"] in needs]
    if not ref_rows:
        return {"record": A31_RECORD.name, "state": "no matching rows",
                "rows": 0, "fields_compared": 0, "differ": []}
    keys = [dict({k: x[k] for k in KEYS if k != "base"}, base="holdings")
            for x in ref_rows]
    got = _A31.read_cells(run_cells(keys, workers), {}, {})
    idx = {_ref_key(c): c for c in got}
    differ = []
    for x in ref_rows:
        c = idx.get(_ref_key(x))
        if c is None:
            differ.append({"cell": _ref_key(x), "fields": ["not recomputed"]})
            continue
        bad = [f for f in ROW_FIELDS if f in x and _fmt(c.get(f)) != x[f]]
        if bad:
            differ.append({"cell": _ref_key(x), "fields": bad})
    return {"record": A31_RECORD.name, "state": "read", "rows": len(ref_rows),
            "fields_compared": len(ROW_FIELDS), "differ": differ}


def gate(configs: list, row_needs=NEEDS, row_seeds=(SEEDS[0],),
         workers: int = 1) -> dict:
    old = load_pre_module()
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    differ, driver_differ, labels = [], [], []
    for label, cfg in configs:
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
        if not cfg.withdraw.active:
            extra = [k for k in WITHDRAW_FIELDS if getattr(h_new, k) is not None]
            if extra:
                bad.append("new fields set with the switch off: %s" % extra)
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
        print("   %-52s %s, driver %s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "identical" if not dbad else "DIFFERS in %s" % dbad,
            time.perf_counter() - t0))
    t0 = time.perf_counter()
    rows = a31_rows(needs=row_needs, seeds=row_seeds, workers=workers)
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
        "a31_rows": rows,
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
                       "grid lives in it: run --gate again")
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and this script"


# ---------------------------------------------------------------------------
# Timing (D38): measured, printed, never written.
# ---------------------------------------------------------------------------

def time_cells(repeats: int = 3, workers: int = 1) -> None:
    sample = []
    for stress in STRESSES:
        for base in BASES:
            sample.append({"need": 0.20, "stress": stress, "elasticity": 0.5,
                           "position": "production", "base": base,
                           "gain": GAIN, "shock": "none", "size": 0.0,
                           "seed": SEEDS[0]})
    best = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        for k in sample:
            one_cell(k)
        dt = (time.perf_counter() - t0) / len(sample)
        best = dt if best is None else min(best, dt)
    n = len(cell_keys())
    print("   %.3f s per cell, %d cells: %.0f s serial, %.0f s on %d workers"
          % (best, n, best * n, best * n / max(workers, 1), max(workers, 1)))
    print("   the probe adds %d runs of %d rounds, about %.0f s"
          % (len(PROBE_CARRIERS) * len(POSITIONS) * len(BASES), SHOCK_ROUND + 1,
             best * len(PROBE_CARRIERS) * len(POSITIONS) * len(BASES)
             * (SHOCK_ROUND + 1) / ROUNDS))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe_cfg = cell_config({"need": NEEDS[0], "stress": "healthy",
                             "elasticity": ELASTICITIES[0],
                             "position": "none", "base": "holdings",
                             "gain": None, "shock": "none", "size": 0.0,
                             "seed": SEEDS[0]})
    cfg = _config_diff(probe_cfg)
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
                   "rescue, the shock at round %d. The first round's carrier "
                   "and driver unchanged; only the split changes."
                   % SHOCK_ROUND,
        "rounds": ROUNDS,
        "authority": AUTHORITY,
        "rule": ("the endogenous rule issues the Layer 2 inflow's shortfall "
                 "below its round 0 level; the switch adds the other side, "
                 "taking back gain times the overshoot from the position "
                 "named. ``position`` names the set it comes out of and "
                 "``base`` the shape it is split in: pro rata to holdings, "
                 "the same amount from every node inside the position holding "
                 "something, or in proportion to the part above the mean. "
                 "Each is capped at the account, nothing spills outside the "
                 "position, and what the cap leaves uncollected is recorded "
                 "and not carried"),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticities": list(ELASTICITIES),
                 "rules": [list(x) for x in RULES],
                 "gain": GAIN,
                 "shocks": [list(x) for x in SHOCKS],
                 "shocks_on_%s_as_well" % RELEASE_STRESS: [list(x)
                                                           for x in RELEASES],
                 "seeds": list(SEEDS)},
        "park_target": _A30.TARGET,
        "tail": TAIL,
        "window": WINDOW,
        "block": BLOCK,
        "horizons_after_shock": list(HORIZON_K),
        "ring_windows": [list(w) for w in RING_WINDOWS],
        "floor_multiple": FLOOR_MULTIPLE,
        "ledger_tolerance": LEDGER_TOL,
        "collected_spread_line": SPREAD_LINE,
        "probe_carriers": [dict(c) for c in PROBE_CARRIERS],
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one step's payload into the station record. No wall-clock content:
    git records when a file was committed."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A31B"
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


def analyse(rows: list, gate_section, pr: list) -> tuple:
    twins, bands = _A31.twins_and_bands(rows)
    cells = _A31.read_cells(rows, twins, bands)
    bp = base_pairs(cells)
    crits = [criterion_a31_8(gate_section, cells),
             criterion_a31_9(cells, pr),
             criterion_a31_10(pr),
             criterion_a31_11(bp),
             criterion_a31_12(bp),
             criterion_a31_13(bp, cells),
             criterion_a31_14(cells, bp)]
    written = [{k: v for k, v in c.items() if not k.startswith("_")}
               for c in cells]
    sections = {"criteria": [c.as_dict() for c in crits],
                "base_pairs": bp, "one_application": pr, "rows": written}
    return crits, sections, bp, cells


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
                    help="with --run: the reduced grid, gated in-process on "
                         "its own configurations, nothing written")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-24s %s" % (k, v))
        print("  %-24s %d at %d seeds"
              % ("cells", len(cell_keys(seeds=SEEDS[:args.seeds])), args.seeds))
        return 0

    if args.gate:
        print("stage A31, second round, rule 19: the module before ``base``, "
              "the driver, and the first round's record\n")
        g = gate(gate_configs(), workers=args.workers)
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A31, second round, D38: seconds per cell, measured on "
              "this machine\n")
        time_cells(workers=args.workers)
        return 0

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A31, second round, smoke: %d cells, gated in-process on "
              "its own configurations, nothing written\n" % len(keys))
        gate_section = gate(
            gate_configs(needs=SMOKE["needs"],
                         elasticities=SMOKE["elasticities"], full=False),
            row_needs=SMOKE["needs"], row_seeds=SMOKE["seeds"][:1],
            workers=args.workers)
        print()
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A31, second round: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        if len(seeds) < 2:
            print("stage A31, second round: not starting. The floor is a "
                  "dispersion across seeds, and a dispersion needs two.")
            return 2
        keys = cell_keys(seeds=seeds)
        print("stage A31, second round: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(seeds), args.workers, why))
    # The probe first. It is a fiftieth of the cost and it reads the same
    # switch, so a fault in it costs seconds instead of the whole grid.
    t0 = time.perf_counter()
    pr = probe(carriers=(PROBE_CARRIERS if not args.smoke
                         else PROBE_CARRIERS[:1]))
    print("   %d one-application probes in %.0f s"
          % (sum(len(e["bases"]) for e in pr), time.perf_counter() - t0))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections, bp, cells = analyse(rows, gate_section, pr)
    print_probe(pr)
    print_base_pairs(bp)
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
