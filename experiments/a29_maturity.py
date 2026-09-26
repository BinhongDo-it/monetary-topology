"""A29, second round: bonds that fall due, and who pays for them.

The first round built the leg that passes down and let the bonds roll over for
ever. On the setting where every bond's proceeds are passed down each round,
circulation holds and the bond stock against the circulating stock climbs in a
straight line: the parking rate times the rounds times the financial layer's
share. This round adds the other side of the sovereign's book. A share of the
bonds falls due each round, interest accrues on what is outstanding, and one of
three routes pays: the holders roll it over, the nodes still trading are taxed,
or claims are created. ``SovereignSpec`` carries the four fields, and with both
debt rates at zero a run is the first round's, bit for bit.

Three steps, one at a time and in this order:

    python experiments/a29_maturity.py --gate            # rule 19
    python experiments/a29_maturity.py --time            # seconds per cell
    python experiments/a29_maturity.py --run --seeds 3   # the grid

``--run`` does not start until ``--gate`` has passed on the module as it is
now. ``--run --smoke`` runs a reduced grid and writes nothing; ``--no-write``
prints and writes nothing on any step.
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
RESULTS = ROOT / "results"
SRC = ROOT / "src" / "monetary_topology"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    DEBT_FIELDS,
    Network,
    ParkSpec,
    SOVEREIGN_LEVY_BASES,
    SovereignSpec,
    WriteOffSpec,
)

RECORD = RESULTS / "a29_maturity.json"
FIRST_RECORD = RESULTS / "a29_sovereign.json"
MODULE = SRC / "network.py"

#: The module as it stood after the first round and before this one, kept
#: beside it under the repository's backup convention.
PRE_MODULE = SRC / "network.py.expired_20260911_pre_A29b"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: The first round's script, for its helpers and its cell, so the two rounds
#: share one definition of everything they share.
_A29 = _load(ROOT / "experiments" / "a29_sovereign.py", "_a29_for_maturity")
config_for = _A29.config_for
r = _A29.r
Criterion = _A29.Criterion
ROUNDS = _A29.ROUNDS
SEEDS = _A29.SEEDS
NEEDS = _A29.NEEDS
PARK_RATES = _A29.PARK_RATES
ELASTICITIES = _A29.ELASTICITIES
AUTHORITIES = _A29.AUTHORITIES
TARGET = _A29.TARGET
TAIL = _A29.TAIL
HORIZONS = _A29.HORIZONS
FLOOR_MULTIPLE = _A29.FLOOR_MULTIPLE
COUNT_FLOOR = _A29.COUNT_FLOOR
LEDGER_TOL = _A29.LEDGER_TOL

#: The pass-down this round holds fixed: every bond's proceeds, every round.
#: On it the first round's line is exact, and that line is what this round
#: reads.
PASS_RATE = 1.0
BOND_SHARE = 1.0
#: Two landings. ``uniform`` tracked ``production`` to within 0.2 on
#: circulation in the first round and flipped the same blocks.
LANDINGS: tuple[str, ...] = ("production", "parkers")
#: ``(maturity_rate, coupon_rate)`` for the levy and issuance routes: principal
#: alone at two terms, coupon alone at two rates, and both.
RATE_PAIRS: tuple[tuple[float, float], ...] = (
    (0.01, 0.0), (0.1, 0.0), (0.0, 0.002), (0.0, 0.02), (0.1, 0.002),
    (0.1, 0.02))
#: ``(route, funding, levy_base, maturity_rate, coupon_rate)``. Twenty-two.
#: The reference is the first round's cell. Rolling over at a zero coupon is
#: the same cell again, whatever the term, which is a check and not a reading.
SETTINGS: tuple[tuple[str, str, str, float, float], ...] = (
    (("reference", "creditors", "equal", 0.0, 0.0),
     ("rollover", "creditors", "equal", 0.1, 0.0),
     ("rollover", "creditors", "equal", 0.1, 0.002),
     ("rollover", "creditors", "equal", 0.1, 0.02))
    + tuple(("levy", "levy", base, mu, cr) for base in SOVEREIGN_LEVY_BASES
            for mu, cr in RATE_PAIRS)
    + tuple(("issuance", "issuance", "equal", mu, cr) for mu, cr in RATE_PAIRS))
ROUTES: tuple[str, ...] = ("reference", "rollover", "levy", "issuance")
KEY_FIELDS: tuple[str, ...] = ("need", "park", "elasticity", "authority",
                               "landing", "route", "funding", "levy_base",
                               "maturity", "coupon", "seed")
#: The reduced grid ``--smoke`` runs: every setting and code path, two seeds.
SMOKE = {"needs": NEEDS[:1], "parks": PARK_RATES[1:], "seeds": SEEDS[:2]}

#: Fields a rollover at a zero coupon must reproduce from the reference cell.
IDENTITY_FIELDS: tuple[str, ...] = (
    "circulating_tail", "parked_tail", "circulating_close", "parked_close",
    "support_tail", "volume_tail", "below_close", "below_tail", "issued_total",
    "passed_total", "circulating_at", "bonds_at", "l1_share_tail",
    "raised_mean", "books_close", "levied_total", "created_total",
    "capitalized_total", "extinguished_total")


# ---------------------------------------------------------------------------
# The grid.
# ---------------------------------------------------------------------------

def cell_keys(seeds=SEEDS, needs=NEEDS, parks=PARK_RATES) -> list:
    keys = []
    for need in needs:
        for park in parks:
            for e in ELASTICITIES:
                for auth in AUTHORITIES:
                    for landing in LANDINGS:
                        for route, funding, base, mu, cr in SETTINGS:
                            for seed in seeds:
                                keys.append({
                                    "need": need, "park": park,
                                    "elasticity": e, "authority": auth,
                                    "landing": landing, "route": route,
                                    "funding": funding, "levy_base": base,
                                    "maturity": mu, "coupon": cr,
                                    "seed": seed})
    return keys


def cell_config(key: dict):
    cfg = config_for("drawdown", WriteOffSpec(), key["authority"], key["need"],
                     key["seed"], resupply_rate=0.0,
                     elasticity=key["elasticity"])
    sov = SovereignSpec(pass_rate=PASS_RATE, bond_share=BOND_SHARE,
                        landing=key["landing"], maturity_rate=key["maturity"],
                        coupon_rate=key["coupon"], funding=key["funding"],
                        levy_base=key["levy_base"])
    return dataclasses.replace(
        cfg, park=ParkSpec(rate=key["park"], target=TARGET), sovereign=sov)


def first_round_key(key: dict) -> dict:
    """The first round's key for the same carrier, landing and seed."""
    return {"arm": "treatment", "need": key["need"], "park": key["park"],
            "elasticity": key["elasticity"], "authority": key["authority"],
            "seed": key["seed"], "bond_share": BOND_SHARE,
            "pass_rate": PASS_RATE, "landing": key["landing"]}


