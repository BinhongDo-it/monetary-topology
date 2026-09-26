"""A30: the same shock on structures under different strain, and how many
rounds it takes to be absorbed.

Ruled 2026-09-11. The reading this station exists for: on a healthy topology an
exogenous shock to circulation is gone within two rounds, and only a structure
already in crisis is knocked over by a single shock. No station on disk hits
structures under different strain with the same shock and counts the rounds;
this one does only that.

The model is not changed. The driver advances ``Network._run_steps()`` round by
round and acts only at its yield, where one round's books are closed and the
next round has not opened:

    freeze   at the close of round 149 a share s of every live node's balance
             leaves the trading accounts and the claim total; at the close of
             round 150 the same amounts come back. No claim is lost, and
             circulation is cut for one round.
    destroy  the same removal, never returned: a loss of wealth.

Every shocked cell is read against its twin, the same configuration and seed
with no shock. On this carrier the only draws inside a round are the spending
propensities, one per node per round whatever the state, so the twin's random
stream and the shocked cell's are the same draws and the difference between the
two runs is the shock's. ``--gate`` and every run check that it stays so.

Strain uses the model's own quantities: how far the floor sits from the
absorbing edge (the floor multiple), and whether a chronic leak is there and
whether someone recycles it (parking, and the sovereign's pass-down).

Three steps, one at a time and in this order:

    python experiments/a30_shock.py --gate            # the driver is the model
    python experiments/a30_shock.py --time            # seconds per cell
    python experiments/a30_shock.py --run --seeds 5   # the grid

``--run`` does not start until ``--gate`` has passed on the module and this
script as they are now. ``--run --smoke`` is a reduced grid that checks the
code runs, gates itself on its own configurations and writes nothing;
``--no-write`` prints and writes nothing on any step.
"""

from __future__ import annotations

import argparse
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
    ParkSpec,
    SovereignSpec,
    WriteOffSpec,
)

RECORD = RESULTS / "a30_shock.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A29's helpers, taken rather than restated: the record format, the config
#: block, the bit-for-bit comparison and the criterion type with its kinds.
_A29 = _load(ROOT / "experiments" / "a29_sovereign.py", "_a29_for_a30")
config_for = _A29.config_for
r = _A29.r
_fmt = _A29._fmt
_config_diff = _A29._config_diff
_module_sha = _A29._module_sha
_same = _A29._same
_tally = _A29._tally
_default_workers = _A29._default_workers
_print_criteria = _A29._print_criteria
Criterion = _A29.Criterion

ROUNDS = _A29.ROUNDS
SEEDS = _A29.SEEDS
TAIL = _A29.TAIL
FLOOR_MULTIPLE = _A29.FLOOR_MULTIPLE
LEDGER_TOL = _A29.LEDGER_TOL
TARGET = _A29.TARGET

#: The round whose flow the shock reaches first. The removal happens at the
#: yield after the round before it. Past the opening transient, and the round
#: A3-6 used.
SHOCK_ROUND = 150
#: Floors from far below the absorbing edge to far past it. A16-8 put a jump
#: between 0.125 and 0.150; A18_F and A29 found two absorbing states at 0.20.
NEEDS: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.50)
#: Three strains, each a switch already on disk.
STRESSES: tuple[str, ...] = ("healthy", "leak_recycled", "leak")
STRESS_SPECS: dict = {
    # No parking: no chronic leak.
    "healthy": {"park": 0.0, "bond_share": None, "pass_rate": 0.0,
                "landing": None},
    # A29's first round: the leak is parked into bonds and all of it is
    # passed down again, onto the production layer, in the same round.
    "leak_recycled": {"park": 0.02, "bond_share": 1.0, "pass_rate": 1.0,
                      "landing": "production"},
    # The same leak with nobody passing it down.
    "leak": {"park": 0.02, "bond_share": None, "pass_rate": 0.0,
             "landing": None},
}
ELASTICITIES: tuple[float, ...] = (0.0, 0.5)
AUTHORITIES: tuple[str, ...] = ("endogenous", "none")
#: (kind, share). "none" is the twin of every other row.
SHOCKS: tuple[tuple[str, float], ...] = (
    ("none", 0.0), ("freeze", 0.1), ("freeze", 0.3), ("freeze", 0.5),
    ("destroy", 0.1), ("destroy", 0.3))
