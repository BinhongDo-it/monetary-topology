"""A29: a sovereign drawn outside the graph, and the bonds that bring parked
claims back into it.

Ruled 2026-09-11. The sovereign sets the edge set, so it is the party that
draws the graph and is not one of its nodes. A financial-layer node that buys
its bonds is parking, which ``ParkSpec`` already builds. The proceeds leave
the graph, and what the sovereign passes down enters it at the receiving nodes
as an in-edge from outside. ``SovereignSpec`` is that ruling in code.

This round builds only the leg that passes down, and the bonds roll over for
ever. Maturity, coupons and who funds a repayment are the next mechanism: one
mechanism at a time, the way ``ParkSpec`` was built one way first.

Three steps, one at a time and in this order:

    python experiments/a29_sovereign.py --gate            # rule 19
    python experiments/a29_sovereign.py --time            # seconds per cell
    python experiments/a29_sovereign.py --run --seeds 3   # the first grid

``--gate`` reads two records that have to be regenerated after the module
changed, so these two come first:

    python experiments/a18_policy_paths.py --park
    python experiments/a23_two_way_park.py --smoke

``--run`` does not start until ``--gate`` has passed on the module as it is
now. ``--run --smoke`` is a reduced grid that checks the code runs and writes
nothing; ``--no-write`` prints and writes nothing on any step.

Per cell, against the same cell with nothing passed down, the grid reads what
circulates and what is parked over the last fifty rounds, kept apart and never
as a ratio (A23's rule), the support, the count below the floor and the
issuance; on the treated side also what was passed down, where it landed, and
the bond stock.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
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
    ParkSpec,
    ResupplySpec,
    SOVEREIGN_LANDINGS,
    SovereignSpec,
    WriteOffSpec,
)

RECORD = RESULTS / "a29_sovereign.json"
MODULE = SRC / "network.py"

#: The module as it stood before ``SovereignSpec``, kept beside it under the
#: repository's backup convention. ``--gate`` runs it and the current module in
#: one process and compares every history field.
PRE_MODULE = SRC / "network.py.expired_20260911_pre_A29"

#: Rule 19's two records, each against its copy in ``results/_baseline``, with
#: the command that regenerates it.
GATE_RECORDS: tuple[tuple[str, str], ...] = (
    ("a18_park.json", "python experiments/a18_policy_paths.py --park"),
    ("subset/a23_two_way_park.json",
     "python experiments/a23_two_way_park.py --smoke"),
)
BASELINE = RESULTS / "_baseline"

#: The history fields ``SovereignSpec`` adds, ``None`` whenever it is off.
NEW_FIELDS: tuple[str, ...] = ("sovereign_pool", "passed_down",
                               "passed_down_l2", "bond_stock")

KINDS: tuple[str, ...] = ("instrument", "premise", "known_answer", "rival",
                          "own_reading", "bookkeeping")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A18 = _load(ROOT / "experiments" / "a18_policy_paths.py", "_a18_for_a29")
config_for = _A18.config_for
r = _A18.r
ROUNDS = _A18.ROUNDS
SEEDS = _A18.SEEDS

#: A18_F's two floors.
NEEDS: tuple[float, ...] = (0.20, 0.50)
#: Two parking rates from A18_F's fine grid, a decade apart.
PARK_RATES: tuple[float, ...] = (0.002, 0.02)
#: ``(bond_share, pass_rate)``. The first three hold the amount and vary the
#: lag, the last two hold the lag and vary the amount. Every group's control is
#: the same cell with ``pass_rate = 0``.
KNOBS: tuple[tuple[float, float], ...] = (
    (1.0, 1.0), (1.0, 0.1), (1.0, 0.01), (0.5, 1.0), (0.25, 1.0))
LANDINGS: tuple[str, ...] = SOVEREIGN_LANDINGS
ELASTICITIES: tuple[float, ...] = (0.0, 0.5)
AUTHORITIES: tuple[str, ...] = ("endogenous", "none")
TARGET = "financial"
#: A23's window: every tail is a fifty-round mean.
TAIL = 50
#: A18_F's horizons, for the bond stock against the circulating stock.
HORIZONS: tuple[int, ...] = (50, 100, 150, 200, 250, 299)
#: A23's multiple of a measured floor, itself B18's convention. Every seed's
#: raw difference is printed beside its state, so no reading rests on it.
FLOOR_MULTIPLE = 2.0
#: A single node's difference in the count below the floor sits inside
#: A18_B6's jitter (a 1e-10 perturbation flips one cell in 150), so that
#: count's floor is never taken below half a node: one node is inside the band.
COUNT_FLOOR = 0.5
#: The two books close to this share of the opening stock. The round loop
#: asserts the same bound every round; here it is read back off the history.
LEDGER_TOL = 1e-9
#: The reduced grid ``--smoke`` runs: every code path, two seeds.
SMOKE = {"needs": NEEDS[:1], "parks": PARK_RATES[1:], "seeds": SEEDS[:2]}


@dataclass
class Criterion:
    name: str
    kind: str
    passed: bool
    detail: str
    #: False only in a run that could not evaluate it (a smoke run with no
    #: gate section). Printed as such and never written.
    evaluated: bool = True

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {self.kind!r}")

    def as_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "passed": self.passed,
                "detail": self.detail}


# ---------------------------------------------------------------------------
# Record helpers, as A24 writes them.
# ---------------------------------------------------------------------------

def _fmt(x):
    """Floats through an explicit spec, never repr (derived-file rule 5)."""
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, float):
        return float(f"{x:.10f}")
    if isinstance(x, (set, frozenset)):
        return sorted(_fmt(v) for v in x)
    if isinstance(x, (tuple, list)):
        return [_fmt(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _fmt(v) for k, v in x.items()}
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(f"{float(x):.10f}")
    return x


def _config_diff(obj, seen=None) -> dict:
    """Every dataclass field of ``obj`` that differs from its own default.

    Discipline 18d: a record carries the configuration it ran under. Fields at
    their defaults are dropped, so what comes back is exactly what this stage
    chose.
    """
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return {}
    seen.add(id(obj))
    out = {}
    for f in dataclasses.fields(obj):
        if not f.init:
            continue
        cur = getattr(obj, f.name)
        if f.default is not dataclasses.MISSING:
            dflt = f.default
        elif f.default_factory is not dataclasses.MISSING:
            dflt = f.default_factory()
        else:
            dflt = None
        if dataclasses.is_dataclass(cur) and not isinstance(cur, type):
            sub = _config_diff(cur, seen)
            if sub:
                out[f.name] = sub
            continue
        if isinstance(cur, np.ndarray):
            continue
        try:
            same = bool(cur == dflt)
        except Exception:
            same = False
        if not same:
            out[f.name] = cur
    return out


def _module_sha(path: Path) -> str:
    """Content hash with line endings normalised, so a checkout that converts
    them does not read as a changed module."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:16]


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def cell_keys(seeds=SEEDS, needs=NEEDS, parks=PARK_RATES,
              authorities=AUTHORITIES) -> list:
    keys = []
    for need in needs:
        for park in parks:
            for e in ELASTICITIES:
                for auth in authorities:
                    base = {"need": need, "park": park, "elasticity": e,
                            "authority": auth}
                    for seed in seeds:
                        keys.append({**base, "arm": "control", "seed": seed,
                                     "bond_share": None, "pass_rate": 0.0,
                                     "landing": None})
                    for bs, pr in KNOBS:
                        for landing in LANDINGS:
                            for seed in seeds:
                                keys.append({**base, "arm": "treatment",
                                             "seed": seed, "bond_share": bs,
                                             "pass_rate": pr,
                                             "landing": landing})
    return keys