def one_cell(key: dict) -> dict:
    cfg = cell_config(key)
    net = Network(cfg)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)
    circ = hold.sum(axis=1)
    parked = np.asarray(h.parked, dtype=float)
    issued = np.asarray(h.issuance, dtype=float)
    passed = np.asarray(h.passed_down, dtype=float)
    pool = np.asarray(h.sovereign_pool, dtype=float)
    bonds = np.asarray(h.bond_stock, dtype=float)
    raised = np.diff(np.concatenate(([0.0], pool))) + passed
    zeros = np.zeros(len(circ))
    debt = {k: (zeros if getattr(h, k) is None
                else np.asarray(getattr(h, k), dtype=float))
            for k in DEBT_FIELDS}
    l1_tail = hold[-TAIL:][:, net._l1].sum(axis=1)
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
        "passed_total": r(passed.sum()),
        "circulating_at": {str(q): r(circ[q]) for q in HORIZONS},
        "bonds_at": {str(q): r(bonds[q]) for q in HORIZONS},
        # The two closed forms need these: the financial layer's share of what
        # circulates, and the mean of what is bought in bonds each round.
        "l1_share_tail": r(float(np.mean(l1_tail
                                         / np.maximum(circ[-TAIL:], 1e-12)))),
        "raised_mean": r(raised.mean()),
        "due_total": r(debt["debt_due"].sum()),
        "levied_total": r(debt["debt_levied"].sum()),
        "levied_l2_total": r(debt["debt_levied_l2"].sum()),
        "created_total": r(debt["debt_created"].sum()),
        "capitalized_total": r(debt["debt_capitalized"].sum()),
        "extinguished_total": r(debt["debt_extinguished"].sum()),
        # Per-round figures at the six horizons. Summarised into a section and
        # dropped from the rows before the record is written.
        "service_at": {str(q): {k: r(debt[k][q]) for k in DEBT_FIELDS}
                       for q in HORIZONS},
    })
    stock = circ + parked
    cap, ext, cre = (debt["debt_capitalized"], debt["debt_extinguished"],
                     debt["debt_created"])
    scale = max(1.0, float(stock.max()), float(np.cumsum(raised).max()),
                float(np.cumsum(cap).max())) / cfg.initial_claims
    tol = LEDGER_TOL * max(1.0, scale)
    in_graph = np.diff(stock) - (issued[1:] + passed[1:] + cre[1:] + cap[1:]
                                 - ext[1:])
    outside = bonds - (np.cumsum(raised) - np.cumsum(ext) + np.cumsum(cap))
    # A boolean and not the residuals: those are machine rounding.
    row["books_close"] = bool(
        np.abs(in_graph).max() <= tol and np.abs(outside).max() <= tol
        and pool.min() >= -tol
        and bool((debt["debt_levied"] <= debt["debt_due"] + tol).all()))
    return row


