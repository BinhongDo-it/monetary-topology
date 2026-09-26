"""A34: the write-off's shape, the one cell where the claim predicts a difference.

A32's surviving claim is that a collection's incidence changes who falls below
the subsistence floor unless a controller is closing a gap in the very quantity
the floor is read against. A31 swept the withdrawal and A33 the issuance, the
two halves of the one controller that does close that gap, and both read no
difference: 825 and 52 comparisons, and the only gaps were single nodes in both
directions.

**The write-off is a controller too, and on a different quantity.** It fires
when the claim total runs past a trigger against the resources offered, which is
not what the floor reads. So the claim predicts its shape *does* decide, and
this is the only station in the family where a null is evidence against the
claim rather than for it.

**The dial did not exist until today.** ``WriteOffSpec.base`` reuses the
withdrawal's splitter, so ``holdings`` keeps the one multiplication the module
has always had and is bit for bit the old path, while ``equal`` and
``threshold`` take the same amount off the accounts in another shape. The parked
side falls pro rata whatever the dial says, because the dial asks who among the
nodes still trading carries the loss and parked claims are not trading.

**One warning that is a day old.** Until 2026-09-12 the write-off did not close
its books as soon as anything was parked: it destroyed on the claim total, which
counts parked claims, while reducing only the held side, and the gap reached 167
on an opening stock of 100. Nothing on disk had ever run both switches at once,
so nothing already read was touched, and this is the first station to put them
in one grid. A34-1 is therefore load-bearing rather than a formality.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a34_writeoff_shape.py --plan
    python experiments/a34_writeoff_shape.py --time
    python experiments/a34_writeoff_shape.py --run --smoke
    python experiments/a34_writeoff_shape.py --run --workers 8
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
    NetworkConfig, WriteOffSpec, WITHDRAW_BASES)

RECORD = RESULTS / "a34_writeoff_shape.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
PRE_MODULE = SRC / "network.py.expired_20260912_pre_A34"
#: The module before the conservation fix that had to come first. ``base``
#: and that fix are two changes and they need two baselines: this one is
#: where the write-off destroyed on the claim total while reducing only the
#: held side, which is the behaviour the fix deliberately changed.
PRE_FIX = SRC / "network.py.expired_20260912_pre_writeoff_fix"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a34")
_A31 = _load(ROOT / "experiments" / "a31_withdrawal.py", "_a31_for_a34")
_A31S = _load(ROOT / "experiments" / "a31_shape.py", "_a31s_for_a34")

_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_num = _A30._num
_median = _A30._median
_range = _A30._range
_tally = _A30._tally
_default_workers = _A30._default_workers
_same = _A30._same
_rng_digest = _A30._rng_digest
_A29 = _A30._A29
_print_criteria = _A30._print_criteria
Criterion = _A30.Criterion

ROUNDS = _A30.ROUNDS
SEEDS = _A30.SEEDS
TAIL = _A30.TAIL
LEDGER_TOL = _A30.LEDGER_TOL
BLOCK = _A30.BLOCK
NEEDS = _A30.NEEDS
STRESSES = _A30.STRESSES
STRESS_SPECS = _A30.STRESS_SPECS
ELASTICITIES = _A30.ELASTICITIES
drive = _A31.drive

AUTHORITY = "endogenous"
BASES: tuple[str, ...] = WITHDRAW_BASES
#: Two operating points, measured before the grid was written: at 0.05 the
#: trigger is met in 292 of 300 rounds on the leaking strains and at 0.20 in 98,
#: and the totals destroyed differ by about a third between them. Two so the
#: reading is not tied to one.
RATES: tuple[float, ...] = (0.05, 0.20)
TRIGGER = 1.0
#: ``(base, rate)``. ``(None, None)`` leaves the write-off off and feeds A34-2.
ARMS: tuple[tuple, ...] = ((None, None),) + tuple(
    (b, r) for r in RATES for b in BASES)
#: One node is the discrete jitter this carrier family carries, measured by
#: A18_C over 135 paired cells and attributed there to A18_B6.
JITTER = 1
SMOKE = {"needs": (0.20,), "stresses": ("leak_recycled",), "seeds": SEEDS[:2],
         "elasticities": (0.5,)}
KEYS: tuple[str, ...] = ("need", "stress", "elasticity", "base", "rate", "seed")


def arm_label(base, rate) -> str:
    return "off" if base is None else "%s @%.2f" % (base, rate)


def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, arms=ARMS) -> list:
    return [{"need": n, "stress": s, "elasticity": e, "base": b, "rate": r,
             "seed": d}
            for n in needs for s in stresses for e in elasticities
            for b, r in arms for d in seeds]


def cell_config(key: dict) -> NetworkConfig:
    cfg = _A30.cell_config({"need": key["need"], "stress": key["stress"],
                            "elasticity": key["elasticity"],
                            "authority": AUTHORITY, "seed": key["seed"]})
    if key["base"] is None:
        return cfg
    return dataclasses.replace(
        cfg, writeoff=WriteOffSpec(rate=key["rate"], trigger=TRIGGER,
                                   base=key["base"]))


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net, seen = drive(cfg, "none", 0.0)
    h = net._history
    wrote = np.asarray(h.written_off, dtype=float)
    holdings = np.asarray(h.holdings, dtype=float)
    close = holdings[-1]
    l1 = np.zeros(close.size, dtype=bool)
    l1[net._l1] = True
    total = float(close.sum())
    row = dict(key)
    row.update({
        "books_close": seen["books"],
        "below_close": int(net._below.sum()),
        "destroyed_total": _num(float(wrote.sum())),
        "rounds_firing": int((wrote > 0.0).sum()),
        "circulating_tail": _num(float(holdings.sum(axis=1)[-TAIL:].mean())),
        "parked_tail": _num(float(np.asarray(h.parked,
                                             dtype=float)[-TAIL:].mean())),
        "l1_share_close": _num(float(close[l1].sum()) / total)
                          if total > 0 else None,
        "support_close": int((close > 0.0).sum()),
        "issued_total": _num(float(np.asarray(h.issuance, dtype=float).sum())),
    })
    return row


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            -1 if x["base"] is None else BASES.index(x["base"]),
            x["rate"] or 0.0, x["seed"])


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

SHAPE_STATES: tuple[tuple[str, str], ...] = (
    ("the shape decides", "the three bases leave different counts below the "
     "floor, by more than the one node of jitter, and the order of those "
     "counts is not the order of what they destroyed"),
    ("the amount decides", "the counts differ by more than the jitter and "
     "their order is the order of what was destroyed, so what moved is how "
     "much went rather than whose it was"),
    ("jitter only", "the counts differ by no more than one node, which is what "
     "this carrier family already carries"),
    ("the shape does not decide", "the three bases leave the same count. "
     "**This is the state that counts against the claim**, since the claim "
     "predicts a difference here"),
    ("the write-off never fired", "the trigger was never met on this carrier, "
     "so the dial had nothing to place. Not read either way"))


def _order(d: dict) -> tuple:
    """The bases sorted by a value, as a tuple, for comparing two orderings."""
    return tuple(sorted(d, key=lambda k: d[k]))


def pairs(rows: list) -> list:
    by = {}
    for r in rows:
        key = (r["need"], r["stress"], r["elasticity"], r["seed"])
        if r["base"] is None:
            by.setdefault(key, {})["off"] = r
        else:
            by.setdefault(key, {}).setdefault(r["rate"], {})[r["base"]] = r
    out = []
    for key in sorted(by, key=lambda k: (k[0], STRESSES.index(k[1]), k[2], k[3])):
        off = by[key].get("off")
        for rate in RATES:
            here = by[key].get(rate)
            if not here or not all(b in here for b in BASES):
                continue
            counts = {b: here[b]["below_close"] for b in BASES}
            destroyed = {b: here[b]["destroyed_total"] for b in BASES}
            fired = max(here[b]["rounds_firing"] for b in BASES)
            gap = int(max(counts.values()) - min(counts.values()))
            same_order = _order(counts) == _order(destroyed)
            if fired == 0:
                state = "the write-off never fired"
            elif gap == 0:
                state = "the shape does not decide"
            elif gap <= JITTER:
                state = "jitter only"
            elif same_order:
                state = "the amount decides"
            else:
                state = "the shape decides"
            dv = [v for v in destroyed.values() if v]
            spread = ((max(dv) - min(dv)) / min(dv)
                      if len(dv) == len(BASES) and min(dv) > 0 else None)
            out.append({
                "need": key[0], "stress": key[1], "elasticity": key[2],
                "seed": key[3], "rate": rate,
                "below_close": counts, "below_gap": gap,
                "destroyed": destroyed, "destroyed_spread": _num(spread),
                "rounds_firing": fired,
                "rounds_by_base": {b: here[b]["rounds_firing"] for b in BASES},
                "count_order": list(_order(counts)),
                "destroyed_order": list(_order(destroyed)),
                "orders_agree": bool(same_order),
                "fired": bool(fired),
                "against_off": ({b: int(counts[b] - off["below_close"])
                                 for b in BASES} if off else None),
                "other_readouts": {
                    b: {k: here[b][k] for k in
                        ("circulating_tail", "parked_tail", "l1_share_close",
                         "support_close", "issued_total")}
                    for b in BASES},
                "state": state,
            })
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a34_0(pr: list) -> Criterion:
    live = [p for p in pr if p["fired"]]
    apart = [p for p in live if p["destroyed_spread"]]
    same_fire = [p for p in live
                 if len({p["destroyed"][b] for b in BASES}) == 1]
    ok = bool(live) and len(apart) == len(live)
    return Criterion(
        "A34-0 the three shapes take from different accounts, measured off the "
        "run (D28)", "instrument", ok,
        "**Measured, not derived from the arm's name.** What each shape "
        "destroyed over the run, which is the one quantity that separates them "
        "without reading any outcome: cells where the trigger was met at all, "
        "%d of %d; of those, %d have the three totals distinct and %d have "
        "them equal. Relative spread of what was destroyed, across the three "
        "bases: median %s, %s. **Rounds the trigger fired in, and the shape "
        "does move them**, which the first version of this criterion asserted "
        "it could not: the trigger reads a ratio rather than an account, and "
        "that says nothing about how long the ratio stays above it. Per pair, "
        "taking the base that fires longest: median %s. Per base, over the "
        "same live cells: %s. A34-4 pairs them cell by cell. State map: at "
        "least one cell where it fired, and "
        "the three totals distinct in every such cell -> PASS; any live cell "
        "where the dial left no trace -> FAIL, and A34-3 would be reading one "
        "arm three times. **Cells where it never fired are not a failure**, "
        "they are carriers with nothing to place, and A34-3 holds them out."
        % (len(live), len(pr), len(apart), len(same_fire),
           _median([p["destroyed_spread"] for p in apart]),
           _range([p["destroyed_spread"] for p in apart]),
           _median([p["rounds_firing"] for p in live]),
           ", ".join("%s %s" % (b, _median([p["rounds_by_base"][b] for p in live]))
                     for b in BASES)))


def criterion_a34_1(rows: list, pr: list) -> Criterion:
    books = sum(1 for r in rows if r["books_close"])
    parked = [p for p in pr if p["fired"]
              and any(p["other_readouts"][b]["parked_tail"] for b in BASES)]
    return Criterion(
        "A34-1 the books close, with the write-off and parking both on",
        "instrument", books == len(rows),
        "Asserted every round in the loop: the claim total equals held plus "
        "parked to %.0e of the opening stock. Read back here: %d of %d cells "
        "close. **This criterion is a day old and it is load-bearing.** Until "
        "2026-09-12 the write-off destroyed on the claim total, which counts "
        "parked claims, while reducing only the held side, so the identity "
        "broke as soon as anything was parked: measured at 167 on an opening "
        "stock of 100 over 80 rounds. No record on disk carried both switches, "
        "and **this is the first station to put them in one grid**: %d of the "
        "cells read here have a parked stock and a write-off that fired. State "
        "map: every cell closing -> PASS; any cell open -> FAIL, and nothing "
        "after this reads."
        % (LEDGER_TOL, books, len(rows), len(parked)))


def criterion_a34_2(pr: list) -> Criterion:
    gaps = [v for p in pr if p["against_off"] for v in p["against_off"].values()]
    spectrum = {}
    for v in gaps:
        spectrum[v] = spectrum.get(v, 0) + 1
    moved = sum(n for v, n in spectrum.items() if abs(v) >= BLOCK)
    return Criterion(
        "A34-2 how far the count travels on this grid at all", "own_reading",
        True,
        "Printed, not judged, and printed before the reading it qualifies. "
        "Each shape against the same carrier and seed with the write-off "
        "switched off: the count below the floor differs by %s over %d "
        "comparisons, so a block of %d or more moves in %d of them. Measured "
        "before the grid was written, one cell of the recycled leak goes from "
        "75 below to 150 when the write-off is turned on, so the instrument's "
        "range here is not in doubt."
        % (dict(sorted(spectrum.items())), len(gaps), BLOCK, moved))


def criterion_a34_3(pr: list) -> Criterion:
    tally = _tally(p["state"] for p in pr)
    live = [p for p in pr if p["fired"]]
    decided = [p for p in live if p["state"] == "the shape decides"]
    amount = [p for p in live if p["state"] == "the amount decides"]
    null = [p for p in live if p["state"] == "the shape does not decide"]
    lines = ["need %.2f %s e %.1f seed %d rate %.2f: %s, gap %d, destroyed %s"
             % (p["need"], p["stress"], p["elasticity"], p["seed"], p["rate"],
                p["below_close"], p["below_gap"], p["destroyed"])
             for p in (decided or amount)[:8]]
    return Criterion(
        "A34-3 does the write-off's shape change who is below the floor",
        "own_reading", True,
        "Printed, not judged. **This is the one station in this family where "
        "the claim predicts a difference**: the write-off is a controller, and "
        "the gap it closes is the claim total over the resources offered, "
        "which is not the quantity the floor is read against. A31 and A33 "
        "swept the two halves of the controller that does close that gap and "
        "read no difference; a null here counts against the claim rather than "
        "for it. The reading runs over the %d of %d cells where the trigger "
        "fired. Of those: %d leave the same count, %d differ by no more than "
        "the one node of jitter A18_C measured, %d differ with the counts "
        "ordered as what they destroyed, and %d differ against that order. "
        "**The ordering is the separator**, because the three shapes destroy "
        "different totals: a spread of %s across the bases, so a difference "
        "that follows the order of what went is the amount rather than whose "
        "it was. States: %s. Counts by state: %s. Cells: %s."
        % (len(live), len(pr), len(null),
           sum(1 for p in live if p["state"] == "jitter only"),
           len(amount), len(decided),
           _median([p["destroyed_spread"] for p in live
                    if p["destroyed_spread"]]),
           "; ".join("%s = %s" % x for x in SHAPE_STATES), tally,
           "; ".join(lines) if lines else "none differ beyond jitter"))



def _rounds_for(pair: dict, base: str):
    """The rounds this base fired in, for this cell.

    The pair collapses the three bases with ``max`` because the gate that uses it
    only asks whether the trigger was met at all.  A34-4 reports per base, so it
    reads the per-base rows instead.  The first version of this criterion called
    ``p["rounds_firing"]`` inside the per-base loop without indexing by base, so it
    printed one number three times and the prose read it as "the shape does not move
    the firing rounds".  The rows say the opposite.
    """
    return pair["rounds_by_base"][base]


def criterion_a34_4(pr: list) -> Criterion:
    live = [p for p in pr if p["fired"]]
    parts = []
    for b in BASES:
        parts.append(
            "%s: destroyed median %s; Layer 1 share of the closing stock "
            "median %s; circulating tail median %s; rounds firing median %s"
            % (b, _median([p["destroyed"][b] for p in live]),
               _median([p["other_readouts"][b]["l1_share_close"] for p in live]),
               _median([p["other_readouts"][b]["circulating_tail"]
                        for p in live]),
               _median([_rounds_for(p, b) for p in live])))
    return Criterion(
        "A34-4 what each shape did", "bookkeeping", True,
        "Printed. %s. Cells where the trigger fired: %d of %d."
        % ("; ".join(parts), len(live), len(pr)))


# ---------------------------------------------------------------------------
# Printing, timing and the record.
# ---------------------------------------------------------------------------

def print_pairs(pr: list) -> None:
    print("\n  A34-2 and A34-3, carrier by carrier. below_close reads %s."
          % " / ".join(BASES))
    print("  %-5s %-14s %-4s %-4s %-5s %-16s %5s %-24s %8s  %s"
          % ("need", "strain", "e", "seed", "rate", "below_close", "gap",
             "destroyed", "spread", "state"))
    for p in pr:
        print("  %-5.2f %-14s %-4.1f %-4d %-5.2f %-16s %5d %-24s %8s  %s"
              % (p["need"], p["stress"], p["elasticity"], p["seed"], p["rate"],
                 "/".join(str(p["below_close"][b]) for b in BASES),
                 p["below_gap"],
                 "/".join("%.0f" % (p["destroyed"][b] or 0) for b in BASES),
                 p["destroyed_spread"], p["state"]))


def time_cells(repeats: int = 3, workers: int = 1) -> None:
    sample = [{"need": 0.20, "stress": s, "elasticity": 0.5, "base": b,
               "rate": RATES[0], "seed": SEEDS[0]}
              for s in STRESSES for b in BASES]
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


def station_config() -> dict:
    cfg = _config_diff(cell_config({"need": NEEDS[0], "stress": "healthy",
                                    "elasticity": ELASTICITIES[0],
                                    "base": BASES[0], "rate": RATES[0],
                                    "seed": SEEDS[0]}))
    cfg.pop("seed", None)
    for sub, keys in (("spec", ("seed",)), ("subsistence", ("need",)),
                      ("wages", ("elasticity",)), ("authority", ("rule",)),
                      ("writeoff", ("rate", "base"))):
        if sub in cfg:
            for k in keys:
                cfg[sub].pop(k, None)
            if not cfg[sub]:
                cfg.pop(sub)
    return {
        "carrier": "A30's: A18's config_for in drawdown, no rescue, no shock, "
                   "with the write-off switched on",
        "rounds": ROUNDS,
        "rule": ("the write-off destroys rate times the claim total in any "
                 "round where that total over the resources offered runs past "
                 "the trigger. ``base`` names how the part aimed at the held "
                 "side is split: pro rata to holdings, the same amount off "
                 "every account holding something, or the part above the mean. "
                 "The parked side falls pro rata whatever the base says"),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticities": list(ELASTICITIES),
                 "bases": list(BASES), "rates": list(RATES),
                 "trigger": TRIGGER,
                 "arm_off_is": "the same carrier with no write-off, which "
                               "feeds A34-2 and no other reading",
                 "seeds": list(SEEDS)},
        "park_target": _A30.TARGET,
        "tail": TAIL, "block": BLOCK, "jitter": JITTER,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


# ---------------------------------------------------------------------------
# Rule 19: the default reproduces the module before it, and it is run.
# ---------------------------------------------------------------------------

CLOSING: tuple[str, ...] = _A31.CLOSING


def load_pre(path: Path, name: str):
    """Loaded under the package name, because the module uses relative
    imports and a bare name has no parent package to resolve them against."""
    full = "monetary_topology." + name
    loader = importlib.machinery.SourceFileLoader(full, str(path))
    spec = importlib.util.spec_from_loader(full, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    loader.exec_module(module)
    return module


_GATE_CACHE: dict = {}


def _gate_one(job: tuple) -> dict:
    """One configuration under both modules, in a worker.

    The old module is loaded once per process and kept, because loading it
    per configuration would cost more than the two runs it is there to
    compare.
    """
    path, modname, label, cfg = job
    old = _GATE_CACHE.get(modname)
    if old is None:
        old = _GATE_CACHE[modname] = load_pre(Path(path), modname)
    names = [f.name for f in dataclasses.fields(_NET.NetworkHistory)]
    ref = old.Network(_A29.transplant(cfg, old))
    h_old = ref.run()
    net = _NET.Network(cfg)
    h_new = net.run()
    bad = [n for n in names if hasattr(h_old, n)
           and not _same(getattr(h_old, n), getattr(h_new, n))]
    bad += [n for n in CLOSING if not _same(getattr(ref, n), getattr(net, n))]
    if _rng_digest(ref) != _rng_digest(net):
        bad.append("generators")
    fired = bool(cfg.writeoff.active
                 and float(np.asarray(h_new.written_off).sum()) > 0.0)
    return {"config": label, "fields": bad, "fired": fired,
            "fields_compared": len(names) + len(CLOSING) + 1}


def gate_configs(seeds=SEEDS[:1]) -> list:
    """Two groups, because there are two changes and each has its own
    baseline and its own scope.

    Against ``pre_A34``, which already carries the conservation fix: the new
    field at its default, over every carrier, with the write-off off and with
    it firing at both rates. The default branch is the old two lines, so the
    thing at risk is not the branch, it is the dataclass gaining a field.
    ``NetworkSpec.replace`` is a hand-written field list and rule 19's own
    note says a field left out of one is silently dropped.

    Against ``pre_writeoff_fix``, only where the fix is claimed to be inert:
    a carrier that parks nothing, or a run with no write-off at all. The fix
    changes the parked-and-firing combination on purpose, and that
    combination appears in no record on disk, which is the whole of failure
    mode 163.
    """
    a34, fix = [], []
    # Every configuration A31's own gate uses, which is where the switches
    # this station did not touch actually live: the withdrawal in both its
    # one-sided and two-sided form, parking, the sovereign, a write-off with
    # the refill on. A record that depends on any of them has to come back.
    for label, cfg in _A31S.gate_configs():
        a34.append(("A31 gate: " + label, cfg))
        parks = bool(getattr(cfg, "park", None) and cfg.park.rate)
        if not cfg.writeoff.active or not parks:
            fix.append(("A31 gate: " + label, cfg))
    for stress in STRESSES:
        parks = bool(STRESS_SPECS[stress].get("park"))
        for e in ELASTICITIES:
            for need in NEEDS:
                for seed in seeds:
                    for base, rate in ((None, None), ("holdings", RATES[0]),
                                       ("holdings", RATES[1])):
                        label = ("%s, need %.2f, e %.1f, %s, seed %d"
                                 % (stress, need, e, arm_label(base, rate),
                                    seed))
                        cfg = cell_config({"need": need, "stress": stress,
                                           "elasticity": e, "base": base,
                                           "rate": rate, "seed": seed})
                        a34.append((label, cfg))
                        if base is None or not parks:
                            fix.append((label, cfg))
    return [(PRE_MODULE, "_network_pre_a34", a34),
            (PRE_FIX, "_network_pre_writeoff_fix", fix)]


def gate(workers: int = 1) -> dict:
    """Run it. The answer to rule 19 is a re-run, not an argument."""
    groups, ok = [], True
    for path, modname, configs in gate_configs():
        if not path.exists():
            groups.append({"baseline": path.name, "state": "missing",
                           "configs": 0, "differ": []})
            ok = False
            continue
        jobs = [(str(path), modname, label, cfg) for label, cfg in configs]
        t0 = time.perf_counter()
        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                got = list(pool.map(_gate_one, jobs, chunksize=4))
        else:
            got = [_gate_one(j) for j in jobs]
        differ = [{"config": x["config"], "fields": x["fields"]}
                  for x in got if x["fields"]]
        fired = sum(1 for x in got if x["fired"])
        groups.append({"baseline": path.name, "state": "run",
                       "configs": len(configs),
                       "fields_compared": got[0]["fields_compared"] if got else 0,
                       "configs_with_the_write_off_firing": fired,
                       "differ": differ,
                       "seconds": round(time.perf_counter() - t0, 1)})
        if differ:
            ok = False
        print("   %-46s %4d configs, %3d of them firing, %d differ  (%.0f s)"
              % (path.name, len(configs), fired, len(differ),
                 groups[-1]["seconds"]))
        for d in differ[:5]:
            print("     %s" % d)
    return {"verdict": "pass" if ok else "FAIL", "groups": groups,
            "module_sha": _module_sha(MODULE), "script_sha": _module_sha(SCRIPT)}


def _gate_section():
    if not RECORD.exists():
        return None
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    return doc.get("sections", {}).get("gate")


def criterion_a34_5(g) -> Criterion:
    """Rule 19, read back off the record rather than asserted in a print."""
    if not g:
        return Criterion(
            "A34-5 rule 19: the default reproduces the module before it",
            "instrument", False,
            "No gate section in the record: run --gate. **The first version "
            "of this station carried the answer as a sentence in a print "
            "statement**, which is a number kept in the code rather than one "
            "read off a run, and it disagreed with the number the pit "
            "account carried for the same check. A count that has to be "
            "maintained by hand drifts, which is the standing reason not to "
            "keep one anywhere.", evaluated=False)
    stale = []
    if g.get("module_sha") != _module_sha(MODULE):
        stale.append("network.py has changed since the gate ran")
    if g.get("script_sha") != _module_sha(SCRIPT):
        stale.append("this script has changed since the gate ran, and the "
                     "grid lives in it")
    lines = "; ".join(
        "%s: %s, %d configurations, %d of them with the write-off firing, "
        "%d fields each, %d differ"
        % (x["baseline"], x["state"], x["configs"],
           x.get("configs_with_the_write_off_firing", 0),
           x.get("fields_compared", 0), len(x["differ"]))
        for x in g["groups"])
    ok = g["verdict"] == "pass" and not stale
    return Criterion(
        "A34-5 rule 19: the default reproduces the module before it",
        "instrument", ok,
        "**Run, not argued.** Two changes reached network.py for this "
        "station and each is compared against its own baseline: the new "
        "``base`` field against the module that already had the "
        "conservation fix, and the fix against the module before it, over "
        "the configurations where the fix is claimed to be inert. Every "
        "field of the history, plus the closing state, plus the generator "
        "digest. %s. %s State map: every group run and nothing differing "
        "-> PASS; any field differing, any baseline missing, or either sha "
        "moved since the gate ran -> FAIL, and the number below is about "
        "some other code. **The fix is not claimed inert where the two "
        "switches meet**: parking and a firing write-off together is the "
        "combination it changed on purpose, it is held out of the second "
        "group, and no record on disk carries it."
        % (lines, ("**Stale: %s.**" % "; ".join(stale)) if stale else ""))


def write_record(payload: dict, section: str = "run") -> None:
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A34"
    # Closed 2026-09-12: the reading is in RESULTS.md and the numbers were
    # re-derived from this record before it was closed.
    doc.pop("diagnostic_only", None)
    doc.pop("diagnostic_reason", None)
    doc["config"] = _fmt(station_config())
    doc["module_sha"] = _module_sha(MODULE)
    doc["pre_module_sha"] = (_module_sha(PRE_MODULE) if PRE_MODULE.exists()
                             else None)
    doc["script_sha"] = _module_sha(SCRIPT)
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s" % RECORD.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--gate", action="store_true")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--workers", type=int, default=_default_workers())
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-22s %s" % (k, v))
        print("  %-22s %d at %d seeds"
              % ("cells", len(cell_keys(seeds=SEEDS[:args.seeds])), args.seeds))
        return 0
    if args.time:
        print("stage A34, D38: seconds per cell, measured on this machine\n")
        time_cells(workers=args.workers)
        return 0
    if args.gate:
        print("stage A34, rule 19: two baselines, one per change. Nothing "
              "about the reading is touched here.\n")
        g = gate(workers=args.workers)
        print("\n  gate: %s" % g["verdict"])
        if not args.no_write:
            write_record(g, section="gate")
        return 0 if g["verdict"] == "pass" else 1

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"], stresses=SMOKE["stresses"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A34, smoke: %d cells, nothing written\n" % len(keys))
    else:
        keys = cell_keys(seeds=SEEDS[:args.seeds])
        print("stage A34: %d cells, seeds %s, %d workers. Rule 19 is "
              "A34-5 and it is read off the gate section of the record, "
              "not carried as a sentence here.\n"
              % (len(keys), list(SEEDS[:args.seeds]), args.workers))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    pr = pairs(rows)
    crits = [criterion_a34_0(pr), criterion_a34_1(rows, pr),
             criterion_a34_2(pr), criterion_a34_3(pr), criterion_a34_4(pr),
             criterion_a34_5(_gate_section())]
    print_pairs(pr)
    _print_criteria(crits)
    failed = [c.name for c in crits if c.evaluated and not c.passed]
    print("\n  %d/%d" % (len(crits) - len(failed), len(crits)))
    if args.smoke or args.no_write:
        return 0 if not failed else 1
    write_record({"criteria": [c.as_dict() for c in crits], "pairs": pr,
                  "rows": rows, "seeds_run": sorted({r["seed"] for r in rows})})
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