def cell_config(key: dict) -> NetworkConfig:
    """A18's ``config_for`` in drawdown, no write-off and no rescue, plus this
    cell's parking and sovereign."""
    cfg = config_for("drawdown", WriteOffSpec(), key["authority"], key["need"],
                     key["seed"], resupply_rate=0.0,
                     elasticity=key["elasticity"])
    sov = SovereignSpec()
    if key["pass_rate"] > 0.0:
        sov = SovereignSpec(pass_rate=key["pass_rate"],
                            bond_share=key["bond_share"],
                            landing=key["landing"])
    return dataclasses.replace(
        cfg, park=ParkSpec(rate=key["park"], target=TARGET), sovereign=sov)


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net = Network(cfg)
    h = net.run()
    circ = np.asarray(h.holdings, dtype=float).sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    issued = np.asarray(h.issuance, dtype=float)
    row = dict(key)
    row.update({
        "circulating_tail": r(circ[-TAIL:].mean()),
        "parked_tail": r(parked[-TAIL:].mean()),
        "circulating_close": r(circ[-1]),
        "parked_close": r(parked[-1]),
        "support_tail": r(np.asarray(h.effective_support,
                                     dtype=float)[-TAIL:].mean()),
        "volume_tail": r(np.asarray(h.total_volume, dtype=float)[-TAIL:].mean()),
        # Drawdown: nobody leaves, so these count who is below the floor.
        "below_close": int(net._below.sum()),
        "below_tail": r(np.asarray(h.starved, dtype=float)[-TAIL:].mean()),
        "issued_total": r(issued.sum()),
        "circulating_at": {str(q): r(circ[q]) for q in HORIZONS},
    })
    if not cfg.sovereign.active:
        return row
    passed = np.asarray(h.passed_down, dtype=float)
    bonds = np.asarray(h.bond_stock, dtype=float)
    pool = np.asarray(h.sovereign_pool, dtype=float)
    stock = circ + parked
    tol = LEDGER_TOL * max(1.0, float(stock.max()) / cfg.initial_claims,
                           float(bonds.max()) / cfg.initial_claims)
    in_graph = np.diff(stock) - (issued[1:] + passed[1:])
    outside = bonds - np.cumsum(passed) - pool
    bought = bonds - key["bond_share"] * parked
    row.update({
        "passed_total": r(passed.sum()),
        "passed_l2_total": r(np.asarray(h.passed_down_l2, dtype=float).sum()),
        "passed_tail": r(passed[-TAIL:].mean()),
        "pool_close": r(pool[-1]),
        "bonds_close": r(bonds[-1]),
        "bonds_at": {str(q): r(bonds[q]) for q in HORIZONS},
        "receivers": int((net._passed_by_node > 0.0).sum()),
        # A boolean and not the residuals: those are machine rounding and would
        # differ in the last digit between two builds.
        "books_close": bool(np.abs(in_graph).max() <= tol
                            and np.abs(outside).max() <= tol
                            and np.abs(bought).max() <= tol
                            and pool.min() >= -tol),
    })
    return row


def _row_key(x: dict) -> tuple:
    return (x["arm"], x["need"], x["park"], x["elasticity"], x["authority"],
            -1.0 if x["bond_share"] is None else x["bond_share"],
            x["pass_rate"], x["landing"] or "", x["seed"])