def first_round_cell(key: dict) -> dict:
    """The first round's own cell, run on the module as it is now."""
    return _A29.one_cell(key)


def _row_key(x: dict) -> tuple:
    return tuple(x[k] for k in KEY_FIELDS)


def run_cells(keys: list, first_keys: list, workers: int) -> tuple:
    if workers <= 1:
        rows = [one_cell(k) for k in keys]
        first = [first_round_cell(k) for k in first_keys]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one_cell, keys, chunksize=4))
            first = list(pool.map(first_round_cell, first_keys, chunksize=4))
    return sorted(rows, key=_row_key), first


# ---------------------------------------------------------------------------
# Readings.
# ---------------------------------------------------------------------------

def _cell(x: dict) -> tuple:
    """Carrier, landing and seed: what a setting is compared within."""
    return (x["need"], x["park"], x["elasticity"], x["authority"],
            x["landing"], x["seed"])


def _setting(x: dict) -> tuple:
    return (x["route"], x["levy_base"], x["maturity"], x["coupon"])


def _setting_label(s: tuple) -> str:
    route, base, mu, cr = s
    name = route if route != "levy" else "levy/%s" % base
    return "%s (mu %.2f, r %.3f)" % (name, mu, cr)


def _first_index(doc: dict) -> dict:
    rows = doc.get("sections", {}).get("run", {}).get("rows", [])
    out = {}
    for x in rows:
        if (x.get("arm") == "treatment" and x.get("bond_share") == BOND_SHARE
                and x.get("pass_rate") == PASS_RATE):
            out[(x["need"], x["park"], x["elasticity"], x["authority"],
                 x["landing"], x["seed"])] = x
    return out


def compare_first_round(first: list) -> dict:
    """The first round's cells, rerun on this module, against its record."""
    if not FIRST_RECORD.exists():
        return {"record": "missing", "compared": 0, "match": 0, "missing": 0,
                "differ": []}
    index = _first_index(json.loads(FIRST_RECORD.read_text(encoding="utf-8")))
    match, missing, differ = 0, 0, []
    for x in first:
        k = (x["need"], x["park"], x["elasticity"], x["authority"],
             x["landing"], x["seed"])
        y = index.get(k)
        if y is None:
            missing += 1
            continue
        fx = _A29._fmt(x)
        if fx == y:
            match += 1
        else:
            fields = sorted(f for f in set(fx) | set(y) if fx.get(f) != y.get(f))
            differ.append({"cell": list(k), "fields": fields})
    return {"record": FIRST_RECORD.name, "compared": len(first),
            "match": match, "missing": missing, "differ": differ}


def identity_check(rows: list) -> dict:
    """Rolling over at a zero coupon against the reference cell."""
    ref = {_cell(x): x for x in rows if x["route"] == "reference"}
    checked, differ = 0, []
    for x in rows:
        if x["route"] != "rollover" or x["coupon"] != 0.0:
            continue
        y = ref.get(_cell(x))
        if y is None:
            continue
        checked += 1
        bad = [f for f in IDENTITY_FIELDS if x[f] != y[f]]
        if bad:
            differ.append({"cell": list(_cell(x)), "fields": bad})
    return {"checked": checked, "differ": differ}


def closed_form(route: str, mu: float, cr: float, p_bar: float, t: int) -> float:
    """Bonds outstanding at round ``t`` with a constant purchase ``p_bar``.

    Each round retires ``mu`` of the stock when it is paid and adds ``r`` of
    it when the coupon is rolled over, then this round's purchase arrives:
    ``B(t) = (1 + g) B(t-1) + p_bar`` with ``g = r`` for a rollover and
    ``g = -mu`` for a levy or issuance collected in full.
    """
    g = cr if route == "rollover" else (-mu if route in ("levy", "issuance")
                                        else 0.0)
    if g == 0.0:
        return p_bar * (t + 1)
    return p_bar * ((1.0 + g) ** (t + 1) - 1.0) / g


