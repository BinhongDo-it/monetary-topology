"""A33: the same controller's other half, and where its claims land.

A32 read that a controller absorbs incidence: where a rule's amount is whatever
closes a gap in the very quantity the subsistence floor is read against, moving
the position, the shape or the ratio of what it takes changes nobody's place
relative to the floor. 585 paired cells, no counterexample. **That reading
stands on one mechanism**, the withdrawal, because it is the only one whose
incidence had been swept while such a controller ran.

This station gives it a second, independent case, and it is the other half of
the same controller: the issuance, whose landing is ``injection_target``.

**The dial is not new and this station is not a repeat.** It is swept in A2d, A4
and A9, and read there against concentration, the support size and the wage
share. What no record on disk carries is a reading of it against the count below
the floor, and that count is what the claim is about. A9 shows the landing does
move other readouts: two landings on one cell there read a retained wage share
of 0.0333 against 0.0586. So the claim being tested is narrow and could fail.

**The instrument's range comes before the reading.** A grid that cannot move the
count says nothing when it reads no movement, and this station's own history is
the reason that is written into a criterion: A31's zero only became a reading
when the same grid was shown to move a block of 75 nodes. So a third arm runs
with the authority off, and A33-2 prints how far the count travels against it.

Registered design: the criteria are written in this script, the record carries
their text, and every quantity this run produced is reported.

    python experiments/a33_injection_landing.py --plan
    python experiments/a33_injection_landing.py --time
    python experiments/a33_injection_landing.py --run --smoke
    python experiments/a33_injection_landing.py --run --workers 8
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
    MonetaryAuthority, NetworkConfig, INJECTION_TARGETS)

RECORD = RESULTS / "a33_injection_landing.json"
MODULE = SRC / "network.py"
SCRIPT = Path(__file__).resolve()


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


_A30 = _load(ROOT / "experiments" / "a30_shock.py", "_a30_for_a33")
_A31 = _load(ROOT / "experiments" / "a31_withdrawal.py", "_a31_for_a33")

_fmt = _A30._fmt
_config_diff = _A30._config_diff
_module_sha = _A30._module_sha
_num = _A30._num
_median = _A30._median
_range = _A30._range
_tally = _A30._tally
_default_workers = _A30._default_workers
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

#: The landings the module offers, plus the arm that measures how far the count
#: can travel on this grid at all. ``off`` feeds A33-2 and nothing else.
LANDINGS: tuple[str, ...] = INJECTION_TARGETS
ARMS: tuple[str, ...] = ("off",) + LANDINGS
#: Same source and same number as A31's, and for the same reason: it is a
#: measured "does not decide" rather than a chosen line. **It is kept, and it
#: is expected to bite on nearly every cell here**, because this mechanism is
#: the issuing half: moving the landing changes how much the controller has to
#: issue, measured at about ten per cent on this carrier, so the amount cannot
#: be held fixed while the landing moves. That is a property of a controller
#: and not a defect, and it is why the reading below leans on the second line.
SPREAD_LINE = 0.0191
#: The second line, and the one that carries the reading here. A gap of a
#: single node is the discrete jitter this carrier already has: A18_C measured
#: the same dial family over 135 paired cells, found the count moving in 30 of
#: them and 23 of those by one node in both directions, and named that jitter
#: as measured in A18_B6. So a gap of two or more is the tier that asks a
#: question, and it is read against the range A33-2 prints rather than against
#: any constant.
JITTER = 1
#: The smoke runs on the strain where the authority actually issues. Measured
#: before this was written: over 300 rounds at wage elasticity 0.5 the rule
#: issues about 424 on ``leak``, about 0.25 on ``healthy`` at the three
#: shallower floors and nothing at all on ``leak_recycled``, where the
#: pass-down already fills the gap. A smoke on an idle carrier reads three
#: equal integers and calls it agreement.
SMOKE = {"needs": (0.20,), "stresses": ("leak",), "seeds": SEEDS[:2],
         "elasticities": (0.5,)}
KEYS: tuple[str, ...] = ("need", "stress", "elasticity", "arm", "seed")


def cell_keys(seeds=SEEDS, needs=NEEDS, stresses=STRESSES,
              elasticities=ELASTICITIES, arms=ARMS) -> list:
    return [{"need": n, "stress": s, "elasticity": e, "arm": a, "seed": d}
            for n in needs for s in stresses for e in elasticities
            for a in arms for d in seeds]


def cell_config(key: dict) -> NetworkConfig:
    """A30's carrier. The only field that moves across arms is the landing,
    and the ``off`` arm is A30's own no-authority cell."""
    rule = "none" if key["arm"] == "off" else "endogenous"
    cfg = _A30.cell_config({"need": key["need"], "stress": key["stress"],
                            "elasticity": key["elasticity"],
                            "authority": rule, "seed": key["seed"]})
    if key["arm"] == "off":
        return cfg
    return dataclasses.replace(cfg, injection_target=key["arm"])


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net, seen = drive(cfg, "none", 0.0)
    h = net._history
    holdings = np.asarray(h.holdings, dtype=float)
    close = holdings[-1]
    l1 = np.zeros(close.size, dtype=bool)
    l1[net._l1] = True
    issued = np.asarray(h.issuance, dtype=float)
    circ = holdings.sum(axis=1)
    wages = getattr(h, "wage_paid", None)
    target = float(net._baseline_active or 0.0)
    l2in = np.asarray(h.layer2_inflow, dtype=float)
    order = np.sort(close)[::-1]
    total = float(close.sum())
    row = dict(key)
    row.update({
        "books_close": seen["books"],
        "below_close": int(net._below.sum()),
        "issued_total": _num(float(issued.sum())),
        "circulating_tail": _num(float(circ[-TAIL:].mean())),
        "support_close": int((close > 0.0).sum()),
        "l1_share_close": _num(float(close[l1].sum()) / total)
                          if total > 0 else None,
        "top1_close": _num(float(order[:max(1, close.size // 100)].sum())
                           / total) if total > 0 else None,
        "gini_close": _num(_gini(close)),
        "wage_paid_total": _num(float(np.asarray(wages, dtype=float).sum()))
                           if wages is not None else None,
        "l2_over_target_tail": _num(float(((l2in[-TAIL:] - target)
                                          / target).mean()))
                               if target > 0 else None,
        # A33-0's object, and it is measured off the run rather than
        # derived from the arm's name. The first version of this criterion
        # computed the landing share from the label, which made it a check
        # that could not fail, and it duly passed on a carrier where the
        # authority issued nothing at all.
        "injection_node_share_close": _num(float(close[net.injection_node])
                                           / total) if total > 0 else None,
        "issued_rounds": int((issued > 0.0).sum()),
    })
    return row


def _gini(v: np.ndarray) -> float:
    x = np.sort(np.maximum(np.asarray(v, dtype=float), 0.0))
    n = x.size
    s = x.sum()
    if n == 0 or s <= 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2.0 * (idx * x).sum()) / (n * s) - (n + 1.0) / n)


def _row_key(x: dict) -> tuple:
    return (x["need"], STRESSES.index(x["stress"]), x["elasticity"],
            ARMS.index(x["arm"]), x["seed"])


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

LANDING_STATES: tuple[tuple[str, str], ...] = (
    ("the landing does not decide", "the two landings leave the same count "
     "below the floor at this carrier and seed"),
    ("the landing decides", "they do not, and the issuance totals differ by "
     "at most %.4f" % SPREAD_LINE),
    ("differs, and so do the totals: not adjudicated", "they do not, and the "
     "issuance totals differ by more than %.4f, so the amount is moving too "
     "and this cell is read neither way" % SPREAD_LINE),
    ("nothing issued: the dial had no object", "the rule asked for nothing on "
     "this carrier, so the landing placed nothing and an equal count says "
     "nothing about it. Not read either way"),
    ("no trace by the close: too little was issued to read", "the rule issued "
     "something, and by the close the two landings leave the same share on the "
     "injection node to six figures, so the placement did not survive to the "
     "round the count is read at. Not read either way"))


def pairs(rows: list) -> list:
    """Every carrier and seed, the two landings against each other and each
    against the arm with no authority."""
    by = {}
    for r in rows:
        by.setdefault((r["need"], r["stress"], r["elasticity"], r["seed"]),
                      {})[r["arm"]] = r
    out = []
    for key in sorted(by, key=lambda k: (k[0], STRESSES.index(k[1]), k[2], k[3])):
        here = by[key]
        if not all(a in here for a in LANDINGS):
            continue
        counts = {a: here[a]["below_close"] for a in LANDINGS}
        issued = [here[a]["issued_total"] for a in LANDINGS]
        spread = ((max(issued) - min(issued)) / min(issued)
                  if all(issued) and min(issued) > 0 else None)
        same = len(set(counts.values())) == 1
        traced = len({here[a]["injection_node_share_close"]
                      for a in LANDINGS}) > 1
        if max(issued) <= 0.0:
            # The rule never asked for anything here, so the dial had nothing
            # to place and an equal count says nothing about it.
            state = "nothing issued: the dial had no object"
        elif not traced:
            state = "no trace by the close: too little was issued to read"
        elif same:
            state = "the landing does not decide"
        elif spread is None or spread > SPREAD_LINE:
            state = "differs, and so do the totals: not adjudicated"
        else:
            state = "the landing decides"
        off = here.get("off")
        out.append({
            "need": key[0], "stress": key[1], "elasticity": key[2],
            "seed": key[3],
            "below_close": counts,
            "below_gap": int(max(counts.values()) - min(counts.values())),
            "issued": {a: here[a]["issued_total"] for a in LANDINGS},
            "issued_spread": _num(spread),
            "issued_any": bool(max(issued) > 0.0),
            "injection_node_share": {a: here[a]["injection_node_share_close"]
                                     for a in LANDINGS},
            # Did the dial leave any trace by the close? Where the rule issues
            # a thousandth of the stock over 300 rounds, trading has wiped the
            # difference out before anything is read, and an equal count there
            # is not evidence either way.
            "left_a_trace": len({here[a]["injection_node_share_close"]
                                 for a in LANDINGS}) > 1,
            "issued_over_circulating": _num(
                max(issued) / here[LANDINGS[0]]["circulating_tail"])
                if here[LANDINGS[0]]["circulating_tail"] else None,
            "state": state,
            "against_no_authority": (
                {a: int(counts[a] - off["below_close"]) for a in LANDINGS}
                if off else None),
            "other_readouts": {
                a: {k: here[a][k] for k in
                    ("gini_close", "support_close", "circulating_tail",
                     "l1_share_close", "top1_close", "wage_paid_total")}
                for a in LANDINGS},
        })
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a33_0(rows: list, pr: list) -> Criterion:
    live = [p for p in pr if p["issued_any"]]
    dead = [p for p in pr if not p["issued_any"]]
    by_strain = {}
    for p in pr:
        by_strain.setdefault(p["stress"], [0, 0])[0 if p["issued_any"] else 1] += 1
    shares = []
    moved = 0
    for p in live:
        v = [p["injection_node_share"][a] for a in LANDINGS]
        if all(x is not None for x in v):
            shares.append(tuple(v))
            if len(set(v)) > 1:
                moved += 1
    ok = bool(live) and moved > 0
    return Criterion(
        "A33-0 the dial carries something, measured off the run (D28)",
        "instrument", ok,
        "**Measured, not derived from the arm's name.** The first version of "
        "this criterion computed the landing share from the label, which made "
        "it a check that could not fail, and it passed on a carrier where the "
        "authority issued nothing at all. What is read instead is the share of "
        "the closing stock held by the injection node, which is where "
        "``top_node`` puts every claim it creates and where ``uniform`` puts "
        "one node's worth. Cells where the rule issued anything: %d of %d, by "
        "strain %s. Of the live ones, %d of %d have the two landings leaving a "
        "different share on that node. State map: at least one live cell where "
        "the dial left a trace -> PASS; none -> FAIL, and A33-3 would be "
        "reading one arm twice. **Neither the idle cells nor the traceless "
        "ones are failures**, and both are held out of A33-3 in states of "
        "their own: the first had nothing to place, and in the second the "
        "placement did not survive to the round the count is read at. **The "
        "two groups part at about five thousandths of the circulating stock**, "
        "on what was issued over what circulates: %s where a trace survives, "
        "%s where it does not. The bands abut rather than stand apart, and "
        "the only cells near the cut are on the strain where the rule issues "
        "a fraction of a per cent; everything the other side of it issues "
        "several times the stock. The first version of this criterion "
        "required every live cell to show a trace and failed the station on "
        "the second group, which is the same error as reading an idle "
        "carrier: a cell with no object is a state, not a fault."
        % (len(live), len(pr),
           {k: {"issued": v[0], "idle": v[1]} for k, v in sorted(by_strain.items())},
           moved, len(shares),
           _range([x["issued_over_circulating"] for x in live
                   if x["left_a_trace"]
                   and x["issued_over_circulating"] is not None]),
           _range([x["issued_over_circulating"] for x in live
                   if not x["left_a_trace"]
                   and x["issued_over_circulating"] is not None])))


def criterion_a33_1(rows: list) -> Criterion:
    books = sum(1 for r in rows if r["books_close"])
    per = {a: [r["issued_total"] for r in rows if r["arm"] == a]
           for a in LANDINGS}
    return Criterion(
        "A33-1 the books close, and the issued total is an output",
        "instrument", books == len(rows),
        "Asserted every round in the loop: the claim total equals held plus "
        "parked to %.0e of the opening stock. Read back here: %d of %d cells "
        "close. The total issued over 300 rounds, by landing: %s. **These are "
        "not required to match and are printed rather than judged**: this is a "
        "controller, so what it issues is an output of the loop and a landing "
        "that feeds the inflow less efficiently issues more, which A33-3 then "
        "has to hold apart from the landing itself."
        % (LEDGER_TOL, books, len(rows),
           "; ".join("%s median %s, %s" % (a, _median(per[a]), _range(per[a]))
                     for a in LANDINGS)))


def criterion_a33_2(pr: list) -> Criterion:
    gaps = [v for p in pr if p["against_no_authority"]
            for v in p["against_no_authority"].values()]
    spectrum = {}
    for v in gaps:
        spectrum[v] = spectrum.get(v, 0) + 1
    moved = sum(n for v, n in spectrum.items() if abs(v) >= BLOCK)
    return Criterion(
        "A33-2 how far the count travels on this grid at all", "own_reading",
        True,
        "Printed, not judged, **and printed before the reading it qualifies**. "
        "Each landing against the same carrier and seed with the authority "
        "switched off: the count below the floor differs by %s over %d "
        "comparisons, so a block of %d or more moves in %d of them. A grid "
        "that cannot move the count says nothing when it reads no movement, "
        "and that is not a hypothetical here: A31's zero became a reading only "
        "once the same grid was shown to move a block."
        % (dict(sorted(spectrum.items())), len(gaps), BLOCK, moved))


def criterion_a33_3(pr: list) -> Criterion:
    tally = _tally(p["state"] for p in pr)
    live = [p for p in pr if p["issued_any"] and p["left_a_trace"]]
    traceless = [p for p in pr if p["issued_any"] and not p["left_a_trace"]]
    differ = [p for p in live if p["below_gap"]]
    spreads = [p["issued_spread"] for p in live
               if p["issued_spread"] is not None]
    lines = ["need %.2f %s e %.1f seed %d: %s, gap %d, issued spread %s"
             % (p["need"], p["stress"], p["elasticity"], p["seed"],
                p["below_close"], p["below_gap"], p["issued_spread"])
             for p in differ[:10]]
    return Criterion(
        "A33-3 does where the issuance lands change who is below the floor",
        "own_reading", True,
        "Printed, not judged. The registered reading: at a fixed carrier and "
        "seed, the two landings against each other. **A32's claim predicts "
        "they leave the same count**, and this is the second mechanism it "
        "rests on rather than a repeat of the first, because this is the "
        "issuance and A31 swept the withdrawal. **The reading runs over the "
        "cells where the rule issued something and the placement still showed "
        "at the close**, %d of %d, holding out %d idle cells and %d where too "
        "little was issued for the landing to survive to the round the count "
        "is read at. An equal count in either of those is not evidence. "
        "%d of those leave a different count. Relative "
        "spread of the issued totals: median %s, %s, **which is why nearly "
        "every cell reads as not adjudicated against that line: the landing "
        "moves the amount, because this is a controller and the amount is its "
        "output**. So the reading leans on the second line instead. Gaps of a "
        "single node, which is the jitter A18_C measured on this carrier "
        "family and attributed to A18_B6: %d. **Gaps of two or more nodes: "
        "%d**, against the %d nodes A33-2 shows this grid can move. States: "
        "%s. Counts by state, over every cell: %s. Where they differ: %s."
        % (len(live), len(pr), len(pr) - len(live) - len(traceless),
           len(traceless), len(differ), _median(spreads), _range(spreads),
           sum(1 for p in differ if p["below_gap"] <= JITTER),
           sum(1 for p in differ if p["below_gap"] > JITTER), BLOCK,
           "; ".join("%s = %s" % x for x in LANDING_STATES), tally,
           "; ".join(lines) if lines else "nowhere"))


def criterion_a33_4(pr: list) -> Criterion:
    fields = ("gini_close", "support_close", "circulating_tail",
              "l1_share_close", "top1_close", "wage_paid_total")
    lines = []
    pr = [p for p in pr if p["issued_any"] and p["left_a_trace"]]
    for f in fields:
        diffs = []
        for p in pr:
            vals = [p["other_readouts"][a][f] for a in LANDINGS]
            if all(v is not None for v in vals) and min(vals) != 0:
                diffs.append(abs(max(vals) - min(vals)) / abs(min(vals)))
        moved = sum(1 for d in diffs if d > 1e-9)
        lines.append("%s: %d of %d pairs differ, relative gap median %s, %s"
                     % (f, moved, len(diffs), _median(diffs), _range(diffs)))
    return Criterion(
        "A33-4 what the landing does move", "bookkeeping", True,
        "Printed. The same pairs, read on the quantities the earlier sweeps of "
        "this dial reported. %s. **This is the scope statement standing on its "
        "own grid**: A32 borrowed A9's numbers for it, and the point it makes "
        "is that a controller absorbing a landing's effect on the count below "
        "the floor is not a claim that it absorbs that landing everywhere."
        % "; ".join(lines))


# ---------------------------------------------------------------------------
# Printing, timing and the record.
# ---------------------------------------------------------------------------

def print_pairs(pr: list) -> None:
    print("\n  A33-2 and A33-3, carrier by carrier. below_close reads "
          "%s; against-off is each landing minus the no-authority arm."
          % " / ".join(LANDINGS))
    print("  %-5s %-14s %-4s %-5s %-14s %6s %-16s %9s  %s"
          % ("need", "strain", "e", "seed", "below_close", "gap",
             "against off", "issued sp", "state"))
    for p in pr:
        print("  %-5.2f %-14s %-4.1f %-5d %-14s %6d %-16s %9s  %s"
              % (p["need"], p["stress"], p["elasticity"], p["seed"],
                 "/".join(str(p["below_close"][a]) for a in LANDINGS),
                 p["below_gap"],
                 "/".join(str(p["against_no_authority"][a]) for a in LANDINGS)
                 if p["against_no_authority"] else "n/a",
                 p["issued_spread"], p["state"]))


def time_cells(repeats: int = 3, workers: int = 1) -> None:
    sample = [{"need": 0.20, "stress": s, "elasticity": 0.5, "arm": a,
               "seed": SEEDS[0]} for s in STRESSES for a in ARMS]
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
                                    "arm": LANDINGS[0], "seed": SEEDS[0]}))
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
                   "rescue, no shock. Every reading is on the unshocked run",
        "rounds": ROUNDS,
        "rule": ("the endogenous rule issues the Layer 2 inflow's shortfall "
                 "below its round 0 level. ``injection_target`` names where "
                 "that issuance arrives: top_node puts all of it on the "
                 "injection node, uniform spreads it over every node. The "
                 "withdrawal switch is off throughout: this station reads the "
                 "issuing half of the controller, A31 read the taking half"),
        "grid": {"need_multiples": list(NEEDS),
                 "stresses": {s: STRESS_SPECS[s] for s in STRESSES},
                 "elasticities": list(ELASTICITIES),
                 "arms": list(ARMS),
                 "arm_off_is": "the same carrier with authority rule=none, "
                               "which feeds A33-2 and no other reading",
                 "seeds": list(SEEDS)},
        "park_target": _A30.TARGET,
        "tail": TAIL, "block": BLOCK,
        "ledger_tolerance": LEDGER_TOL,
        "issued_spread_line": SPREAD_LINE,
        "non_default_fields": cfg,
    }