SHOCK_KINDS: tuple[str, ...] = ("none", "freeze", "destroy")
#: tau: the flow has to stay inside the floor for this many consecutive rounds.
WINDOW = 10
#: The number in the reading this station tests.
TWO_ROUNDS = 2
#: This carrier's block is about 75 nodes (A18_F, A29); fifty or more is a block.
BLOCK = 50
#: Rounds after the shock whose deviation is printed per cell: k = 0 is the
#: shock round itself, and k = 149 is the last round.
HORIZON_K: tuple[int, ...] = tuple(range(0, 11)) + (25, 50, 149)
#: The reduced grid ``--smoke`` runs: every strain, authority and shock at the
#: bistable floor, one elasticity, two seeds.
SMOKE = {"needs": (0.20,), "elasticities": (0.5,), "seeds": SEEDS[:2]}


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, authorities=AUTHORITIES,
              shocks=SHOCKS) -> list:
    keys = []
    for need in needs:
        for stress in stresses:
            for e in elasticities:
                for auth in authorities:
                    for kind, size in shocks:
                        for seed in seeds:
                            keys.append({"need": need, "stress": stress,
                                         "elasticity": e, "authority": auth,
                                         "shock": kind, "size": size,
                                         "seed": seed})
    return keys


def cell_config(key: dict) -> NetworkConfig:
    """A18's ``config_for`` in drawdown, no write-off and no rescue, plus this
    cell's strain. The shock is not in the config: the driver applies it."""
    cfg = config_for("drawdown", WriteOffSpec(), key["authority"], key["need"],
                     key["seed"], resupply_rate=0.0,
                     elasticity=key["elasticity"])
    s = STRESS_SPECS[key["stress"]]
    park = ParkSpec() if s["park"] == 0.0 else ParkSpec(rate=s["park"],
                                                         target=TARGET)
    sov = SovereignSpec()
    if s["pass_rate"] > 0.0:
        sov = SovereignSpec(pass_rate=s["pass_rate"],
                            bond_share=s["bond_share"], landing=s["landing"])
    return dataclasses.replace(cfg, park=park, sovereign=sov)


# ---------------------------------------------------------------------------
# The driver.
# ---------------------------------------------------------------------------

def _rng_digest(net: Network) -> str:
    """Where every generator the round loop can draw from has got to. Compared
    within one run between a cell and its twin, and never written."""
    parts = []
    for name in ("rng", "_channel_rng", "_rewire_rng", "_cut_rng"):
        g = getattr(net, name, None)
        parts.append(repr(None if g is None else g.bit_generator.state))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def drive(cfg: NetworkConfig, shock: str, size: float) -> tuple:
    """Run one configuration through ``_run_steps``, acting only at the yield.

    Returns the network, whose ``_history`` is the run's history, and what the
    driver saw: the amount removed, whether the claim total stayed equal to
    held plus parked at every yield, and whether a freeze came back node for
    node.
    """
    if shock not in SHOCK_KINDS:
        raise ValueError("shock must be one of %s, got %r" % (SHOCK_KINDS, shock))
    net = Network(cfg)
    frozen = None
    removed = 0.0
    books = True
    returned = None
    for t in net._run_steps():
        if shock != "none" and t == SHOCK_ROUND - 1:
            take = size * np.maximum(net.holdings, 0.0) * net._alive
            net.holdings -= take
            removed = float(take.sum())
            net._total_claims -= removed
            if shock == "freeze":
                frozen = take
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
    return net, {"removed": removed, "books": books, "returned": returned}


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net, seen = drive(cfg, key["shock"], key["size"])
    h = net._history
    row = dict(key)
    row.update({
        "removed": r(seen["removed"]),
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
        # The authority's target: the Layer 2 inflow of round 0, which the
        # endogenous rule issues back up to and never past.
        "_target": float(net._baseline_active or 0.0),
        "_rng": _rng_digest(net),
    })
    return row


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            AUTHORITIES.index(x["authority"]), SHOCKS.index((x["shock"],
                                                             x["size"])),
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

def _base(x: dict) -> tuple:
    return (x["need"], x["stress"], x["elasticity"], x["authority"])


def _gkey(x: dict) -> tuple:
    return _base(x) + (x["shock"], x["size"])


def _gsort(g: tuple) -> tuple:
    return (g[0], STRESSES.index(g[1]), g[2], AUTHORITIES.index(g[3]),
            SHOCKS.index((g[4], g[5])))


def _num(x):
    """A finite float the stage's way, or None."""
    if x is None:
        return None
    x = float(x)
    return r(x) if np.isfinite(x) else None


def _median(values):
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    return r(float(np.median(vals))) if vals else None