def bends(rows: list) -> list:
    last = HORIZONS[-1]
    groups = {}
    for x in rows:
        groups.setdefault(_setting(x) + (x["park"],), []).append(x)
    out = []
    for key in sorted(groups):
        route, base, mu, cr, park = key
        xs = groups[key]
        meas, pred, ratio, share = [], [], [], []
        for x in xs:
            c = x["circulating_at"][str(last)]
            b = x["bonds_at"][str(last)]
            p = closed_form(route, mu, cr, x["raised_mean"], last)
            if c > 0:
                meas.append(b / c)
                pred.append(p / c)
            if p > 0:
                ratio.append(b / p)
            share.append(x["l1_share_tail"])
        entry = {"route": route, "levy_base": base, "maturity": mu,
                 "coupon": cr, "park": park, "cells": len(xs),
                 "bonds_over_circulating_%d" % last: _A29._median(meas),
                 "closed_form_over_circulating_%d" % last: _A29._median(pred),
                 "measured_over_closed_form": _A29._median(ratio),
                 "l1_share_tail": _A29._median(share)}
        if mu > 0.0 and route in ("levy", "issuance"):
            entry["plateau_p_s_over_mu"] = r(park * _A29._median(share) / mu)
        out.append(entry)
    return out


def costs(rows: list) -> list:
    """Each setting against the reference cell, seed by seed, never pooled."""
    ref = {}
    for x in rows:
        if x["route"] == "reference":
            ref.setdefault(_cell(x)[:5], {})[x["seed"]] = x
    groups = {}
    for x in rows:
        if x["route"] == "reference":
            continue
        groups.setdefault(_cell(x)[:5] + _setting(x), {})[x["seed"]] = x
    out = []
    for g in sorted(groups):
        c = ref.get(g[:5], {})
        seeds = sorted(s for s in groups[g] if s in c)
        entry = {"need": g[0], "park": g[1], "elasticity": g[2],
                 "authority": g[3], "landing": g[4], "route": g[5],
                 "levy_base": g[6], "maturity": g[7], "coupon": g[8],
                 "seeds": seeds}
        for q, count in _A29.READINGS:
            fl = _A29._floor([c[s][q] for s in sorted(c)], count)
            diffs = [groups[g][s][q] - c[s][q] for s in seeds]
            entry[q] = {"diffs": [r(d) for d in diffs],
                        "floor": None if fl is None else r(fl),
                        "state": _A29._state(diffs, fl)}
        out.append(entry)
    return out


def who_pays(rows: list) -> list:
    ref = {_cell(x): x for x in rows if x["route"] == "reference"}
    groups = {}
    for x in rows:
        if x["route"] in ("reference",):
            continue
        groups.setdefault(_setting(x) + (x["park"],), []).append(x)
    out = []
    for key in sorted(groups):
        xs = groups[key]
        due = sum(x["due_total"] for x in xs)
        lev = sum(x["levied_total"] for x in xs)
        lev2 = sum(x["levied_l2_total"] for x in xs)
        cre = sum(x["created_total"] for x in xs)
        cap = sum(x["capitalized_total"] for x in xs)
        rolled = due - lev - cre - cap
        # The authority's own issuance over the reference cell's, summed on
        # the cells where it issues at all, against what this route moved in
        # cash on the same cells: does the levy's gap come back as issuance.
        extra, moved = 0.0, 0.0
        for x in xs:
            y = ref.get(_cell(x))
            if x["authority"] == "endogenous" and y is not None:
                extra += x["issued_total"] - y["issued_total"]
                moved += x["levied_total"] + x["created_total"]
        out.append({
            "route": key[0], "levy_base": key[1], "maturity": key[2],
            "coupon": key[3], "park": key[4], "cells": len(xs),
            "due": r(due),
            "share_levied": r(lev / due) if due > 0 else None,
            "share_created": r(cre / due) if due > 0 else None,
            "share_capitalized": r(cap / due) if due > 0 else None,
            "share_rolled": r(rolled / due) if due > 0 else None,
            "levy_share_outside_financial_layer": r(lev2 / lev) if lev > 0 else None,
            "authority_extra_issuance": r(extra),
            "authority_extra_over_levied_or_created": (r(extra / moved)
                                                       if moved > 0 else None),
        })
    return out


