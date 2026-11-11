"""A58: the balance-sheet recession and zombie lending, on one cell, taken apart.

Japan in the 1990s and early 2000s had two mechanisms at once, and the record
cannot separate them.

    zombie      existing creditors keep feeding the borrowers below the line,
                along the edges they already lend on, and public capital lands
                on those creditors (Peek and Rosengren 2005; Caballero, Hoshi
                and Kashyap 2008). Here: A18_B's ``resupply`` with
                ``funding = "issuance"`` and its ``retain``.
    deleveraging  firms carry a stock of debt from before, repay a share of it
                every round ahead of their own spending, and what the creditors
                collect leaves circulation (Koo). Here: a second ledger opened
                at construction, owed by the intermediate block to the
                financial nodes each firm already pays upward, serviced at
                ``repay_k`` with A18_D's seniority, and A18_E's parking on the
                financial layer.

The rescue ledger is left alone: ``ResupplySpec.repay`` stays zero, so the
rescue is A18_B's gift on every arm and the zombie side means the same thing
whether or not the debt is on. With no opening debt the subclass is ``Network``.

    python experiments/a58_koo_zombie.py --gate
    python experiments/a58_koo_zombie.py --selftest
    python experiments/a58_koo_zombie.py --time
    python experiments/a58_koo_zombie.py --run [--workers N]
    python experiments/a58_koo_zombie.py --tables
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import Network, ParkSpec, ResupplySpec, WriteOffSpec  # noqa: E402

RECORD = RESULTS / "a58_koo_zombie.json"
A18_SCRIPT = ROOT / "experiments" / "a18_policy_paths.py"
A54_SCRIPT = ROOT / "experiments" / "a54_penalty.py"
STAGE = "A58"


def _load(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_A18 = _load(A18_SCRIPT, "a18_for_a58")
_A54 = _load(A54_SCRIPT, "a54_for_a58")
r = _A18.r

MODE = "drawdown"
FUNDING = "issuance"
CELLS = ((0.20, 1.0), (0.50, 2.0))       # A18_B's Japan cell; the retention sweep's cell
SEEDS = tuple(_A18.SEEDS)
RETAINS = (0.0, 0.5, 0.9, 0.95, 1.0)
D0S = (50.0, 100.0)                      # opening debt, in units of the opening stock of 100
REPAYS = (0.05, 0.20)                    # from A18_D's measured REPAY_LEVELS
PARKS = tuple(_A18.PARK_MULTIPLIER_LEVELS)   # (0, 0.20, 0.50), A18_E5's
COLLECTED = (0.20, 0.50, 1.0)            # share of each collected repayment the creditor parks
OFF = None


@dataclass(frozen=True)
class Koo:
    d0: float
    repay: float
    park: float
    #: Share of what a creditor collects on the opening debt that it parks at
    #: once, the rest of its holdings untouched. Zero keeps the label and the
    #: run of the states recorded before this switch existed.
    collected: float = 0.0

    def label(self) -> str:
        base = "D0=%g repay=%g park=%g" % (self.d0, self.repay, self.park)
        return base if self.collected <= 0.0 else base + " collected=%g" % self.collected


KOO_HOLDINGS = tuple(Koo(d, k, p) for d in D0S for k in REPAYS for p in PARKS)
KOO_COLLECTED = tuple(Koo(d, k, 0.0, c) for d in D0S for k in REPAYS for c in COLLECTED)
KOO_STATES = (OFF,) + KOO_HOLDINGS + KOO_COLLECTED
ZOMBIE_STATES = (OFF,) + RETAINS


@dataclass
class Criterion:
    name: str
    kind: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "passed": self.passed, "detail": self.detail}


# -- the model ---------------------------------------------------------------

class KooNetwork(Network):
    """``Network`` plus a stock of firm debt opened at construction.

    ``[i, j]`` is what firm ``j`` owes financial node ``i``. A firm's creditors
    are the financial nodes it already pays upward; the stock is split evenly
    across firms and, within a firm, across its creditors. Serviced every round
    at ``repay_k`` of the balance, before discretionary spending, from what the
    firm holds, to creditors still trading; what cannot be paid stays owed.
    Conservative: the ledger moves, the claim total does not.
    """

    def __init__(self, config, d0: float = 0.0, repay_k: float = 0.0, collected: float = 0.0):
        super().__init__(config)
        n = self.holdings.size
        self._bubble = np.zeros((n, n))
        self._bubble_d0 = float(d0)
        self._bubble_repay = float(repay_k)
        self._bubble_repaid = 0.0
        self._bubble_collected = float(collected)
        self._bubble_parked = 0.0
        if d0 <= 0.0:
            return
        fin = np.asarray(self._l1)
        firms = np.asarray(self._mid)
        per_firm = d0 / firms.size
        for j in firms:
            creds = fin[self.adjacency[j, fin] > 0]
            if creds.size == 0:
                raise ValueError("firm %d pays no financial node" % j)
            self._bubble[creds, j] = per_firm / creds.size

    def _repay_flow(self):
        base = super()._repay_flow()
        if self._bubble_repay <= 0.0 or not self._bubble.any():
            return base
        ledger = self._bubble
        owed_by = ledger.sum(axis=0)
        due = self._bubble_repay * owed_by
        pay = np.minimum(due, np.maximum(self.holdings, 0.0))
        pay = np.where(self._alive, pay, 0.0)
        matrix = np.zeros((self._n, self._n))
        for j in np.flatnonzero(pay > 0.0):
            claims = ledger[:, j] * self._alive
            total = float(claims.sum())
            if total <= 0.0:
                continue
            amounts = pay[j] * (claims / total)
            matrix[j, :] += amounts
            ledger[:, j] -= amounts
            self.holdings[j] -= pay[j]
            self.holdings += amounts
            self._bubble_repaid += float(pay[j])
            if self._bubble_collected > 0.0:
                # Koo's narrower claim: what comes back is not lent out again.
                # Only the collection is parked; the creditor's other holdings
                # circulate as before. Holdings plus parked is unchanged.
                parked = self._bubble_collected * amounts
                self.holdings -= parked
                self._parked += parked
                self._bubble_parked += float(parked.sum())
        np.clip(ledger, 0.0, None, out=ledger)
        if not matrix.any():
            return base
        return matrix if base is None else base + matrix


def config(need: float, rate: float, seed: int, zombie, koo):
    cfg = _A18.config_for(MODE, WriteOffSpec(), "endogenous", need, seed, resupply_rate=0.0)
    if zombie is not OFF:
        cfg = dataclasses.replace(cfg, resupply=ResupplySpec(rate=rate, funding=FUNDING, retain=zombie))
    if koo is not OFF and koo.park > 0.0:
        cfg = dataclasses.replace(cfg, park=ParkSpec(rate=koo.park))
    return cfg


def build(need, rate, seed, zombie, koo) -> KooNetwork:
    cfg = config(need, rate, seed, zombie, koo)
    if koo is OFF:
        return KooNetwork(cfg)
    return KooNetwork(cfg, d0=koo.d0, repay_k=koo.repay, collected=koo.collected)


def run_one(job: tuple) -> dict:
    need, rate, seed, zombie, koo = job
    net = build(need, rate, seed, zombie, koo)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)[-1]
    circ = float(np.asarray(h.total_claims, dtype=float)[-1])
    parked = float(np.asarray(h.parked, dtype=float)[-1])
    out = float(net._bubble.sum())
    return {
        "need": float(need), "rate": float(rate), "seed": int(seed),
        "zombie": None if zombie is OFF else float(zombie),
        "koo": None if koo is OFF else koo.label(),
        "below_close": int(net._below.sum()),
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "volume_total": r(float(np.asarray(h.total_volume, dtype=float).sum())),
        "circulating_close": r(circ), "parked_close": r(parked), "stock_close": r(circ + parked),
        "fin_close": r(float(hold[np.asarray(net._l1)].sum())),
        "firms_close": r(float(hold[np.asarray(net._mid)].sum())),
        "rescue_lent": r(float(net._resupplied)), "rescue_repaid": r(float(net._repaid)),
        "debt_open": r(net._bubble_d0), "debt_repaid": r(net._bubble_repaid),
        "debt_outstanding": r(out),
        "debt_residual": float(net._bubble_d0 - net._bubble_repaid - out),
        "debt_parked": r(net._bubble_parked),
    }


def jobs() -> list:
    return [(need, rate, s, z, k) for (need, rate) in CELLS for s in SEEDS
            for z in ZOMBIE_STATES for k in KOO_STATES]


def run_jobs(J: list, workers: int) -> list:
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(run_one, J, chunksize=4))


# -- the gate (rule 19) and the known answer -------------------------------------

GATE_RETAINS = (0.0, 0.9, 1.0)
GATE_SEEDS = (0, 1, 2)


def _path(need, rate, seed, zombie, park, sub: bool):
    koo = Koo(0.0, 0.0, park) if park > 0 else OFF
    cfg = config(need, rate, seed, zombie, koo)
    net = KooNetwork(cfg) if sub else Network(cfg)
    net.run()
    return np.asarray(net._history.holdings, dtype=float)


def _gate_one(job):
    need, rate, seed, zombie, park = job
    same = bool(np.array_equal(_path(need, rate, seed, zombie, park, True),
                               _path(need, rate, seed, zombie, park, False)))
    return {"need": need, "rate": rate, "seed": seed, "zombie": zombie, "park": park, "same": same}


def gate_jobs() -> list:
    J = [(n, ra, s, z, 0.0) for (n, ra) in CELLS for z in (OFF,) + GATE_RETAINS for s in GATE_SEEDS]
    J += [(n, ra, s, 0.0, 0.20) for (n, ra) in CELLS for s in GATE_SEEDS]
    return J


def gate_verdict(rows: list) -> tuple:
    bad = [x for x in rows if not x["same"]]
    return (bool(rows) and not bad,
            "%d checks: the subclass with no opening debt against Network, whole holdings path, "
            "both cells, zombie off and retain %s, seeds %s, and parking 0.20 with the rescue on; "
            "%d differ" % (len(rows), list(GATE_RETAINS), list(GATE_SEEDS), len(bad)))


def a18_rows() -> list:
    doc = json.loads(_A18.RECORD_B.read_text(encoding="utf-8"))
    return [x for x in doc["runs"] if x["mode"] == MODE and x["funding"] == FUNDING
            and (x["need_multiple"], x["rate"]) in CELLS and x["retain"] in (0.0, 0.5, 0.9, 1.0)]


# -- the criteria -------------------------------------------------------------

def criterion_0(gate: dict | None) -> Criterion:
    ok = bool(gate) and gate.get("verdict") == "pass"
    return Criterion("A58-0 the subclass with no debt is the model", "instrument", ok,
                     gate["detail"] if gate else "no gate section")


def criterion_1(rows: list, recorded: list) -> Criterion:
    mine = {(x["need"], x["rate"], x["seed"], x["zombie"]): x for x in rows if x["koo"] is None and x["zombie"] is not None}
    match, missing = 0, 0
    for x in recorded:
        k = (x["need_multiple"], x["rate"], x["seed"], x["retain"])
        if k not in mine:
            missing += 1
            continue
        match += (mine[k]["below_close"] == x["below_close"] and mine[k]["mr_close"] == x["mr_close"])
    ok = bool(recorded) and missing == 0 and match == len(recorded)
    return Criterion("A58-1 A18_B's two cells are reproduced", "known_answer", ok,
                     "%d of %d recorded rows equal on the count below the line and M/R; %d not run here"
                     % (match, len(recorded), missing))


def criterion_2(rows: list) -> Criterion:
    worst = max((abs(x["debt_residual"]) / max(1.0, x["debt_open"]) for x in rows), default=None)
    rescue = sum(1 for x in rows if x["rescue_repaid"] != 0.0)
    ok = worst is not None and worst < 1e-9 and rescue == 0
    return Criterion("A58-2 the debt ledger closes and the rescue is never repaid", "instrument", ok,
                     "opening debt less repaid less outstanding: largest %.2e of the opening debt; runs "
                     "where the rescue ledger was repaid: %d" % (worst if worst is not None else float("nan"), rescue))


def _corner(rows: list) -> dict:
    return {(x["need"], x["rate"], x["seed"], x["zombie"], x["koo"]): x for x in rows}


def deleveraging_ratios(rows: list) -> list:
    """Circulating half, deleveraging alone with parking over neither side on."""
    c = _corner(rows)
    out = []
    for (need, rate) in CELLS:
        for s in SEEDS:
            base = c.get((need, rate, s, None, None))
            for k in KOO_HOLDINGS:
                if k.park <= 0.0:
                    continue
                x = c.get((need, rate, s, None, k.label()))
                if base and x and base["circulating_close"] > 0:
                    out.append(x["circulating_close"] / base["circulating_close"])
    return out


def criterion_3(ratios: list) -> Criterion:
    med = float(np.median(ratios)) if ratios else float("nan")
    ok = bool(ratios) and med < 1.0
    return Criterion("A58-3 deleveraging with parking, alone, lowers the money that circulates", "own_reading", ok,
                     "circulating half against neither side on: median ratio %.4f over %d pairs, lower in %d"
                     % (med, len(ratios), sum(v < 1.0 for v in ratios)))


def collected_ratios(rows: list) -> dict:
    """Circulating half, deleveraging alone with only the collections parked, over neither side on.

    Keyed by opening debt, so whether the size of the debt now matters can be read.
    """
    c = _corner(rows)
    out = {d: [] for d in D0S}
    for (need, rate) in CELLS:
        for s in SEEDS:
            base = c.get((need, rate, s, None, None))
            for k in KOO_COLLECTED:
                x = c.get((need, rate, s, None, k.label()))
                if base and x and base["circulating_close"] > 0:
                    out[k.d0].append(x["circulating_close"] / base["circulating_close"])
    return out


def criterion_6(by_d0: dict) -> Criterion:
    allr = [v for d in D0S for v in by_d0.get(d, [])]
    med = float(np.median(allr)) if allr else float("nan")
    meds = {d: float(np.median(by_d0[d])) if by_d0.get(d) else float("nan") for d in D0S}
    ok = bool(allr) and med < 1.0
    return Criterion("A58-6 parking only the collections, alone, lowers the money that circulates", "own_reading", ok,
                     "circulating half against neither side on: median ratio %.4f over %d pairs, lower in %d; "
                     "median by opening debt %s" % (med, len(allr), sum(v < 1.0 for v in allr),
                                                    {("%g" % d): round(m, 4) for d, m in meds.items()}))


def criterion_7(rows: list) -> Criterion:
    xs = [x for x in rows if x["koo"] is not None and "collected=" in x["koo"]]
    worst = max((abs(x["parked_close"] - x["debt_parked"]) for x in xs), default=None)
    ok = bool(xs) and worst is not None and worst <= 1e-5
    return Criterion("A58-7 on the collection arm, everything parked is a parked collection", "instrument", ok,
                     "%d runs; parked stock at the close against collections parked: largest gap %.2e"
                     % (len(xs), worst if worst is not None else float("nan")))


MEASURES = ("below_close", "volume_total", "mr_close", "circulating_close")
STATES = (("zero", "the two sides add"), ("amplify", "together they do more than the sum, same sign"),
          ("offset", "together they do less than the sum"), ("other", "the sum is zero and the joint move is not"))


def interactions(rows: list) -> list:
    c = _corner(rows)
    out = []
    for (need, rate) in CELLS:
        for s in SEEDS:
            y00 = c.get((need, rate, s, None, None))
            for z in RETAINS:
                y10 = c.get((need, rate, s, z, None))
                for k in KOO_STATES:
                    if k is OFF:
                        continue
                    y01 = c.get((need, rate, s, None, k.label()))
                    y11 = c.get((need, rate, s, z, k.label()))
                    if None in (y00, y10, y01, y11):
                        out.append({"need": need, "rate": rate, "seed": s, "zombie": z, "koo": k.label(),
                                    "complete": False})
                        continue
                    row = {"need": need, "rate": rate, "seed": s, "zombie": z, "koo": k.label(), "complete": True}
                    for m in MEASURES:
                        dz, dk = y10[m] - y00[m], y01[m] - y00[m]
                        it = y11[m] - y10[m] - y01[m] + y00[m]
                        tol = 0 if m == "below_close" else 1e-9 * max(1.0, abs(y00[m]))
                        if abs(it) <= tol:
                            st = "zero"
                        elif dz + dk == 0:
                            st = "other"
                        elif (it > 0) == (dz + dk > 0):
                            st = "amplify"
                        else:
                            st = "offset"
                        row[m] = {"dz": dz, "dk": dk, "interaction": it, "state": st}
                    out.append(row)
    return out


def criterion_4(inter: list) -> Criterion:
    complete = [x for x in inter if x["complete"]]
    states_ok = all(x[m]["state"] in dict(STATES) for x in complete for m in MEASURES)
    ok = bool(inter) and len(complete) == len(inter) and states_ok
    tally = {m: {st: sum(x[m]["state"] == st for x in complete) for st, _ in STATES} for m in MEASURES}
    return Criterion("A58-4 every cell decomposed, every interaction given a state", "own_reading", ok,
                     "%d of %d cells have all four corners; states by measure %s; map %s"
                     % (len(complete), len(inter), tally, dict(STATES)))


def criterion_5(rows: list, planned: int) -> Criterion:
    keys = {(x["need"], x["rate"], x["seed"], x["zombie"], x["koo"]) for x in rows}
    ok = len(rows) == planned and len(keys) == planned
    return Criterion("A58-5 every planned run is in the record once", "bookkeeping", ok,
                     "%d rows, %d distinct, %d planned" % (len(rows), len(keys), planned))


def analyse(rows: list, gate: dict | None) -> tuple:
    inter = interactions(rows)
    ratios = deleveraging_ratios(rows)
    coll = collected_ratios(rows)
    crits = [criterion_0(gate), criterion_1(rows, a18_rows()), criterion_2(rows),
             criterion_3(ratios), criterion_4(inter), criterion_5(rows, len(jobs())),
             criterion_6(coll), criterion_7(rows)]
    return crits, {"interactions": inter, "deleveraging_ratios": ratios,
                   "collected_ratios": {("%g" % d): v for d, v in coll.items()}}


# -- the selftest (11f) ------------------------------------------------------

def selftest() -> dict:
    out = []

    def check(name, good, bad):
        g, b = good(), bad()
        out.append({"criterion": name, "passes_on_good": g.passed, "fails_on_bad": not b.passed})
        print("   %-6s good %s, seeded fault %s" % (name, "PASS" if g.passed else "FAIL",
                                                   "caught" if not b.passed else "MISSED"))

    check("A58-0", lambda: criterion_0({"verdict": "pass", "detail": "fixture"}),
          lambda: criterion_0({"verdict": "fail", "detail": "fixture"}))

    rec = [{"need_multiple": 0.2, "rate": 1.0, "seed": 0, "retain": 0.0, "below_close": 150, "mr_close": 1.15895}]
    mine = [{"need": 0.2, "rate": 1.0, "seed": 0, "zombie": 0.0, "koo": None, "below_close": 150, "mr_close": 1.15895}]
    bad1 = [dict(mine[0], mr_close=1.158951)]
    check("A58-1", lambda: criterion_1(mine, rec), lambda: criterion_1(bad1, rec))

    good2 = [{"debt_residual": 1e-13, "debt_open": 50.0, "rescue_repaid": 0.0}]
    bad2 = [{"debt_residual": 1e-13, "debt_open": 50.0, "rescue_repaid": 0.3}]
    check("A58-2", lambda: criterion_2(good2), lambda: criterion_2(bad2))

    check("A58-3", lambda: criterion_3([0.4, 0.7, 1.02]), lambda: criterion_3([1.1, 1.3, 0.9]))

    full = {"complete": True, **{m: {"dz": -1, "dk": -1, "interaction": 0, "state": "zero"} for m in MEASURES}}
    check("A58-4", lambda: criterion_4([full, full]), lambda: criterion_4([full, {"complete": False}]))

    rows5 = [{"need": 0.2, "rate": 1.0, "seed": s, "zombie": None, "koo": None} for s in range(3)]
    check("A58-5", lambda: criterion_5(rows5, 3), lambda: criterion_5(rows5 + [rows5[0]], 4))

    check("A58-6", lambda: criterion_6({50.0: [0.8, 0.9], 100.0: [0.6, 1.01]}),
          lambda: criterion_6({50.0: [1.1, 1.2], 100.0: [0.9, 1.3]}))

    r7 = [{"koo": "D0=50 repay=0.2 park=0 collected=1", "parked_close": 12.0, "debt_parked": 12.0}]
    check("A58-7", lambda: criterion_7(r7), lambda: criterion_7([dict(r7[0], parked_close=12.5)]))

    # The model side: a debt that is never repaid must leave the ledger where it opened,
    # and a repaid one must move claims from firms to creditors.
    a = run_one((0.2, 1.0, 0, OFF, Koo(50.0, 0.20, 0.0)))
    b = run_one((0.2, 1.0, 0, OFF, Koo(50.0, 0.0, 0.0)))
    ok_model = a["debt_repaid"] > 0 and b["debt_repaid"] == 0 and b["debt_outstanding"] == 50.0
    out.append({"criterion": "ledger", "passes_on_good": ok_model, "fails_on_bad": True})
    print("   ledger repaid %.3f at 0.20, %.3f at 0, outstanding %.3f: %s"
          % (a["debt_repaid"], b["debt_repaid"], b["debt_outstanding"], "ok" if ok_model else "WRONG"))

    # Parking every collection must park exactly what was repaid, and nothing
    # must be parked when the share is zero.
    full = run_one((0.2, 1.0, 0, OFF, Koo(50.0, 0.20, 0.0, 1.0)))
    ok_coll = (full["parked_close"] > 0 and abs(full["parked_close"] - full["debt_repaid"]) <= 1e-5
               and a["parked_close"] == 0.0)
    out.append({"criterion": "collected", "passes_on_good": ok_coll, "fails_on_bad": True})
    print("   collected=1: parked %.4f against repaid %.4f; collected=0 parked %.4f: %s"
          % (full["parked_close"], full["debt_repaid"], a["parked_close"], "ok" if ok_coll else "WRONG"))

    held = sum(x["passes_on_good"] and x["fails_on_bad"] for x in out)
    return {"checks": out, "held": held, "of": len(out), "verdict": "pass" if held == len(out) else "fail"}


# -- the record ----------------------------------------------------------------

def station_config() -> dict:
    return {"mode": MODE, "funding": FUNDING, "cells": [{"need": n, "rate": ra} for n, ra in CELLS],
            "seeds": list(SEEDS), "retains": list(RETAINS), "opening_debt": list(D0S),
            "repay_k": list(REPAYS), "park": list(PARKS), "park_collected": list(COLLECTED),
            "debtors": "the intermediate block", "creditors": "the financial nodes each firm pays upward",
            "rescue_repay": 0.0, "f2i": _A18.F2I, "elasticity": _A18.ELASTICITY, "rounds": _A18.ROUNDS}


def write_record(section: str, payload: dict) -> None:
    doc = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    doc["stage"] = STAGE
    doc["config"] = _A54._fmt(station_config())
    doc.setdefault("sections", {})[section] = _A54._fmt(payload)
    RECORD.write_text(_A54._dump(doc), encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


ROW_FIELDS = ("need", "rate", "seed", "zombie", "koo", "below_close", "mr_close", "volume_total",
              "circulating_close", "parked_close", "stock_close", "fin_close", "firms_close",
              "rescue_lent", "rescue_repaid", "debt_open", "debt_repaid", "debt_outstanding", "debt_residual",
              "debt_parked")


def tables() -> int:
    doc = json.loads(RECORD.read_text(encoding="utf-8"))
    run = doc["sections"]["run"]
    rows = [dict(zip(run["rows"]["fields"], v)) for v in run["rows"]["rows"]]
    c = _corner(rows)
    print("criteria: " + ", ".join("%s %s" % (x["name"].split()[0], "PASS" if x["passed"] else "FAIL")
                                    for x in run["criteria"]))
    for (need, rate) in CELLS:
        print("\n### cell: floor %.2f, rate %.1f; medians over seeds %s" % (need, rate, list(SEEDS)))
        print("zombie      koo                          below   volume      M/R      circulating  parked    firms")
        for z in ZOMBIE_STATES:
            for k in KOO_STATES:
                xs = [c[(need, rate, s, z, None if k is OFF else k.label())] for s in SEEDS]
                med = lambda f: float(np.median([x[f] for x in xs]))
                print("%-11s %-28s %6.0f  %10.1f  %8.3f  %10.2f  %9.2f  %7.2f" % (
                    "off" if z is OFF else "retain %g" % z, "off" if k is OFF else k.label(),
                    med("below_close"), med("volume_total"), med("mr_close"), med("circulating_close"),
                    med("parked_close"), med("firms_close")))
    inter = run["analysis"]["interactions"]
    print("\n### interaction states, by measure, over every cell")
    for m in MEASURES:
        print("%-18s %s" % (m, {st: sum(x[m]["state"] == st for x in inter if x["complete"]) for st, _ in STATES}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--gate", "--selftest", "--time", "--run", "--tables"):
        mode.add_argument(flag, action="store_true")
    ap.add_argument("--workers", type=int, default=_A54._default_workers())
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    if args.tables:
        return tables()
    if args.selftest:
        print("stage %s, seeded faults\n" % STAGE)
        s = selftest()
        print("\n   %d of %d held, verdict: %s" % (s["held"], s["of"], s["verdict"]))
        if not args.no_write:
            write_record("selftest", s)
        return 0 if s["verdict"] == "pass" else 1
    if args.time:
        for job in ((0.2, 1.0, 0, OFF, OFF), (0.5, 2.0, 0, 1.0, Koo(100.0, 0.20, 0.50))):
            t0 = time.perf_counter()
            run_one(job)
            print("   %s: %.2f s" % (job, time.perf_counter() - t0))
        print("   planned runs: %d" % len(jobs()))
        return 0
    if args.gate:
        print("stage %s, rule 19\n" % STAGE)
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            rows = list(ex.map(_gate_one, gate_jobs()))
        ok, detail = gate_verdict(rows)
        print("   " + detail + "\n   verdict: %s" % ("pass" if ok else "fail"))
        if not args.no_write:
            write_record("gate", {"verdict": "pass" if ok else "fail", "detail": detail, "rows": rows})
        return 0 if ok else 1
    doc = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    gate = doc.get("sections", {}).get("gate")
    if not gate or gate.get("verdict") != "pass":
        print("stage %s: not starting, the gate has not passed (run --gate)" % STAGE)
        return 2
    J = jobs()
    print("stage %s: %d runs, %d workers" % (STAGE, len(J), args.workers))
    t0 = time.perf_counter()
    rows = run_jobs(J, args.workers)
    print("   ran %d runs in %.0f s" % (len(rows), time.perf_counter() - t0))
    crits, analysis = analyse(rows, gate)
    for x in crits:
        print("  [%s] %s (%s)\n         %s" % ("PASS" if x.passed else "FAIL", x.name, x.kind, x.detail))
    if not args.no_write:
        write_record("run", {"criteria": [x.as_dict() for x in crits], "analysis": analysis,
                             "rows": {"fields": list(ROW_FIELDS),
                                      "rows": [[x[k] for k in ROW_FIELDS] for x in rows]}})
    return 0 if all(x.passed for x in crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
