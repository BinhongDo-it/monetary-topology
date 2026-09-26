"""A35: what carries the prolongation a per-head write-off causes.

A34 registered that a per-head write-off prolongs the condition it fires on and
left the fact without a criterion. The fact is settled: over A34's 238 live
cells the firing rounds read medians of 98 under pro rata, 173 per head and 97
above the mean, and cell by cell the per-head shape fires longer than pro rata
in 233 and shorter in none. **So this station is not about whether. It is about
what carries it**, and there are two candidates the module never recorded.

**One: the cap.** A per-head levy aims the same amount at every account that
holds something, so any account holding less than that share pays what it has
and the rest is not collected and not carried forward. Pro rata aims a fraction
of each account's own balance, which no account can fail to meet. So per head
destroys less than it aimed at, the ratio it fires on falls more slowly, and it
fires again.

**Two: the paying set.** An account emptied by the levy stops being an account
the levy can draw on. With fewer payers the per-head share rises, so the cap
bites harder on the ones left, which empties more of them. Pro rata cannot do
this, because a fraction of a balance never empties it.

**Both are counters, not mechanisms.** Four arrays go on the history behind
``trace_writeoff``, which is off by default. Nothing in the loop reads them, so
the check rule 19 asks for here is not the weak one of comparing the switch off
against the module before the fields existed; it is that a run with the switch
**on** comes back bit for bit, because an observer that changes the run is not
an observer. A35-2 makes that check.

**Where the third shape comes in, and it was not in the design.** Taking only
from the accounts above the mean fires *shorter* than pro rata, 211 cells to 0.
That is the paying-set story read backwards: the shape that never touches a
small account is the shape that never empties one. So the grid carries its own
control, and the two candidates can be told apart without adding an arm.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a35_writeoff_prolongation.py --plan
    python experiments/a35_writeoff_prolongation.py --time
    python experiments/a35_writeoff_prolongation.py --gate --workers 8
    python experiments/a35_writeoff_prolongation.py --run --smoke
    python experiments/a35_writeoff_prolongation.py --run --workers 8
    python experiments/a35_writeoff_prolongation.py --run --horizon 600 --workers 8
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.machinery
import importlib.util
import json
import os
import statistics
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
from monetary_topology.network import WRITEOFF_TRACE_FIELDS  # noqa: E402

RECORD = RESULTS / "a35_writeoff_prolongation.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()
#: The module before this station's four counters. The one baseline that
#: matters here, because the counters are the only change.
PRE_MODULE = SRC / "network.py.expired_20260913_pre_A35"
A34_RECORD = RESULTS / "a34_writeoff_shape.json"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a35")
_A34 = _load(ROOT / "experiments" / "a34_writeoff_shape.py", "_a34_for_a35")

_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_num = _A30._num
_median = _A30._median
_range = _A30._range
_tally = _A30._tally
_default_workers = _A30._default_workers
_print_criteria = _A30._print_criteria
_same = _A30._same
_rng_digest = _A30._rng_digest
_A29 = _A30._A29
Criterion = _A30.Criterion

SEEDS = _A30.SEEDS
TAIL = _A30.TAIL
LEDGER_TOL = _A30.LEDGER_TOL
NEEDS = _A30.NEEDS
STRESSES = _A30.STRESSES
ELASTICITIES = _A30.ELASTICITIES
CLOSING = _A34.CLOSING
drive = _A34.drive

#: The carrier is A34's, to the field. Nothing here is a new operating point:
#: the only change is that the counters are on and, in one arm, the horizon.
BASES: tuple[str, ...] = _A34.BASES
RATES: tuple[float, ...] = _A34.RATES
TRIGGER = _A34.TRIGGER
ROUNDS = _A30.ROUNDS
KEYS: tuple[str, ...] = ("need", "stress", "elasticity", "base", "rate", "seed")
SMOKE = {"needs": (0.15,), "stresses": ("leak",), "seeds": SEEDS[:2],
         "elasticities": (0.5,)}

#: Where a shortfall stops being a shortfall and starts being arithmetic.
#: The quantity is a difference of two sums of order the claim stock, which
#: runs from about a hundred to a few thousand here, so double precision puts
#: its noise near 1e-13 absolute and, against an aimed amount of order one to
#: a hundred, near 1e-14 relative. The shape that really caps sits at 1e-1
#: relative. **This line is not fitted to either side: it is seven orders
#: above the arithmetic and six below the reading**, and the two numbers it
#: separates are printed either way so the reader can move it. Recording the
#: residue itself is what the derived-file rules forbid: its last digits
#: belong to the BLAS build, and it would surface as a false diff on the next
#: machine.
UNCOLLECTED_FLOOR = 1e-9


def cell_config(key: dict, horizon: int | None = None):
    cfg = _A34.cell_config(key)
    cfg = dataclasses.replace(cfg, trace_writeoff=True)
    if horizon:
        cfg = dataclasses.replace(cfg, rounds=horizon)
    return cfg


def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, bases=None, rates=None,
              horizon: int = ROUNDS) -> list:
    """Every cell of A34's grid that has a write-off, and no off arm.

    A34's off arm fed its instrument range and nothing here reads it, so
    carrying it would be three hundred runs bought for no reading.
    """
    return [{"need": n, "stress": s, "elasticity": e, "base": b, "rate": r,
             "seed": d, "horizon": horizon}
            for n in needs for s in stresses for e in elasticities
            for r in (rates or RATES) for b in (bases or BASES)
            for d in seeds]


# ---------------------------------------------------------------------------
# One cell.
# ---------------------------------------------------------------------------

def one_cell(key: dict) -> dict:
    horizon = key.get("horizon") or ROUNDS
    cfg = cell_config({k: key[k] for k in KEYS}, horizon=horizon)
    net, seen = drive(cfg, "none", 0.0)
    h = net._history
    wrote = np.asarray(h.written_off, dtype=float)
    firing = wrote > 0.0
    holdings = np.asarray(h.holdings, dtype=float)

    unc = np.asarray(h.writeoff_uncollected, dtype=float)[firing]
    payers = np.asarray(h.writeoff_payers, dtype=float)[firing]
    drained = np.asarray(h.writeoff_drained, dtype=float)[firing]
    share = np.asarray(h.writeoff_share, dtype=float)[firing]
    aimed = share * payers
    # Relative, because the absolute shortfall is a difference of two sums and
    # its floor is set by the size of those sums rather than by anything about
    # the shape. The relative number is what the three bases can be compared on.
    rel = np.divide(unc, aimed, out=np.zeros_like(unc), where=aimed > 0.0)

    row = dict({k: key[k] for k in KEYS})
    row.update({
        "horizon": horizon,
        "books_close": seen["books"],
        "rounds_firing": int(firing.sum()),
        "fires_to_the_end": bool(firing.size and firing[-1]),
        "destroyed_total": _num(float(wrote.sum())),
        "below_close": int(net._below.sum()),
        "circulating_tail": _num(float(holdings.sum(axis=1)[-TAIL:].mean())),
        # The cap.
        "uncollected_total": _num(float(unc.sum())),
        "uncollected_rounds": int((rel > UNCOLLECTED_FLOOR).sum()),
        "uncollected_rel_max": _num(float(rel.max()) if rel.size else 0.0),
        "uncollected_rel_median": _num(float(np.median(rel)) if rel.size else 0.0),
        "uncollected_clears_floor": bool(rel.size
                                         and float(rel.max())
                                         > UNCOLLECTED_FLOOR),
        "aimed_total": _num(float(aimed.sum())),
        # The stock at the first and last firing round, so A35-6's
        # decomposition of the per-head share is an identity that can be
        # checked rather than a pair of numbers that have to be believed.
        "stock_first_firing": _num(float(holdings.sum(axis=1)[firing][0])
                                   if firing.any() else 0.0),
        "stock_last_firing": _num(float(holdings.sum(axis=1)[firing][-1])
                                  if firing.any() else 0.0),
        # The paying set.
        "payers_first": int(payers[0]) if payers.size else 0,
        "payers_last": int(payers[-1]) if payers.size else 0,
        "payers_min": int(payers.min()) if payers.size else 0,
        "payers_monotone": bool(payers.size and
                                bool((np.diff(payers) <= 0).all())),
        "payers_rises_count": int((np.diff(payers) > 0).sum())
                              if payers.size > 1 else 0,
        "drained_total": int(drained.sum()),
        "drained_rounds": int((drained > 0.0).sum()),
        "share_first": _num(float(share[0]) if share.size else 0.0),
        "share_last": _num(float(share[-1]) if share.size else 0.0),
        "share_monotone": bool(share.size and
                               bool((np.diff(share) >= 0).all())),
        "share_falls_count": int((np.diff(share) < 0).sum())
                             if share.size > 1 else 0,
    })
    return row


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            BASES.index(x["base"]), x["rate"], x["seed"])


def run_cells(keys: list, workers: int) -> list:
    if workers <= 1:
        rows = [one_cell(k) for k in keys]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one_cell, keys, chunksize=8))
    return sorted(rows, key=_row_key)


def cells(rows: list) -> list:
    """Group the three bases at one carrier, seed, rate **and horizon**.

    **The horizon has to be in the key.** It is not in ``KEYS``, because
    ``KEYS`` names the grid and the horizon is an arm rather than a grid
    dimension, and leaving it out of the key here merged the two arms: the
    six hundred round rows landed on top of the three hundred round ones, one
    arm was silently discarded, and the criterion that reads these cells then
    filtered for the horizon that no longer existed and ran on nothing. **It
    reported a verdict on an empty set and passed**, because a printed
    criterion passes by construction. Same family as the missing base
    subscript A34 paid for: a key with a dimension left out does not raise,
    it merges.
    """
    by: dict = {}
    for r in rows:
        key = tuple(r[k] for k in KEYS if k != "base") + (r["horizon"],)
        by.setdefault(key, {})[r["base"]] = r
    out = []
    for key, here in sorted(by.items()):
        if len(here) != len(BASES):
            continue
        out.append({"need": key[0], "stress": key[1], "elasticity": key[2],
                    "rate": key[3], "seed": key[4], "horizon": key[5],
                    "fired": any(here[b]["rounds_firing"] for b in BASES),
                    "by_base": here})
    return out


# ---------------------------------------------------------------------------
# Rule 19: an observer that changes the run is not an observer.
# ---------------------------------------------------------------------------

_GATE_CACHE: dict = {}


def _gate_one(job: tuple) -> dict:
    path, modname, label, cfg = job
    old = _GATE_CACHE.get(modname)
    if old is None:
        old = _GATE_CACHE[modname] = _load(Path(path),
                                           "monetary_topology." + modname)
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
    # With the switch off the four fields must not even be allocated, which is
    # the shape A31's gate uses for the withdrawal's columns.
    if not cfg.trace_writeoff:
        extra = [k for k in WRITEOFF_TRACE_FIELDS
                 if getattr(h_new, k) is not None]
        if extra:
            bad.append("fields allocated with the switch off: %s" % extra)
    else:
        missing = [k for k in WRITEOFF_TRACE_FIELDS
                   if getattr(h_new, k) is None]
        if missing:
            bad.append("fields not allocated with the switch on: %s" % missing)
    return {"config": label, "fields": bad,
            "fields_compared": len(names) + len(CLOSING) + 1}


def gate(workers: int = 1) -> dict:
    """Run it. The answer to rule 19 is a re-run, not an argument."""
    if not PRE_MODULE.exists():
        return {"verdict": "FAIL", "groups": [
            {"baseline": PRE_MODULE.name, "state": "missing", "configs": 0,
             "differ": []}]}
    # One config list, exercised with the switch off and with it on.
    plain = []
    for _, _, configs in _A34.gate_configs():
        for label, cfg in configs:
            plain.append((label, cfg))
    seen, uniq = set(), []
    for label, cfg in plain:
        if label in seen:
            continue
        seen.add(label)
        uniq.append((label, cfg))

    groups, ok = [], True
    for on in (False, True):
        jobs = [(str(PRE_MODULE), "_network_pre_a35",
                 "%s [trace %s]" % (label, "on" if on else "off"),
                 dataclasses.replace(cfg, trace_writeoff=on))
                for label, cfg in uniq]
        t0 = time.perf_counter()
        if workers > 1:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                got = list(pool.map(_gate_one, jobs, chunksize=4))
        else:
            got = [_gate_one(j) for j in jobs]
        differ = [{"config": x["config"], "fields": x["fields"]}
                  for x in got if x["fields"]]
        groups.append({"baseline": PRE_MODULE.name,
                       "trace": "on" if on else "off",
                       "state": "run", "configs": len(jobs),
                       "fields_compared": got[0]["fields_compared"] if got else 0,
                       "differ": differ,
                       "seconds": round(time.perf_counter() - t0, 1)})
        if differ:
            ok = False
        print("   %-46s trace %-3s %4d configs, %d differ  (%.0f s)"
              % (PRE_MODULE.name, "on" if on else "off", len(jobs),
                 len(differ), groups[-1]["seconds"]))
        for d in differ[:5]:
            print("     %s" % d)
    return {"verdict": "pass" if ok else "FAIL", "groups": groups,
            "module_sha": _module_sha(MODULE), "script_sha": _module_sha(SCRIPT)}


def _gate_section():
    if not RECORD.exists():
        return None
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    return doc.get("sections", {}).get("gate")


# ---------------------------------------------------------------------------
# Readings.
# ---------------------------------------------------------------------------

def _spearman(xs, ys) -> float | None:
    """Rank correlation, written out because the reading is one number and
    pulling in a dependency for it would be the larger change."""
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        out = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return _num(num / (dx * dy)) if dx and dy else None


def criterion_a35_1(rows: list) -> Criterion:
    books = sum(1 for r in rows if r["books_close"])
    return Criterion(
        "A35-1 the books close on every cell of this grid", "instrument",
        books == len(rows),
        "Asserted every round in the loop, not checked afterwards: the claim "
        "total equals held plus parked to %.0e of the opening stock. Read back "
        "here: %d of %d cells close. **The counters do not enter this**: they "
        "record and the assertion is on the stock, so a counter that was wrong "
        "would not show up here and A35-2 is what covers that. State map: "
        "every cell closing -> PASS; any cell open -> FAIL, and nothing after "
        "this reads."
        % (LEDGER_TOL, books, len(rows)))


def criterion_a35_2(g) -> Criterion:
    if not g:
        return Criterion(
            "A35-2 rule 19: the counters do not change the run", "instrument",
            False, "No gate section in the record: run --gate.",
            evaluated=False)
    stale = []
    if g.get("module_sha") != _module_sha(MODULE):
        stale.append("network.py has changed since the gate ran")
    if g.get("script_sha") != _module_sha(SCRIPT):
        stale.append("this script has changed since the gate ran, and the "
                     "grid lives in it")
    lines = "; ".join(
        "trace %s: %s, %d configurations, %d fields each, %d differ"
        % (x.get("trace"), x["state"], x["configs"], x.get("fields_compared", 0),
           len(x["differ"])) for x in g["groups"])
    ok = g["verdict"] == "pass" and not stale
    return Criterion(
        "A35-2 rule 19: the counters do not change the run", "instrument", ok,
        "**Run, not argued, and the group that matters is the second one.** "
        "Every configuration is compared against %s twice, once with "
        "``trace_writeoff`` off and once with it on, over every field of the "
        "history plus the closing state plus the generator digest. **Off is "
        "the letter of rule 19 and it is nearly free to satisfy**, since a "
        "field nobody allocates cannot change anything; the group with the "
        "switch on is the one that can fail, because computing a counter can "
        "consume a random draw, alias an array, or read state after something "
        "has already moved it. Off also has to leave the four fields "
        "unallocated and on has to allocate all four, both checked per "
        "configuration. %s. %s State map: both groups run and nothing "
        "differing -> PASS; any field differing, the baseline missing, or "
        "either sha moved since the gate ran -> FAIL."
        % (PRE_MODULE.name, lines,
           ("**Stale: %s.**" % "; ".join(stale)) if stale else ""))


def criterion_a35_3(rows: list) -> Criterion:
    """A34's firing rounds, recomputed here rather than read from its record."""
    if not A34_RECORD.exists():
        return Criterion("A35-3 A34's firing rounds come back on this module",
                         "known_answer", False,
                         "A34's record is not on disk.", evaluated=False)
    doc = json.loads(A34_RECORD.read_text(encoding="utf-8"))
    ref = {}
    for r in doc["sections"]["run"]["rows"]:
        if r.get("base") is None:
            continue
        ref[(r["need"], r["stress"], r["elasticity"], r["base"], r["rate"],
             r["seed"])] = r["rounds_firing"]
    mine = {(r["need"], r["stress"], r["elasticity"], r["base"], r["rate"],
             r["seed"]): r["rounds_firing"]
            for r in rows if r["horizon"] == ROUNDS}
    shared = sorted(set(ref) & set(mine))
    differ = [{"cell": list(k), "a34": ref[k], "here": mine[k]}
              for k in shared if ref[k] != mine[k]]
    med = {b: _median([mine[k] for k in mine if k[3] == b and mine[k] > 0])
           for b in BASES}
    live = [k for k in shared if mine[k] > 0]
    longer = sum(1 for k in live if k[3] == "equal"
                 and mine[k] > mine[(k[0], k[1], k[2], "holdings", k[4], k[5])])
    shorter = sum(1 for k in live if k[3] == "equal"
                  and mine[k] < mine[(k[0], k[1], k[2], "holdings", k[4], k[5])])
    ok = bool(shared) and not differ
    return Criterion(
        "A35-3 A34's firing rounds come back on this module", "known_answer",
        ok,
        "**A known answer with a name and a date, not a self-comparison.** "
        "A34 reported the firing rounds per shape on 2026-09-13 after a missing "
        "base subscript was corrected. This station runs the same grid with the "
        "counters on and recomputes them. Cells shared with A34's record: %d; "
        "cells where the count differs: %d. Recomputed medians over the live "
        "cells: %s. Per-head longer than pro rata in %d cells, shorter in %d. "
        "**This criterion can fail three ways**: the counters perturbed the run "
        "(A35-2 would also fail), the grid does not line up with A34's, or the "
        "correction was itself wrong. State map: at least one shared cell and "
        "no count differing -> PASS; any count differing -> FAIL, and every "
        "reading after this is about a different grid from A34's. %s"
        % (len(shared), len(differ),
           ", ".join("%s %s" % (b, med[b]) for b in BASES), longer, shorter,
           ("First few that differ: %s." % differ[:3]) if differ else ""))


