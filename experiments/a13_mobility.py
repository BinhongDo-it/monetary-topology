"""A13: whether position can be bought and sold, and whether it matters.

Every stage before this one ran on a graph fixed at construction. Measured
rather than inferred: the adjacency and the routing matrix are bitwise identical
after three hundred rounds. That is the framework's thesis written into the
construction, and the thesis is what the stages were built to test, so this
stage opens the channel the construction closed.

What the switch does, and where its two rates come from, is in ``RewireSpec``.
The short form: acquisition fires twice, once to qualify and once for the
cluster, because Chetty et al. (2022) find that perfect exposure by status still
leaves nearly half the connection gap standing; loss is bimodal at about one
third, because Eckbo, Thorburn and Wang (2015) find one third of the CEOs of
bankrupt firms keep full-time executive employment with no median pay change
while two thirds leave the market outright. Neither rate is chosen here.

Why the qualification is a rank and a share rather than a level. Measured before
the arms were written: the richest production node peaks in **round zero** at
``1.0477`` and falls monotonically to ``0.4518``, while the claim stock grows
from ``100`` to ``3412``. A level in claim units is therefore crossed in 300 of
300 rounds at ``0.25``, in 7 at ``0.50``, in 1 at ``1.00``, and in none at
``2.00``. There is no usable band: below it everyone always qualifies and above
it nobody ever does, and the same level loosens for the core and tightens for
the periphery as the stock grows. A rank always has somebody in it, and a share
travels with the stock.

Scope. Most arms here buy edges only. They do not transfer the financial
layer's spending propensity or its role in the payroll channel, both of which
stay with the construction's own split, so those arms read what buying access
does rather than what holding the layer's other two properties does.

A financial-layer node differs from a production-layer node in three ways, not
one: the edges it holds, the spending propensity it draws from, and whether it
pays wages. Promotion above hands over only the first. Handing over all three at
once attributes nothing, so it is a ladder instead, added 2026-08-24: ``both``
buys the edges, ``both + propensity`` adds the layer's spending propensity, and
``both + propensity + payroll`` adds its role in the payroll channel. Each step's difference
belongs to the mechanism that step added, and A13-8 prints the steps.

What the arms do to the graph. Since 2026-10-14 ``conserve_degree`` makes every
exchange of edges exact (``RewireSpec`` says how), so in the thirteen arms that
only exchange edges no node's out-degree moves in any round, and the run checks
that off the rows before it writes anything. Four arms move out-degree and are
meant to: ``both, degree not conserved`` adds edges on promotion, the two
inbound-cut arms delete what the core sends a demoted node, and the payroll rung
hands over the wage edges. Every row carries the edge count before the first
round and at the close, and the rounds in which any out-degree moved. The three
rank-only ``k = 1`` arms make the same promotions and differ in how many core
members each promotion reaches (one, half the time as many as the node has
edges to give, always that many), at one edge count.

The record was first taken on the earlier rule, which gave up
``min(targets, edges held)`` edges and pointed the node at every target, so a
fired cluster took a node from 5 out-edges to the whole core of 20 and the span
read position and density together. The grid was rerun on the exact rule the
same day. ``both, degree not conserved`` takes the branch the fix left alone and
reads as it did, so the density confound now sits in that one arm.

What a row's shares are shares of. ``top1_wealth``, ``top10_wealth`` and
``gini`` are read on ``claims_recorded``, the last row of the claims history.
The three accounts a terminal share can be read on, and where each is sampled,
are set out in ``monetary_topology.asset.carrier_model``. On the registered
carrier the last row is the state the run ends in. With ``--asset`` it precedes
the last asset settlement and holds no asset, so an asset row prints the same
three statistics again on ``claims_settled`` and on ``net_worth``, and A13-3 is
read against A2d's record on the asset carrier. That record carries sigma's and
the structure's widths on all three accounts, and the record written here sets
mobility's width beside them on each.

Usage::

    python experiments/a13_mobility.py
    python experiments/a13_mobility.py --rounds 300 --seeds 5

Writes ``results/a13_mobility.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.mechanisms import gini
from monetary_topology.network import (
    Network,
    NetworkConfig,
    NetworkSpec,
    RewireSpec,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

DIGITS = 6

#: The two published rates, used as the centre of the sweep rather than as
#: settings. Both are for populations this model's nodes are not, so they place
#: the grid and carry no verdict.
CLUSTER_RATE = 0.5
RETAIN_RATE = 1.0 / 3.0

#: Spans this stage compares itself against, read from the records rather than
#: restated. A2d measured both on the same quantity, terminal top1% wealth.
A2D_RECORD = "a2d_terminal_selector.json"

#: The same two grids read with A3's asset layer on the carrier. An asset run is
#: set beside this one. Both rulers move with the carrier, sigma's several
#: times over, so a span taken on one carrier says nothing beside a ruler taken
#: on the other.
A2D_RECORD_ASSET = "a2d_terminal_selector_asset.json"

#: Every share a row reports. A13-1 asks for all of them to be finite.
SHARES = ("top1_wealth", "top10_wealth", "gini", "support", "mr_close")

#: The three accounts an asset run is read on, with the suffix their row keys
#: carry. The first is the one this stage has always recorded, under the old
#: key ``top1_wealth``; the names are the ones ``carrier_model`` sets out.
ACCOUNTS = {
    "claims_recorded": "wealth",
    "claims_settled": "claims_settled",
    "net_worth": "net_worth",
}


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else ("PASS" if self.passed else "FAIL")
        return f"  [{mark}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


def top_share(v: np.ndarray, k: int) -> float:
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = s.sum()
    return float(s[:k].sum() / total) if total > 0 else float("nan")


ARMS: dict[str, RewireSpec] = {
    "off": RewireSpec(),
    # Rank alone. Registered as the unbounded arm: there is always a top
    # non-core node, so somebody joins every round for ever.
    "rank k=1 cluster 0": RewireSpec(acquire_top_k=1, cluster_rate=0.0),
    "rank k=1 cluster .5": RewireSpec(acquire_top_k=1, cluster_rate=CLUSTER_RATE),
    "rank k=1 cluster 1": RewireSpec(acquire_top_k=1, cluster_rate=1.0),
    "rank k=5 cluster .5": RewireSpec(acquire_top_k=5, cluster_rate=CLUSTER_RATE),
    # Rank and share together. The share is what bounds the core.
    "rank k=2 share .001": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE),
    "rank k=2 share .002": RewireSpec(
        acquire_top_k=2, min_claim_share=0.002, cluster_rate=CLUSTER_RATE),
    # Demotion alone.
    "demote .005": RewireSpec(demote_claim_share=0.005, retain_rate=RETAIN_RATE),
    "demote .005 retain 0": RewireSpec(demote_claim_share=0.005, retain_rate=0.0),
    "demote .005 retain 1": RewireSpec(demote_claim_share=0.005, retain_rate=1.0),
    # Both directions.
    "both": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE),
    "both, degree not conserved": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE, conserve_degree=False),
    "both, every 10 rounds": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE, interval=10),
    # Added 2026-08-24. Demotion in the arms above redirects a node's outbound
    # edges and leaves what the core sends it untouched, which implements the
    # half of the published asymmetry that recovers and none of the half that
    # does not. Grindaker, Kostol and Roszbach find no enduring effect on a
    # displaced executive's labour income after five years and a permanent fall
    # in capital income of about five percent of gross income a year. The
    # recovering half is free here, since the wage mask is never rewired and the
    # out-edges are replaced rather than deleted. The permanent half needs the
    # inbound cut.
    "demote, inbound cut": RewireSpec(
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        demote_cuts_inbound=True),
    "both, inbound cut": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        demote_cuts_inbound=True),
    # Added 2026-08-24. The arms above buy edges and nothing else, so what they
    # measure is what buying access does. A financial-layer node differs from a
    # production-layer node in three ways: the edges it holds, the spending
    # propensity it draws from, and whether it pays wages. Handing over all
    # three at once attributes nothing, which is why this is a ladder with
    # one rung per property and `both` as its first rung. Read the three in
    # order and each step's difference belongs to the thing that step added.
    "both + propensity": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        transfer_propensity=True),
    "both + propensity + payroll": RewireSpec(
        acquire_top_k=2, min_claim_share=0.001, cluster_rate=CLUSTER_RATE,
        demote_claim_share=0.005, retain_rate=RETAIN_RATE,
        transfer_propensity=True, transfer_payroll=True),
}

#: The ladder, in order, first rung first. A13-8 reads the differences between
#: consecutive rungs, so the order is the criterion's meaning and not a display
#: choice.
LADDER = ("both", "both + propensity", "both + propensity + payroll")

#: Three arms that admit one node a round by rank alone and differ in nothing
#: but how often the cluster fires: never, half the time, always. They make the
#: same number of promotions and end on the same core and the same edge count,
#: so what separates them is how many of each promoted node's edges point into
#: the core.
DENSITY_LADDER = ("rank k=1 cluster 0", "rank k=1 cluster .5", "rank k=1 cluster 1")


#: The arms of ``ARMS`` that are told to exchange edges and to do nothing else
#: to the graph: they conserve degree, hand over no payroll role and cut no
#: inbound edge. These are the arms in which no node's out-degree may move, and
#: a width taken over them is a width with the edge count held.
EXCHANGE_ONLY = tuple(
    a for a, s in ARMS.items()
    if s.conserve_degree and not s.transfer_payroll and not s.demote_cuts_inbound
)

def watch_out_degree(net: Network) -> dict:
    """Count the rounds in which any node's out-degree moves.

    Wraps the instance's ``_rewire`` and reads the adjacency before and after.
    It draws no random number and changes nothing, so a watched run is the run.
    """
    seen = {"rounds": 0}
    inner = net._rewire

    def rewire(t: int) -> tuple[int, int]:
        before = net.adjacency.sum(axis=1)
        out = inner(t)
        if np.any(net.adjacency.sum(axis=1) != before):
            seen["rounds"] += 1
        return out

    net._rewire = rewire
    return seen


def state_digest(net: Network, h) -> str:
    """One hash over everything a run leaves behind.

    The row keeps six decimals, so two runs can agree on every printed reading
    and still differ. A13-5a claims the null arm *is* the construction, and this
    is what lets it mean that: every array in the history, and the state the
    model is left in.

    **Compared in process and never written.** The bytes of a float can differ
    in the last place between BLAS builds, and a record that carried the hash
    would then differ between two machines on a run that is the same run.
    """
    sha = hashlib.sha256()
    for f in sorted(dataclasses.fields(h), key=lambda f: f.name):
        value = getattr(h, f.name)
        if isinstance(value, np.ndarray):
            sha.update(f.name.encode())
            sha.update(np.ascontiguousarray(value).tobytes())
    for name in ("adjacency", "holdings", "_in_core", "units", "price"):
        value = getattr(net, name, None)
        if isinstance(value, np.ndarray):
            sha.update(name.encode())
            sha.update(np.ascontiguousarray(value).tobytes())
    return sha.hexdigest()


def one(spec: RewireSpec, seed: int, rounds: int,
        asset: bool = False, digests: dict[int, str] | None = None) -> dict:
    cfg = NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed,
                        rounds=rounds, rewire=spec)
    net = carrier_model(cfg, asset=asset)
    seen = watch_out_degree(net)
    out_initial = net.adjacency.sum(axis=1)
    h = net.run()
    close = h.holdings[-1]
    n = h.node_count
    out_close = net.adjacency.sum(axis=1)
    row = {
        "seed": seed,
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top10_wealth": r(top_share(close, n // 10)),
        "gini": r(gini(close)),
        "support": r(float(h.effective_support[-1])),
        "mr_close": r(float(h.total_ratio[-1])),
        "promoted": int(h.promoted.sum()),
        "demoted": int(h.demoted.sum()),
        "core_close": int(net._in_core.sum()),
        "core_open": int(cfg.spec.layer1_size),
        # What the run did to the graph. The first is counted round by round.
        # The rest compare the graph before the first round with the close, so
        # a node that gained an edge and lost it again reads as unchanged there.
        "outdeg_moved_rounds": int(seen["rounds"]),
        "edges_initial": int(round(float(out_initial.sum()))),
        "edges_close": int(round(float(out_close.sum()))),
        "outdeg_nodes_changed": int((out_close != out_initial).sum()),
        "outdeg_max_gain": int(round(float((out_close - out_initial).max()))),
        "outdeg_max_loss": int(round(float((out_initial - out_close).max()))),
    }
    if asset:
        # The history row above is claims_recorded: written before the round's
        # asset settlement, with held units not in it. These are the same
        # statistics on claims_settled, what the run is left with, and on
        # net_worth, the model's own: claims plus units at the closing price.
        # ``true_net_worth`` is a welfare quantity and is not read here.
        settled = np.asarray(net.holdings, dtype=float)
        worth = np.asarray(net.net_worth(), dtype=float)
        for tag, v in (("claims_settled", settled), ("net_worth", worth)):
            row[f"top1_{tag}"] = r(top_share(v, max(1, n // 100)))
            row[f"top10_{tag}"] = r(top_share(v, n // 10))
            row[f"gini_{tag}"] = r(gini(v))
        row["claims_moved_after_sample"] = r(float(np.abs(settled - close).max()))
        row["held_value_share"] = r(float((worth - settled).sum() / worth.sum()))
    if digests is not None:
        digests[seed] = state_digest(net, h)
    return row


def mean_over(rows: list[dict], key: str) -> float:
    return r(float(np.mean([row[key] for row in rows])))


# ---------------------------------------------------------------------------
# Objects printed beside the criteria. None of them is scored.
# ---------------------------------------------------------------------------

#: What each field of the record is. Written into the record, because the two
#: carriers put different objects under the same key.
DEFINITIONS = {
    "top1_wealth, top10_wealth, gini": (
        "shares on claims_recorded: claims per node in the last row of the "
        "history. A round's row is written before that round's _post_round "
        "hook. On the registered carrier the hook does nothing and the row is "
        "the state the run ends in. On the asset carrier the round's asset "
        "settlement comes after it, and held units are in no row. The criteria "
        "read these on both carriers."
    ),
    "top1_claims_settled, top10_claims_settled, gini_claims_settled": (
        "asset carrier only: the same statistics on claims_settled, the claims "
        "the run ends with, after the last asset settlement."
    ),
    "top1_net_worth, top10_net_worth, gini_net_worth": (
        "asset carrier only: the same statistics on net_worth, the model's "
        "net_worth(): claims_settled plus units held at the closing price. "
        "true_net_worth(), which also subtracts the uncounted cost, is not read."
    ),
    "claims_moved_after_sample": (
        "asset carrier only: the largest change in any one node's claims "
        "between claims_recorded and claims_settled."
    ),
    "held_value_share": (
        "asset carrier only: units held at the closing price, as a share of "
        "total net worth."
    ),
    "support, mr_close": (
        "effective support and total claims over total resources, in the last "
        "row of the history."
    ),
    "core_open, core_close": (
        "the core's size at construction, before the first round, and at the "
        "close."
    ),
    "edges_initial, edges_close": (
        "edges in the adjacency before the first round and at the close."
    ),
    "outdeg_moved_rounds": (
        "rounds in which the rewiring changed some node's out-degree, counted "
        "round by round."
    ),
    "outdeg_nodes_changed, outdeg_max_gain, outdeg_max_loss": (
        "nodes whose out-degree at the close differs from the one before the "
        "first round, and the largest gain and loss among them."
    ),
    "top1_minus_off, mr_minus_off": (
        "the arm's five-seed mean less the off arm's, the same quantity as a "
        "width and as A13-8's steps. The by-seed lists beside them pair each "
        "seed with the off arm on the same seed."
    ),
    "width_exchange_only": (
        "the width of the five-seed means over the thirteen arms that only "
        "exchange edges, with the two arms at its ends."
    ),
    "width_by_seed": (
        "for each seed, the largest arm's value less the smallest arm's on that "
        "seed alone."
    ),
    "ruler": (
        "A2d's sigma and structure widths from A2d's record on the carrier this "
        "record was taken on, one pair per account that record carries. The "
        "claims_recorded pair is checked against the widths of that record's "
        "grid rows before it is used."
    ),
    "exchange_only_check": (
        "the thirteen arms that only exchange edges, with the rounds in which "
        "any node's out-degree moved and the nodes whose out-degree at the "
        "close differs from the one before the first round, summed over seeds. "
        "Both are zero or no record is written."
    ),
    "one_side_of_off": (
        "arms that fired and whose difference from the off arm, seed by seed, "
        "has one sign in every seed."
    ),
}


def spans(top1: dict[str, float]) -> dict:
    """Width of the arm means over all arms and over the exchange-only arms."""
    out = {}
    for suffix, arms in (("", list(top1)), ("_exchange_only", EXCHANGE_ONLY)):
        sub = {a: top1[a] for a in arms if a in top1}
        if not sub:
            continue
        lo, hi = min(sub, key=sub.get), max(sub, key=sub.get)
        out[f"width{suffix}"] = r(sub[hi] - sub[lo])
        out[f"lowest{suffix}"] = lo
        out[f"highest{suffix}"] = hi
    return out


def ruler_reading(asset: bool) -> dict:
    """A2d's two widths on the carrier this run was taken on, per account.

    Read off A2d's record. The claims_recorded pair is the one A13-3 prints, and
    it has to equal the widths of that record's own grid rows, or the ruler is
    not the record it names and nothing is written.
    """
    name = A2D_RECORD_ASSET if asset else A2D_RECORD
    ref = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    rows = {}
    for grid in ("sigma_grid", "structure_grid"):
        vs = [row["top1_wealth"] for row in ref[grid]]
        rows[grid] = r(max(vs) - min(vs))
    readings = ref.get("accounts", {}).get("readings", {})
    accounts = {
        account: {"sigma_width": readings[account]["sigma"]["width"],
                  "structure_width": readings[account]["structure"]["width"]}
        for account in ACCOUNTS if account in readings
    }
    from_rows = {"sigma_width": rows["sigma_grid"],
                 "structure_width": rows["structure_grid"]}
    if "claims_recorded" not in accounts:
        accounts["claims_recorded"] = from_rows
    elif accounts["claims_recorded"] != from_rows:
        raise ValueError(
            f"{name} carries claims_recorded widths {accounts['claims_recorded']} "
            f"and its grid rows give {from_rows}; the ruler is not that record")
    return {"record": name,
            "cells": {g: len(ref[g]) for g in ("sigma_grid", "structure_grid")},
            "accounts": accounts}


def fired(rows: list[dict]) -> bool:
    return any(row["promoted"] or row["demoted"] for row in rows)


def minus_off(by_arm: dict[str, list[dict]], arm: str, key: str) -> list[float]:
    """This arm less the off arm, seed by seed. The seeds are the same graphs."""
    off = {row["seed"]: row[key] for row in by_arm["off"]}
    return [r(row[key] - off[row["seed"]]) for row in by_arm[arm]
            if row["seed"] in off]


def one_side_of_off(by_arm: dict[str, list[dict]], key: str) -> list[str]:
    out = []
    for arm, rows in by_arm.items():
        d = minus_off(by_arm, arm, key)
        if fired(rows) and d and (all(v > 0 for v in d) or all(v < 0 for v in d)):
            out.append(arm)
    return out


def ladder_by_seed(by_arm: dict[str, list[dict]],
                   key: str = "top1_wealth") -> list[dict]:
    """A13-8's steps, one number per seed, so a mean one seed carries shows."""
    steps = []
    for lo, hi in zip(LADDER, LADDER[1:]):
        if lo not in by_arm or hi not in by_arm:
            continue
        at = {row["seed"]: row[key] for row in by_arm[lo]}
        d = [r(row[key] - at[row["seed"]]) for row in by_arm[hi]
             if row["seed"] in at]
        steps.append({
            "from": lo, "to": hi,
            "mean": r(mean_over(by_arm[hi], key) - mean_over(by_arm[lo], key)),
            "by_seed": d,
            "seeds_positive": sum(v > 0 for v in d),
        })
    return steps