def _range(values) -> str:
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not vals:
        return "none"
    return "%s to %s" % (r(min(vals)), r(max(vals)))


def _shock_label(kind: str, size: float) -> str:
    return "%s %.1f" % (kind, size)


def twins_and_bands(rows: list) -> tuple:
    """Each base cell's unshocked runs by seed, and the floor under a shocked
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


ABSORB_STATES: tuple[tuple[str, str], ...] = (
    ("inside at once", "the shock round is already inside the floor, so the "
     "shock is smaller than it: no reading"),
    ("back within two rounds", "back inside the floor within two rounds, and "
     "it stays there"),
    ("back slowly", "back inside the floor after more than two rounds, and it "
     "stays there"),
    ("never back, above", "never back inside the floor: the flow settles "
     "above its twin"),
    ("never back, below", "never back inside the floor: the flow settles "
     "below its twin"),
    ("never back, swinging", "never back inside the floor, and the tail sits "
     "on neither side of the band"),
    ("one seed", "one twin seed, so no floor: no reading"))


def absorption(d: np.ndarray, band) -> tuple:
    """tau and its state. k = 0 is the shock round; tau is the first k from
    which the flow stays inside the band for ``WINDOW`` consecutive rounds."""
    if band is None:
        return None, "one seed"
    k0 = SHOCK_ROUND
    inside = np.abs(d) <= band
    for k in range(0, ROUNDS - k0 - WINDOW + 1):
        if inside[k0 + k:k0 + k + WINDOW].all():
            if k == 0:
                return 0, "inside at once"
            return k, ("back within two rounds" if k <= TWO_ROUNDS
                       else "back slowly")
    tail_d = float(d[-TAIL:].mean())
    tail_b = float(band[-TAIL:].mean())
    if tail_d > tail_b:
        return None, "never back, above"
    if tail_d < -tail_b:
        return None, "never back, below"
    return None, "never back, swinging"


FLIP_STATES: tuple[tuple[str, str], ...] = (
    ("block under", "%d or more nodes more below the floor than the twin at "
     "the close: a block knocked under" % BLOCK),
    ("block lifted", "%d or more fewer: a block lifted" % BLOCK),
    ("some under", "2 to %d more" % (BLOCK - 1)),
    ("some lifted", "2 to %d fewer" % (BLOCK - 1)),
    ("one node", "one node either way, inside A18_B6's jitter: no reading"),
    ("unmoved", "the same count"))


def flip(diff: int) -> str:
    if diff >= BLOCK:
        return "block under"
    if diff <= -BLOCK:
        return "block lifted"
    if diff >= 2:
        return "some under"
    if diff <= -2:
        return "some lifted"
    if diff != 0:
        return "one node"
    return "unmoved"


def read_cells(rows: list, twins: dict, bands: dict) -> list:
    """Every cell's own numbers, and for a shocked cell its readings against
    the twin. Private arrays are carried along for the group paths and are
    stripped before anything is written."""
    k0 = SHOCK_ROUND
    out = []
    for x in rows:
        c = {k: v for k, v in x.items() if not k.startswith("_")}
        flow, circ, parked = x["_flow"], x["_circ"], x["_parked"]
        c.update({
            "flow_at_shock_round": _num(flow[k0]),
            "flow_tail": _num(flow[-TAIL:].mean()),
            "circulating_tail": _num(circ[-TAIL:].mean()),
            "parked_tail": _num(parked[-TAIL:].mean()),
            "issued_total": _num(x["_issued"].sum()),
            # Where the Layer 2 inflow sits against the authority's target:
            # the round before the shock, and over the tail.
            "l2_over_target_before_shock": (
                _num(x["_l2"][k0 - 1] / x["_target"] - 1.0)
                if x["_target"] > 0 else None),
            "l2_over_target_tail": (
                _num(x["_l2"][-TAIL:].mean() / x["_target"] - 1.0)
                if x["_target"] > 0 else None),
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
        diff_close = int(x["below_close"] - tw["below_close"])
        after = bd[k0:]
        hit = np.flatnonzero(np.abs(after) >= BLOCK)
        twin_flow_tail = float(base_flow[-TAIL:].mean())
        tail_ratio = (float(flow[-TAIL:].mean()) / twin_flow_tail
                      if twin_flow_tail > 0 else None)
        twin_circ_tail = float(tw["_circ"][-TAIL:].mean())
        twin_parked_tail = float(tw["_parked"][-TAIL:].mean())
        extra = float(x["_issued"][k0 + 1:].sum() - tw["_issued"][k0 + 1:].sum())
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
            # A block can go under for a while and come back: the path after
            # the shock, beside the close.
            "below_diff_peak": int(after.max()),
            "below_diff_peak_k": int(np.argmax(after)),
            "below_diff_trough": int(after.min()),
            "rounds_block_under": int((after >= BLOCK).sum()),
            "rounds_block_lifted": int((after <= -BLOCK).sum()),
            "flow_tail_ratio": _num(tail_ratio),
            "circulating_tail_ratio": (
                _num(circ[-TAIL:].mean() / twin_circ_tail)
                if twin_circ_tail > 0 else None),
            "parked_tail_ratio": (_num(parked[-TAIL:].mean() / twin_parked_tail)
                                  if twin_parked_tail > 0 else None),
            # On relative gaps: a twin that is itself running down (a leak
            # with nobody issuing) shrinks every absolute gap with it, so a
            # ratio of absolute gaps would read the run-down as recovery.
            "recovered": (_num(1.0 - (tail_ratio - 1.0) / float(rel[k0]))
                          if tail_ratio is not None and np.isfinite(rel[k0])
                          and rel[k0] != 0.0 else None),
            "extra_issued_after": _num(extra),
            "extra_issued_share_of_removed": (
                _num(extra / x["removed"]) if x["removed"] > 0 else None),
            "same_draws_as_twin": x["_rng"] == tw["_rng"],
        })
        c["_rel"] = rel
        out.append(c)
    return out


def _col_median(a: np.ndarray) -> list:
    out = []
    for col in a.T:
        f = col[np.isfinite(col)]
        out.append(r(float(np.median(f))) if f.size else None)
    return out


def groups(cells: list) -> list:
    """Every shocked group (need, strain, elasticity, authority, shock) over
    its seeds, never pooled across groups."""
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
            "authority": g[3], "shock": g[4], "size": g[5],
            "seeds": [c["seed"] for c in cs],
            "absorption": states,
            "absorption_state": states[0] if len(set(states)) == 1 else "split",
            "tau": taus,
            "tau_median": _median([t for t in taus if t is not None]),
            "flip": [c["flip"] for c in cs],
            "below_diff_close": [c["below_diff_close"] for c in cs],
            "twin_below_close": [c["twin_below_close"] for c in cs],
            "block_first_k": [c["block_first_k"] for c in cs],
            "below_diff_peak": [c["below_diff_peak"] for c in cs],
            "rounds_block_under": [c["rounds_block_under"] for c in cs],
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
            "extra_issued_share_median": _median(
                [c["extra_issued_share_of_removed"] for c in cs]),
            "median_deviation_path_from_shock_round": _col_median(
                np.array([c["_rel"][SHOCK_ROUND:] for c in cs])),
        })
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def _shocked(cells: list) -> list:
    return [c for c in cells if c["shock"] != "none" and c.get("has_twin")]


def _pooled(cells: list, key) -> dict:
    by = {}
    for c in _shocked(cells):
        by.setdefault(key(c), []).append(c)
    return by


def _sas(c: dict) -> tuple:
    """Strain, authority, shock: the three the reading is about."""
    return (STRESSES.index(c["stress"]), AUTHORITIES.index(c["authority"]),
            SHOCKS.index((c["shock"], c["size"])))


def _sas_label(c: dict) -> str:
    return "%s, %s, %s" % (c["stress"], c["authority"],
                           _shock_label(c["shock"], c["size"]))


A30_0 = "A30-0 the driver is the model, and the shock moves only what it says"


def criterion_a30_0(g, cells: list) -> Criterion:
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
        "twin's end: %d of %d, so the two runs draw the same numbers and "
        "their difference is the shock's. The round loop's own asserts did "
        "not fire: all %d cells completed."
        % (LEDGER_TOL, books, len(cells), back, len(freezes), draws,
           len(shocked), len(cells)))
    state_map = (
        "State map: the driver identical to Network.run() on every gate "
        "configuration and the three checks above holding in every cell -> "
        "PASS; anything else -> FAIL; no gate section -> not judged, and "
        "--run does not start.")
    if not g:
        return Criterion(A30_0, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + part + " " + state_map, evaluated=False)
    differ = g["differ"]
    head = (
        "With no shock the driver touches nothing: on %d configurations (the "
        "library default and every base cell of this grid at seed %d), %d "
        "history fields and the closing state (claim total, holdings, parked, "
        "below the floor, and where every generator got to) compared bit for "
        "bit against Network.run(), %d configurations differ%s."
        % (len(g["configs"]), SEEDS[0], g["fields_compared"], len(differ),
           "" if not differ else ": " + "; ".join(
               "%s in %s" % (x["config"], x["fields"]) for x in differ[:5])))
    return Criterion(A30_0, "instrument", g["verdict"] == "pass" and rows_ok,
                     "%s %s Gate verdict: %s. %s" % (head, part, g["verdict"],
                                                    state_map))


def criterion_a30_1(cells: list) -> Criterion:
    shocked = _shocked(cells)
    below = sum(1 for c in shocked if c["flow_below_twin_at_shock_round"])
    parts = []
    for kind, size in SHOCKS[1:]:
        v = [c["drop_at_shock_round"] for c in shocked
             if (c["shock"], c["size"]) == (kind, size)]
        if v:
            parts.append("%s: median %s, %s" % (_shock_label(kind, size),
                                                _median(v), _range(v)))
    ok = bool(shocked) and below == len(shocked)
    return Criterion(
        "A30-1 the shock reaches the flow (D28)", "instrument", ok,
        "Round %d's flow against its twin's, same seed: below it in %d of %d "
        "shocked cells. The deviation at the shock round as a share of the "
        "twin's flow, by shock: %s. State map: every shocked cell below its "
        "twin -> PASS; any not below -> FAIL, and the readings after this one "
        "have no object in those cells."
        % (SHOCK_ROUND, below, len(shocked), "; ".join(parts)))


def criterion_a30_2(cells: list, grp: list) -> Criterion:
    by = _pooled(cells, _sas)
    lines = []
    for k in sorted(by):
        cs = by[k]
        lines.append("%s: %s; tau median %s" % (
            _sas_label(cs[0]), _tally(c["absorption"] for c in cs),
            _median([c["tau"] for c in cs if c["tau"] is not None])))
    bs = [g["band_share_at_shock_round"] for g in grp]
    return Criterion(
        "A30-2 how many rounds the flow takes to come back", "own_reading",
        True,
        "Printed, not judged. tau is the first round after the shock from "
        "which the flow stays inside its twin's floor for %d consecutive "
        "rounds; round %d is k = 0. Floor = the twin's dispersion across seeds "
        "at the same round, band = %.1f floors. Inside the floor is a "
        "statement against how much economies of this kind differ from seed "
        "to seed; the paired difference itself carries no noise, because the "
        "two runs draw the same numbers (A30-0), and what is left of it is "
        "A30-4's recovered share. State map: %s. The band at the "
        "shock round as a share of the twin's flow: median %s, %s. By strain, "
        "authority and shock, over floors, elasticities and seeds: %s. Group "
        "by group in the groups section; per cell, with the deviation at k = "
        "%s, in the rows section."
        % (WINDOW, SHOCK_ROUND, FLOOR_MULTIPLE,
           "; ".join("%s = %s" % s for s in ABSORB_STATES), _median(bs),
           _range(bs), "; ".join(lines),
           ", ".join(str(k) for k in HORIZON_K)))


def criterion_a30_3(cells: list) -> Criterion:
    shocked = _shocked(cells)
    by = _pooled(cells, lambda c: (c["need"],) + _sas(c))
    moved, passing = [], []
    for k in sorted(by):
        cs = by[k]
        blocks = [c for c in cs if c["flip"] in ("block under", "block lifted")]
        if blocks:
            moved.append(
                "need %.2f %s: %s of %d, first reached at k = %s, twin below "
                "the floor at the close %s" % (
                    cs[0]["need"], _sas_label(cs[0]),
                    _tally(c["flip"] for c in blocks), len(cs),
                    sorted(c["block_first_k"] for c in blocks),
                    sorted({c["twin_below_close"] for c in cs})))
        back = [c for c in cs if c["flip"] not in ("block under",
                                                   "block lifted")
                and (c["rounds_block_under"] or c["rounds_block_lifted"])]
        if back:
            passing.append(
                "need %.2f %s: %d of %d, peak %s more below at k = %s, rounds "
                "a block was under %s" % (
                    cs[0]["need"], _sas_label(cs[0]), len(back), len(cs),
                    sorted(c["below_diff_peak"] for c in back),
                    sorted(c["below_diff_peak_k"] for c in back),
                    sorted(c["rounds_block_under"] for c in back)))
    return Criterion(
        "A30-3 whether one shock knocks a block under", "own_reading", True,
        "Printed, not judged. The count below the floor at the close against "
        "the twin's, same seed, and beside it the path after the shock, so a "
        "block that went under and came back is told apart from one that "
        "stayed. State map at the close: %s. All shocked cells: %s. Where a "
        "block has moved at the close (need, strain, authority, shock; over "
        "elasticities and seeds): %s. Where a block moved after the shock and "
        "was back by the close: %s."
        % ("; ".join("%s = %s" % s for s in FLIP_STATES),
           _tally(c["flip"] for c in shocked),
           "; ".join(moved) if moved else "nowhere",
           "; ".join(passing) if passing else "nowhere"))


def _refill_lines(cells: list) -> list:
    """Authority on, claims destroyed: how much of the loss is issued back,
    beside where the twin's Layer 2 inflow stood against the authority's
    target when the shock hit, and where the cell's own stands in the tail."""
    by = _pooled(cells, lambda c: (STRESSES.index(c["stress"]),
                                   c["elasticity"],
                                   SHOCKS.index((c["shock"], c["size"]))))
    lines = []
    for k in sorted(by):
        cs = [c for c in by[k] if c["authority"] == "endogenous"
              and c["shock"] == "destroy"]
        if not cs:
            continue
        lines.append(
            "%s e %.1f %s: issued back %s of what was removed, twin's Layer 2 "
            "inflow over the target at the shock %s, the cell's own in the "
            "tail %s" % (
                cs[0]["stress"], cs[0]["elasticity"],
                _shock_label(cs[0]["shock"], cs[0]["size"]),
                _median([c["extra_issued_share_of_removed"] for c in cs]),
                _median([c["l2_over_target_before_shock"] for c in cs]),
                _median([c["l2_over_target_tail"] for c in cs])))
    return lines