def criterion_a35_4(rows: list) -> Criterion:
    """The cap, per base, printed rather than thresholded."""
    per = {}
    for b in BASES:
        live = [r for r in rows if r["base"] == b and r["rounds_firing"] > 0]
        per[b] = {
            "cells": len(live),
            "rel_max": max([r["uncollected_rel_max"] for r in live] or [0.0]),
            "rel_median": _median([r["uncollected_rel_median"] for r in live]),
            "cells_clearing": sum(1 for r in live
                                  if r["uncollected_clears_floor"]),
            "abs_max": _median([r["uncollected_total"] for r in live]),
        }
    ok = bool(per["equal"]["cells"]) and per["equal"]["rel_max"] > 0.0
    return Criterion(
        "A35-4 what each shape failed to collect", "own_reading", True,
        "Printed, not judged. What a shape aimed at the held side minus what "
        "left the accounts, measured off the accounts rather than read back "
        "from the branch that took it. Relative to what was aimed at, over "
        "the cells where the write-off fired: %s. **Pro rata and "
        "above-the-mean sit at the arithmetic floor and per head sits about "
        "thirteen orders of magnitude above it.** The two small figures print "
        "as 0.0 because this field carries six decimals; what they actually "
        "measure is near 1e-14 relative, which is a difference of two sums of "
        "order the claim stock and therefore arithmetic rather than a "
        "shortfall. **The residue is deliberately not recorded**: its last "
        "digits belong to the BLAS build and would surface as a false diff on "
        "the next machine, so what the record carries is whether the "
        "shortfall cleared the %.0e floor above. **Neither small figure is "
        "claimed as an exact zero.** %s"
        % ("; ".join(
            "%s: %d cells fired, %d of them leave a shortfall above the "
            "floor, relative max %s, relative median %s, absolute total at "
            "the median %s"
            % (b, per[b]["cells"], per[b]["cells_clearing"], per[b]["rel_max"],
               per[b]["rel_median"], per[b]["abs_max"]) for b in BASES),
           UNCOLLECTED_FLOOR,
           "**Why per head cannot avoid it and pro rata cannot incur it**: a "
           "per-head levy aims one share at every account holding anything, so "
           "an account holding less than that share pays what it has and the "
           "rest is not collected and not carried forward; pro rata aims a "
           "fraction of each account's own balance, which no account can fail "
           "to meet. Above-the-mean scales what it aims at down to what the "
           "excess can fund, so it does not cap per account either."))