def graph_reading(by_arm: dict[str, list[dict]]) -> dict:
    """What each arm did to the graph, beside what it did to the two readings.

    Printed because four arms move out-degree on purpose and thirteen must
    not, and a reader needs the edge columns beside the readings to say which
    of the two a reading followed.
    """
    off_top1 = mean_over(by_arm["off"], "top1_wealth")
    off_mr = mean_over(by_arm["off"], "mr_close")
    per_arm = {}
    for arm, rows in by_arm.items():
        initial, closed = mean_over(rows, "edges_initial"), mean_over(rows, "edges_close")
        top1, mr = mean_over(rows, "top1_wealth"), mean_over(rows, "mr_close")
        per_arm[arm] = {
            "edges_initial": initial,
            "edges_close": closed,
            "edges_ratio": r(closed / initial) if initial else None,
            "rounds_with_outdeg_move": sum(row["outdeg_moved_rounds"] for row in rows),
            "seeds_with_outdeg_change": sum(row["outdeg_nodes_changed"] > 0
                                            for row in rows),
            "outdeg_max_gain": max(row["outdeg_max_gain"] for row in rows),
            "outdeg_max_loss": max(row["outdeg_max_loss"] for row in rows),
            "top1": top1,
            "top1_minus_off": r(top1 - off_top1),
            "top1_minus_off_by_seed": minus_off(by_arm, arm, "top1_wealth"),
            "mr": mr,
            "mr_minus_off": r(mr - off_mr),
            "mr_minus_off_by_seed": minus_off(by_arm, arm, "mr_close"),
        }
    ratios = {a: v["edges_ratio"] for a, v in per_arm.items()
              if v["edges_ratio"] is not None}
    return {
        "per_arm": per_arm,
        **spans({a: v["top1"] for a, v in per_arm.items()}),
        "edges_ratio_range": ([min(ratios.values()), max(ratios.values())]
                              if ratios else None),
        "fired_with_out_degree_fixed": sorted(
            a for a, rows in by_arm.items()
            if fired(rows) and per_arm[a]["rounds_with_outdeg_move"] == 0
            and per_arm[a]["seeds_with_outdeg_change"] == 0),
        "density_ladder": [a for a in DENSITY_LADDER if a in per_arm],
        "one_side_of_off": {
            "top1_wealth": one_side_of_off(by_arm, "top1_wealth"),
            "mr_close": one_side_of_off(by_arm, "mr_close"),
        },
        "arms_that_fired": sorted(a for a, rows in by_arm.items() if fired(rows)),
    }