def criterion_a30_4(cells: list) -> Criterion:
    by = _pooled(cells, _sas)
    lines = []
    for k in sorted(by):
        cs = by[k]
        fr = [c["flow_tail_ratio"] for c in cs]
        up = [c["extra_issued_share_of_removed"] for c in cs
              if c["absorption"] == "never back, above"]
        lines.append("%s: flow %s (%s), circulating %s, recovered %s%s" % (
            _sas_label(cs[0]), _median(fr), _range(fr),
            _median([c["circulating_tail_ratio"] for c in cs]),
            _median([c["recovered"] for c in cs]),
            "" if not up else "; where it settles above, extra issuance "
            "after the shock over what was removed %s" % _median(up)))
    return Criterion(
        "A30-4 what the shock leaves behind", "own_reading", True,
        "Printed, not judged. The last %d rounds against the twin's: flow over "
        "flow, and circulating stock over circulating stock, never parked "
        "over circulating. Recovered = one less the tail's gap over the shock "
        "round's, both as shares of the twin's flow: 1 is all of it back, 0 "
        "none of it, above 1 an overshoot, below 0 a gap that grew. A15 "
        "recovered 66.1%% of a wage bill it caught. By strain, authority and "
        "shock, medians over floors, elasticities and seeds: %s. The "
        "endogenous rule issues the Layer 2 inflow's shortfall from its round "
        "0 level and nothing past it, so where the twin already stood above "
        "that level the part of a loss above it is never issued back. "
        "Authority on, claims destroyed, medians over floors and seeds: %s."
        % (TAIL, "; ".join(lines), "; ".join(_refill_lines(cells))))