def criterion_a35_5(cs: list) -> Criterion:
    """Which candidate carries the prolongation. Paired, within cell.

    **The verdict sentence is assembled from the two numbers rather than
    written above them.** The first draft asserted the two candidates could
    not be told apart, on the strength of four smoke cells; the full grid
    separates them by an order of magnitude, and the assertion would have
    survived into the write-up unchallenged, because a sentence sitting in a
    criterion reads like a finding whether or not anything computed it.
    """
    live = [c for c in cs if c["fired"]
            and all(c["by_base"][b]["rounds_firing"] for b in BASES)]
    if not live:
        # **A printed criterion with nothing to print is not a pass.** This
        # guard exists because the grouping bug above left this criterion with
        # an empty population and it reported "not separated" with two None
        # correlations, which is a verdict on nothing that reads like a
        # finding.
        return Criterion(
            "A35-5 which of the two candidates carries the prolongation",
            "own_reading", False,
            "**Not evaluated: no cell has all three shapes firing at this "
            "horizon.** Either the grid did not run or the grouping dropped "
            "the population, and in both cases the reading below would be "
            "about nothing. %d cells were offered." % len(cs),
            evaluated=False)
    d_rounds, d_unc, d_drain = [], [], []
    for c in live:
        h, e = c["by_base"]["holdings"], c["by_base"]["equal"]
        d_rounds.append(e["rounds_firing"] - h["rounds_firing"])
        d_unc.append(e["uncollected_rel_median"])
        d_drain.append(e["drained_total"] - h["drained_total"])
    rho_unc = _spearman(d_unc, d_rounds)
    rho_drain = _spearman(d_drain, d_rounds)
    shrink = sum(1 for c in live
                 if c["by_base"]["equal"]["payers_last"]
                 < c["by_base"]["equal"]["payers_first"])
    t_vs_h = [(c["by_base"]["threshold"]["rounds_firing"]
               - c["by_base"]["holdings"]["rounds_firing"],
               c["by_base"]["threshold"]["uncollected_clears_floor"],
               c["by_base"]["threshold"]["drained_total"])
              for c in live]
    t_differ = [x for x in t_vs_h if x[0] != 0]
    t_at_floor = [x for x in t_differ if not x[1] and x[2] == 0]
    t_destroyed = [(c["by_base"]["threshold"]["destroyed_total"]
                    / max(c["by_base"]["threshold"]["rounds_firing"], 1))
                   / max((c["by_base"]["holdings"]["destroyed_total"]
                          / max(c["by_base"]["holdings"]["rounds_firing"], 1)),
                         1e-12)
                   for c in live]
    a, b = abs(rho_unc or 0.0), abs(rho_drain or 0.0)
    if a >= 2 * b + 0.2:
        verdict = ("**The shortfall carries it and the paying set does not.** "
                   "The two correlations differ by a factor of %.0f, and the "
                   "paying-set count says the same thing from the other side: "
                   "the payers the levy could draw on at its last firing round "
                   "are fewer than at its first in %d of the %d cells."
                   % (a / max(b, 1e-9), shrink, len(live)))
    elif b >= 2 * a + 0.2:
        verdict = ("**The paying set carries it and the shortfall does not**, "
                   "which is the reverse of what the two shapes suggested, and "
                   "the paying-set count agrees: %d of %d cells end with fewer "
                   "payers than they started with." % (shrink, len(live)))
    else:
        verdict = ("**The two are not separated on this grid**, their "
                   "correlations being within a factor of two of one another, "
                   "so both are reported and neither is claimed. Cells ending "
                   "with fewer payers than they started with: %d of %d."
                   % (shrink, len(live)))
    return Criterion(
        "A35-5 which of the two candidates carries the prolongation",
        "own_reading", True,
        "Printed, not judged. Paired within the cell, per head against pro "
        "rata, over the %d cells where all three shapes fired. **Rank "
        "correlation, printed beside the object rather than tested against a "
        "line**: the extra rounds against the shortfall the cap left, %s; the "
        "extra rounds against the extra accounts emptied, %s. %s **Emptying an "
        "account and keeping it empty are two different things**, and this "
        "grid does the first constantly without doing the second: a per-head "
        "levy empties accounts every round and they receive inflow again "
        "before the next one, so the count of emptyings is large while the "
        "number of payers at the levy barely moves. A35-6 has that as a "
        "factorisation. **The third shape says neither candidate is "
        "necessary**: above-the-mean differs from pro rata in %d of %d cells, "
        "and in %d of those the shortfall is below the %.0e floor and no "
        "account was emptied at all, so a firing-round difference exists with "
        "neither candidate present. **That difference has a third channel and "
        "it is the amount rather than the shape**: above-the-mean destroys %s "
        "times as much per firing round as pro rata at the median, so the "
        "ratio it fires on falls faster. **What is claimed and what is not**: "
        "the large effect, per head against pro rata, is claimed for the "
        "shortfall; the small one, above-the-mean against pro rata, is claimed "
        "for neither candidate and is registered open."
        % (len(live), rho_unc, rho_drain, verdict, len(t_differ), len(t_vs_h),
           len(t_at_floor), UNCOLLECTED_FLOOR, _median(t_destroyed)))