def asset_readings(by_arm: dict[str, list[dict]]) -> dict:
    """The asset run's three accounts of the same runs, side by side."""
    out = {}
    seeds = sorted({row["seed"] for rows in by_arm.values() for row in rows})
    for account, suffix in ACCOUNTS.items():
        key = f"top1_{suffix}"
        means = {a: mean_over(rows, key) for a, rows in by_arm.items()}
        by_seed = []
        for s in seeds:
            vs = [row[key] for rows in by_arm.values() for row in rows
                  if row["seed"] == s]
            by_seed.append(r(max(vs) - min(vs)))
        out[account] = {
            "row_key": key,
            "arm_means": means,
            **spans(means),
            "width_by_seed": by_seed,
            "off": means.get("off"),
            "off_by_seed": [row[key] for row in by_arm.get("off", [])],
            "ladder": ladder_by_seed(by_arm, key),
            "one_side_of_off": one_side_of_off(by_arm, key),
        }
    return out


def exchange_only_check(by_arm: dict[str, list[dict]]) -> dict:
    """What ``conserve_degree`` claims, read off the rows.

    In an arm that only exchanges edges no node's out-degree may move, in any
    round or at the close. Counted per arm so the one that leaks is named.
    """
    arms = [a for a in EXCHANGE_ONLY if a in by_arm]
    rounds = {a: sum(row["outdeg_moved_rounds"] for row in by_arm[a]) for a in arms}
    nodes = {a: sum(row["outdeg_nodes_changed"] for row in by_arm[a]) for a in arms}
    return {
        "arms": arms,
        "rounds_with_outdeg_move": sum(rounds.values()),
        "nodes_changed_at_close": sum(nodes.values()),
        "arms_that_moved": sorted(a for a in arms if rounds[a] or nodes[a]),
    }


