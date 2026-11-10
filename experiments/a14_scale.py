"""A14: which readings are scale free, and which are artefacts of two hundred nodes.

Two knobs carry no derivation anywhere in this repository. ``n = 200`` is one,
and ``layer1_size / n = 0.10`` is the other. A2d's structure grid held both
fixed, so the structural span it reports is a lower bound.

The measurement that shaped this stage, taken before the arms were written. A
sweep of ``n`` with the degree parameters left alone reads terminal top1% wealth
rising from 0.2300 to 0.3388 between 200 and 1000 nodes. The same sweep with the
degrees scaled to hold each layer's density fixed reads it **falling**, 0.2300
to 0.1905. The degree parameters are absolute edge counts, so raising ``n``
without them thins the financial layer from 32% internal density to 6% and gives
preferential attachment room to build hubs it did not have. **A sweep of ``n``
alone is a sweep of density with extra steps**, which is why both arms are here
and neither is optional.

What this stage does not do is rerun the other stages. It reads their headline
quantities on a grid. Their criteria carry thresholds set for 200 nodes, and
moving those for a reason unrelated to their own questions would be a change to
their records that answers nothing.

Excluded, and named rather than silently dropped: A8's and A12's four surfaces,
because ``f2i`` is an absolute edge count whose maximum of 30 is 7.5% of the
possible financial-to-intermediate edges at 200 nodes and 0.3% at 1000, so the
same grid tests a different regime; A7's shortcut rate, for the same reason and
unchecked; and the rewire switch, which stays off throughout because two knobs
move one at a time.

What ``top1_wealth``, ``top01_wealth`` and ``gini`` read, on either carrier, is
the account the docstring of ``monetary_topology.asset.carrier_model`` calls
``claims_recorded``: the last history row, written after the last round's
network step and before its asset step. On the registered carrier nothing
follows that row and claims are all a node holds. With ``--asset`` every run
also carries ``claims_settled`` and ``net_worth`` under ``accounts``, and
``asset_accounts`` prints the stage's readings on all three. They are printed
and not scored. The asset layer carries two absolute numbers, a supply of a
hundred units and a price ladder of 0.5, 1 and 2 in claims, while the mean
opening claim falls from 0.5 at 200 nodes to 0.1 at 1000; on that carrier a
sweep of ``n`` therefore also thins entry to the asset market.
``per_node_control`` runs the same 27 cells with both held per node, half a
unit a node and the ladder scaled by ``200 / n``, which at 200 nodes is the
grid itself, run for run.

Usage::

    python experiments/a14_scale.py
    python experiments/a14_scale.py --seeds 5
    python experiments/a14_scale.py --asset

Writes ``results/a14_scale.json``, or ``results/a14_scale_asset.json`` with
``--asset``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import A3Config, A3Model, AssetSpec, carrier_model
from monetary_topology.mechanisms import gini
from monetary_topology.network import Network, NetworkConfig, NetworkSpec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DIGITS = 6

#: Node counts. 2000 is out: the density-preserving arm reaches an internal
#: out-degree of 63 there and does not finish in a useful time, and the reversal
#: this stage exists to show is already legible across 200, 500 and 1000.
SIZES = (200, 500, 1000)

#: Core as a share of nodes. 0.05 is the published break, 0.10 is the current
#: value and carries no derivation, 0.20 is an upper reference with no source.
FRACTIONS = (0.05, 0.10, 0.20)

_B = NetworkSpec()
#: The densities at the construction's own size, which the scaled arm preserves.
DENSITY_L1 = _B.layer1_out_degree / (20 - 1)
DENSITY_L2 = _B.layer2_out_degree / (180 - 1)
DENSITY_UP = _B.upward_out_degree / 20

#: A4-2's registered readings, quoted so the comparison is against the record
#: rather than against a number restated here.
A4_STRATIFIED = 0.93673
A4_NULL = 0.00711
A4_NULL_CEILING = 0.02

#: The construction's own cell: the size and core share every other stage runs
#: at, where the density-preserving arm asks for the default degrees and so is
#: the same specification as the fixed-degree arm.
CONSTRUCTION_N = 200
CONSTRUCTION_FRACTION = 0.10

#: A14-3's six quantities, in the order its criterion prints them.
HEADLINE = ("top1_wealth", "gini", "support_ratio", "support_close",
            "volume_ratio", "mr_close")

#: The three accounts of ``carrier_model``'s docstring. The first is what
#: ``top1_wealth``, ``top01_wealth`` and ``gini`` have always read.
ACCOUNTS = ("claims_recorded", "claims_settled", "net_worth")

#: The two distribution readings compared across the three accounts. The other
#: four headline quantities are flows and have no settled or marked version.
SHARE_KEYS = ("top1_wealth", "gini")

#: The control that holds the asset layer per node: half a unit a node, which is
#: the registered supply at 200 nodes, and the opening ladder scaled by 200 / n
#: so that its rungs stay at 1, 2 and 4 times the mean opening claim.
PER_NODE_UNITS = 0.5

#: What each field reads, written into the record so that the name ``wealth``
#: is not left to say more than the field does on a carrier with held units.
DEFINITIONS = {
    "top1_wealth, top01_wealth, gini": (
        "claims_recorded: shares and Gini of the last history row "
        "(NetworkHistory.holdings[-1]), written after the last round's network "
        "step and before its asset step. On the registered carrier nothing "
        "follows that row and claims are the whole of what a node holds."
    ),
    "direction_by_fraction": (
        "A14-3's comparison of the two degree arms, made for all six of its "
        "quantities at each core share on claims_recorded: the path of the "
        "five-seed mean over the sizes, how many seeds are higher at the "
        "largest size than at the smallest, and how many of the pairs of one "
        "run at each of those two sizes are. Printed, not scored; A14-3 itself "
        "is registered at 0.10."
    ),
    "accounts.claims_settled": (
        "asset carrier only: the same three readings on the claims after the "
        "last round's asset step, which collects rent, serves stretch debt, "
        "settles resales and reprices."
    ),
    "accounts.net_worth": (
        "asset carrier only: the same three readings on net_worth(), settled "
        "claims plus held units at the closing price."
    ),
    "accounts.*_initial": (
        "read on the model before the run, after the opening allocation: units "
        "held in all and by tier, owners, most units on one node, the mean "
        "opening claim per node, the supply by tier, the opening price ladder, "
        "and the cheapest gate on any node divided by the stretch."
    ),
    "accounts.*_close_settled": (
        "read on the model after the run: units held, owners, most units on "
        "one node, held units marked at the closing price, and total claims."
    ),
    "accounts.last_round_cash_moved, last_round_largest_change": (
        "whether any node's claims differ between claims_recorded and "
        "claims_settled, and the largest single-node difference."
    ),
    "accounts.asset_layer_inert": (
        "true when no unit is held at the opening or at the close and the "
        "settled claim history equals the recorded one element for element, "
        "so the run is the plain carrier's run."
    ),
    "asset_accounts": (
        "the stage's readings on the asset grid under each account, the null "
        "arm's holdings by size, the last asset step, how net worth compares "
        "with claims, and the share of net worth held as units. Printed, not "
        "scored."
    ),
    "per_node_control": (
        "the same 27 cells and seeds with the asset layer held per node: "
        "AssetSpec(units_per_node=0.5) and the opening price ladder times "
        "200 / n, the network configuration untouched. At 200 nodes this is "
        "the asset grid's own specification. Printed, not scored."
    ),
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


def spec_for(n: int, fraction: float, arm: str, seed: int) -> NetworkSpec:
    n1 = max(2, round(n * fraction))
    n2 = n - n1
    if arm == "scaled":
        d1 = max(1, round(DENSITY_L1 * (n1 - 1)))
        d2 = max(1, round(DENSITY_L2 * (n2 - 1)))
        du = max(1, round(DENSITY_UP * n1))
    else:
        d1, d2, du = (_B.layer1_out_degree, _B.layer2_out_degree,
                      _B.upward_out_degree)
    return NetworkSpec(
        seed=seed, layer1_size=n1, layer2_size=n2,
        layer1_out_degree=min(d1, n1 - 1),
        layer2_out_degree=min(d2, n2 - 1),
        upward_out_degree=min(du, n1),
        uniform_access=(arm == "null"),
    )


def per_node_asset(n: int) -> AssetSpec:
    """The asset layer of ``per_node_control`` at ``n`` nodes."""
    base = AssetSpec()
    return AssetSpec(
        units_per_node=PER_NODE_UNITS,
        initial_price=tuple(p * CONSTRUCTION_N / n for p in base.initial_price),
    )


def shares(v: np.ndarray, n: int) -> dict:
    """The stage's three distribution readings on one vector."""
    return {
        "top1_wealth": r(top_share(v, max(1, n // 100))),
        "top01_wealth": r(top_share(v, max(1, n // 1000))),
        "gini": r(gini(v)),
    }


def opening_units(model, n: int) -> dict:
    """Who holds what after the opening allocation. Read before the run."""
    per_node = model.units.sum(axis=1)
    stretch = float(model.a3.asset.stretch)
    gates = model.terms_gate * model.price[None, :]
    return {
        "units_initial": int(round(float(per_node.sum()))),
        "units_initial_by_tier": [int(round(float(x)))
                                  for x in model.units.sum(axis=0)],
        "owners_initial": int((per_node > 0).sum()),
        "max_units_one_node_initial": int(round(float(per_node.max()))),
        "claims_per_node_initial": r(float(model.config.initial_claims) / n),
        "supply_by_tier_initial": [int(x) for x in model.supply],
        "price_initial": [r(float(p)) for p in model.price],
        "lowest_stretch_gate_initial": r(float(gates.min()) / stretch),
    }


def asset_accounts(model, h, n: int, initial: dict) -> dict:
    """The two accounts the history does not carry, and what the layer held.

    ``h.holdings[-1]`` is ``claims_recorded``, written before the last round's
    asset step, so it is neither of these. Both are read off the model after
    the run.
    """
    recorded = h.holdings[-1]
    settled = np.asarray(model.holdings, dtype=float)
    worth = np.asarray(model.net_worth(), dtype=float)
    per_node = model.units.sum(axis=1)
    held_close = int(round(float(per_node.sum())))
    inert = (
        initial["units_initial"] == 0 and held_close == 0
        and np.array_equal(np.asarray(model.claims_history), h.holdings)
    )
    return {
        "claims_settled": shares(settled, n),
        "net_worth": shares(worth, n),
        "last_round_cash_moved": bool(np.any(settled != recorded)),
        "last_round_largest_change": r(float(np.max(np.abs(settled - recorded)))),
        **initial,
        "units_close_settled": held_close,
        "owners_close_settled": int((per_node > 0).sum()),
        "max_units_one_node_close_settled": int(round(float(per_node.max()))),
        "marked_units_close_settled": r(float((model.units @ model.price).sum())),
        "claims_close_settled": r(float(settled.sum())),
        "asset_layer_inert": bool(inert),
    }


def one(n: int, fraction: float, arm: str, seed: int, rounds: int,
        asset: bool = False, per_node: bool = False) -> dict:
    spec = spec_for(n, fraction, arm, seed)
    cfg = NetworkConfig(spec=spec, seed=seed, rounds=rounds)
    if per_node:
        model = A3Model(A3Config(asset=per_node_asset(n), network=cfg))
    else:
        model = carrier_model(cfg, asset=asset)
    held = asset or per_node
    initial = opening_units(model, n) if held else None
    h = model.run()
    close = h.holdings[-1]
    sup = np.asarray(h.effective_support, dtype=float)
    vol = np.asarray(h.total_volume, dtype=float)
    row = {
        "n": n, "fraction": fraction, "arm": arm, "seed": seed,
        "layer1_size": spec.layer1_size,
        "l1_out_degree": spec.layer1_out_degree,
        "l1_density": r(spec.layer1_out_degree / max(spec.layer1_size - 1, 1)),
        "edges": int(h.adjacency.sum()),
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top01_wealth": r(top_share(close, max(1, n // 1000))),
        "gini": r(gini(close)),
        "support_ratio": r(float(sup[-1] / sup[0])),
        "support_close": r(float(sup[-1])),
        "volume_ratio": r(float(vol[-1] / vol[0])),
        "mr_close": r(float(h.total_ratio[-1])),
        "top1_nodes": max(1, n // 100),
        "top01_nodes": max(1, n // 1000),
    }
    if held:
        row["accounts"] = asset_accounts(model, h, n, initial)
    return row


def mean_of(rows: list[dict], key: str) -> float:
    return r(float(np.mean([row[key] for row in rows])))


def grid_coverage(rows: list[dict], seeds: int | None) -> dict:
    """What A14-1 reads: every cell's seeds, and the construction's two arms.

    ``seeds`` is how many each cell was asked for. ``None`` takes the seeds the
    rows themselves carry, which is all a caller holding only rows can ask for.
    """
    cells: dict[tuple, list[int]] = {}
    for row in rows:
        cells.setdefault((row["n"], row["fraction"], row["arm"]), []).append(
            row["seed"])
    want = (list(range(seeds)) if seeds is not None
            else sorted({row["seed"] for row in rows}))
    short = sorted(k for k, v in cells.items() if sorted(v) != want)

    def arm_rows(arm: str) -> list[dict]:
        return sorted(
            (row for row in rows
             if row["n"] == CONSTRUCTION_N
             and row["fraction"] == CONSTRUCTION_FRACTION
             and row["arm"] == arm),
            key=lambda row: row["seed"])

    fixed, scaled = arm_rows("fixed"), arm_rows("scaled")
    fields = sorted(k for k in (fixed[0] if fixed else {}) if k != "arm")
    differing = sorted({
        k for a, b in zip(fixed, scaled) for k in fields if a[k] != b.get(k)})
    coincide = (len(fixed) == len(scaled) == len(want) > 0 and not differing
                and all(a["seed"] == b["seed"] for a, b in zip(fixed, scaled)))
    return {
        "cells": len(cells), "want": want, "short": short,
        "fields": fields, "differing": differing, "coincide": coincide,
        "finite": all(np.isfinite(row["top1_wealth"]) for row in rows),
    }


def evaluate(rows: list[dict], rounds: int,
             seeds: int | None = None) -> list[Criterion]:
    out: list[Criterion] = []

    def pick(**kw) -> list[dict]:
        return [row for row in rows
                if all(row[k] == v for k, v in kw.items())]

    expected = len(SIZES) * len(FRACTIONS) * 3
    per = len({(row["n"], row["fraction"], row["arm"]) for row in rows})
    cover = grid_coverage(rows, seeds)
    want = cover["want"]
    seeds_text = (f"seeds {want[0]}-{want[-1]}" if want else "no seeds")
    out.append(Criterion(
        "A14-1  every cell ran, and the construction's own cell reproduces",
        per == expected and cover["finite"]
        and not cover["short"] and cover["coincide"],
        f"{per}/{expected} cells. The construction's own cell is n=200, "
        f"fraction=0.10, arm fixed, where the two degree arms coincide by "
        f"definition: fixed reads "
        f"{mean_of(pick(n=200, fraction=0.10, arm='fixed'), 'top1_wealth')} and "
        f"scaled reads "
        f"{mean_of(pick(n=200, fraction=0.10, arm='scaled'), 'top1_wealth')}."
        + (f" Every cell carries {seeds_text}."
           if not cover["short"] else
           f" {len(cover['short'])} cells do not carry {seeds_text}: "
           f"{cover['short'][:3]}.")
        + (f" The two arms agree row for row on all {len(cover['fields'])} "
           f"fields other than the arm label."
           if cover["coincide"] else
           f" The two arms do not agree row for row: "
           f"{cover['differing'][:4] or 'rows missing'}."),
    ))

    # The span with n in the grid, against A2d's without it.
    span_here = [mean_of(pick(n=n, fraction=f, arm=a), "top1_wealth")
                 for n in SIZES for f in FRACTIONS for a in ("fixed", "scaled")]
    ref = json.loads((RESULTS / "a2d_terminal_selector.json").read_text(encoding="utf-8"))
    a2d = [row["top1_wealth"] for row in ref["structure_grid"]]
    out.append(Criterion(
        "A14-2  the structural span with n and the core fraction in the grid",
        True,
        f"this stage {r(min(span_here))}-{r(max(span_here))}, width "
        f"{r(max(span_here) - min(span_here))}. A2d's structure grid, which held "
        f"n at 200 and the fraction at 0.10, reported "
        f"{r(min(a2d))}-{r(max(a2d))}, width {r(max(a2d) - min(a2d))}. Read: "
        f"A2d's figure is a lower bound and this is the value with both knobs "
        f"in.",
    ))

    # The reversal. Two arms, same quantity, direction compared.
    lines = []
    reversed_any = False
    for key in ("top1_wealth", "gini", "support_ratio", "support_close",
                "volume_ratio", "mr_close"):
        d = {}
        for arm in ("fixed", "scaled"):
            v = [mean_of(pick(n=n, fraction=0.10, arm=arm), key) for n in SIZES]
            d[arm] = (v[0], v[-1], r(v[-1] - v[0]))
        same = np.sign(d["fixed"][2]) == np.sign(d["scaled"][2])
        reversed_any |= not same
        lines.append(
            f"{key}: fixed {d['fixed'][0]}->{d['fixed'][1]} ({d['fixed'][2]:+}), "
            f"scaled {d['scaled'][0]}->{d['scaled'][1]} ({d['scaled'][2]:+}), "
            f"{'same direction' if same else 'REVERSED'}")
    out.append(Criterion(
        "A14-3  the two degree arms, same quantity, direction compared",
        True,
        "; ".join(lines)
        + ". Read: two arms agreeing in direction is a scale effect; a "
          "reversal says the quantity was measuring density, not size."
        + (" At least one quantity reverses."
           if reversed_any else " No quantity reverses."),
    ))

    # The core fraction axis.
    frac_lines = []
    for f in FRACTIONS:
        v = mean_of(pick(n=1000, fraction=f, arm="scaled"), "top1_wealth")
        g = mean_of(pick(n=1000, fraction=f, arm="scaled"), "gini")
        frac_lines.append(f"{f}: top1% {v}, gini {g}")
    out.append(Criterion(
        "A14-4  the core fraction axis at n=1000, density held",
        True,
        "; ".join(frac_lines)
        + ". Read: 0.05 is the published break (Fagereng et al.'s composition "
          "change at P95, and Saez-Zucman's flat P90-99 share over three "
          "decades); 0.10 is the current value and carries no derivation "
          "anywhere in this repository; 0.20 is an upper reference with no "
          "source.",
    ))

    # Resolution, printed rather than claimed.
    res = "; ".join(
        f"n={n}: top1% is {max(1, n // 100)} nodes, top0.1% is "
        f"{max(1, n // 1000)}" for n in SIZES)
    out.append(Criterion(
        "A14-5  what the top percentiles are, in nodes, at each size",
        True,
        res + ". Read: the distribution the published estimates describe has a "
              "top 0.1% and at 200 nodes that group is one node by the floor "
              "rather than by the construction.",
    ))

    # The one quantity this stage can put against a published figure. Printed,
    # not scored: the published number is for city income and activity, not for
    # claim holdings, so it places the magnitude and does not judge the model.
    g0 = mean_of(pick(n=SIZES[0], fraction=0.10, arm="fixed"), "gini")
    g1 = mean_of(pick(n=SIZES[-1], fraction=0.10, arm="fixed"), "gini")
    doublings = float(np.log2(SIZES[-1] / SIZES[0]))
    per_doubling = r(((g1 / g0) ** (1.0 / doublings) - 1.0) * 100.0)
    s0 = mean_of(pick(n=SIZES[0], fraction=0.10, arm="scaled"), "gini")
    s1 = mean_of(pick(n=SIZES[-1], fraction=0.10, arm="scaled"), "gini")
    per_doubling_scaled = r(((s1 / s0) ** (1.0 / doublings) - 1.0) * 100.0)
    out.append(Criterion(
        "A14-7  Gini per doubling of population, against the published figure",
        True,
        f"fixed-degree arm: {g0} at n={SIZES[0]} to {g1} at n={SIZES[-1]}, "
        f"{doublings:.2f} doublings, **{per_doubling:+}% per doubling**. "
        f"Density-preserving arm: {s0} to {s1}, {per_doubling_scaled:+}% per "
        f"doubling. Published reference: intra-urban economic activity Gini "
        f"scales with population at alpha = 0.11, about +8% per doubling, over "
        f"11,000 global urban centres. Read: the fixed-degree arm is the one "
        f"with a source for its degree assumption, and its sign is the "
        f"comparison; the magnitude is bounded above by the model's closing "
        f"Gini already sitting near one, which is a reading about the model's "
        f"top tail rather than about population.",
    ))

    # A4's two readings across the grid.
    a4 = []
    for n in SIZES:
        s = mean_of(pick(n=n, fraction=0.10, arm="fixed"), "gini")
        z = mean_of(pick(n=n, fraction=0.10, arm="null"), "gini")
        a4.append((n, s, z, r(s - z)))
    ok = all(z < A4_NULL_CEILING for _, _, z, _ in a4)
    out.append(Criterion(
        "A14-6  A4's null stays under its registered ceiling at every size",
        ok,
        "; ".join(f"n={n}: stratified {s}, null {z}, gap {g}" for n, s, z, g in a4)
        + f". A4's record: stratified {A4_STRATIFIED}, null {A4_NULL}, ceiling "
          f"{A4_NULL_CEILING}.",
    ))
    return out


def account_value(row: dict, account: str, key: str) -> float:
    """One reading of one run under one of the three accounts."""
    if account == "claims_recorded":
        return row[key]
    return row["accounts"][account][key]


def _cell(rows: list[dict], n: int, fraction: float, arm: str) -> list[dict]:
    return sorted(
        (row for row in rows if row["n"] == n
         and row["fraction"] == fraction and row["arm"] == arm),
        key=lambda row: row["seed"])


def _account_mean(group: list[dict], account: str, key: str) -> float:
    return r(float(np.mean([account_value(row, account, key)
                            for row in group])))


def direction_by_fraction(rows: list[dict], account: str = "claims_recorded",
                          keys: tuple[str, ...] | None = None) -> dict:
    """A14-3's comparison of the two degree arms, at every core share.

    A14-3 is registered at a core share of 0.10 and its line in the criteria is
    untouched. This makes the same comparison at 0.05 and 0.20 as well, for all
    six of its quantities on ``claims_recorded`` and for the two distribution
    readings on the other accounts, with two counts beside each path: how many
    seeds are higher at the largest size than at the same seed at the smallest,
    and how many of all the pairs of one run at each of those sizes are, which
    does not lean on seed numbers matching across sizes. **Printed, not
    scored.**
    """
    if keys is None:
        keys = HEADLINE if account == "claims_recorded" else SHARE_KEYS
    first, last = SIZES[0], SIZES[-1]
    direction: dict = {}
    for f in FRACTIONS:
        per_key: dict = {}
        for key in keys:
            arms: dict = {}
            for arm in ("fixed", "scaled"):
                path = [_account_mean(_cell(rows, n, f, arm), account, key)
                        for n in SIZES]
                lo = {row["seed"]: account_value(row, account, key)
                      for row in _cell(rows, first, f, arm)}
                hi = {row["seed"]: account_value(row, account, key)
                      for row in _cell(rows, last, f, arm)}
                arms[arm] = {
                    "path": path,
                    "change": r(path[-1] - path[0]),
                    "seeds_rising": sum(hi[s] > lo[s] for s in lo if s in hi),
                    "seeds": len(lo),
                    "pairs_rising": sum(b > a for a in lo.values()
                                        for b in hi.values()),
                    "pairs": len(lo) * len(hi),
                }
            arms["reversed"] = bool(
                np.sign(arms["fixed"]["change"])
                != np.sign(arms["scaled"]["change"]))
            per_key[key] = arms
        direction[str(f)] = per_key
    return direction


def asset_account_readings(rows: list[dict]) -> dict:
    """The stage's readings on an asset grid under each account.

    **Printed, not scored.** The registered carrier has no held units, so there
    the three accounts are one vector and this block does not exist. On the
    asset carrier the supply is a hundred units and the price ladder 0.5, 1 and
    2 at every ``n`` while the mean opening claim falls, so the sweep of ``n``
    there also thins entry to the asset market; what is printed here says what
    each account reads and does not turn into a verdict on size.
    """
    def cell(n: int, fraction: float, arm: str) -> list[dict]:
        return _cell(rows, n, fraction, arm)

    mean = _account_mean
    stratified = [row for row in rows if row["arm"] != "null"]
    out: dict = {}
    for account in ACCOUNTS:
        span = [mean(cell(n, f, a), account, "top1_wealth")
                for n in SIZES for f in FRACTIONS for a in ("fixed", "scaled")]
        nulls = [row for row in rows if row["arm"] == "null"]
        out[account] = {
            "non_null_top1_span": [r(min(span)), r(max(span)),
                                   r(max(span) - min(span))],
            "construction_cell_top1": mean(
                cell(CONSTRUCTION_N, CONSTRUCTION_FRACTION, "fixed"),
                account, "top1_wealth"),
            "direction_by_fraction": direction_by_fraction(
                rows, account, SHARE_KEYS),
            "null_gini_by_size": {
                str(n): mean(cell(n, CONSTRUCTION_FRACTION, "null"),
                             account, "gini") for n in SIZES},
            "null_gini_lowest_run_by_size": {
                str(n): r(min(account_value(row, account, "gini")
                              for row in nulls if row["n"] == n))
                for n in SIZES},
        }

    against: dict = {}
    for base in ("claims_recorded", "claims_settled"):
        per_key: dict = {}
        for key in SHARE_KEYS:
            cells = [(mean(cell(n, f, a), "net_worth", key),
                      mean(cell(n, f, a), base, key))
                     for n in SIZES for f in FRACTIONS for a in ("fixed", "scaled")]
            runs = [(account_value(row, "net_worth", key),
                     account_value(row, base, key)) for row in stratified]
            per_key[key] = {
                "cells_net_worth_above": sum(w > c for w, c in cells),
                "cells": len(cells),
                "runs_net_worth_above": sum(w > c for w, c in runs),
                "runs": len(runs),
            }
        against[base] = per_key
    out["net_worth_against_claims"] = against

    def held_share(row: dict) -> float:
        a = row["accounts"]
        total = a["claims_close_settled"] + a["marked_units_close_settled"]
        return a["marked_units_close_settled"] / total if total > 0 else 0.0

    held = [held_share(row) for row in stratified]
    out["held_share_of_net_worth"] = {
        "stratified_runs": len(held),
        "lowest": r(min(held)) if held else None,
        "highest": r(max(held)) if held else None,
        "median_by_size": {
            str(n): r(float(np.median([held_share(row) for row in stratified
                                       if row["n"] == n])))
            for n in SIZES},
    }

    nulls_by_size = {}
    for n in SIZES:
        group = [row for f in FRACTIONS for row in cell(n, f, "null")]
        acc = [row["accounts"] for row in group]
        nulls_by_size[str(n)] = {
            "runs": len(group),
            "claims_per_node_initial": sorted(
                {a["claims_per_node_initial"] for a in acc}),
            "supply_by_tier_initial": sorted(
                {tuple(a["supply_by_tier_initial"]) for a in acc}),
            "lowest_stretch_gate_initial": sorted(
                {a["lowest_stretch_gate_initial"] for a in acc}),
            "units_initial": sorted({a["units_initial"] for a in acc}),
            "units_initial_by_tier": sorted(
                {tuple(a["units_initial_by_tier"]) for a in acc}),
            "max_units_one_node_initial": sorted(
                {a["max_units_one_node_initial"] for a in acc}),
            "units_close_settled": sorted({a["units_close_settled"] for a in acc}),
            "max_units_one_node_close_settled": [
                min(a["max_units_one_node_close_settled"] for a in acc),
                max(a["max_units_one_node_close_settled"] for a in acc)],
            "runs_asset_layer_inert": sum(a["asset_layer_inert"] for a in acc),
        }
    out["null_arm_units"] = nulls_by_size
    moved = [row["accounts"] for row in rows]
    out["last_round_settlement"] = {
        "runs": len(moved),
        "runs_cash_moved": sum(a["last_round_cash_moved"] for a in moved),
        "largest_single_node_change": r(max(
            a["last_round_largest_change"] for a in moved)),
    }
    return out


def per_node_control(control: list[dict], grid: list[dict]) -> dict:
    """The block ``per_node_control``: its runs, its readings, and its identity
    with the asset grid at the construction's size. **Printed, not scored.**"""
    by_key = {(row["n"], row["fraction"], row["arm"], row["seed"]): row
              for row in grid}
    at_base = [row for row in control if row["n"] == CONSTRUCTION_N]
    same = sum(
        by_key.get((row["n"], row["fraction"], row["arm"], row["seed"])) == row
        for row in at_base)
    return {
        "units_per_node": PER_NODE_UNITS,
        "price_ladder_scale": f"{CONSTRUCTION_N} / n",
        "rows_at_construction_n_equal_to_the_asset_grid": [same, len(at_base)],
        "readings": asset_account_readings(control),
        "runs": control,
    }


def print_directions(direction: dict, indent: str = "  ") -> None:
    for f, per_key in direction.items():
        for key, t in per_key.items():
            print(f"{indent}fraction {f} {key}: fixed {t['fixed']['path']} "
                  f"({t['fixed']['seeds_rising']}/{t['fixed']['seeds']} seeds, "
                  f"{t['fixed']['pairs_rising']}/{t['fixed']['pairs']} pairs "
                  f"rise), scaled {t['scaled']['path']} "
                  f"({t['scaled']['seeds_rising']}/{t['scaled']['seeds']}, "
                  f"{t['scaled']['pairs_rising']}/{t['scaled']['pairs']}), "
                  f"{'REVERSED' if t['reversed'] else 'same direction'}")


def print_asset_accounts(block: dict, title: str) -> None:
    print(f"\n{title} (printed, not scored)")
    for account in ACCOUNTS:
        b = block[account]
        lo, hi, width = b["non_null_top1_span"]
        print(f"  {account}: top1% at the construction's cell "
              f"{b['construction_cell_top1']}, span {lo}-{hi} width {width}, "
              f"null gini {b['null_gini_by_size']}, lowest null run "
              f"{b['null_gini_lowest_run_by_size']}")
        print_directions(b["direction_by_fraction"], indent="    ")
    for base, per_key in block["net_worth_against_claims"].items():
        for key, c in per_key.items():
            print(f"  net worth above {base} on {key}: "
                  f"{c['cells_net_worth_above']}/{c['cells']} cells, "
                  f"{c['runs_net_worth_above']}/{c['runs']} runs")
    s = block["held_share_of_net_worth"]
    print(f"  held units at the closing price, share of net worth: "
          f"{s['lowest']}-{s['highest']} over {s['stratified_runs']} stratified "
          f"runs, median by size {s['median_by_size']}")
    for n, u in block["null_arm_units"].items():
        print(f"  null arm n={n}: claims per node "
              f"{u['claims_per_node_initial']} against a lowest gate of "
              f"{u['lowest_stretch_gate_initial']}; supply "
              f"{u['supply_by_tier_initial']}; units held "
              f"{u['units_initial']} at the opening and "
              f"{u['units_close_settled']} at the close; most on one node "
              f"{u['max_units_one_node_initial']} then "
              f"{u['max_units_one_node_close_settled']}; "
              f"{u['runs_asset_layer_inert']}/{u['runs']} runs inert")
    s = block["last_round_settlement"]
    print(f"  last round: claims moved after the recorded row in "
          f"{s['runs_cash_moved']}/{s['runs']} runs, largest single-node "
          f"change {s['largest_single_node_change']}")


def run_grid(rounds: int, seeds: int, asset: bool, per_node: bool = False,
             echo: bool = True) -> list[dict]:
    rows: list[dict] = []
    for n in SIZES:
        for f in FRACTIONS:
            for arm in ("fixed", "scaled", "null"):
                got = [one(n, f, arm, seed, rounds, asset, per_node)
                       for seed in range(seeds)]
                rows.extend(got)
                if echo:
                    print(f"{n:>6}{f:>7.2f}{arm:>8}{got[0]['layer1_size']:>5}"
                          f"{got[0]['l1_out_degree']:>5}"
                          f"{got[0]['l1_density']:>7.3f}"
                          f"{mean_of(got,'edges'):>8.0f}"
                          f"{mean_of(got,'top1_wealth'):>9.4f}"
                          f"{mean_of(got,'gini'):>8.4f}"
                          f"{mean_of(got,'support_ratio'):>10.4f}"
                          f"{mean_of(got,'mr_close'):>9.2f}", flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument(
        "--asset", action="store_true",
        help="put A3's asset layer on the carrier. Off is what this stage "
             "was registered on. Concentration read without it carries the "
             "employment channel and not the revaluation channel, and the "
             "empirical decomposition puts the weight on the second. With it "
             "on, top1_wealth and gini still read claims_recorded; settled "
             "claims and net worth are written under accounts, and the grid "
             "is run again as per_node_control.",
    )
    args = ap.parse_args()

    print(f"A14  rounds={args.rounds} seeds={args.seeds} "
          f"sizes={list(SIZES)} fractions={list(FRACTIONS)}\n")
    hdr = (f"{'n':>6}{'frac':>7}{'arm':>8}{'L1':>5}{'deg':>5}{'dens':>7}"
           f"{'edges':>8}{'top1%':>9}{'gini':>8}{'sup ratio':>10}{'M/R':>9}")
    print(hdr)
    print("-" * len(hdr))

    rows = run_grid(args.rounds, args.seeds, args.asset)

    criteria = evaluate(rows, args.rounds, args.seeds)
    directions = direction_by_fraction(rows)
    print("\nthe two degree arms at every core share, claims_recorded "
          "(printed, not scored)")
    print_directions(directions)
    accounts_block = asset_account_readings(rows) if args.asset else None
    control_block = None
    if accounts_block is not None:
        print_asset_accounts(accounts_block, "accounts on the asset grid")
        print("\nper_node_control: the same grid with the asset layer held "
              "per node")
        print(hdr)
        print("-" * len(hdr))
        control = run_grid(args.rounds, args.seeds, asset=True, per_node=True)
        control_block = per_node_control(control, rows)
        print_asset_accounts(control_block["readings"],
                             "accounts on per_node_control")
        same, total = control_block[
            "rows_at_construction_n_equal_to_the_asset_grid"]
        print(f"  rows at n={CONSTRUCTION_N} equal to the asset grid's: "
              f"{same}/{total}")
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a14_scale.json" if not args.asset else "a14_scale_asset.json"
    )
    plain_definitions = ("top1_wealth, top01_wealth, gini",
                         "direction_by_fraction")
    path.write_text(
        json.dumps(
            {
                "stage": "A14",
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "sizes": list(SIZES),
                "fractions": list(FRACTIONS),
                "density_l1": r(DENSITY_L1),
                "density_l2": r(DENSITY_L2),
                "density_up": r(DENSITY_UP),
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this "
                        "station's registered carrier; the registered "
                        "reading is results/a14_scale.json"
                    ),
                    "asset_accounts": accounts_block,
                    "per_node_control": control_block,
                    } if args.asset else {}),
                "definitions": (
                    DEFINITIONS if args.asset else
                    {k: DEFINITIONS[k] for k in plain_definitions}),
                "direction_by_fraction": directions,
                "runs": rows,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed),
                     "detail": c.detail, "void": bool(c.void)}
                    for c in criteria
                ],
            },
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