def write_record(payload: dict) -> None:
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A33"
    # Closed 2026-09-12: the reading is in RESULTS.md and the numbers were
    # re-derived from this record before it was closed.
    doc.pop("diagnostic_only", None)
    doc.pop("diagnostic_reason", None)
    doc["config"] = _fmt(station_config())
    doc["script_sha"] = _module_sha(SCRIPT)
    doc["module_sha"] = _module_sha(MODULE)
    doc.setdefault("sections", {})["run"] = _fmt(payload)
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
        print("stage A33, D38: seconds per cell, measured on this machine\n")
        time_cells(workers=args.workers)
        return 0

    if args.smoke:
        keys = cell_keys(needs=SMOKE["needs"], stresses=SMOKE["stresses"],
                         elasticities=SMOKE["elasticities"],
                         seeds=SMOKE["seeds"])
        print("stage A33, smoke: %d cells, nothing written\n" % len(keys))
    else:
        seeds = SEEDS[:args.seeds]
        keys = cell_keys(seeds=seeds)
        print("stage A33: %d cells, seeds %s, %d workers. No module change, "
              "so rule 19 has no object here: injection_target is a field the "
              "module already carries.\n"
              % (len(keys), list(seeds), args.workers))
    t0 = time.perf_counter()
    rows = run_cells(keys, args.workers)
    print("   ran %d cells in %.0f s" % (len(rows), time.perf_counter() - t0))
    pr = pairs(rows)
    crits = [criterion_a33_0(rows, pr), criterion_a33_1(rows),
             criterion_a33_2(pr), criterion_a33_3(pr), criterion_a33_4(pr)]
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