def exchange_only_holds(check: dict) -> bool:
    return bool(check["arms"]) and set(check["arms"]) == set(EXCHANGE_ONLY) \
        and not check["arms_that_moved"]


def graph_lines(graph: dict) -> list[str]:
    per = graph["per_arm"]
    lines = [f"  {'arm':<28}{'edges':>9}{'x start':>9}{'top1-off':>11}{'M/R-off':>10}"]
    for arm in sorted(per, key=lambda a: per[a]["edges_close"]):
        v = per[arm]
        lines.append(f"  {arm:<28}{v['edges_close']:>9.1f}{v['edges_ratio']:>9.3f}"
                     f"{v['top1_minus_off']:>+11.6f}{v['mr_minus_off']:>+10.3f}")
    lines.append("  fired with every out-degree where it started: "
                 + ", ".join(graph["fired_with_out_degree_fixed"]))
    lines.append(f"  one side of the off arm in every seed, top1: "
                 f"{len(graph['one_side_of_off']['top1_wealth'])} of "
                 f"{len(graph['arms_that_fired'])} arms that fired; M/R: "
                 f"{len(graph['one_side_of_off']['mr_close'])}")
    lines.append(f"  width over all arms {graph['width']:.6f} ({graph['lowest']} .. "
                 f"{graph['highest']}); over the {len(EXCHANGE_ONLY)} that only "
                 f"exchange edges {graph['width_exchange_only']:.6f} "
                 f"({graph['lowest_exchange_only']} .. {graph['highest_exchange_only']})")
    return lines