def _default_workers() -> int:
    """A1b's convention: half the logical cores, at most eight."""
    return max(1, min(8, (os.cpu_count() or 2) // 2))


def run_cells(keys: list, workers: int) -> list:
    if workers <= 1:
        rows = [one_cell(k) for k in keys]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one_cell, keys, chunksize=4))
    return sorted(rows, key=_row_key)


# ---------------------------------------------------------------------------
# Readings. Objects first; every state below is printed beside the numbers it
# came from, and a state that is not a reading says so.
# ---------------------------------------------------------------------------

def _index(rows: list) -> tuple:
    ctrl, treat = {}, {}
    for x in rows:
        base = (x["need"], x["park"], x["elasticity"], x["authority"])
        if x["arm"] == "control":
            ctrl.setdefault(base, {})[x["seed"]] = x
        else:
            g = base + (x["bond_share"], x["pass_rate"], x["landing"])
            treat.setdefault(g, {})[x["seed"]] = x
    return ctrl, treat


def _gkey(p: dict) -> tuple:
    return (p["need"], p["park"], p["elasticity"], p["authority"],
            p["bond_share"], p["pass_rate"], p["landing"])


def _label(g: tuple) -> str:
    s = "need %.2f park %.3f e %.1f %s" % g[:4]
    if len(g) > 4:
        s += " knobs (%.2f, %.2f) %s" % g[4:7]
    return s


def _floor(values: list, count: bool = False):
    """The control's dispersion across seeds, the measured floor (gate six)."""
    if len(values) < 2:
        return None
    sd = float(np.std(values, ddof=1))
    return max(sd, COUNT_FLOOR) if count else sd


def _state(diffs: list, floor) -> str:
    if not diffs:
        return "no pair"
    if floor is None:
        return "one seed"
    band = FLOOR_MULTIPLE * floor
    if all(d > band for d in diffs):
        return "up"
    if all(d < -band for d in diffs):
        return "down"
    if all(abs(d) <= band for d in diffs):
        return "flat"
    return "split"


def _tally(items) -> str:
    counts = {}
    for it in items:
        counts[it] = counts.get(it, 0) + 1
    return ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts)) or "none"


def _median(values: list):
    vals = [v for v in values if v is not None]
    return r(float(np.median(vals))) if vals else None


#: (reading, is a count). For the first two, up is better; for the count below
#: the floor, down is better.
READINGS: tuple[tuple[str, bool], ...] = (
    ("circulating_tail", False), ("support_tail", False),
    ("below_close", True))


def pairs(rows: list) -> list:
    """Every treatment group against its control, seed by seed, never pooled."""
    ctrl, treat = _index(rows)
    out = []
    for g in sorted(treat):
        c = ctrl.get(g[:4], {})
        seeds = sorted(s for s in treat[g] if s in c)
        entry = {"need": g[0], "park": g[1], "elasticity": g[2],
                 "authority": g[3], "bond_share": g[4], "pass_rate": g[5],
                 "landing": g[6], "seeds": seeds}
        for q, count in READINGS:
            fl = _floor([c[s][q] for s in sorted(c)], count)
            diffs = [treat[g][s][q] - c[s][q] for s in seeds]
            entry[q] = {"diffs": [r(d) for d in diffs],
                        "floor": None if fl is None else r(fl),
                        "state": _state(diffs, fl)}
        out.append(entry)
    return out


def landing_pairs(rows: list) -> list:
    """The same cell and seed under two landings, A18_C's format."""
    _, treat = _index(rows)
    cells = {}
    for g, by_seed in treat.items():
        for s, x in by_seed.items():
            cells.setdefault(g[:6] + (s,), {})[g[6]] = x
    out = []
    for k in sorted(cells):
        by = cells[k]
        lands = [x for x in LANDINGS if x in by]
        for i in range(len(lands)):
            for j in range(i + 1, len(lands)):
                a, b = by[lands[i]], by[lands[j]]
                out.append({
                    "need": k[0], "park": k[1], "elasticity": k[2],
                    "authority": k[3], "bond_share": k[4], "pass_rate": k[5],
                    "seed": k[6], "pair": [lands[i], lands[j]],
                    "below_diff": int(a["below_close"] - b["below_close"]),
                    "circulating_diff": r(a["circulating_tail"]
                                          - b["circulating_tail"]),
                })
    return out


def landing_summary(lp: list) -> dict:
    per = {}
    for x in lp:
        slot = per.setdefault(str(x["elasticity"]), {
            "pairs": 0, "below_diff_0": 0, "below_diff_1": 0,
            "below_diff_2_or_more": 0, "below_diff_max": 0, "_c": []})
        d = abs(x["below_diff"])
        slot["pairs"] += 1
        slot["below_diff_0" if d == 0 else
             "below_diff_1" if d == 1 else "below_diff_2_or_more"] += 1
        slot["below_diff_max"] = max(slot["below_diff_max"], d)
        slot["_c"].append(abs(x["circulating_diff"]))
    for slot in per.values():
        slot["circulating_abs_diff_median"] = _median(slot.pop("_c"))
    return per