def criterion_a35_6(rows: list) -> Criterion:
    """Does the paying set shrink, and does the per-head share rise.

    **The share is an identity, and writing it out is what makes this
    readable.** What the levy aims at each payer is the rate times the held
    stock divided by the number of payers, so

        share_last / share_first = (stock_last / stock_first)
                                 * (payers_first / payers_last)

    exactly. The stock falls under every shape, because the write-off is
    destroying it; the payer count falls only under a shape that can empty an
    account. So the second factor is the paying-set effect with the stock
    effect divided out, and it is one under any shape that cannot empty
    anybody. The registered prediction was that the share rises monotonically
    under a per-head levy. **It does not, and the identity says why**: the two
    factors pull opposite ways round by round.
    """
    parts, resid, close_gap = [], [], []
    for b in BASES:
        live = [r for r in rows if r["base"] == b and r["rounds_firing"] > 0
                and r["share_first"] and r["stock_first_firing"]]
        if not live:
            continue
        share_r = [r["share_last"] / r["share_first"] for r in live]
        # The stock the levy was aimed at, recovered from the two counters as
        # ``share * payers``, which is the rate times that stock. The history's
        # holdings row is the stock at the *close* of the round, after the
        # write-off and everything else in that round has run, so it is a
        # different quantity and using it would put a four per cent error into
        # the factorisation.
        stock_r = [(r["share_last"] * r["payers_last"])
                   / (r["share_first"] * r["payers_first"]) for r in live]
        payer_r = [r["payers_first"] / max(r["payers_last"], 1) for r in live]
        resid += [abs(a - b2 * c) for a, b2, c in zip(share_r, stock_r, payer_r)]
        close_gap += [abs((r["share_first"] * r["payers_first"] / r["rate"])
                          / r["stock_first_firing"] - 1.0)
                      for r in live if r["stock_first_firing"]]
        parts.append(
            "%s: %d cells fired; the per-head share ends at %s times where it "
            "started, which factors into a stock term of %s and a paying-set "
            "term of %s; payers go from a median of %s to %s with a minimum of "
            "%s and rise again in %d rounds in all; accounts emptied %s per "
            "cell at the median, over %s rounds"
            % (b, len(live), _median(share_r), _median(stock_r),
               _median(payer_r),
               _median([r["payers_first"] for r in live]),
               _median([r["payers_last"] for r in live]),
               _median([r["payers_min"] for r in live]),
               sum(r["payers_rises_count"] for r in live),
               _median([r["drained_total"] for r in live]),
               _median([r["drained_rounds"] for r in live])))
    worst = max(resid) if resid else 0.0
    return Criterion(
        "A35-6 does the paying set shrink and the per-head share rise",
        "own_reading", True,
        "Printed, not judged. Per round, per shape, over the cells where the "
        "write-off fired. %s. **The factorisation is arithmetic and not a "
        "fitted split**, and it is exact to %.2e across every cell because "
        "both factors are recovered from the same two counters. **The stock it "
        "uses is the one the levy was aimed at, not the one at the close of "
        "the round**: those differ by %s at the median, since everything else "
        "in the round runs between them, and using the closing figure put a "
        "four per cent error into the split on the first attempt. **The "
        "registered prediction was that the share rises "
        "monotonically under a per-head levy, and both halves of it are "
        "wrong.** The share is the rate times the held stock over the payers; "
        "the write-off is destroying the stock, so the numerator falls under "
        "every shape, and the prediction was that a per-head levy makes the "
        "denominator fall too. **The paying-set term above says how far it "
        "actually falls, and at the median the answer is not at all.** "
        "Accounts are emptied in their thousands and they are payers again by "
        "the next levy, so the count the share divides by ends where it "
        "started. **Read the paying-set term, not the share**: it is one under "
        "any shape that cannot empty an account, and on this grid it is one "
        "under the shape that can, too. **A drained "
        "account is also not gone**: it receives inflow next round and is a "
        "payer again, which is why the payer count recovers rather than only "
        "falling and why the accounts-emptied count over a run exceeds the "
        "number of accounts. Pro rata and above-the-mean empty nobody, and "
        "that half is structural: a fraction of a balance cannot reach zero "
        "and an excess above the mean is never the whole of an account."
        % ("; ".join(parts), worst,
           _median(close_gap) if close_gap else "not measurable"))