def service_trajectories(rows: list) -> list:
    groups = {}
    for x in rows:
        if x["route"] == "reference":
            continue
        groups.setdefault(_setting(x) + (x["park"],), []).append(x)
    out = []
    for key in sorted(groups):
        xs = groups[key]
        entry = {"route": key[0], "levy_base": key[1], "maturity": key[2],
                 "coupon": key[3], "park": key[4]}
        for q in HORIZONS:
            entry[str(q)] = {k: _A29._median([x["service_at"][str(q)][k]
                                              for x in xs])
                             for k in DEBT_FIELDS}
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a29_8(g, first_cmp: dict, ident: dict) -> Criterion:
    name = "A29-8 off by default reproduces the first round"
    state_map = ("State map: all three hold -> PASS; any comparison that "
                 "differs -> FAIL; no gate section -> not evaluated.")
    if not g:
        return Criterion(name, "instrument", False,
                         "Not evaluated in this run: no gate section. "
                         + state_map, evaluated=False)
    ip = g["in_process"]
    ok = (g["verdict"] == "pass" and not first_cmp["differ"]
          and not ident["differ"] and first_cmp["match"] > 0)
    return Criterion(
        name, "instrument", ok,
        "(a) The first round's module and this one, run in one process on %d "
        "configurations, %d history fields compared bit for bit, %d "
        "configurations differ, the six new fields None in every run: %s. "
        "(b) The first round's cells rerun on this module against its "
        "record: %d compared, %d identical, %d not in the record, %d differ. "
        "(c) A rollover at a zero coupon against the reference cell: %d "
        "checked, %d differ. Both sides of (b) ran on the same machine. %s"
        % (len(ip["configs"]), ip["fields_compared"], len(ip["differ"]),
           not ip["new_fields_set"], first_cmp["compared"], first_cmp["match"],
           first_cmp["missing"], len(first_cmp["differ"]), ident["checked"],
           len(ident["differ"]), state_map))


def criterion_a29_9(rows: list) -> Criterion:
    bad = [x for x in rows if not x["books_close"]]
    return Criterion(
        "A29-9 the three books close", "instrument", not bad,
        "In the graph, every round: the change in held plus parked equals "
        "issuance, plus what was passed down, plus what was created, plus "
        "coupon capitalized, less principal retired; a levy goes out and comes "
        "back in the same round. Outside it: bonds equal every bond bought less "
        "retirements plus capitalized coupon, the pool never goes below zero, "
        "and no levy collects more than falls due. All to %.0e of the opening "
        "stock, asserted in the round loop and read back here off the history: "
        "%d of %d cells close.%s"
        % (LEDGER_TOL, len(rows) - len(bad), len(rows),
           "" if not bad else " Open: " + "; ".join(
               "%s %s" % (_setting_label(_setting(x)), list(_cell(x)))
               for x in bad[:10])))


def criterion_a29_10(rows: list) -> Criterion:
    served = [x for x in rows if x["maturity"] > 0.0 or x["coupon"] > 0.0]
    dead = []
    parts = []
    for route in ("rollover", "levy", "issuance"):
        xs = [x for x in served if x["route"] == route]
        if route == "rollover":
            xs = [x for x in xs if x["coupon"] > 0.0]
            moved = [x for x in xs if x["capitalized_total"] > 0.0]
            parts.append("rollover: coupon added to holdings %.2f over %d cells"
                         % (sum(x["capitalized_total"] for x in xs), len(xs)))
        else:
            moved = [x for x in xs if x["levied_total"] + x["created_total"] > 0.0]
            if route == "levy":
                for base in SOVEREIGN_LEVY_BASES:
                    b = [x for x in xs if x["levy_base"] == base]
                    due = sum(x["due_total"] for x in b)
                    lev = sum(x["levied_total"] for x in b)
                    lev2 = sum(x["levied_l2_total"] for x in b)
                    parts.append(
                        "levy/%s: %d cells, collected %.4f of what fell due, "
                        "%.4f of the levy paid outside the financial layer"
                        % (base, len(b), lev / due if due > 0 else 0.0,
                           lev2 / lev if lev > 0 else 0.0))
            else:
                parts.append("issuance: created %.2f over %d cells"
                             % (sum(x["created_total"] for x in xs), len(xs)))
        dead += [x for x in xs if x not in moved]
    return Criterion(
        "A29-10 the switch carries something (D28)", "instrument", not dead,
        "Every cell with a positive debt rate paid or rolled something: %d of "
        "%d did, %d did not. %s. A rollover at a zero coupon moves nothing by "
        "construction and is A29-8's check, not counted here."
        % (len(served) - len(dead) - sum(
            1 for x in served if x["route"] == "rollover" and x["coupon"] == 0.0),
           len(served) - sum(1 for x in served
                             if x["route"] == "rollover" and x["coupon"] == 0.0),
           len(dead), "; ".join(parts)))