def crowding(rows: list, circ_state: dict) -> list:
    """Issuance on: the treated cell's cumulative issuance over its control's.
    Issuance off: what the pass-down alone brings back, as a share of what the
    issuing control brings back over the same cell with no issuance."""
    ctrl, treat = _index(rows)
    out = []
    for g in sorted(treat):
        need, park, e, auth = g[:4]
        c = ctrl.get(g[:4], {})
        seeds = sorted(s for s in treat[g] if s in c)
        entry = {"need": need, "park": park, "elasticity": e,
                 "authority": auth, "bond_share": g[4], "pass_rate": g[5],
                 "landing": g[6], "seeds": seeds}
        if auth == "endogenous":
            ratios = [treat[g][s]["issued_total"] / c[s]["issued_total"]
                      if c[s]["issued_total"] > 0 else None for s in seeds]
            base = [c[s]["issued_total"] for s in sorted(c)]
            rel = (float(np.std(base, ddof=1)) / float(np.mean(base))
                   if len(base) >= 2 and float(np.mean(base)) > 0 else None)
            entry["issuance_ratio"] = [None if x is None else r(x)
                                       for x in ratios]
            entry["issuance_floor_relative"] = None if rel is None else r(rel)
            entry["state"] = _crowd_state(ratios, rel, circ_state.get(g))
        else:
            ce = ctrl.get((need, park, e, "endogenous"), {})
            shares = []
            for s in seeds:
                if s not in ce:
                    shares.append(None)
                    continue
                den = ce[s]["circulating_tail"] - c[s]["circulating_tail"]
                num = treat[g][s]["circulating_tail"] - c[s]["circulating_tail"]
                shares.append(r(num / den) if den > 0 else None)
            entry["share_of_what_issuance_brings_back"] = shares
        out.append(entry)
    return out


def _crowd_state(ratios: list, rel, circ) -> str:
    if not ratios or rel is None or any(x is None for x in ratios):
        return "not read"
    band = FLOOR_MULTIPLE * rel
    if all(x < 1.0 - band for x in ratios):
        return "substitute"
    if all(abs(x - 1.0) <= band for x in ratios):
        if circ == "up":
            return "additive"
        if circ == "flat":
            return "unrelated"
        return "not read"
    if all(x > 1.0 + band for x in ratios):
        return "more issuance"
    return "split"


def money_and_debt(rows: list) -> list:
    """How the claims that keep circulation going arrive: as money (issuance)
    or as debt (what the bonds bring back). Issuance-on groups only."""
    ctrl, treat = _index(rows)
    out = []
    for g in sorted(treat):
        if g[3] != "endogenous":
            continue
        by = treat[g]
        c = ctrl.get(g[:4], {})
        debt_share = []
        for s in sorted(by):
            tot = by[s]["issued_total"] + by[s]["passed_total"]
            debt_share.append(by[s]["passed_total"] / tot if tot > 0 else None)
        out.append({
            "need": g[0], "park": g[1], "elasticity": g[2],
            "bond_share": g[4], "pass_rate": g[5], "landing": g[6],
            "issued_median": _median([by[s]["issued_total"] for s in by]),
            "passed_median": _median([by[s]["passed_total"] for s in by]),
            "control_issued_median": _median([c[s]["issued_total"] for s in c]),
            "debt_share_median": _median(debt_share),
        })
    return out


def trajectories(rows: list) -> list:
    _, treat = _index(rows)
    out = []
    for g in sorted(treat):
        by = treat[g]
        ratio = {}
        for q in HORIZONS:
            vals = [by[s]["bonds_at"][str(q)] / by[s]["circulating_at"][str(q)]
                    for s in sorted(by) if by[s]["circulating_at"][str(q)] > 0]
            ratio[str(q)] = _median(vals)
        out.append({"need": g[0], "park": g[1], "elasticity": g[2],
                    "authority": g[3], "bond_share": g[4], "pass_rate": g[5],
                    "landing": g[6], "bonds_over_circulating_median": ratio})
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a29_0() -> Criterion:
    probe = cell_config({"arm": "treatment", "need": NEEDS[0],
                         "park": PARK_RATES[0], "elasticity": ELASTICITIES[0],
                         "authority": AUTHORITIES[0], "seed": SEEDS[0],
                         "bond_share": 0.5, "pass_rate": 0.1,
                         "landing": "parkers"})
    control = cell_config({"arm": "control", "need": NEEDS[0],
                           "park": PARK_RATES[0], "elasticity": ELASTICITIES[0],
                           "authority": AUTHORITIES[0], "seed": SEEDS[0],
                           "bond_share": None, "pass_rate": 0.0,
                           "landing": None})
    got = set(_config_diff(probe).get("sovereign", {}))
    want = {f.name for f in dataclasses.fields(SovereignSpec)}
    in_control = "sovereign" in _config_diff(control)
    on_config = "sovereign" in {f.name for f in dataclasses.fields(NetworkConfig)}
    ok = got == want and not in_control and on_config
    return Criterion(
        "A29-0 the new fields reach the config block", "instrument", ok,
        "A treated probe with every SovereignSpec field off its default puts "
        "%s into the config block against the field set %s; a control cell "
        "puts in nothing: %s. NetworkConfig carries the field: %s. It is "
        "copied with dataclasses.replace, so there is no hand-written field "
        "list to extend." % (sorted(got), sorted(want), not in_control,
                             on_config))