def criterion_a30_5(grp: list) -> Criterion:
    want = ROUNDS - SHOCK_ROUND
    key = "median_deviation_path_from_shock_round"
    full = [g for g in grp if len(g[key]) == want
            and all(v is not None for v in g[key])]
    return Criterion(
        "A30-5 the deviation paths are on the record", "bookkeeping",
        bool(grp) and len(full) == len(grp),
        "The median over seeds of the flow's deviation from its twin, as a "
        "share of the twin's flow, every round from %d to %d: %d of %d shocked "
        "groups carry a full path. They are in the groups section, one per "
        "need, strain, elasticity, authority and shock. State map: every "
        "group full -> PASS; a group short or with a missing round -> FAIL, "
        "reprint." % (SHOCK_ROUND, ROUNDS - 1, len(full), len(grp)))


# ---------------------------------------------------------------------------
# Console tables: printed, never written.
# ---------------------------------------------------------------------------

CODES: dict = {"inside at once": "in", "back within two rounds": "2r",
               "back slowly": "slow", "never back, above": "hi",
               "never back, below": "lo", "never back, swinging": "sw",
               "one seed": "1s", "split": "mix"}


def _axes(items: list) -> tuple:
    needs = sorted({x["need"] for x in items})
    stresses = [s for s in STRESSES if any(x["stress"] == s for x in items)]
    es = sorted({x["elasticity"] for x in items})
    auths = [a for a in AUTHORITIES if any(x["authority"] == a for x in items)]
    return needs, stresses, es, auths