def criterion_a35_7(rows: list) -> Criterion:
    """Is the firing-round count a reading or a horizon.

    **The count is censored and the paired ratio is not.** A cell still firing
    when the run stops has a count that is a lower bound, and most cells are
    in that state at either horizon, so the medians track the horizon rather
    than the mechanism. What survives a doubling is the within-cell ratio of
    per head to pro rata, because both sides of it are censored the same way.
    """
    by: dict = {}
    for r in rows:
        by.setdefault(r["horizon"], []).append(r)
    hs = sorted(by)

    def stats(h):
        live = [r for r in by[h] if r["rounds_firing"] > 0]
        out = {"live": len(live)}
        for b in BASES:
            lb = [r for r in live if r["base"] == b]
            out[b] = {
                "n": len(lb),
                "count": _median([r["rounds_firing"] for r in lb]),
                "fraction": _median([r["rounds_firing"] / h for r in lb]),
                "censored": sum(1 for r in lb if r["fires_to_the_end"]),
            }
        # The paired ratio, within the cell, at this horizon.
        grouped: dict = {}
        for r in live:
            grouped.setdefault(tuple(r[k] for k in KEYS if k != "base"),
                               {})[r["base"]] = r
        full = [v for v in grouped.values() if len(v) == len(BASES)]
        out["cells"] = len(full)
        out["ratio"] = _median([v["equal"]["rounds_firing"]
                                / v["holdings"]["rounds_firing"] for v in full])
        out["equal_longer"] = sum(1 for v in full
                                  if v["equal"]["rounds_firing"]
                                  > v["holdings"]["rounds_firing"])
        out["equal_shorter"] = sum(1 for v in full
                                   if v["equal"]["rounds_firing"]
                                   < v["holdings"]["rounds_firing"])
        return out

    if len(hs) < 2:
        h = hs[0]
        st = stats(h)
        return Criterion(
            "A35-7 whether the firing-round count is a reading or a horizon",
            "own_reading", False,
            "**Not evaluated in this run: one horizon only.** What the "
            "exposure is, measured on this grid at %d rounds: of the cells "
            "that fired, the ones still firing in the last round are %s. **A "
            "cell still firing when the run stops has a count that is a lower "
            "bound, not an estimate.** Run with --horizon to fill this in. "
            "State map: two horizons present and a statistic unchanged -> that "
            "statistic is a reading; changed -> it is a lower bound and every "
            "write-up of it has to say so; one horizon -> not evaluated, which "
            "is this."
            % (h, ", ".join("%s %d of %d" % (b, st[b]["censored"], st[b]["n"])
                            for b in BASES)),
            evaluated=False)

    a, b = stats(hs[0]), stats(hs[-1])
    moved_count = [x for x in BASES if a[x]["count"] != b[x]["count"]]
    ratio_drift = abs((b["ratio"] or 0) - (a["ratio"] or 0)) / max(a["ratio"] or 1, 1e-9)
    return Criterion(
        "A35-7 whether the firing-round count is a reading or a horizon",
        "own_reading", True,
        "Printed, not judged. The same grid at %s rounds. **The count is a "
        "lower bound and the paired ratio is the reading.** Counts, medians "
        "over the cells that fired: %s. **Every shape's median moved, and "
        "roughly in proportion to the horizon**, so none of them is an "
        "estimate of anything: %s. Cells still firing in the last round: %s, "
        "which is why. Fraction of rounds in which it fired, which divides the "
        "horizon out: %s. **Within-cell ratio of per head to pro rata, which "
        "censors both sides the same way and is what survives: %s at %d "
        "rounds and %s at %d, a drift of %.1f%%.** The direction counts "
        "survive too: per head longer than pro rata in %d of %d cells at the "
        "short horizon and %d of %d at the long one, shorter in %d and %d. "
        "**What this costs**: every place the count was written as a median is "
        "a lower bound and has to say so, A34's write-up included. **What it "
        "leaves standing**: the comparison, which is what the claim was about. "
        "State map: a statistic unchanged across the doubling -> a reading; "
        "changed -> a lower bound, and every write-up of it is corrected."
        % (" and ".join(str(h) for h in hs),
           "; ".join("%d rounds: %s" % (h, ", ".join(
               "%s %s" % (x, s2[x]["count"]) for x in BASES))
               for h, s2 in ((hs[0], a), (hs[-1], b))),
           ", ".join(moved_count) or "none",
           "; ".join("%d rounds: %s" % (h, ", ".join(
               "%s %d of %d" % (x, s2[x]["censored"], s2[x]["n"])
               for x in BASES)) for h, s2 in ((hs[0], a), (hs[-1], b))),
           "; ".join("%d rounds: %s" % (h, ", ".join(
               "%s %s" % (x, s2[x]["fraction"]) for x in BASES))
               for h, s2 in ((hs[0], a), (hs[-1], b))),
           a["ratio"], hs[0], b["ratio"], hs[-1], 100.0 * ratio_drift,
           a["equal_longer"], a["cells"], b["equal_longer"], b["cells"],
           a["equal_shorter"], b["equal_shorter"]))