def criterion_a29_11(bd: list) -> Criterion:
    last = HORIZONS[-1]
    parts = []
    for e in bd:
        if e["route"] == "reference":
            continue
        s = ("%s park %.3f: bonds over circulating %s, closed form %s, "
             "measured over closed form %s"
             % (_setting_label((e["route"], e["levy_base"], e["maturity"],
                                e["coupon"])), e["park"],
                e["bonds_over_circulating_%d" % last],
                e["closed_form_over_circulating_%d" % last],
                e["measured_over_closed_form"]))
        parts.append(s)
    ref = [e for e in bd if e["route"] == "reference"]
    head = ("Printed, not judged. Bonds over circulating at round %d, median "
            "over floors, elasticities, authorities, landings and seeds, "
            "against the closed form with each cell's own mean purchase: "
            "B(t) = (1+g) B(t-1) + P, g = r for a rollover and -mu for a levy "
            "or issuance collected in full. It holds the purchase constant, so "
            "where a route feeds the purchase, or a levy falls short, measured "
            "over closed form reads above one. Reference: %s. "
            % (last, "; ".join("park %.3f %s" % (e["park"],
                                                   e["bonds_over_circulating_%d" % last])
                               for e in ref)))
    return Criterion("A29-11 does the line bend", "own_reading", True,
                     head + " | ".join(parts))


def criterion_a29_12(cs: list) -> Criterion:
    parts = ["Printed, not judged. Each setting against the reference cell, "
             "seed by seed, floor the reference's dispersion across seeds, "
             "band %.1f floors, a count's floor at least %.1f node. State map "
             "for circulation and support: up = more, flat = within the band, "
             "down = less; for the count below the floor, up = more nodes "
             "below; split = seeds disagree, no reading."
             % (FLOOR_MULTIPLE, COUNT_FLOOR)]
    labels = sorted({(x["route"], x["levy_base"]) for x in cs})
    for route, base in labels:
        sub = [x for x in cs if x["route"] == route and x["levy_base"] == base]
        name = route if route != "levy" else "levy/%s" % base
        parts.append("%s: circulation %s, median difference %s; support %s; "
                     "below %s, median difference %s." % (
            name, _A29._tally(x["circulating_tail"]["state"] for x in sub),
            _A29._median([d for x in sub for d in x["circulating_tail"]["diffs"]]),
            _A29._tally(x["support_tail"]["state"] for x in sub),
            _A29._tally(x["below_close"]["state"] for x in sub),
            _A29._median([d for x in sub for d in x["below_close"]["diffs"]])))
    more_below = [x for x in cs if x["below_close"]["state"] == "up"]
    listed = ["%s need %.2f park %.3f e %.1f %s %s diffs %s"
              % (_setting_label((x["route"], x["levy_base"], x["maturity"],
                                 x["coupon"])), x["need"], x["park"],
                 x["elasticity"], x["authority"], x["landing"],
                 x["below_close"]["diffs"]) for x in more_below[:12]]
    if len(more_below) > 12:
        listed.append("%d more in the costs section" % (len(more_below) - 12))
    parts.append("More nodes below the floor: %s."
                 % ("; ".join(listed) if listed else "none"))
    return Criterion("A29-12 what each route costs circulation", "own_reading",
                     True, " ".join(parts))


def criterion_a29_13(wp: list) -> Criterion:
    parts = ["Printed, not judged. What fell due, split into what a levy "
             "collected, what was created, what was added to the holders' "
             "bonds as unpaid coupon, and principal rolled; with the levy's "
             "share paid outside the financial layer, and, where the authority "
             "issues, its issuance above the reference cell's as a share of "
             "what the route moved in cash: near one means the gap a levy opens "
             "comes back as issuance."]
    for e in wp:
        parts.append("%s park %.3f: levied %s, created %s, capitalized %s, "
                     "rolled %s, levy outside the financial layer %s, "
                     "authority's extra issuance %s, over what moved %s"
                     % (_setting_label((e["route"], e["levy_base"],
                                        e["maturity"], e["coupon"])),
                        e["park"], e["share_levied"], e["share_created"],
                        e["share_capitalized"], e["share_rolled"],
                        e["levy_share_outside_financial_layer"],
                        e["authority_extra_issuance"],
                        e["authority_extra_over_levied_or_created"]))
    return Criterion("A29-13 who pays", "own_reading", True, " | ".join(parts))


def criterion_a29_14(tr: list) -> Criterion:
    last = str(HORIZONS[-1])
    parts = []
    for e in tr:
        v = e[last]
        parts.append("%s park %.3f: due %s, levied %s, created %s, "
                     "capitalized %s, retired %s"
                     % (_setting_label((e["route"], e["levy_base"],
                                        e["maturity"], e["coupon"])),
                        e["park"], v["debt_due"], v["debt_levied"],
                        v["debt_created"], v["debt_capitalized"],
                        v["debt_extinguished"]))
    return Criterion(
        "A29-14 the debt service over time", "bookkeeping", True,
        "Printed. Per-round figures at round %s, median over the carrier, "
        "landings and seeds; all six horizons are in the service section. %s"
        % (last, " | ".join(parts)))