def evaluate(by_arm: dict[str, list[dict]], *, seeds: int | None = None,
             asset: bool = False,
             digests: dict[str, dict[int, str]] | None = None) -> list[Criterion]:
    """Score one grid.

    ``seeds`` is how many seeds every arm was asked for; left out, it is the
    longest arm's count, so a grid in which every arm lost the same seed still
    has to be told. ``asset`` picks the ruler A13-3 is read against.
    ``digests`` are the per-run hashes from ``state_digest``; without them
    A13-5a compares the rows alone and says so.
    """
    out: list[Criterion] = []
    every = [row for rows in by_arm.values() for row in rows]

    # A grid, not a count of names: every arm, on every seed, with every share
    # finite. The count of names alone passed with a seed missing.
    want = list(range(seeds if seeds is not None
                      else max((len(rows) for rows in by_arm.values()), default=0)))
    short = sorted(a for a, rows in by_arm.items()
                   if sorted(row["seed"] for row in rows) != want)
    not_finite = sorted({a for a, rows in by_arm.items() for row in rows
                         if not all(np.isfinite(row[k]) for k in SHARES)})
    out.append(Criterion(
        "A13-1  every arm ran and returned a finite share",
        set(by_arm) == set(ARMS) and bool(want) and not short and not not_finite,
        f"{len(by_arm)}/{len(ARMS)} arms, {len(every)} runs. The stock-flow "
        f"identity is asserted inside the loop, so reaching here is also the "
        f"claim that it held in every round of every run."
        + (f" Not on seeds {want}: {short}." if short else "")
        + (f" A share that is not finite: {not_finite}." if not_finite else ""),
    ))

    # The off arm is the pre-switch construction. Discipline 19 says the check
    # is run rather than argued, and this is where it is run.
    off = by_arm["off"]
    out.append(Criterion(
        "A13-2  the off arm moves nothing",
        all(row["promoted"] == 0 and row["demoted"] == 0 for row in off),
        f"promoted {sum(row['promoted'] for row in off)}, demoted "
        f"{sum(row['demoted'] for row in off)} across {len(off)} runs. With the "
        f"switch off `_rewire` is unreachable, so this is the construction "
        f"itself and every record taken before 2026-08-23 is this arm.",
    ))

    # The span, against the two A2d measured on the same quantity.
    vals = [mean_over(rows, "top1_wealth") for rows in by_arm.values()]
    span = r(max(vals) - min(vals))
    # The ruler is taken on the carrier the run was taken on. Before
    # 2026-10-14 it was the registered carrier's record for both, which set an
    # asset span beside two widths measured without the asset layer.
    ruler = ruler_reading(asset)
    sig_w = ruler["accounts"]["claims_recorded"]["sigma_width"]
    st_w = ruler["accounts"]["claims_recorded"]["structure_width"]
    out.append(Criterion(
        "A13-3  mobility's span on terminal top1% wealth, against sigma's and "
        "the structure's",
        True,
        f"mobility {r(min(vals))}-{r(max(vals))}, width {span}. From A2d's "
        f"record on the same quantity: sigma width {sig_w}, structure width "
        f"{st_w}. Read: the larger span names what selects the terminal "
        f"distribution. This criterion prints the three and does not draw a "
        f"line."
        + (f" Ruler: {ruler['record']}, the same grids on this carrier, read "
           f"like this record's shares on claims_recorded, the last history "
           f"row." if asset else ""),
    ))

    # Rank alone is unbounded, and the terminal core size is the object that
    # says so. Three states, all reachable a priori.
    rank_only = [a for a in ARMS if a.startswith("rank") and "share" not in a]
    grew = {a: mean_over(by_arm[a], "core_close") for a in rank_only}
    bounded = {a: mean_over(by_arm[a], "core_close")
               for a in ARMS if "share" in a}
    n_nodes = NetworkSpec().layer1_size + NetworkSpec().layer2_size
    out.append(Criterion(
        "A13-4  the terminal core size, rank alone against rank with a share",
        True,
        "rank alone: " + ", ".join(f"{a} {v:.1f}" for a, v in grew.items())
        + f" out of {n_nodes}; with a share: "
        + ", ".join(f"{a} {v:.1f}" for a, v in bounded.items())
        + f", from an opening core of {NetworkSpec().layer1_size}. Read: a rank "
        f"always has somebody in it, so rank alone admits somebody every round "
        f"for ever; the share is what bounds the object.",
    ))

    # An arm that never fires passes everything by never running. Two arms
    # cannot fire by construction and are named rather than filtered silently:
    # ``off`` is the switch off, and ``retain 1`` sets the retention rate to one
    # with only demotion configured, so every candidate is retained. That second
    # arm is a null and its reading is checked below rather than skipped.
    cannot_fire = {
        a for a, s in ARMS.items()
        if not s.active
        or (s.retain_rate >= 1.0 and s.acquire_top_k == 0 and s.acquire_level == 0.0)
    }
    firing = {a: (mean_over(by_arm[a], "promoted"), mean_over(by_arm[a], "demoted"))
              for a in ARMS if a not in cannot_fire}
    out.append(Criterion(
        "A13-5  every arm that can fire, fired",
        all(p > 0 or d > 0 for p, d in firing.values()),
        "; ".join(f"{a} +{p:.0f}/-{d:.0f}" for a, (p, d) in firing.items())
        + f". Cannot fire by construction and excluded: {sorted(cannot_fire)}.",
    ))

    # The null that cannot fire has to land on the construction exactly, and it
    # is free: retaining every candidate is the same object as not demoting.
    #
    # Every reading in the row, not four of them, and then the hash of the whole
    # run, because a row keeps six decimals and "bitwise" is a claim about more
    # than six. Four readings passed with the null arm's top10 set to 0.9.
    null_arm = "demote .005 retain 1"
    null_rows, off_rows = by_arm[null_arm], by_arm["off"]
    keys = sorted(k for k in off_rows[0] if k != "seed") if off_rows else []
    rows_same = (
        bool(off_rows) and len(null_rows) == len(off_rows)
        and all(a["seed"] == b["seed"] and all(a.get(k) == b[k] for k in keys)
                for a, b in zip(null_rows, off_rows))
    )
    if digests is None:
        hashed = ""
        same = rows_same
    else:
        d_null, d_off = digests.get(null_arm, {}), digests.get("off", {})
        equal = sum(d_null.get(s) == d for s, d in d_off.items())
        hashed = (f", and one SHA-256 per run over the whole history and the "
                  f"state the run ends in, equal in {equal} of {len(d_off)} "
                  f"seeds")
        same = (rows_same and bool(d_off) and set(d_null) == set(d_off)
                and equal == len(d_off)
                and sorted(d_off) == [row["seed"] for row in off_rows])
    out.append(Criterion(
        "A13-5a  retaining every candidate is bitwise the construction",
        same,
        f"{null_arm} against off, every reading in the row ({len(keys)} per "
        f"seed) over {len(off_rows)} seeds{hashed}: "
        + ("identical" if same else "not identical, so the demotion path is "
           "doing something when it is told to do nothing"),
    ))

    # What does move. Printed, not scored.
    mr = {a: mean_over(rows, "mr_close") for a, rows in by_arm.items()}
    out.append(Criterion(
        "A13-6  what mobility does move: M/R",
        True,
        f"off {mr['off']}, and across the mobility arms "
        f"{r(min(mr.values()))}-{r(max(mr.values()))}. "
        + "; ".join(f"{a} {v}" for a, v in mr.items() if a != "off")
        + ". Read beside A13-3: the two quantities separate under this "
        f"mechanism, and which of them moves is the reading.",
    ))
    # The revolving door. Registered 2026-08-24 with the inbound arms, and it
    # reads a count rather than a level because what it is about is how many
    # times the same nodes cross, not where anybody ends.
    churn = {a: mean_over(rows, "demoted") for a, rows in by_arm.items()
             if ARMS[a].active}
    out_only = [a for a in churn if not ARMS[a].demote_cuts_inbound]
    cut = [a for a in churn if ARMS[a].demote_cuts_inbound]
    out.append(Criterion(
        "A13-7  demotions counted, outbound-only against inbound-cut",
        bool(cut) and bool(out_only),
        "; ".join(f"{a} {churn[a]:.0f}" for a in sorted(churn))
        + ". Read: leaving what the core sends a demoted node untouched lets its "
          "share recover to the promotion condition, so the same nodes cross "
          "repeatedly. Cutting the inbound edges closes that, and the count is "
          "where it shows. This criterion passes when both kinds of arm are "
          "present, which is the only way the comparison exists at all.",
    ))

    # A13-8. One rung per mechanism, so each difference has one owner.
    top1 = {a: mean_over(rows, "top1_wealth") for a, rows in by_arm.items()}
    rungs = [a for a in LADDER if a in top1]
    if len(rungs) == len(LADDER):
        steps = []
        for lo, hi in zip(rungs, rungs[1:]):
            steps.append(
                f"{lo} -> {hi}: top1% {top1[lo]:.6f} -> {top1[hi]:.6f} "
                f"({top1[hi] - top1[lo]:+.6f})"
            )
        first, last = top1[rungs[0]], top1[rungs[-1]]
        out.append(Criterion(
            "A13-8  what a promoted node acquires, one mechanism per rung",
            True,
            "; ".join(steps)
            + f". Whole ladder {first:.6f} -> {last:.6f} ({last - first:+.6f}), "
              f"against the off arm at {top1['off']:.6f}. "
              "Read: the arms before this one buy edges only, so they measure "
              "what buying access does. This ladder adds the spending "
              "propensity and then the payroll role, one at a time, so each "
              "step's difference belongs to the mechanism that step added. "
              "The criterion prints the steps and draws no line: what it "
              "settles is whether the three mechanisms are separable at all, "
              "not how large any of them is.",
        ))
    else:
        out.append(Criterion(
            "A13-8  what a promoted node acquires, one mechanism per rung",
            False,
            f"the ladder needs all of {list(LADDER)} and this run has "
            f"{rungs}; not judged",
            void=True,
        ))

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second.",
    )
    ap.add_argument(
        "--no-write", action="store_true",
        help="print the table and the criteria and write no record. For a "
             "smoke run at reduced rounds or seeds, which otherwise "
             "overwrites the registered record at the same path with "
             "numbers taken on a different grid. Bought on 2026-08-24 by "
             "doing exactly that.",
    )
    args = ap.parse_args()

    print(f"A13  rounds={args.rounds} seeds={args.seeds} arms={len(ARMS)}\n")
    hdr = (f"{'arm':<28}{'top1%':>9}{'top10%':>9}{'gini':>9}{'support':>9}"
           f"{'M/R':>9}{'+':>6}{'-':>6}{'core':>6}")
    print(hdr)
    print("-" * len(hdr))

    by_arm: dict[str, list[dict]] = {}
    digests: dict[str, dict[int, str]] = {}
    for tag, spec in ARMS.items():
        rows = [one(spec, seed, args.rounds, args.asset,
                    digests.setdefault(tag, {}))
                for seed in range(args.seeds)]
        by_arm[tag] = rows
        print(f"{tag:<28}{mean_over(rows,'top1_wealth'):>9.4f}"
              f"{mean_over(rows,'top10_wealth'):>9.4f}{mean_over(rows,'gini'):>9.4f}"
              f"{mean_over(rows,'support'):>9.3f}{mean_over(rows,'mr_close'):>9.2f}"
              f"{mean_over(rows,'promoted'):>6.0f}{mean_over(rows,'demoted'):>6.0f}"
              f"{mean_over(rows,'core_close'):>6.1f}")

    criteria = evaluate(by_arm, seeds=args.seeds, asset=args.asset,
                        digests=digests)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    graph = graph_reading(by_arm)
    print("\nwhat each arm did to the graph (five-seed means, not scored)")
    for line in graph_lines(graph):
        print(line)
    ladder = ladder_by_seed(by_arm)
    print("\nA13-8's steps seed by seed")
    for step in ladder:
        print(f"  {step['from']} -> {step['to']}: mean {step['mean']:+.6f}; "
              + ", ".join(f"{v:+.6f}" for v in step["by_seed"])
              + f"; positive in {step['seeds_positive']} of {len(step['by_seed'])}")
    ruler = ruler_reading(args.asset)
    readings = asset_readings(by_arm) if args.asset else None
    if readings:
        print("\nthe asset run on three accounts (top1%, five-seed means)")
        for account, v in readings.items():
            steps = "; ".join(
                f"{s['mean']:+.6f} ({s['seeds_positive']}/{len(s['by_seed'])} seeds up)"
                for s in v["ladder"])
            print(f"  {account:<16} off {v['off']:.6f}  width {v['width']:.6f}  "
                  f"ladder steps {steps}  one side of off: "
                  f"{len(v['one_side_of_off'])} arms")
            print(f"  {'':<16} width by seed "
                  + ", ".join(f"{w:.6f}" for w in v["width_by_seed"]))
        print("\nA2d's two widths on this carrier, from its record, on each account")
        for account, v in readings.items():
            ref = ruler["accounts"].get(account)
            if ref:
                print(f"  {account:<16} mobility {v['width']:.6f}  "
                      f"sigma {ref['sigma_width']:.6f}  "
                      f"structure {ref['structure_width']:.6f}")
            else:
                print(f"  {account:<16} mobility {v['width']:.6f}  "
                      f"{ruler['record']} carries no reading on this account")
    exchange = exchange_only_check(by_arm)
    print(f"\nthe {len(EXCHANGE_ONLY)} arms that only exchange edges: rounds with an "
          f"out-degree moved {exchange['rounds_with_outdeg_move']}, nodes changed "
          f"at the close {exchange['nodes_changed_at_close']}, arms that moved "
          f"{exchange['arms_that_moved']}")
    null_check = {
        "arms": ["demote .005 retain 1", "off"],
        "readings_compared": sorted(k for k in by_arm["off"][0] if k != "seed"),
        "seeds": len(by_arm["off"]),
        "runs_hashed_equal": sum(
            digests["demote .005 retain 1"].get(s) == d
            for s, d in digests["off"].items()),
    }

    # Not a criterion and not in the count above. It checks the shared rule
    # this record is read on, so a rule that leaks stops the run instead of
    # writing a span over arms that changed density.
    held_ok = exchange_only_holds(exchange)
    if not held_ok:
        print("\n  an arm that only exchanges edges moved an out-degree; "
              "no record written")

    if args.no_write:
        print("\n  --no-write: no record written")
        return 0 if all(c.passed for c in live) and held_ok else 1
    if not held_ok:
        return 1

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a13_mobility.json" if not args.asset else "a13_mobility_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A13",
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "cluster_rate": CLUSTER_RATE,
                "retain_rate": RETAIN_RATE,
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this "
                        "station's registered carrier; the registered "
                        "reading is results/a13_mobility.json"
                    )} if args.asset else {}),
                "arms": {a: [str(v) for v in [ARMS[a]]] for a in ARMS},
                "runs": {a: rows for a, rows in by_arm.items()},
                "definitions": DEFINITIONS,
                "graph": graph,
                "ladder_by_seed": ladder,
                "null_check": null_check,
                "ruler": ruler,
                "exchange_only_check": exchange,
                **({"asset_readings": readings} if readings else {}),
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "detail": c.detail, "void": bool(c.void)}
                    for c in criteria
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