def print_twins(cells: list) -> None:
    tw = [c for c in cells if c["shock"] == "none"]
    needs, stresses, es, auths = _axes(tw)
    print("\n   twins: below the floor at the close, median over seeds "
          "(the strain each shock lands on)")
    print("   %-26s%s" % ("", "".join("%-16s" % ("%s e%.1f" % (a, e))
                                     for a in auths for e in es)))
    for need in needs:
        for s in stresses:
            vals = []
            for a in auths:
                for e in es:
                    v = [c["below_close"] for c in tw if c["need"] == need
                         and c["stress"] == s and c["authority"] == a
                         and c["elasticity"] == e]
                    vals.append("%-16s" % (_median(v) if v else "-"))
            print("   %-26s%s" % ("need %.2f %s" % (need, s), "".join(vals)))


def print_tables(grp: list) -> None:
    needs, stresses, es, auths = _axes(grp)
    index = {_gkey(g): g for g in grp}
    print("\n   each entry: absorption (%s), tau median, blocks under (+) or "
          "lifted (-) at the close over the seeds, seeds where a block went "
          "under and came back, flow tail over the twin's"
          % ", ".join("%s = %s" % (v, k) for k, v in CODES.items()))
    for kind, size in SHOCKS[1:]:
        if not any(g["shock"] == kind and g["size"] == size for g in grp):
            continue
        print("\n   %s" % _shock_label(kind, size))
        print("   %-26s%s" % ("", "".join("%-32s" % ("%s e%.1f" % (a, e))
                                         for a in auths for e in es)))
        for need in needs:
            for s in stresses:
                txt = []
                for a in auths:
                    for e in es:
                        g = index.get((need, s, e, a, kind, size))
                        if g is None:
                            txt.append("%-32s" % "-")
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
                                k = CODES.get(st, "?")
                                cnt[k] = cnt.get(k, 0) + 1
                            code = "/".join("%s%d" % (k, cnt[k])
                                            for k in sorted(cnt))
                        txt.append("%-32s" % ("%s t%s b%s u%d %s" % (
                            code,
                            "-" if tau is None else "%g" % tau, blk,
                            g["block_came_back"],
                            "-" if fr is None else "%.3f" % fr)))
                print("   %-26s%s" % ("need %.2f %s" % (need, s),
                                      "".join(txt)))