# ---------------------------------------------------------------------------
# Rule 19: the first round's module against this one.
# ---------------------------------------------------------------------------

def load_pre_module():
    name = "monetary_topology._network_pre_a29b"
    loader = importlib.machinery.SourceFileLoader(name, str(PRE_MODULE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def gate_configs() -> list:
    out = list(_A29.gate_configs())
    for landing in _A29.LANDINGS:
        for bs, pr in ((1.0, 1.0), (0.5, 1.0), (1.0, 0.01)):
            for auth in AUTHORITIES:
                key = {"arm": "treatment", "need": 0.50, "park": 0.02,
                       "elasticity": 0.5, "authority": auth, "seed": SEEDS[0],
                       "bond_share": bs, "pass_rate": pr, "landing": landing}
                out.append(("first round %s (%.2f, %.2f) %s"
                            % (landing, bs, pr, auth), _A29.cell_config(key)))
    return out


def gate() -> dict:
    old = load_pre_module()
    names, differ, new_set, labels = None, [], [], []
    for label, cfg in gate_configs():
        if cfg.sovereign.serves_debt:
            raise RuntimeError("a gate configuration serves debt: %s" % label)
        t0 = time.perf_counter()
        hn = Network(cfg).run()
        ho = old.Network(_A29.transplant(cfg, old)).run()
        dt = time.perf_counter() - t0
        names = [f.name for f in dataclasses.fields(ho)]
        bad = [n for n in names if not _A29._same(getattr(ho, n), getattr(hn, n))]
        extra = [k for k in DEBT_FIELDS if getattr(hn, k) is not None]
        labels.append(label)
        if bad:
            differ.append({"config": label, "fields": bad})
        if extra:
            new_set.append({"config": label, "fields": extra})
        print("   %-58s %s%s  (%.2f s)" % (
            label, "identical" if not bad else "DIFFERS in %s" % bad,
            "" if not extra else ", new fields set %s" % extra, dt))
    return {
        "module_sha": _A29._module_sha(MODULE),
        "pre_module_sha": _A29._module_sha(PRE_MODULE),
        "in_process": {"configs": labels, "fields_compared": len(names or []),
                       "differ": differ, "new_fields_set": new_set},
        "verdict": "pass" if not differ and not new_set else "fail",
    }


def _gate_section():
    if not RECORD.exists():
        return None
    return json.loads(RECORD.read_text(encoding="utf-8")).get(
        "sections", {}).get("gate")


def _gate_allows(g) -> tuple:
    if not g:
        return False, "no gate section in the record: run --gate first"
    if g.get("module_sha") != _A29._module_sha(MODULE):
        return False, "network.py has changed since the gate ran: run --gate again"
    if g.get("verdict") != "pass":
        return False, "the gate reads %r: see its output" % g.get("verdict")
    return True, "the gate passed on this module"


# ---------------------------------------------------------------------------
# Timing (D38): measured, printed, never written.
# ---------------------------------------------------------------------------

def time_cells(repeats: int = 3, workers: int = 1) -> None:
    base = {"need": NEEDS[1], "park": PARK_RATES[1], "elasticity": 0.5,
            "authority": "endogenous", "landing": "production",
            "seed": SEEDS[0]}
    probes = [s for s in SETTINGS if s[0] == "reference"
              or (s[3], s[4]) == (0.1, 0.02)]
    keys = [{**base, "route": s[0], "funding": s[1], "levy_base": s[2],
             "maturity": s[3], "coupon": s[4]} for s in probes]
    one_cell(keys[0])  # warm-up, not timed
    per = []
    for k in keys:
        ts = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            one_cell(k)
            ts.append(time.perf_counter() - t0)
        per.append(float(np.mean(ts)))
        print("   %-40s %.3f s per cell (mean of %d)"
              % (_setting_label(_setting(k)), per[-1], repeats))
    mean = float(np.mean(per))
    eff = max(1, min(workers, __import__("os").cpu_count() or 1))
    for n in (3, len(SEEDS)):
        cells = len(cell_keys(seeds=SEEDS[:n]))
        first = cells // len(SETTINGS)
        serial = (cells + first) * mean
        print("   %d seeds: %d cells and %d first-round cells, %.0f s serial, "
              "about %.0f s on %d workers" % (n, cells, first, serial,
                                              serial / eff, eff))


# ---------------------------------------------------------------------------
# The record.
# ---------------------------------------------------------------------------

def station_config() -> dict:
    probe = cell_config({"need": NEEDS[0], "park": PARK_RATES[0],
                         "elasticity": ELASTICITIES[0],
                         "authority": AUTHORITIES[0], "landing": LANDINGS[0],
                         "route": "levy", "funding": "levy",
                         "levy_base": "threshold", "maturity": 0.1,
                         "coupon": 0.02, "seed": SEEDS[0]})
    cfg = _A29._config_diff(probe)
    cfg.pop("seed", None)
    for sub, keys in (("spec", ("seed",)), ("subsistence", ("need",)),
                      ("park", ("rate",)), ("wages", ("elasticity",)),
                      ("authority", ("rule",)),
                      ("sovereign", ("landing", "maturity_rate", "coupon_rate",
                                     "funding", "levy_base"))):
        if sub in cfg:
            for k in keys:
                cfg[sub].pop(k, None)
            if not cfg[sub]:
                cfg.pop(sub)
    return {
        "carrier": "A18's config_for: drawdown, no write-off, no rescue",
        "round": "second: bonds that fall due, and who pays",
        "rounds": ROUNDS,
        "park_target": TARGET,
        "pass_down": {"pass_rate": PASS_RATE, "bond_share": BOND_SHARE},
        "grid": {"need_multiples": list(NEEDS), "park_rates": list(PARK_RATES),
                 "elasticities": list(ELASTICITIES),
                 "authorities": list(AUTHORITIES), "landings": list(LANDINGS),
                 "settings_route_funding_base_maturity_coupon":
                     [list(s) for s in SETTINGS],
                 "seeds": list(SEEDS)},
        "tail": TAIL,
        "horizons": list(HORIZONS),
        "floor_multiple": FLOOR_MULTIPLE,
        "count_floor": COUNT_FLOOR,
        "ledger_tolerance": LEDGER_TOL,
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one step's payload into the record. No wall-clock content."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A29"
    doc["diagnostic_only"] = True
    doc["diagnostic_reason"] = ("the station is not closed: second round, bonds "
                                "that fall due and who pays for them")
    doc["config"] = _A29._fmt(station_config())
    doc.setdefault("sections", {})[section] = _A29._fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s, sections %s" % (RECORD.name, sorted(doc["sections"])))


def analyse(rows: list, first: list, gate_section) -> tuple:
    first_cmp = compare_first_round(first)
    ident = identity_check(rows)
    bd = bends(rows)
    cs = costs(rows)
    wp = who_pays(rows)
    tr = service_trajectories(rows)
    crits = [criterion_a29_8(gate_section, first_cmp, ident),
             criterion_a29_9(rows), criterion_a29_10(rows),
             criterion_a29_11(bd), criterion_a29_12(cs),
             criterion_a29_13(wp), criterion_a29_14(tr)]
    slim = [{k: v for k, v in x.items() if k != "service_at"} for x in rows]
    sections = {
        "criteria": [c.as_dict() for c in crits],
        "first_round_comparison": first_cmp,
        "identity": ident,
        "bends": bd,
        "costs": cs,
        "who_pays": wp,
        "service": tr,
        "rows": slim,
    }
    return crits, sections


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true")
    mode.add_argument("--time", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--plan", action="store_true")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=_A29._default_workers())
    ap.add_argument("--smoke", action="store_true",
                    help="with --run: the reduced grid, nothing written")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in station_config().items():
            print("  %-20s %s" % (k, v))
        print("  %-20s %d at %d seeds" % ("cells",
                                           len(cell_keys(seeds=SEEDS[:args.seeds])),
                                           args.seeds))
        return 0

    if args.gate:
        print("stage A29, second round, rule 19: the first round's module "
              "against this one\n")
        g = gate()
        print("\n   verdict: %s" % g["verdict"])
        if not args.no_write:
            write_record("gate", g)
        return 0 if g["verdict"] == "pass" else 1

    if args.time:
        print("stage A29, second round, D38: seconds per cell on this machine\n")
        time_cells(workers=args.workers)
        return 0

    gate_section = _gate_section()
    if args.smoke:
        keys = cell_keys(**SMOKE)
        print("stage A29, second round, smoke: %d cells, nothing written\n"
              % len(keys))
    else:
        ok, why = _gate_allows(gate_section)
        if not ok:
            print("stage A29, second round: not starting. %s." % why)
            return 2
        keys = cell_keys(seeds=SEEDS[:args.seeds])
        print("stage A29, second round: %d cells, seeds %s, %d workers. %s.\n"
              % (len(keys), list(SEEDS[:args.seeds]), args.workers, why))
    first_keys = [first_round_key(k) for k in keys if k["route"] == "reference"]
    t0 = time.perf_counter()
    rows, first = run_cells(keys, first_keys, args.workers)
    print("   ran %d cells and %d first-round cells in %.0f s"
          % (len(rows), len(first), time.perf_counter() - t0))
    crits, sections = analyse(rows, first, gate_section)
    _A29._print_criteria(crits)
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