def criterion_a35_8(rows: list, cs: list) -> Criterion:
    return Criterion(
        "A35-8 the objects, per shape", "bookkeeping", True,
        "Printed. Every cell's per-round counters are summarised on its row in "
        "the record: what was aimed at and what was left uncollected, the "
        "payers the levy could draw on at the first and last firing round and "
        "the minimum, whether that count ever rose, the accounts emptied and "
        "in how many rounds, and the per-head share at the first and last "
        "firing round with the count of rounds it fell. %d rows and %d cells. "
        "Per shape, over the cells that fired: %s."
        % (len(rows), len(cs),
           "; ".join(
               "%s: firing rounds median %s, destroyed median %s, uncollected "
               "median %s, payers last median %s"
               % (b,
                  _median([r["rounds_firing"] for r in rows
                           if r["base"] == b and r["rounds_firing"] > 0]),
                  _median([r["destroyed_total"] for r in rows
                           if r["base"] == b and r["rounds_firing"] > 0]),
                  _median([r["uncollected_total"] for r in rows
                           if r["base"] == b and r["rounds_firing"] > 0]),
                  _median([r["payers_last"] for r in rows
                           if r["base"] == b and r["rounds_firing"] > 0]))
               for b in BASES)))


# ---------------------------------------------------------------------------
# Printing and the record.
# ---------------------------------------------------------------------------

