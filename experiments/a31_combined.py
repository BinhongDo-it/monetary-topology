"""A31, third round: two positions drawn on at once, each in its own shape.

The first round moved the position and read no difference. The second round
moved the shape inside one position and read no difference either, and it found
why: this rule is a controller whose setpoint is the Layer 2 inflow, which is
the quantity the subsistence floor is read against, so a shape difference is
absorbed rather than mixed away. Collected totals differing by up to 55.7% left
the count below the floor at the same integer in all 450 seed comparisons.

**What is left, and it is one axis.** ``position`` spans which set and ``base``
spans which shape, and neither covers the ratio in which two sets are drawn on
at once. The first round sampled that ratio at three points, 0, about 0.75 and
1 of the take landing on the financial layer, and read the same count at all
three. ``WithdrawSpec.mix`` fills the ratio in and lets the two sets carry
different shapes while it does.

**The grid is small on purpose, and it is placed where the instrument moves.**
The second round's own numbers say where that is: over 1,350 two-sided
cell-seeds read against the one-sided twin, the count below the floor differed
by 0 in 1,287, by 1 in 45, and by 75 in 18, and all 18 sat on one carrier, the
floor of 0.20 on the recycled leak at wage elasticity 0.5, seeds 1 and 4. A
grid that cannot move the count says nothing when it reads no movement, so this
one runs at that elasticity, keeps the other four floors and the other two
strains as controls, and drops the shocks: every reading here is on the
unshocked twins, which is where the block moved.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a31_combined.py --plan
    python experiments/a31_combined.py --gate
    python experiments/a31_combined.py --time
    python experiments/a31_combined.py --run --smoke
    python experiments/a31_combined.py --run --workers 8
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
    Network, NetworkConfig, NetworkHistory, WithdrawSpec, WITHDRAW_FIELDS)

RECORD = RESULTS / "a31_combined.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
#: The module as it stood before ``mix`` existed, which is the second round's.
PRE_MODULE = SRC / "network.py.expired_20260912_pre_A31C"
#: The second round's record, whose rows this module has to reproduce.
SHAPE_RECORD = RESULTS / "a31_shape.json"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A29 = _load(ROOT / "experiments" / "a29_sovereign.py", "_a29_for_comb")
_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_comb")
_A31 = _load(ROOT / "experiments" / "a31_withdrawal.py", "_a31_for_comb")
_A31S = _load(ROOT / "experiments" / "a31_shape.py", "_a31s_for_comb")

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
LEDGER_TOL = _A30.LEDGER_TOL
BLOCK = _A30.BLOCK
NEEDS = _A30.NEEDS
STRESSES = _A30.STRESSES
STRESS_SPECS = _A30.STRESS_SPECS
flip = _A30.flip

AUTHORITY = _A31.AUTHORITY
drive = _A31.drive
block_class = _A31.block_class
BLOCK_CLASSES = _A31.BLOCK_CLASSES
CLOSING = _A31.CLOSING
SPREAD_LINE = _A31S.SPREAD_LINE
ROW_FIELDS = _A31S.ROW_FIELDS

#: Fixed, for the reason in the module docstring.
GAIN = 1.0
#: The only wage elasticity at which this carrier's block has ever moved.
ELASTICITY = 0.5

#: Every rule, by the label the tables key on. ``one-sided`` leaves the switch
#: off and is the reference every other row is read against. Three singles
#: reproduce the axis the first round read; five mixes fill the ratio in; the
#: last one names two positions that overlap, so it is also the check that the
#: cap on the summed take holds.
SPECS: dict[str, dict] = {
    "one-sided": {},
    "financial": {"position": "financial", "base": "holdings"},
    "production": {"position": "production", "base": "holdings"},
    "proportional": {"position": "proportional", "base": "holdings"},
    "fin thr .50 + prod eq .50": {
        "mix": (("financial", "threshold", 0.50),
                ("production", "equal", 0.50))},
    "fin eq .50 + prod thr .50": {
        "mix": (("financial", "equal", 0.50),
                ("production", "threshold", 0.50))},
    "fin hld .50 + prod hld .50": {
        "mix": (("financial", "holdings", 0.50),
                ("production", "holdings", 0.50))},
    "fin thr .25 + prod eq .75": {
        "mix": (("financial", "threshold", 0.25),
                ("production", "equal", 0.75))},
    "fin thr .75 + prod eq .25": {
        "mix": (("financial", "threshold", 0.75),
                ("production", "equal", 0.25))},
    "prop hld .50 + fin hld .50": {
        "mix": (("proportional", "holdings", 0.50),
                ("financial", "holdings", 0.50))},
}
RULES: tuple[str, ...] = tuple(SPECS)
MIXES: tuple[str, ...] = tuple(k for k, v in SPECS.items() if v.get("mix"))
SINGLES: tuple[str, ...] = tuple(k for k, v in SPECS.items()
                                 if v.get("position"))
#: The share of the amount each mix aims at the production side, which is what
#: the realised Layer 2 share is read against.
PRODUCTION_WEIGHT: dict[str, float] = {
    label: sum(share for where, _, share in SPECS[label]["mix"]
               if where == "production")
    for label in MIXES}

SMOKE = {"needs": (0.20,), "stresses": ("leak_recycled",), "seeds": SEEDS[:2]}

KEYS: tuple[str, ...] = ("need", "stress", "elasticity", "rule", "gain",
                         "shock", "size", "seed")


def spec_for(label: str) -> WithdrawSpec | None:
    kw = SPECS[label]
    if not kw:
        return None
    return WithdrawSpec(gain=GAIN, **kw)


# ---------------------------------------------------------------------------
# The loaded readers key a cell by its rule, and here a rule is a label.
# ---------------------------------------------------------------------------

def _carrier(x: dict) -> tuple:
    return (x["need"], x["stress"], x["elasticity"])


def _rule(x: dict) -> tuple:
    return ("none", None) if x["rule"] == "one-sided" else (x["rule"], x["gain"])


_A31._rule = _rule


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            RULES.index(x["rule"]), x["seed"])


def _ref_key(x: dict) -> tuple:
    return tuple(x[k] for k in KEYS)


# ---------------------------------------------------------------------------
# The grid. No shocks: every reading here is on the unshocked twins.
# ---------------------------------------------------------------------------

def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              rules=RULES) -> list:
    return [{"need": need, "stress": stress, "elasticity": ELASTICITY,
             "rule": rule, "gain": None if rule == "one-sided" else GAIN,
             "shock": "none", "size": 0.0, "seed": seed}
            for need in needs for stress in stresses for rule in rules
            for seed in seeds]


def cell_config(key: dict) -> NetworkConfig:
    cfg = _A30.cell_config({"need": key["need"], "stress": key["stress"],
                            "elasticity": key["elasticity"],
                            "authority": AUTHORITY, "seed": key["seed"]})
    w = spec_for(key["rule"])
    return cfg if w is None else dataclasses.replace(cfg, withdraw=w)


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
        "holdings_min_close": _num(float(net.holdings.min())),
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
# Readings.
# ---------------------------------------------------------------------------

RULE_STATES: tuple[tuple[str, str], ...] = (
    ("the ratio decides", "at a fixed carrier and seed the rules do not all "
     "leave the same count below the floor, and the spread of what they "
     "collected is at or under %.4f" % SPREAD_LINE),
    ("the setpoint decides", "they all leave the same count, so on this "
     "carrier neither the ratio nor the shape settles it"),
    ("differs, and so do the totals: not adjudicated", "the counts differ and "
     "the collected totals differ by more than %.4f, so the aggregate channel "
     "is open and this carrier is read neither way" % SPREAD_LINE))


def rule_pairs(cells: list) -> list:
    """Every rule against the one-sided twin on the same carrier and seed, and
    then the rules against each other, seed by seed.

    Seed by seed is the comparison that means something here: this carrier is
    bistable across seeds at the floor it was built on, so a reading taken
    across seeds reads split wherever the carrier itself is bistable and says
    nothing about the rule.
    """
    by_cell = {}
    for c in cells:
        by_cell.setdefault(_carrier(c) + (c["seed"],), {})[c["rule"]] = c
    out = []
    carriers = sorted({k[:3] for k in by_cell},
                      key=lambda k: (k[0], STRESSES.index(k[1]), k[2]))
    for carrier in carriers:
        seeds = sorted(k[3] for k in by_cell if k[:3] == carrier)
        rules = {}
        per_seed = []
        for seed in seeds:
            here = by_cell[carrier + (seed,)]
            ref = here.get("one-sided")
            if ref is None:
                continue
            diffs = {}
            for rule, c in here.items():
                if rule == "one-sided":
                    continue
                diff = int(c["below_close"] - ref["below_close"])
                diffs[rule] = diff
                e = rules.setdefault(rule, {
                    "seeds": [], "below_diff": [], "class": [],
                    "withdrawn": [], "uncollected_share": [],
                    "withdrawn_l2_share": [], "l2_over_target_tail": [],
                    "circulating_ratio": [], "holdings_min": []})
                asked = ((c["withdrawn_total"] or 0.0)
                         + (c["withdrawn_unmet_total"] or 0.0))
                e["seeds"].append(seed)
                e["below_diff"].append(diff)
                e["class"].append(block_class(diff))
                e["withdrawn"].append(c["withdrawn_total"])
                e["uncollected_share"].append(
                    _num((c["withdrawn_unmet_total"] or 0.0) / asked)
                    if asked > 0 else None)
                e["withdrawn_l2_share"].append(c["withdrawn_l2_share"])
                e["l2_over_target_tail"].append(c["l2_over_target_tail"])
                e["circulating_ratio"].append(
                    _num(c["circulating_tail"] / ref["circulating_tail"])
                    if ref["circulating_tail"] else None)
                e["holdings_min"].append(c["holdings_min_close"])
            per_seed.append({
                "seed": seed, "one_sided_below": int(ref["below_close"]),
                "below_diff": diffs,
                "same": len(set(diffs.values())) == 1 if diffs else None,
                "singles_and_mixes_agree": (
                    {diffs[r] for r in SINGLES if r in diffs}
                    == {diffs[r] for r in MIXES if r in diffs}
                    if diffs else None)})
        summary = {}
        for rule, e in rules.items():
            summary[rule] = {
                "seeds": e["seeds"], "below_diff": e["below_diff"],
                "class": e["class"],
                "state": (e["class"][0] if len(set(e["class"])) == 1
                          else "split"),
                "withdrawn_median": _median(e["withdrawn"]),
                "uncollected_share_median": _median(e["uncollected_share"]),
                "withdrawn_l2_share_median": _median(e["withdrawn_l2_share"]),
                "l2_over_target_tail_median": _median(e["l2_over_target_tail"]),
                "circulating_ratio_median": _median(e["circulating_ratio"]),
                "holdings_min_worst": (min(x for x in e["holdings_min"]
                                           if x is not None)
                                       if any(x is not None
                                              for x in e["holdings_min"])
                                       else None),
            }
        taken = [s["withdrawn_median"] for s in summary.values()
                 if s["withdrawn_median"]]
        spread = ((max(taken) - min(taken)) / min(taken)
                  if len(taken) == len(summary) and taken and min(taken) > 0
                  else None)
        differing = [x for x in per_seed if x["same"] is False]
        if not per_seed:
            reading = "no seeds"
        elif not differing:
            reading = "the setpoint decides"
        elif spread is None or spread > SPREAD_LINE:
            reading = "differs, and so do the totals: not adjudicated"
        else:
            reading = "the ratio decides"
        out.append({
            "need": carrier[0], "stress": carrier[1],
            "elasticity": carrier[2],
            "collected_spread": _num(spread),
            "one_sided_below": [x["one_sided_below"] for x in per_seed],
            "rules": summary,
            "per_seed": per_seed,
            "seeds_compared": len(per_seed),
            "seeds_differing": len(differing),
            "reading": reading,
        })
    return out


def _two_sided(cells: list) -> list:
    return [c for c in cells if c["rule"] != "one-sided"]


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a31_15(g) -> Criterion:
    name = "A31-15 an empty mix reproduces the second round, bit for bit"
    state_map = (
        "State map: the module before this field identical to the module now on "
        "the switch-off and single-position configurations, the driver "
        "identical to Network.run(), and the second round's recorded rows "
        "reproduced -> PASS; anything else -> FAIL; no gate section -> not "
        "judged, and --run does not start.")
    if not g:
        return Criterion(name, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + state_map, evaluated=False)
    rows = g.get("shape_rows", {})
    return Criterion(
        name, "instrument", g["verdict"] == "pass",
        "The module before ``mix`` existed and the module now ran %d "
        "configurations in one process, the switch-off set and the second "
        "round's own single-position cells: %d history fields and the closing "
        "state compared bit for bit, %d differ, and the generators end in the "
        "same place. The driver with no shock against Network.run(): %d "
        "differ. The second round's recorded rows recomputed on this module: "
        "%d rows, %d fields each, %d differ.%s %s"
        % (len(g["configs"]), g["fields_compared"], len(g["differ"]),
           len(g["driver_differ"]), rows.get("rows", 0),
           rows.get("fields_compared", 0), len(rows.get("differ", [])),
           "" if not g["differ"] else " First: %s" % g["differ"][:3],
           state_map))


def criterion_a31_16(cells: list, rp: list) -> Criterion:
    books = sum(1 for c in cells if c["books_close"])
    negative = [(c["rule"], c["need"], c["stress"], c["seed"],
                 c["holdings_min_close"])
                for c in cells
                if c["holdings_min_close"] is not None
                and c["holdings_min_close"] < -LEDGER_TOL]
    lines = []
    for label in MIXES:
        xs = [c for c in _two_sided(cells) if c["rule"] == label]
        share = [c["withdrawn_l2_share"] for c in xs
                 if c["withdrawn_l2_share"] is not None]
        unmet = [((c["withdrawn_unmet_total"] or 0.0)
                  / ((c["withdrawn_total"] or 0.0)
                     + (c["withdrawn_unmet_total"] or 0.0)))
                 for c in xs
                 if ((c["withdrawn_total"] or 0.0)
                     + (c["withdrawn_unmet_total"] or 0.0)) > 0]
        lines.append("%s: aimed at the production side %.2f, Layer 2 share of "
                     "what was taken median %s, %s; uncollected over asked "
                     "median %s"
                     % (label, PRODUCTION_WEIGHT[label], _median(share),
                        _range(share), _median(unmet)))
    ok = books == len(cells) and not negative and bool(_two_sided(cells))
    return Criterion(
        "A31-16 the books close, the summed take is capped, and the weights "
        "land where they were aimed", "instrument", ok,
        "Asserted every round in the loop: what leaves held plus parked equals "
        "what was taken, and what the cap leaves uncollected is recorded and "
        "not carried. Read back here: %d of %d cells close their claim total "
        "against held plus parked to %.0e of the opening stock. **Two "
        "positions can overlap**, since ``proportional`` contains both layers, "
        "so the summed take is capped at the account a second time; the "
        "smallest account at the close over every cell is the check, and %d "
        "cells end with an account below zero%s. Where each mix aimed and "
        "where it landed: %s. The realised Layer 2 share sits under the aimed "
        "weight exactly when the production side's shape cannot collect its "
        "part, which is the uncollected figure beside it. State map: every "
        "cell closing and no account below zero -> PASS; anything else -> "
        "FAIL, and nothing after this reads."
        % (books, len(cells), LEDGER_TOL, len(negative),
           "" if not negative else " %s" % negative[:5], "; ".join(lines)))


def criterion_a31_17(rp: list, cells: list) -> Criterion:
    tally = _tally(e["reading"] for e in rp)
    compared = sum(e["seeds_compared"] for e in rp)
    differing = sum(e["seeds_differing"] for e in rp)
    disagree = sum(1 for e in rp for x in e["per_seed"]
                   if x["singles_and_mixes_agree"] is False)
    diffs = [v for e in rp for s in e["rules"].values()
             for v in s["below_diff"]]
    spectrum = {}
    for v in diffs:
        spectrum[v] = spectrum.get(v, 0) + 1
    moved = sum(n for v, n in spectrum.items() if abs(v) >= BLOCK)
    lines = []
    for e in rp:
        if e["seeds_differing"]:
            lines.append("need %.2f %s: %d of %d seeds differ, spread %s"
                         % (e["need"], e["stress"], e["seeds_differing"],
                            e["seeds_compared"], e["collected_spread"]))
    return Criterion(
        "A31-17 two positions at once, in two shapes: who is below the floor",
        "own_reading", True,
        "Printed, not judged. Every rule against the one-sided twin on the "
        "same carrier and seed, at the close. **The instrument's own range "
        "comes first, because a grid that cannot move the count says nothing "
        "when it reads no movement**: over %d two-sided cell-seeds the count "
        "below the floor differs from the one-sided twin by %s, so a block of "
        "%d or more moves in %d of them. Against that: %d comparisons of all "
        "%d two-sided rules at a fixed carrier and seed, %d leaving a "
        "different count; and %d of those comparisons have the single-position "
        "rules and the mixes reaching different counts. Block states: %s. "
        "Carrier states: %s. Carriers by reading: %s. Where they differ: %s."
        % (len(diffs), dict(sorted(spectrum.items())), BLOCK, moved,
           compared, len(RULES) - 1, differing, disagree,
           "; ".join("%s = %s" % x for x in BLOCK_CLASSES),
           "; ".join("%s = %s" % x for x in RULE_STATES),
           tally, "; ".join(lines) if lines else "nowhere"))


def criterion_a31_18(rp: list, cells: list) -> Criterion:
    one = [c["l2_over_target_tail"] for c in cells
           if c["rule"] == "one-sided"]
    parts = []
    for label in RULES[1:]:
        v = [c["l2_over_target_tail"] for c in cells if c["rule"] == label]
        parts.append("%s median %s" % (label, _median(v)))
    return Criterion(
        "A31-18 the setpoint holds whichever ratio takes it", "own_reading",
        True,
        "Printed, not judged. The Layer 2 inflow over the rule's own target, "
        "averaged over the last %d rounds. One-sided reference: median %s, %s. "
        "By rule: %s. The second round read -0.0001 on the same quantity under "
        "all three shapes. Reading: every rule pinning says the pinning is a "
        "property of the setpoint and not of the ratio or the shape that holds "
        "it; a rule failing to pin says it cannot collect what the rule asks "
        "for, which A31-17 reads through the collected totals."
        % (TAIL, _median(one), _range(one), "; ".join(parts)))


def criterion_a31_19(cells: list, rp: list) -> Criterion:
    parts = []
    for label in RULES[1:]:
        xs = [c for c in cells if c["rule"] == label]
        parts.append(
            "%s: Layer 2 share median %s; collected median %s; rounds "
            "withdrawing median %s of %d"
            % (label, _median([c["withdrawn_l2_share"] for c in xs]),
               _median([c["withdrawn_total"] for c in xs]),
               _median([c["rounds_withdrawing"] for c in xs]), ROUNDS))
    return Criterion(
        "A31-19 where it came from, by rule", "bookkeeping", True,
        "Printed. %s. Carriers: %d, over %d two-sided cells."
        % ("; ".join(parts), len(rp), len(_two_sided(cells))))


# ---------------------------------------------------------------------------
# Printing.
# ---------------------------------------------------------------------------

def print_rules(rp: list) -> None:
    print("\n  A31-17 and A31-18, every rule against the one-sided twin, "
          "carrier by carrier. below_diff is by seed.")
    for e in rp:
        print("\n  need %.2f  %s  e %.1f   one-sided below the floor %s   "
              "spread %s   %s"
              % (e["need"], e["stress"], e["elasticity"], e["one_sided_below"],
                 e["collected_spread"], e["reading"]))
        print("    %-28s %-18s %9s %8s %9s %9s"
              % ("rule", "below_diff", "collected", "l2 share", "uncoll.",
                 "tail dev"))
        for label in RULES[1:]:
            s = e["rules"].get(label)
            if s is None:
                continue
            print("    %-28s %-18s %9s %8s %9s %9s"
                  % (label, s["below_diff"], s["withdrawn_median"],
                     s["withdrawn_l2_share_median"],
                     s["uncollected_share_median"],
                     s["l2_over_target_tail_median"]))


# ---------------------------------------------------------------------------
# Rule 19.
# ---------------------------------------------------------------------------

def load_pre_module():
    name = "monetary_topology._network_pre_a31c"
    loader = importlib.machinery.SourceFileLoader(name, str(PRE_MODULE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def gate_configs(needs=NEEDS, stresses=STRESSES, full: bool = True) -> list:
    """The second round's off-switch set, plus its single-position cells with
    the mix empty. The single-position half is what this field could break."""
    out = list(_A31S.gate_configs(needs=needs, elasticities=(ELASTICITY,),
                                 full=full))
    need = needs[-1]
    for stress in stresses:
        for label in SINGLES:
            out.append((
                "A31 single %s, need %.2f, %s" % (label, need, stress),
                cell_config({"need": need, "stress": stress,
                             "elasticity": ELASTICITY, "rule": label,
                             "gain": GAIN, "shock": "none", "size": 0.0,
                             "seed": SEEDS[0]})))
    return out


def shape_rows(needs=NEEDS, seeds=(SEEDS[0],), workers: int = 1) -> dict:
    """The second round's recorded rows, recomputed on this module.

    Its grid is in its own script, so those keys are replayed through its
    ``one_cell`` rather than this one: what is being checked is that an empty
    mix leaves the single-position rule exactly where it was.
    """
    if not SHAPE_RECORD.exists():
        return {"record": SHAPE_RECORD.name, "state": "missing", "rows": 0,
                "fields_compared": 0, "differ": []}
    doc = json.loads(SHAPE_RECORD.read_text(encoding="utf-8"))
    ref = [x for x in doc.get("sections", {}).get("run", {}).get("rows", [])
           if x["seed"] in seeds and x["need"] in needs]
    if not ref:
        return {"record": SHAPE_RECORD.name, "state": "no matching rows",
                "rows": 0, "fields_compared": 0, "differ": []}
    keys = [{k: x[k] for k in _A31S.KEYS} for x in ref]
    # Both rounds patch the loaded reader's idea of what a rule is, and this
    # call reads the other round's keys, so the patch is handed back for the
    # length of it. Without this the reader looks for this round's key in the
    # other round's rows and raises.
    mine, _A31._rule = _A31._rule, _A31S._rule
    try:
        got = _A31.read_cells(_A31S.run_cells(keys, workers), {}, {})
    finally:
        _A31._rule = mine
    idx = {_A31S._ref_key(c) + (c["base"],): c for c in got}
    differ = []
    for x in ref:
        c = idx.get(_A31S._ref_key(x) + (x["base"],))
        if c is None:
            differ.append({"cell": _A31S._ref_key(x), "fields": ["not recomputed"]})
            continue
        bad = [f for f in ROW_FIELDS if f in x and _fmt(c.get(f)) != x[f]]
        if bad:
            differ.append({"cell": _A31S._ref_key(x), "fields": bad})
    return {"record": SHAPE_RECORD.name, "state": "read", "rows": len(ref),
            "fields_compared": len(ROW_FIELDS), "differ": differ}


def gate(configs: list, row_needs=NEEDS, row_seeds=(SEEDS[0],),
         workers: int = 1) -> dict:
    old = load_pre_module()
    names = [f.name for f in dataclasses.fields(NetworkHistory)]
    differ, driver_differ, labels = [], [], []
    for label, cfg in configs:
        t0 = time.perf_counter()
        if cfg.withdraw.mix:
            raise RuntimeError("a gate configuration has a mix set: %s" % label)
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
        print("   %-50s %s, driver %s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "identical" if not dbad else "DIFFERS in %s" % dbad,
            time.perf_counter() - t0))
    t0 = time.perf_counter()
    rows = shape_rows(needs=row_needs, seeds=row_seeds, workers=workers)
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
        "shape_rows": rows,
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


def time_cells(repeats: int = 3, workers: int = 1) -> None:
    sample = [{"need": 0.20, "stress": s, "elasticity": ELASTICITY,
               "rule": r, "gain": GAIN, "shock": "none", "size": 0.0,
               "seed": SEEDS[0]}
              for s in STRESSES for r in (SINGLES[0], MIXES[0])]
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


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    cfg = _config_diff(cell_config({"need": NEEDS[0], "stress": "healthy",
                                    "elasticity": ELASTICITY,
                                    "rule": "one-sided", "gain": None,
                                    "shock": "none", "size": 0.0,
                                    "seed": SEEDS[0]}))
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
                   "rescue. No shock: every reading here is on the unshocked "
                   "twins, which is where the second round's block moved",
        "rounds": ROUNDS,
        "authority": AUTHORITY,
        "rule": ("the endogenous rule issues the Layer 2 inflow's shortfall "
                 "below its round 0 level; the switch takes back gain times "
                 "the overshoot. ``mix`` names two positions drawn on in the "
                 "same round, each with its own shape and its own share of the "
                 "amount, each capped at the account, and the summed take "
                 "capped once more because two named positions can overlap"),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticity": ELASTICITY,
                 "elasticity_why": ("the only one at which this carrier's "
                                    "block has moved: all 18 of the second "
                                    "round's block moves sat there"),
                 "gain": GAIN,
                 "rules": {k: (v or "the switch off") for k, v in SPECS.items()},
                 "production_weight": PRODUCTION_WEIGHT,
                 "shocks": "none",
                 "seeds": list(SEEDS)},
        "park_target": _A30.TARGET,
        "tail": TAIL,
        "block": BLOCK,
        "ledger_tolerance": LEDGER_TOL,
        "collected_spread_line": SPREAD_LINE,
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A31C"
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
    cells = _A31.read_cells(rows, {}, {})
    rp = rule_pairs(cells)
    crits = [criterion_a31_15(gate_section),
             criterion_a31_16(cells, rp),
             criterion_a31_17(rp, cells),
             criterion_a31_18(rp, cells),
             criterion_a31_19(cells, rp)]
    written = [{k: v for k, v in c.items() if not k.startswith("_")}
               for c in cells]
    sections = {"criteria": [c.as_dict() for c in crits],
                "rule_pairs": rp, "rows": written}
    return crits, sections, rp, cells


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--plan", action="store_true")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--workers", type=int, default=_default_workers())
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-24s %s" % (k, v))
        print("  %-24s %d at %d seeds"
              % ("cells", len(cell_keys(seeds=SEEDS[:args.seeds])), args.seeds))
        return 0

    if args.gate:
        print("stage A31, third round, rule 19: the module before ``mix``, the "
              "driver, and the second round's record\n")
        g = gate(gate_configs(), workers=args.workers)
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A31, third round, D38: seconds per cell, measured on this "
              "machine\n")
        time_cells(workers=args.workers)
        return 0

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"], stresses=SMOKE["stresses"],
                         seeds=SMOKE["seeds"])
        print("stage A31, third round, smoke: %d cells, gated in-process on "
              "its own configurations, nothing written\n" % len(keys))
        gate_section = gate(
            gate_configs(needs=SMOKE["needs"], stresses=SMOKE["stresses"],
                         full=False),
            row_needs=SMOKE["needs"], row_seeds=SMOKE["seeds"][:1],
            workers=args.workers)
        print()
    else:
        gate_section = _gate_section()
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A31, third round: not starting. %s." % why)
            return 2
        seeds = SEEDS[:args.seeds]
        if len(seeds) < 2:
            print("stage A31, third round: not starting. The reading is seed "
                  "by seed, and that needs two.")
            return 2
        keys = cell_keys(seeds=seeds)
        print("stage A31, third round: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(seeds), args.workers, why))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, sections, rp, cells = analyse(rows, gate_section)
    print_rules(rp)
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