def criterion_a29_1(g) -> Criterion:
    if not g:
        return Criterion(
            "A29-1 off by default reproduces the module before it",
            "instrument", False,
            "Not evaluated in this run: no gate section. State map: pass -> "
            "PASS; fail -> FAIL; records not regenerated -> not judged, and "
            "--run does not start.", evaluated=False)
    ip = g["in_process"]
    rec = "; ".join("%s: matches baseline %s, regenerated after the module "
                    "%s" % (x["record"], x.get("matches_baseline"),
                            x.get("regenerated_after_module"))
                    for x in g["records"])
    return Criterion(
        "A29-1 off by default reproduces the module before it", "instrument",
        g["verdict"] == "pass",
        "The module before SovereignSpec and the module now, run in one "
        "process on %d configurations (the library default, A18's exit arm "
        "with and without write-off, A18_E twice, A23, A18_F, and every "
        "control cell of this grid at seed %d): %d history fields compared "
        "bit for bit, %d configurations differ, the four new fields are None "
        "in every run: %s. Records against results/_baseline: %s. Verdict: "
        "%s. State map: pass -> PASS; fail -> FAIL; records not regenerated "
        "-> not judged, and --run does not start."
        % (len(ip["configs"]), SEEDS[0], ip["fields_compared"],
           len(ip["differ"]), not ip["new_fields_set"], rec, g["verdict"]))


def criterion_a29_2(rows: list) -> Criterion:
    t = [x for x in rows if x["arm"] == "treatment"]
    bad = [x for x in t if not x["books_close"]]
    return Criterion(
        "A29-2 both books close", "instrument", not bad,
        "In the graph, every round: the change in held plus parked equals "
        "issuance plus what was passed down. Outside it: the pool equals bonds "
        "bought less everything passed down, and never goes below zero. Bonds "
        "bought equal bond_share times the parked stock. All to %.0e of the "
        "opening stock, asserted in the round loop and read back here off the "
        "history: %d of %d treated cells close.%s"
        % (LEDGER_TOL, len(t) - len(bad), len(t),
           "" if not bad else " Open: " + "; ".join(
               _label(_gkey(x)) + " seed %d" % x["seed"] for x in bad[:10])))


def criterion_a29_3(rows: list) -> Criterion:
    t = [x for x in rows if x["arm"] == "treatment"]
    premise = [x for x in t if x["parked_close"] <= 0.0]
    moved = [x for x in t if x["parked_close"] > 0.0]
    dead = [x for x in moved if x["passed_total"] <= 0.0]
    parts = []
    for land in LANDINGS:
        xs = [x for x in moved if x["landing"] == land]
        if not xs:
            continue
        tot = sum(x["passed_total"] for x in xs)
        l2 = sum(x["passed_l2_total"] for x in xs)
        parts.append(
            "%s: passed down %.4f over %d cells, %.4f of it outside the "
            "financial layer, receivers median %s, pool at close median %s"
            % (land, tot, len(xs), l2 / tot if tot > 0 else 0.0,
               _median([x["receivers"] for x in xs]),
               _median([x["pool_close"] for x in xs])))
    return Criterion(
        "A29-3 the switch carries something (D28)", "instrument", not dead,
        "Wherever something was parked, something was passed down: %d of %d "
        "treated cells parked, %d of those passed nothing. Cells that parked "
        "nothing have no pool and so no object, and are premise: %d. %s."
        % (len(moved), len(t), len(dead), len(premise), "; ".join(parts)))


STATES_4: tuple[tuple[str, str], ...] = (
    ("up", "brought back"), ("flat", "unmoved"), ("down", "worse"),
    ("split", "seeds disagree, no reading"),
    ("one seed", "one seed, no reading"), ("no pair", "no control, no reading"))


def criterion_a29_4(pr: list) -> Criterion:
    parts = [
        "Printed, not judged. Each treated group against the same cell with "
        "pass_rate 0, seed by seed; floor = the control's dispersion across "
        "seeds, band = %.1f floors, and a count's floor is at least %.1f node. "
        "State map for circulation over the last %d rounds: %s. Support reads "
        "the same way; the count below the floor reads the other way, "
        "down = fewer nodes below." % (
            FLOOR_MULTIPLE, COUNT_FLOOR, TAIL,
            "; ".join("%s = %s" % s for s in STATES_4))]
    parts.append("All groups: circulation %s; support %s; below the floor %s."
                 % tuple(_tally(p[q]["state"] for p in pr)
                         for q, _ in READINGS))
    for land in LANDINGS:
        for auth in AUTHORITIES:
            sub = [p for p in pr if p["landing"] == land
                   and p["authority"] == auth]
            if sub:
                parts.append("%s, authority %s: circulation %s; support %s; "
                             "below %s." % ((land, auth) + tuple(
                                 _tally(p[q]["state"] for p in sub)
                                 for q, _ in READINGS)))
    worse = [p for p in pr if p["circulating_tail"]["state"] == "down"]
    listed = ["%s seeds %s diffs %s" % (_label(_gkey(p)), p["seeds"],
                                        p["circulating_tail"]["diffs"])
              for p in worse[:12]]
    if len(worse) > 12:
        listed.append("%d more in pairs" % (len(worse) - 12))
    parts.append("Worse: %s." % ("; ".join(listed) if listed else "none"))
    return Criterion("A29-4 does passing down bring circulation back",
                     "own_reading", True, " ".join(parts))


STATES_5: tuple[tuple[str, str], ...] = (
    ("matters", "the landing matters"),
    ("matters only at elasticity 0", "it matters only where the wage "
     "channel is dead"),
    ("matters only at elasticity 0.5", "not a registered branch, printed"),
    ("does not matter", "the landing does not matter"))