# ---------------------------------------------------------------------------
# Rule 19. The model is not changed, so the gate is the driver: with no shock
# it has to be ``Network.run()``, and that is run, not argued.
# ---------------------------------------------------------------------------

#: The closing state compared beside the history.
CLOSING: tuple[str, ...] = ("_total_claims", "holdings", "_parked", "_below")


def gate_configs(needs=NEEDS, stresses=STRESSES, elasticities=ELASTICITIES,
                 authorities=AUTHORITIES) -> list:
    out = [("library default", NetworkConfig())]
    for need in needs:
        for stress in stresses:
            for e in elasticities:
                for auth in authorities:
                    key = {"need": need, "stress": stress, "elasticity": e,
                           "authority": auth, "shock": "none", "size": 0.0,
                           "seed": SEEDS[0]}
                    out.append(("need %.2f %s e %.1f %s" % (need, stress, e,
                                                            auth),
                                cell_config(key)))
    return out


def gate(configs: list) -> dict:
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    differ, labels = [], []
    for label, cfg in configs:
        t0 = time.perf_counter()
        ref = Network(cfg)
        h_ref = ref.run()
        net, seen = drive(cfg, "none", 0.0)
        h_drv = net._history
        bad = [n for n in names
               if not _same(getattr(h_ref, n), getattr(h_drv, n))]
        bad += [n for n in CLOSING if not _same(getattr(ref, n),
                                                getattr(net, n))]
        if _rng_digest(ref) != _rng_digest(net):
            bad.append("generators")
        if not seen["books"]:
            bad.append("claim total against held plus parked")
        labels.append(label)
        if bad:
            differ.append({"config": label, "fields": bad})
        print("   %-44s %s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            time.perf_counter() - t0))
    return {
        "module_sha": _module_sha(MODULE),
        "script_sha": _module_sha(SCRIPT),
        "configs": labels,
        "fields_compared": len(names) + len(CLOSING) + 1,
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
                       "driver lives in it: run --gate again")
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module and this script"


# ---------------------------------------------------------------------------
# Timing (D38): measured, printed, never written.
# ---------------------------------------------------------------------------

def time_cells(repeats: int = 3, workers: int = 1) -> None:
    probes = [
        {"need": 0.20, "stress": "healthy", "elasticity": 0.5,
         "authority": "endogenous", "shock": "none", "size": 0.0,
         "seed": SEEDS[0]},
        {"need": 0.20, "stress": "leak_recycled", "elasticity": 0.5,
         "authority": "endogenous", "shock": "freeze", "size": 0.3,
         "seed": SEEDS[0]},
        {"need": 0.50, "stress": "leak", "elasticity": 0.0,
         "authority": "none", "shock": "destroy", "size": 0.3,
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
        print("   need %.2f %-14s e %.1f %-10s %-12s %.3f s per cell (mean of "
              "%d)" % (k["need"], k["stress"], k["elasticity"],
                       k["authority"], _shock_label(k["shock"], k["size"]),
                       per[-1], repeats))
    mean = float(np.mean(per))
    # The estimate divides by the workers this machine can actually run.
    eff = max(1, min(workers, os.cpu_count() or 1))
    for n in (3, len(SEEDS)):
        cells = len(cell_keys(seeds=SEEDS[:n]))
        print("   %d seeds: %d cells, %.0f s serial, about %.0f s on %d "
              "workers" % (n, cells, cells * mean, cells * mean / eff, eff))
    n_gate = len(gate_configs())
    print("   --gate: %d configurations, two runs each, serial, about %.0f s"
          % (n_gate, 2 * n_gate * mean))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe = cell_config({"need": NEEDS[0], "stress": "healthy",
                         "elasticity": ELASTICITIES[0],
                         "authority": AUTHORITIES[0], "shock": "none",
                         "size": 0.0, "seed": SEEDS[0]})
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
        "carrier": "A18's config_for: drawdown, no write-off, no rescue",
        "rounds": ROUNDS,
        "shock_round": SHOCK_ROUND,
        "shock": ("freeze: a share of every live node's balance leaves the "
                  "trading accounts and the claim total at the close of round "
                  "%d and comes back at the close of round %d; destroy: the "
                  "same removal, never returned" % (SHOCK_ROUND - 1,
                                                    SHOCK_ROUND)),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticities": list(ELASTICITIES),
                 "authorities": list(AUTHORITIES),
                 "shocks": [list(s) for s in SHOCKS], "seeds": list(SEEDS)},
        "park_target": TARGET,
        "tail": TAIL,
        "window": WINDOW,
        "two_rounds": TWO_ROUNDS,
        "block": BLOCK,
        "horizons_after_shock": list(HORIZON_K),
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
    doc["stage"] = "A30"
    # Closed 2026-09-11: every criterion is read, and the question it opened
    # (an authority that also takes back) is a station of its own, A31.
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
    crits = [criterion_a30_0(gate_section, cells), criterion_a30_1(cells),
             criterion_a30_2(cells, grp), criterion_a30_3(cells),
             criterion_a30_4(cells), criterion_a30_5(grp)]
    written = [{k: v for k, v in c.items() if not k.startswith("_")}
               for c in cells]
    sections = {"criteria": [c.as_dict() for c in crits], "groups": grp,
                "rows": written}
    return crits, sections, grp, cells


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
        print("stage A30, rule 19: the driver against Network.run(), with no "
              "shock\n")
        g = gate(gate_configs())
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A30, D38: seconds per cell, measured on this machine\n")
        time_cells(workers=args.workers)
        return 0

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A30, smoke: %d cells, gated in-process on its own "
              "configurations, nothing written\n" % len(keys))
        gate_section = gate(gate_configs(needs=SMOKE["needs"],
                                         elasticities=SMOKE["elasticities"]))
        print()
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A30: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        if len(seeds) < 2:
            print("stage A30: not starting. The floor is a dispersion across "
                  "seeds, and a dispersion needs two.")
            return 2
        keys = cell_keys(seeds=seeds)
        print("stage A30: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(seeds), args.workers, why))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections, grp, cells = analyse(rows, gate_section)
    print_twins(cells)
    print_tables(grp)
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