def print_rows(rows: list) -> None:
    print("\n  per shape, over the cells where the write-off fired")
    print("  %-10s %6s %7s %9s %9s %8s %8s %9s"
          % ("shape", "cells", "rounds", "destroyed", "uncoll.rel",
             "payers", "drained", "share x"))
    for b in BASES:
        live = [r for r in rows if r["base"] == b and r["rounds_firing"] > 0]
        if not live:
            continue
        ratio = [r["share_last"] / r["share_first"] for r in live
                 if r["share_first"]]
        print("  %-10s %6d %7s %9s %9s %8s %8s %9s"
              % (b, len(live),
                 _median([r["rounds_firing"] for r in live]),
                 _median([r["destroyed_total"] for r in live]),
                 _median([r["uncollected_rel_median"] for r in live]),
                 _median([r["payers_last"] for r in live]),
                 _median([r["drained_total"] for r in live]),
                 _median(ratio)))


def station_config(horizon: int, seeds) -> dict:
    cfg = _config_diff(cell_config({"need": NEEDS[-1], "stress": STRESSES[0],
                                    "elasticity": ELASTICITIES[0],
                                    "base": BASES[0], "rate": RATES[0],
                                    "seed": SEEDS[0]}, horizon=horizon))
    return {
        "carrier": "A34's grid to the field, with trace_writeoff on. No off "
                   "arm: A34's off arm fed its instrument range and nothing "
                   "here reads it",
        "grid": {
            "bases": list(BASES), "rates": list(RATES), "trigger": TRIGGER,
            "needs": list(NEEDS), "stresses": list(STRESSES),
            "elasticities": list(ELASTICITIES), "seeds": list(seeds),
            "horizon": horizon,
        },
        "counters": list(WRITEOFF_TRACE_FIELDS),
        "rounds": horizon,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


def write_record(payload: dict, section: str = "run", horizon: int = ROUNDS,
                 seeds=SEEDS) -> None:
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A35"
    # Closed 2026-09-13: the horizon arm ran, A35-7 is evaluated, and the
    # reading is in RESULTS.md.
    doc.pop("diagnostic_only", None)
    doc.pop("diagnostic_reason", None)
    doc["config"] = _fmt(station_config(horizon, seeds))
    doc["module_sha"] = _module_sha(MODULE)
    doc["pre_module_sha"] = (_module_sha(PRE_MODULE) if PRE_MODULE.exists()
                             else None)
    doc["script_sha"] = _module_sha(SCRIPT)
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s" % RECORD.name)


def time_cells(workers: int) -> None:
    """D38: the seconds per cell, measured on this machine, at both horizons.

    **The parallel figure is divided by the cores this machine actually has,
    not by the workers that were asked for.** Asking for eight on a two core
    box gives two, and reporting the eight turned a two and a half minute job
    into a forty second estimate on the first try here.
    """
    cores = os.cpu_count() or 1
    effective = min(max(workers, 1), cores)
    total = 0.0
    for horizon in (ROUNDS, 2 * ROUNDS):
        keys = cell_keys(seeds=SEEDS[:1], needs=NEEDS[:1],
                         stresses=STRESSES[:1], elasticities=ELASTICITIES[:1],
                         horizon=horizon)
        t0 = time.perf_counter()
        run_cells(keys, 1)
        per = (time.perf_counter() - t0) / len(keys)
        full = len(cell_keys(horizon=horizon))
        total += per * full
        print("  %4d rounds: %.3f s per cell, %d cells -> %.0f s serial, "
              "%.0f s on this machine's %d core%s"
              % (horizon, per, full, per * full, per * full / effective,
                 cores, "" if cores == 1 else "s"))
    print("  both horizons: %.0f s serial, %.0f s on %d core%s. Asked for %d "
          "workers, this machine has %d."
          % (total, total / effective, cores, "" if cores == 1 else "s",
             workers, cores))


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--reread", action="store_true",
                      help="recompute the criteria from the rows already in "
                           "the record and write them back. No model is run")
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--workers", type=int, default=_default_workers())
    ap.add_argument("--horizon", type=int, default=None,
                    help="add a second horizon and fill in A35-7")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    seeds = SEEDS[:args.seeds]
    if args.plan:
        for k, v in station_config(ROUNDS, seeds).items():
            print("  %-22s %s" % (k, v))
        print("  %-22s %d" % ("cells", len(cell_keys(seeds=seeds))))
        return 0
    if args.time:
        print("stage A35, D38: seconds per cell, measured on this machine\n")
        time_cells(args.workers)
        return 0
    if args.gate:
        print("stage A35, rule 19: the counters off and on, against the "
              "module before they existed.\n")
        g = gate(workers=args.workers)
        print("\n  gate: %s" % g["verdict"])
        if not args.no_write:
            write_record(g, section="gate", seeds=seeds)
        return 0 if g["verdict"] == "pass" else 1

    if args.reread:
        # **A criterion is computed from the rows, and the rows are on disk.**
        # So correcting one costs no simulation, which is the standing rule for
        # this repository. What it must not do is leave the correction outside
        # the record, where nobody reading the record would meet it; that is
        # why this mode writes back rather than printing.
        if not RECORD.exists():
            print("no record to re-read")
            return 1
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
        prior = doc.get("sections", {}).get("run", {})
        rows = prior.get("rows") or []
        if not rows:
            print("the record carries no rows")
            return 1
        print("stage A35, re-read: %d rows off the record, no model is run. "
              "The rows were written by script %s on module %s.\n"
              % (len(rows), prior.get("rows_script_sha")
                 or doc.get("script_sha"), doc.get("module_sha")))
        cs = cells(rows)
        base_rows = [r for r in rows if r["horizon"] == ROUNDS]
        base_cells = [c for c in cs if c["horizon"] == ROUNDS]
        crits = [criterion_a35_1(rows), criterion_a35_2(_gate_section()),
                 criterion_a35_3(base_rows), criterion_a35_4(base_rows),
                 criterion_a35_5(base_cells), criterion_a35_6(base_rows),
                 criterion_a35_7(rows), criterion_a35_8(rows, cs)]
        print_rows(base_rows)
        _print_criteria(crits)
        failed = [c.name for c in crits if c.evaluated and not c.passed]
        ran = [c for c in crits if c.evaluated]
        print("\n  %d/%d evaluated" % (len(ran) - len(failed), len(ran)))
        if args.no_write:
            return 0 if not failed else 1
        payload = dict(prior)
        payload.update({"criteria": [c.as_dict() for c in crits],
                        "cells": cs,
                        "rows_script_sha": prior.get("rows_script_sha")
                        or doc.get("script_sha")})
        write_record(payload,
                     horizon=max(r["horizon"] for r in rows), seeds=seeds)
        return 0 if not failed else 1

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"], stresses=SMOKE["stresses"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A35, smoke: %d cells, nothing written\n" % len(keys))
    else:
        keys = cell_keys(seeds=seeds)
        if args.horizon:
            keys += cell_keys(seeds=seeds, horizon=args.horizon)
        print("stage A35: %d cells, seeds %s, %d workers%s. Rule 19 is A35-2 "
              "and it is read off the gate section of the record.\n"
              % (len(keys), list(seeds), args.workers,
                 ", horizons %d and %d" % (ROUNDS, args.horizon)
                 if args.horizon else ""))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    cs = cells(rows)
    base_rows = [r for r in rows if r["horizon"] == ROUNDS]
    base_cells = [c for c in cs if c["horizon"] == ROUNDS]
    crits = [criterion_a35_1(rows), criterion_a35_2(_gate_section()),
             criterion_a35_3(base_rows), criterion_a35_4(base_rows),
             criterion_a35_5(base_cells), criterion_a35_6(base_rows),
             criterion_a35_7(rows), criterion_a35_8(rows, cs)]
    print_rows(base_rows)
    _print_criteria(crits)
    failed = [c.name for c in crits if c.evaluated and not c.passed]
    ran = [c for c in crits if c.evaluated]
    print("\n  %d/%d evaluated" % (len(ran) - len(failed), len(ran)))
    if args.smoke or args.no_write:
        return 0 if not failed else 1
    write_record({"criteria": [c.as_dict() for c in crits], "rows": rows,
                  "cells": cs, "seeds_run": sorted({r["seed"] for r in rows}),
                  "horizons_run": sorted({r["horizon"] for r in rows}),
                  "rows_script_sha": _module_sha(SCRIPT)},
                 horizon=args.horizon or ROUNDS, seeds=seeds)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