def criterion_a29_5(summary: dict) -> Criterion:
    m0 = summary.get("0.0", {}).get("below_diff_2_or_more", 0) > 0
    m5 = summary.get("0.5", {}).get("below_diff_2_or_more", 0) > 0
    state = ("matters" if m0 and m5 else
             "matters only at elasticity 0" if m0 else
             "matters only at elasticity 0.5" if m5 else "does not matter")
    rows = []
    for e in sorted(summary):
        s = summary[e]
        rows.append(
            "elasticity %s: %d pairs, below-count difference 0 in %d, 1 in %d, "
            "2 or more in %d, largest %d; circulating difference median %s"
            % (e, s["pairs"], s["below_diff_0"], s["below_diff_1"],
               s["below_diff_2_or_more"], s["below_diff_max"],
               s["circulating_abs_diff_median"]))
    return Criterion(
        "A29-5 does the landing matter", "own_reading", True,
        "Printed, not judged. The same cell and seed under two landings, "
        "A18_C's format; a difference of one node is inside A18_B6's jitter, "
        "so the reading is on two or more. %s. State: %s. State map: %s."
        % ("; ".join(rows), state, "; ".join("%s = %s" % s for s in STATES_5)))


STATES_6: tuple[tuple[str, str], ...] = (
    ("substitute", "pass-down and issuance are two exits from one gap"),
    ("additive", "each exit carries its own part"),
    ("unrelated", "the pass-down does not reach the gap"),
    ("more issuance", "not a registered branch, printed"),
    ("split", "seeds disagree, no reading"),
    ("not read", "a ratio, floor or circulation state is missing, no reading"))


def criterion_a29_6(cr: list, md: list) -> Criterion:
    on = [x for x in cr if x["authority"] == "endogenous"]
    off = [x for x in cr if x["authority"] == "none"]
    parts = ["Printed, not judged. Issuance on: cumulative issuance over the "
             "control's, per seed, against the control's relative dispersion "
             "times %.1f; with issuance unchanged, the circulation state from "
             "A29-4 separates additive from unrelated. State map: %s."
             % (FLOOR_MULTIPLE, "; ".join("%s = %s" % s for s in STATES_6))]
    parts.append("Issuance on, all groups: %s." % _tally(x["state"] for x in on))
    for land in LANDINGS:
        parts.append("%s: %s." % (land, _tally(
            x["state"] for x in on if x["landing"] == land)))
    for land in LANDINGS:
        shares = [s for x in off if x["landing"] == land
                  for s in x["share_of_what_issuance_brings_back"]]
        parts.append("Issuance off, %s: the pass-down alone brings back a "
                     "median %s of what issuance brings back." % (
                         land, _median(shares)))
    ds = [x["debt_share_median"] for x in md]
    parts.append("Money against debt, issuance on: the share of the claims "
                 "created that arrive as debt, median over groups %s, range "
                 "%s to %s." % (_median(ds), min(ds) if ds else None,
                                max(ds) if ds else None))
    return Criterion("A29-6 crowding out: the pass-down against issuance",
                     "own_reading", True, " ".join(parts))


def criterion_a29_7(rows: list, traj: list) -> Criterion:
    t = [x for x in rows if x["arm"] == "treatment"]
    monotone = all(all(x["bonds_at"][str(a)] <= x["bonds_at"][str(b)]
                       for a, b in zip(HORIZONS, HORIZONS[1:])) for x in t)
    last = str(HORIZONS[-1])
    parts = []
    for park in PARK_RATES:
        for bs, pr in KNOBS:
            v = [e["bonds_over_circulating_median"][last] for e in traj
                 if e["park"] == park and e["bond_share"] == bs
                 and e["pass_rate"] == pr
                 and e["bonds_over_circulating_median"][last] is not None]
            if v:
                parts.append("park %.3f knobs (%.2f, %.2f): %s to %s"
                             % (park, bs, pr, min(v), max(v)))
    return Criterion(
        "A29-7 the bond stock against the circulating stock", "bookkeeping",
        monotone,
        "Printed. No bond matures in this round, so the stock never falls: "
        "checked at every horizon in every treated cell, %s. Bonds over "
        "circulating at round %s, median over seeds, range across floors, "
        "landings, elasticities and authorities: %s. The full trajectories are in the "
        "trajectories section." % (monotone, last, "; ".join(parts)))


# ---------------------------------------------------------------------------
# Rule 19: the module before and the module now, and the two records.
# ---------------------------------------------------------------------------

def load_pre_module():
    name = "monetary_topology._network_pre_a29"
    loader = importlib.machinery.SourceFileLoader(name, str(PRE_MODULE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def transplant(obj, old):
    """Rebuild a config tree with the older module's classes, field by field,
    taking only the fields the older class has."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        cls = type(obj)
        target = getattr(old, cls.__name__, None)
        if (cls.__module__ == _NET.__name__ and target is not None
                and target is not cls):
            return target(**{f.name: transplant(getattr(obj, f.name), old)
                             for f in dataclasses.fields(target) if f.init})
        return obj
    if isinstance(obj, tuple):
        return tuple(transplant(x, old) for x in obj)
    if isinstance(obj, list):
        return [transplant(x, old) for x in obj]
    if isinstance(obj, dict):
        return {k: transplant(v, old) for k, v in obj.items()}
    return obj


def _same(a, b) -> bool:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        a, b = np.asarray(a), np.asarray(b)
        return (a.shape == b.shape and a.dtype == b.dtype
                and a.tobytes() == b.tobytes())
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    return type(a) is type(b) and repr(a) == repr(b)


def gate_configs() -> list:
    ws = WriteOffSpec
    out = [("library default", NetworkConfig()),
           ("A18 exit, no write-off",
            config_for("exit", ws(), "endogenous", 0.20, 0)),
           ("A18 exit, write-off with refill",
            config_for("exit", _A18.WRITEOFF_REFILL, "endogenous", 0.05, 1))]
    c = config_for("drawdown", ws(), "endogenous", 0.50, 0, resupply_rate=2.0)
    for target in ("financial", "all"):
        out.append(("A18_E park 0.20, %s parks" % target, dataclasses.replace(
            c, resupply=ResupplySpec(rate=2.0, funding="issuance"),
            park=ParkSpec(rate=0.20, target=target))))
    c = config_for("drawdown", ws(), "endogenous", 0.50, 1, resupply_rate=2.0)
    out.append(("A23 two-way park", dataclasses.replace(
        c, resupply=ResupplySpec(rate=2.0, funding="issuance"),
        park=ParkSpec(rate=0.20, target="financial", return_rate=0.5))))
    c = config_for("drawdown", ws(), "endogenous", 0.50, 2, resupply_rate=2.0)
    out.append(("A18_F carry, creditors fund", dataclasses.replace(
        c, resupply=ResupplySpec(rate=2.0, funding="creditors"),
        park=ParkSpec(rate=0.002, target="financial"))))
    for k in cell_keys(seeds=SEEDS[:1]):
        if k["arm"] == "control":
            out.append(("A29 control " + _label(
                (k["need"], k["park"], k["elasticity"], k["authority"])),
                cell_config(k)))
    return out


def _first_differences(live: Path, base: Path, limit: int = 5) -> list:
    a = json.loads(live.read_text(encoding="utf-8"))
    b = json.loads(base.read_text(encoding="utf-8"))
    notes = []
    if set(a) != set(b):
        notes.append("top-level keys: only live %s, only baseline %s"
                     % (sorted(set(a) - set(b)), sorted(set(b) - set(a))))
    for key in sorted(set(a) & set(b)):
        x, y = a[key], b[key]
        if x == y:
            continue
        if isinstance(x, list) and isinstance(y, list):
            notes.append("%s: %d rows live, %d baseline" % (key, len(x), len(y)))
            shown = 0
            for i, (u, v) in enumerate(zip(x, y)):
                if u != v:
                    if isinstance(u, dict) and isinstance(v, dict):
                        u = {k: (u.get(k), v.get(k)) for k in set(u) | set(v)
                             if u.get(k) != v.get(k)}
                    notes.append("  %s[%d] differs: %s" % (key, i, u))
                    shown += 1
                    if shown >= limit:
                        break
        else:
            notes.append("%s differs" % key)
    return notes


def gate() -> dict:
    old = load_pre_module()
    names, differ, new_set, labels = None, [], [], []
    for label, cfg in gate_configs():
        if cfg.sovereign != SovereignSpec():
            raise RuntimeError("a gate configuration has the switch on: %s"
                               % label)
        t0 = time.perf_counter()
        hn = Network(cfg).run()
        ho = old.Network(transplant(cfg, old)).run()
        dt = time.perf_counter() - t0
        names = [f.name for f in dataclasses.fields(ho)]
        bad = [n for n in names if not _same(getattr(ho, n), getattr(hn, n))]
        extra = [k for k in NEW_FIELDS if getattr(hn, k) is not None]
        labels.append(label)
        if bad:
            differ.append({"config": label, "fields": bad})
        if extra:
            new_set.append({"config": label, "fields": extra})
        print("   %-58s %s%s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "" if not extra else ", new fields set %s" % extra, dt))
    module_mtime = MODULE.stat().st_mtime
    records = []
    for rel, cmd in GATE_RECORDS:
        live, base = RESULTS / rel, BASELINE / rel
        entry = {"record": rel, "regenerate_with": cmd}
        if not live.exists() or not base.exists():
            entry["state"] = "missing"
            print("\n   %s: missing (%s)" % (rel, live if not live.exists()
                                             else base))
        else:
            match = _file_sha(live) == _file_sha(base)
            fresh = live.stat().st_mtime > module_mtime
            entry["matches_baseline"] = match
            entry["regenerated_after_module"] = fresh
            entry["state"] = ("pass" if match and fresh else
                              "fail" if fresh else "not regenerated")
            print("\n   %s: matches baseline %s, regenerated after the module "
                  "%s" % (rel, match, fresh))
            if not fresh:
                print("     regenerate with:  %s" % cmd)
            if fresh and not match:
                for line in _first_differences(live, base):
                    print("     " + line)
        records.append(entry)
    in_process_ok = not differ and not new_set
    if not in_process_ok or any(e["state"] == "fail" for e in records):
        verdict = "fail"
    elif all(e["state"] == "pass" for e in records):
        verdict = "pass"
    else:
        verdict = "records not regenerated"
    if in_process_ok and any(e["state"] == "fail" for e in records):
        print("\n   The in-process comparison is identical, so a record that "
              "differs was already off before this module change; its "
              "baseline is older than the code that last touched it.")
    return {
        "module_sha": _module_sha(MODULE),
        "pre_module_sha": _module_sha(PRE_MODULE),
        "in_process": {"configs": labels, "fields_compared": len(names or []),
                       "differ": differ, "new_fields_set": new_set},
        "records": records,
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
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module"


# ---------------------------------------------------------------------------
# Timing (D38): measured, printed, never written.
# ---------------------------------------------------------------------------

def time_cells(repeats: int = 3, workers: int = 1) -> None:
    probe = {"need": NEEDS[1], "park": PARK_RATES[1], "elasticity": 0.5,
             "authority": "endogenous", "seed": SEEDS[0]}
    keys = [{**probe, "arm": "control", "bond_share": None, "pass_rate": 0.0,
             "landing": None}]
    keys += [{**probe, "arm": "treatment", "bond_share": 1.0, "pass_rate": 0.1,
              "landing": land} for land in LANDINGS]
    one_cell(keys[0])  # warm-up, not timed
    per = {}
    for k in keys:
        ts = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            one_cell(k)
            ts.append(time.perf_counter() - t0)
        per[k["landing"] or "control"] = float(np.mean(ts))
    for name, s in per.items():
        print("   %-12s %.3f s per cell (mean of %d)" % (name, s, repeats))
    ctrl = per["control"]
    treat = float(np.mean([per[x] for x in LANDINGS]))
    # The estimate divides by the workers this machine can actually run.
    eff = max(1, min(workers, os.cpu_count() or 1))
    for n in (3, len(SEEDS)):
        keys_n = cell_keys(seeds=SEEDS[:n])
        c = sum(1 for k in keys_n if k["arm"] == "control")
        t = len(keys_n) - c
        serial = c * ctrl + t * treat
        print("   %d seeds: %d cells (%d control, %d treated), %.0f s serial, "
              "about %.0f s on %d workers" % (n, len(keys_n), c, t, serial,
                                              serial / eff, eff))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe = cell_config({"arm": "control", "need": NEEDS[0],
                         "park": PARK_RATES[0], "elasticity": ELASTICITIES[0],
                         "authority": AUTHORITIES[0], "seed": SEEDS[0],
                         "bond_share": None, "pass_rate": 0.0, "landing": None})
    cfg = _config_diff(probe)
    cfg.pop("seed", None)
    for sub, keys in (("spec", ("seed",)), ("subsistence", ("need",)),
                      ("park", ("rate",)), ("wages", ("elasticity",)),
                      ("authority", ("rule",))):
        if sub in cfg:
            for k in keys:
                cfg[sub].pop(k, None)
            if not cfg[sub]:
                cfg.pop(sub)
    return {
        "carrier": "A18's config_for: drawdown, no write-off, no rescue",
        "rounds": ROUNDS,
        "park_target": TARGET,
        "grid": {"need_multiples": list(NEEDS), "park_rates": list(PARK_RATES),
                 "bond_share_and_pass_rate": [list(k) for k in KNOBS],
                 "landings": list(LANDINGS),
                 "elasticities": list(ELASTICITIES),
                 "authorities": list(AUTHORITIES), "seeds": list(SEEDS)},
        "tail": TAIL,
        "horizons": list(HORIZONS),
        "floor_multiple": FLOOR_MULTIPLE,
        "count_floor": COUNT_FLOOR,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one step's payload into the station record. No wall-clock content:
    git records when a file was committed."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A29"
    doc["diagnostic_only"] = True
    doc["diagnostic_reason"] = ("the station is not closed: first round, the "
                                "leg that passes down, bonds never mature")
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def analyse(rows: list, gate_section) -> tuple:
    pr = pairs(rows)
    circ_state = {_gkey(p): p["circulating_tail"]["state"] for p in pr}
    lp = landing_pairs(rows)
    ls = landing_summary(lp)
    cr = crowding(rows, circ_state)
    md = money_and_debt(rows)
    tr = trajectories(rows)
    crits = [criterion_a29_0(), criterion_a29_1(gate_section),
             criterion_a29_2(rows), criterion_a29_3(rows),
             criterion_a29_4(pr), criterion_a29_5(ls),
             criterion_a29_6(cr, md), criterion_a29_7(rows, tr)]
    sections = {
        "criteria": [c.as_dict() for c in crits],
        "pairs": pr,
        "landing_summary": ls,
        "landing_pairs_two_or_more": [x for x in lp
                                      if abs(x["below_diff"]) >= 2],
        "crowding": cr,
        "money_and_debt": md,
        "trajectories": tr,
        "rows": rows,
    }
    return crits, sections


def _print_criteria(crits: list) -> None:
    for c in crits:
        tag = ("not evaluated" if not c.evaluated else
               "PASS" if c.passed else "FAIL")
        print("\n  [%s] %s  (%s)" % (tag, c.name, c.kind))
        print("        %s" % c.detail)


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--plan", action="store_true")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=_default_workers())
    ap.add_argument("--smoke", action="store_true",
                    help="with --run: the reduced grid, nothing written")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-20s %s" % (k, v))
        keys = cell_keys(seeds=SEEDS[:args.seeds])
        print("  %-20s %d at %d seeds" % ("cells", len(keys), args.seeds))
        return 0

    if args.gate:
        print("stage A29, rule 19: the module before SovereignSpec against the "
              "module now\n")
        g = gate()
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A29, D38: seconds per cell, measured on this machine\n")
        time_cells(workers=args.workers)
        return 0

    gate_section = _gate_section()
    if args.smoke:
        keys = cell_keys(**SMOKE)
        print("stage A29, smoke: %d cells, nothing written\n" % len(keys))
    else:
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A29: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        keys = cell_keys(seeds=seeds)
        print("stage A29: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(seeds), args.workers, why))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections = analyse(rows, gate_section)
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
