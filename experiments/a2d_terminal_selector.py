"""A2d: what selects the terminal distribution on the A2 network.

Volume One section 1 says spending inside a layer is functionally equivalent to
saving. A0-4 already read that on the four-stratum block carrier: Layer 2 inflow
was flat to ``0.000e+00`` across a top-stratum propensity sweep from 0.05 to
1.00, while A0-5 read the same sweep moving Layer 1 churn by a factor of 15.
This stage asks the same question on the network carrier, with the whole sigma
vector rather than the top stratum's propensity, and with the terminal
distribution rather than a flow level as the readout.

It then asks what does select it. Two candidates are already in the
construction and neither is a new parameter: whether the monetary authority
issues at all, and where issuance enters. A0-9 read ``issuance accumulates in
the layer it was issued to``, which attributes the concentration to the entry
point. On this carrier that attribution is testable, because
``injection_target`` has a uniform branch that spreads issuance over every node.

Three grids, one readout each, spans compared against each other rather than
against any constant:

  sigma grid       structure and issuance frozen, sigma swept
  structure grid   sigma and issuance frozen, one structural knob moved at a time
  issuance grid    sigma and structure frozen, rule and entry point moved

Usage::

    python experiments/a2d_terminal_selector.py
    python experiments/a2d_terminal_selector.py --rounds 300 --seeds 5

Writes ``results/a2d_terminal_selector.json``. Exits non-zero if any criterion
fails.

**Which account a terminal share is read on.** The six fields every row
carries, and the four criteria, read the last row of the run's history: claims
per node, written after the round's flows and before that round's asset step.
On the plain carrier that row is the state the run ends in, and claims are all
a node holds. With ``--asset`` neither is so, and the record carries the same
readings under ``accounts`` on the three accounts the docstring of
``monetary_topology.asset.carrier_model`` defines: ``claims_recorded`` (that
row), ``claims_settled`` and ``net_worth``. Nothing registered moves: the
criteria score ``claims_recorded`` on both carriers.

``--asset`` also reads the issuance grid on twenty seeds
(``issuance_by_seed``). At five seeds the sign of the matched-volume entry pair
splits on every account, and on net worth its standard deviation across seeds
is as large as its mean, so five seeds place neither its sign nor, there, its
size. Its size on the recorded row is placed at five: below the on-off gap in
every seed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.asset import carrier_model
from monetary_topology.config import MonetaryAuthority, SpendRule
from monetary_topology.mechanisms import gini
from monetary_topology.network import Network, NetworkConfig, NetworkSpec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

DIGITS = 6

#: Financial-layer retention. The span brackets the construction's own 0.50 and
#: the value Kuznets (1953) tables 47-48 read for the top five percent in 1929,
#: which is 0.38. Neither endpoint carries a verdict; the grid is spacing.
RET_L1 = (0.20, 0.30, 0.38, 0.50, 0.65, 0.80)
#: Production-layer retention. Zero is the boundary the model reaches toward
#: the dissaving the same tables read at low income multiples; it cannot go
#: below, because ``SpendRule`` caps propensity at one.
RET_L2 = (0.00, 0.0625, 0.15, 0.30)

#: One structural knob moved at a time, everything else at its default. These
#: are the knobs the manuscript does not pin. ``layer1_size`` is paired with
#: ``layer2_size`` so the node count stays at 200 and the top-one-percent set
#: stays two nodes across the whole grid.
STRUCTURE = (
    ("layer1_size", (10, 15, 20, 30, 40)),
    ("layer1_out_degree", (3, 4, 6, 8, 10)),
    ("layer2_out_degree", (2, 3, 4, 6)),
    ("upward_out_degree", (1, 2, 3, 4)),
    ("layer1_initial_share", (0.50, 0.60, 0.679, 0.75, 0.90)),
)

ISSUANCE = (
    ("endogenous", "top_node"),
    ("endogenous", "uniform"),
    ("fixed", "top_node"),
    ("fixed", "uniform"),
    ("none", "top_node"),
    ("none", "uniform"),
)

#: The six fields every row has carried since the stage was registered. They
#: are read on ``claims_recorded`` and nothing added later may move them.
LEGACY = ("top1_wealth", "top10_wealth", "gini", "support", "issued", "claims_close")

#: What a terminal share can be read on. One account on the plain carrier,
#: three once an asset layer is on it.
DEFINITIONS = {
    "claims_recorded": (
        "claims per node in the last row of the run's history. The row is "
        "written after the round's flows and before that round's asset step, and "
        "held units are not in it, so on a carrier with an asset layer it is not "
        "the state the run ends in. Every top-level field of this record, and its "
        "criteria, are read on this account."
    ),
    "claims_settled": (
        "claims per node after the last round's asset step: rent, stretch-debt "
        "service, resale settlement. The claims the run ends with. Present only "
        "when the carrier has an asset layer; on the plain carrier the recorded "
        "row is already the end state, and the record counts the runs in which "
        "it is."
    ),
    "net_worth": (
        "claims_settled plus held units at each tier's closing price. The "
        "account revaluation is on. Present only with an asset layer."
    ),
}

#: Appended to the details of A2d-2, A2d-3 and A2d-4 when the carrier has an
#: asset layer, where the share the criteria read is not the end state and
#: does not count held units. The names keep the registered wording, which on
#: the plain carrier is exact: there claims are all a node holds.
ASSET_ACCOUNT_NOTE = (
    "On this carrier the share is read on claims_recorded: claims in the last "
    "history row, written before that round's asset step, with held units left "
    "out. Settled claims and net worth are read under accounts."
)

#: Seeds for the issuance grid when it is read seed by seed on the asset
#: carrier. Not a round number chosen for comfort: at five seeds the sign of
#: the matched-volume entry pair splits on every account, and on net worth its
#: standard deviation across seeds is 0.047 against a mean of 0.041, so its
#: standard error at five is 0.021 and neither its sign nor its size is placed
#: there. Twenty brings that to about 0.012. On the recorded row its size is
#: placed at five, below the on-off gap in every seed. The plain carrier does
#: not get this arm: there the same pair has a standard deviation of 0.001 and
#: all five seeds agree in sign.
ISSUANCE_SEEDS = 20


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


def spend_from_retention(ret_l1: float, ret_l2: float) -> SpendRule:
    """Retention is ``1 - propensity`` and the network takes the per-layer mean,
    so the two production entries and the two financial entries each carry one
    value. Setting low equal to high removes the draw, which is what makes the
    grid a sweep of one number per layer rather than of a distribution."""
    p1, p2 = 1.0 - ret_l1, 1.0 - ret_l2
    return SpendRule(low=(p2, p2, p1, p1), high=(p2, p2, p1, p1))


def closes(model, h) -> dict[str, np.ndarray]:
    """The vectors a terminal share can be read on, keyed by account.

    The three accounts are the ones ``carrier_model``'s docstring defines.
    ``h.holdings[-1]`` is written inside the round, before ``_post_round``.
    On a plain ``Network`` that hook does nothing and the row is the end
    state. On an asset carrier the hook collects rent, services stretch debt,
    settles resales and reprices, and then appends to ``claims_history`` and
    ``net_worth_history``; those two are read here, and only when present.
    """
    out = {"claims_recorded": np.asarray(h.holdings[-1], dtype=float)}
    settled = getattr(model, "claims_history", None)
    if settled:
        out["claims_settled"] = np.asarray(settled[-1], dtype=float)
        out["net_worth"] = np.asarray(model.net_worth_history[-1], dtype=float)
    return out


def one(
    ret_l1: float,
    ret_l2: float,
    rule: str,
    target: str,
    seed: int,
    rounds: int,
    spec_kw: dict | None = None,
    cfg_kw: dict | None = None,
    asset: bool = False,
) -> dict:
    spec_kw = dict(spec_kw or {})
    cfg_kw = dict(cfg_kw or {})
    cfg = NetworkConfig(
        spec=NetworkSpec(seed=seed, **spec_kw),
        seed=seed,
        rounds=rounds,
        spend=spend_from_retention(ret_l1, ret_l2),
        authority=MonetaryAuthority(rule=rule),
        injection_target=target,
        **cfg_kw,
    )
    # The model is kept, not only its history: the history's last row is
    # written before the round's asset step, and the settled claims and net
    # worth live on the model.
    model = carrier_model(cfg, asset=asset)
    h = model.run()
    n = h.node_count
    by_account = closes(model, h)
    close = by_account["claims_recorded"]
    row = {
        "top1_wealth": r(top_share(close, max(1, n // 100))),
        "top10_wealth": r(top_share(close, n // 10)),
        "gini": r(gini(close)),
        "support": r(float(h.effective_support[-1])),
        "issued": r(float(h.issuance.sum())),
        "claims_close": r(float(close.sum())),
    }
    # Underscored keys never reach the record as they are: ``mean_over_seeds``
    # builds a row from ``LEGACY`` and folds these into ``accounts``.
    row["_accounts"] = {
        name: {
            "top1": r(top_share(v, max(1, n // 100))),
            "top10": r(top_share(v, n // 10)),
            "gini": r(gini(v)),
            "total": r(float(v.sum())),
        }
        for name, v in by_account.items()
    }
    row["_recorded_row_is_end_state"] = bool(
        np.array_equal(np.asarray(model.holdings, dtype=float), close)
    )
    return row


def mean_over_seeds(seeds: int, **kw) -> dict:
    rows = [one(seed=s, **kw) for s in range(seeds)]
    out = {k: r(float(np.mean([row[k] for row in rows]))) for k in LEGACY}
    out["accounts"] = {}
    for name in rows[0]["_accounts"]:
        block = {
            q: r(float(np.mean([row["_accounts"][name][q] for row in rows])))
            for q in ("top1", "top10", "gini", "total")
        }
        block["top1_per_seed"] = [row["_accounts"][name]["top1"] for row in rows]
        out["accounts"][name] = block
    out["recorded_row_is_end_state_runs"] = [
        int(sum(row["_recorded_row_is_end_state"] for row in rows)), len(rows)
    ]
    return out


def span(values) -> tuple[float, float, float]:
    v = np.asarray(values, dtype=float)
    return r(float(v.min())), r(float(v.max())), r(float(v.max() - v.min()))


def _se(d: np.ndarray) -> float | None:
    return r(float(d.std(ddof=1) / np.sqrt(len(d)))) if len(d) > 1 else None


def seed_by_seed_state(gap_seed) -> str:
    """The on-off gap read seed by seed: three names, one per state.

    The state on the mean says where the gap of the means falls. This one says
    whether the seeds agree on it. A gap that is positive in some seeds and not
    in others is neither separated nor overlapping; it is not placed at that
    number of seeds, and gets a name of its own.
    """
    g = np.asarray(gap_seed, dtype=float)
    n, k = len(g), int((g > 0).sum())
    if k == n:
        return "every seed separated"
    if k == 0:
        return "no seed separated"
    return f"not placed at {n} seeds: positive in {k}"


def account_reading(sigma_rows, structure_rows, issuance_rows, account: str) -> dict:
    """The stage's three readings on one account, with the seeds kept apart.

    The grid-level numbers are computed exactly as ``evaluate`` computes them,
    on that account's ``top1``. Beside each sits what a mean over seeds hides:
    in how many seeds the reading holds, and the paired differences seed by
    seed. A pair whose signs split across seeds is not a small number, it is
    an unplaced one, and the two print the same once averaged.
    """
    top1 = lambda row: row["accounts"][account]["top1"]
    seeds = lambda row: np.asarray(row["accounts"][account]["top1_per_seed"], dtype=float)
    s_lo, s_hi, s_w = span([top1(row) for row in sigma_rows])
    t_lo, t_hi, t_w = span([top1(row) for row in structure_rows])
    s_seed = np.array([seeds(row) for row in sigma_rows])
    t_seed = np.array([seeds(row) for row in structure_rows])
    s_w_seed = s_seed.max(axis=0) - s_seed.min(axis=0)
    t_w_seed = t_seed.max(axis=0) - t_seed.min(axis=0)

    mean = {(row["rule"], row["target"]): top1(row) for row in issuance_rows}
    by_seed = {(row["rule"], row["target"]): seeds(row) for row in issuance_rows}
    on = [v for k, v in mean.items() if k[0] != "none"]
    off = [v for k, v in mean.items() if k[0] == "none"]
    gap = r(min(on) - max(off))
    if gap <= 0:
        state = "overlap: issuance does not separate"
    elif gap > s_w:
        state = "separated by more than sigma's whole span"
    else:
        state = "separated, but by less than sigma's span"
    on_seed = np.array([v for k, v in by_seed.items() if k[0] != "none"])
    off_seed = np.array([v for k, v in by_seed.items() if k[0] == "none"])
    gap_seed = on_seed.min(axis=0) - off_seed.max(axis=0)

    pairs = {}
    for rule in ("endogenous", "fixed", "none"):
        d = by_seed[(rule, "top_node")] - by_seed[(rule, "uniform")]
        pairs[rule] = {
            "top_node": mean[(rule, "top_node")],
            "uniform": mean[(rule, "uniform")],
            "abs_diff_of_means": r(abs(mean[(rule, "top_node")] - mean[(rule, "uniform")])),
            "top_node_minus_uniform_per_seed": [r(x) for x in d],
            "seeds_positive": int((d > 0).sum()),
            "seeds_negative": int((d < 0).sum()),
            "se_across_seeds": _se(d),
            # The fourth criterion's reading, seed by seed: the pair's size
            # against that seed's own on-off gap.
            "seeds_below_the_on_off_gap": int((np.abs(d) < gap_seed).sum()),
        }

    # The retention direction, one number per financial-layer retention: the
    # mean over the production-layer columns. Top row minus bottom row is
    # what raising financial retention across the grid does to the share.
    lo_r, hi_r = min(RET_L1), max(RET_L1)
    row_mean = {
        str(r1): r(float(np.mean([top1(row) for row in sigma_rows if row["ret_l1"] == r1])))
        for r1 in RET_L1
    }
    lift = (np.mean([seeds(row) for row in sigma_rows if row["ret_l1"] == hi_r], axis=0)
            - np.mean([seeds(row) for row in sigma_rows if row["ret_l1"] == lo_r], axis=0))
    return {
        "sigma": {"min": s_lo, "max": s_hi, "width": s_w},
        "structure": {"min": t_lo, "max": t_hi, "width": t_w},
        "structural_over_sigma_width": r(t_w / s_w) if s_w > 0 else None,
        "seeds_with_structural_span_larger": int((t_w_seed > s_w_seed).sum()),
        "sigma_width_per_seed": [r(x) for x in s_w_seed],
        "structure_width_per_seed": [r(x) for x in t_w_seed],
        "top1_by_financial_retention": row_mean,
        "highest_minus_lowest_financial_retention_per_seed": [r(x) for x in lift],
        "seeds_with_retention_lifting_top1": int((lift > 0).sum()),
        "on": [r(min(on)), r(max(on))],
        "off": [r(min(off)), r(max(off))],
        "on_off_gap": gap,
        "state_on_the_mean": state,
        "state_seed_by_seed": seed_by_seed_state(gap_seed),
        "on_off_gap_per_seed": [r(x) for x in gap_seed],
        "seeds_with_gap_positive": int((gap_seed > 0).sum()),
        "seeds_with_gap_above_sigma_width": int((gap_seed > s_w_seed).sum()),
        "entry_pairs": pairs,
    }


def net_worth_against_claims(rows) -> dict:
    """Levels, not spans: the top share of net worth against the top share of
    settled claims, on the same runs, cell by cell and run by run.

    Every number is taken from the rows' own ``accounts``. ``held_units_share``
    is the part of net worth that is held units at the closing price, from the
    cell means of the two totals.
    """
    nw = [row["accounts"]["net_worth"] for row in rows]
    cs = [row["accounts"]["claims_settled"] for row in rows]
    ratio = np.array([a["top1"] / b["top1"] for a, b in zip(nw, cs)])
    held = np.array([1.0 - b["total"] / a["total"] for a, b in zip(nw, cs)])
    runs = [(x, y) for a, b in zip(nw, cs)
            for x, y in zip(a["top1_per_seed"], b["top1_per_seed"])]
    return {
        "cells": len(rows),
        "cells_with_net_worth_top1_above": int(sum(a["top1"] > b["top1"] for a, b in zip(nw, cs))),
        "runs": len(runs),
        "runs_with_net_worth_top1_above": int(sum(x > y for x, y in runs)),
        "top1_ratio_net_worth_over_claims_settled": {
            "min": r(float(ratio.min())),
            "median": r(float(np.median(ratio))),
            "max": r(float(ratio.max())),
        },
        "held_units_share": {"min": r(float(held.min())), "max": r(float(held.max()))},
    }


def read_issuance_arm(cells, grid_rows=None) -> dict:
    """What the seed-by-seed issuance arm reads, from its cells alone.

    ``cells`` are the six issuance cells, each with ``top1_per_seed`` keyed by
    account and in seed order. Every number here is a function of those lists,
    so a reader can recompute it from the record.
    """
    names = list(cells[0]["top1_per_seed"])
    readings = {}
    for a in names:
        v = {(c["rule"], c["target"]): np.array(c["top1_per_seed"][a], dtype=float) for c in cells}
        off = v[("none", "top_node")]
        issuing = [k for k in v if k[0] != "none"]
        gap_seed = np.array([v[k] for k in issuing]).min(axis=0) - np.maximum(
            v[("none", "top_node")], v[("none", "uniform")])
        pairs = {}
        for rule in ("endogenous", "fixed", "none"):
            d = v[(rule, "top_node")] - v[(rule, "uniform")]
            pairs[rule] = {
                "mean": r(float(d.mean())),
                "median": r(float(np.median(d))),
                "se_across_seeds": _se(d),
                "seeds_positive": int((d > 0).sum()),
                "seeds_negative": int((d < 0).sum()),
                "seeds_below_the_on_off_gap": int((np.abs(d) < gap_seed).sum()),
                "per_seed": [r(x) for x in d],
            }
        readings[a] = {
            "none": r(float(off.mean())),
            "minus_none": {
                f"{k[0]}/{k[1]}": {
                    "mean": r(float((v[k] - off).mean())),
                    "median": r(float(np.median(v[k] - off))),
                    "se_across_seeds": _se(v[k] - off),
                    "seeds_positive": int(((v[k] - off) > 0).sum()),
                    "seeds_negative": int(((v[k] - off) < 0).sum()),
                }
                for k in issuing
            },
            "on_off_gap_of_means": r(
                min(float(v[k].mean()) for k in issuing) - float(off.mean())),
            "seeds_with_gap_positive": int((gap_seed > 0).sum()),
            "top_node_minus_uniform": pairs,
        }
    out = {"readings": readings}
    if "claims_recorded" in names and "claims_settled" in names:
        # What the last asset step does to each issuing cell's distance from
        # no issuance: settled minus recorded, seed by seed.
        step = {}
        for c in cells:
            if c["rule"] == "none":
                continue
            none = next(x for x in cells if (x["rule"], x["target"]) == ("none", "top_node"))
            before = (np.array(c["top1_per_seed"]["claims_recorded"], dtype=float)
                      - np.array(none["top1_per_seed"]["claims_recorded"], dtype=float))
            after = (np.array(c["top1_per_seed"]["claims_settled"], dtype=float)
                     - np.array(none["top1_per_seed"]["claims_settled"], dtype=float))
            d = after - before
            step[f"{c['rule']}/{c['target']}"] = {
                "mean": r(float(d.mean())),
                "se_across_seeds": _se(d),
                "seeds_positive": int((d > 0).sum()),
                "seeds_negative": int((d < 0).sum()),
            }
        out["last_asset_step"] = step
    same = None
    if grid_rows is not None:
        checks = [
            cell["top1_per_seed"][a][: len(row["accounts"][a]["top1_per_seed"])]
            == row["accounts"][a]["top1_per_seed"]
            for cell in cells
            for row in grid_rows
            if (row["rule"], row["target"]) == (cell["rule"], cell["target"])
            for a in names
        ]
        # Only a comparison that reached every cell on every account says yes.
        if len(checks) == len(cells) * len(names):
            same = all(checks)
    out["first_seeds_equal_the_grid"] = same
    return out


def issuance_by_seed(rounds: int, seeds: int, asset: bool, grid_rows=None) -> dict:
    """The issuance grid alone, on ``seeds`` seeds, every account kept by seed.

    Printed and not scored. Its first seeds are the same runs the grid made,
    and ``first_seeds_equal_the_grid`` says whether they came out the same.
    """
    runs = {
        (rule, target): [
            one(0.50, 0.0625, rule, target, s, rounds, asset=asset) for s in range(seeds)
        ]
        for rule, target in ISSUANCE
    }
    names = list(runs[ISSUANCE[0]][0]["_accounts"])
    cells = []
    for (rule, target), rows in runs.items():
        cells.append({
            "rule": rule,
            "target": target,
            "issued": r(float(np.mean([row["issued"] for row in rows]))),
            "top1_per_seed": {a: [row["_accounts"][a]["top1"] for row in rows] for a in names},
        })
    return {
        "seeds": seeds,
        "scored": False,
        "cells": cells,
        **read_issuance_arm(cells, grid_rows),
    }


def evaluate(sigma_rows, structure_rows, issuance_rows, account_note=None) -> list[Criterion]:
    """The four criteria. ``account_note``, when given, is appended to the
    three that read a share, so a record names the account its numbers are on
    where the criteria's names alone would not."""
    out: list[Criterion] = []
    tail = f" {account_note}" if account_note else ""

    # 1. structural, about the code rather than about the world.
    n_expected = len(RET_L1) * len(RET_L2)
    n_struct = sum(len(vals) for _, vals in STRUCTURE)
    ok = (
        len(sigma_rows) == n_expected
        and len(structure_rows) == n_struct
        and len(issuance_rows) == len(ISSUANCE)
        and all(np.isfinite(row["top1_wealth"]) for row in sigma_rows)
        and all(np.isfinite(row["top1_wealth"]) for row in structure_rows)
        and all(np.isfinite(row["top1_wealth"]) for row in issuance_rows)
    )
    out.append(
        Criterion(
            "A2d-1  every cell of all three grids ran and returned a finite share",
            ok,
            f"sigma {len(sigma_rows)}/{n_expected}, structure "
            f"{len(structure_rows)}/{n_struct}, issuance "
            f"{len(issuance_rows)}/{len(ISSUANCE)}. The stock-flow identity is "
            f"asserted inside the loop, so reaching here is also the claim that "
            f"it held in every round of every cell.",
        )
    )

    # 2. the two spans, printed side by side. Reading declared before the run:
    #    whichever span is larger names the thing that moves the terminal
    #    distribution more. No line is drawn on either.
    s_lo, s_hi, s_w = span([row["top1_wealth"] for row in sigma_rows])
    t_lo, t_hi, t_w = span([row["top1_wealth"] for row in structure_rows])
    ratio = r(t_w / s_w) if s_w > 0 else float("inf")
    out.append(
        Criterion(
            "A2d-2  sigma's span on terminal top1% wealth against the structural span",
            True,
            f"sigma grid {s_lo}-{s_hi}, width {s_w}. structure grid {t_lo}-{t_hi}, "
            f"width {t_w}. structural width is {ratio}x the sigma width. "
            f"Read: the larger span names the knob that selects the terminal "
            f"distribution. This criterion prints both and does not draw a line."
            f"{tail}",
        )
    )

    # 3. issuance on against issuance off. Three states, all reachable.
    on = [row["top1_wealth"] for row in issuance_rows if row["rule"] != "none"]
    off = [row["top1_wealth"] for row in issuance_rows if row["rule"] == "none"]
    gap = r(min(on) - max(off))
    if gap <= 0:
        state = "overlap: issuance does not separate"
    elif gap > s_w:
        state = "separated by more than sigma's whole span"
    else:
        state = "separated, but by less than sigma's span"
    out.append(
        Criterion(
            "A2d-3  issuance on against issuance off",
            gap > 0,
            f"on {r(min(on))}-{r(max(on))}, off {r(min(off))}-{r(max(off))}, "
            f"gap {gap} against sigma's span {s_w}. State: {state}.{tail}",
        )
    )

    # 4. the entry point, at matched rule and matched sigma.
    pairs = []
    for rule in ("endogenous", "fixed", "none"):
        a = [row for row in issuance_rows if row["rule"] == rule and row["target"] == "top_node"]
        b = [row for row in issuance_rows if row["rule"] == rule and row["target"] == "uniform"]
        if a and b:
            pairs.append((rule, a[0]["top1_wealth"], b[0]["top1_wealth"],
                          r(abs(a[0]["top1_wealth"] - b[0]["top1_wealth"])),
                          a[0]["issued"], b[0]["issued"]))
    worst = max(p[3] for p in pairs)
    detail = "; ".join(
        f"{rule}: top_node {x} vs uniform {y}, |diff| {d}, issued {ia} vs {ib}"
        for rule, x, y, d, ia, ib in pairs
    )
    out.append(
        Criterion(
            "A2d-4  the entry point, at matched rule and matched sigma",
            True,
            f"{detail}. Largest |diff| {worst} against the on-off gap {gap}. "
            f"Read: an entry-point effect smaller than the on-off gap says the "
            f"concentration is not attributable to where issuance lands. "
            f"This criterion prints the pairs and does not draw a line.{tail}",
        )
    )
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
             "empirical decomposition puts the weight on the second. With it "
             "on, the registered fields still read claims at the last history "
             "row; settled claims and net worth are written beside them under "
             "accounts, and the issuance grid is read on twenty seeds.",
    )
    args = ap.parse_args()

    # ``asset`` rides in ``base`` so it reaches ``one`` through the same
    # kwargs every other setting uses, and the three grids cannot end up
    # on different carriers.
    base = dict(rounds=args.rounds, seeds=args.seeds, asset=args.asset)
    print(f"A2d  rounds={args.rounds} seeds={args.seeds}\n")

    print("sigma grid, structure and issuance frozen")
    print(f"{'ret_L1':>8}{'ret_L2':>8}{'top1%':>10}{'gini':>9}{'support':>9}{'issued':>10}")
    sigma_rows = []
    for r1 in RET_L1:
        for r2 in RET_L2:
            m = mean_over_seeds(ret_l1=r1, ret_l2=r2, rule="endogenous",
                                target="top_node", **base)
            m |= {"ret_l1": r1, "ret_l2": r2}
            sigma_rows.append(m)
            print(f"{r1:>8.4f}{r2:>8.4f}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
                  f"{m['support']:>9.3f}{m['issued']:>10.1f}")

    print("\nstructure grid, sigma and issuance frozen at their defaults")
    print(f"{'knob':>22}{'value':>10}{'top1%':>10}{'gini':>9}{'support':>9}")
    structure_rows = []
    for knob, values in STRUCTURE:
        for v in values:
            spec_kw, cfg_kw = {}, {}
            if knob == "layer1_size":
                spec_kw = {"layer1_size": v, "layer2_size": 200 - v}
            elif knob == "layer1_initial_share":
                cfg_kw = {"layer1_initial_share": v}
            else:
                spec_kw = {knob: v}
            m = mean_over_seeds(ret_l1=0.50, ret_l2=0.0625, rule="endogenous",
                                target="top_node", spec_kw=spec_kw,
                                cfg_kw=cfg_kw, **base)
            m |= {"knob": knob, "value": v}
            structure_rows.append(m)
            print(f"{knob:>22}{v:>10}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
                  f"{m['support']:>9.3f}")

    print("\nissuance grid, sigma and structure frozen at their defaults")
    print(f"{'rule':>12}{'target':>10}{'top1%':>10}{'gini':>9}{'support':>9}"
          f"{'issued':>10}{'claims':>10}")
    issuance_rows = []
    for rule, target in ISSUANCE:
        m = mean_over_seeds(ret_l1=0.50, ret_l2=0.0625, rule=rule,
                            target=target, **base)
        m |= {"rule": rule, "target": target}
        issuance_rows.append(m)
        print(f"{rule:>12}{target:>10}{m['top1_wealth']:>10.4f}{m['gini']:>9.4f}"
              f"{m['support']:>9.3f}{m['issued']:>10.1f}{m['claims_close']:>10.1f}")

    criteria = evaluate(sigma_rows, structure_rows, issuance_rows,
                        account_note=ASSET_ACCOUNT_NOTE if args.asset else None)
    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, "
          f"{len(criteria) - len(live)} void")

    names = list(sigma_rows[0]["accounts"])
    all_rows = sigma_rows + structure_rows + issuance_rows
    accounts_block = {
        "definitions": {a: DEFINITIONS[a] for a in names},
        "registered_fields_read": "claims_recorded",
        "recorded_row_is_end_state_runs": [
            sum(row["recorded_row_is_end_state_runs"][0] for row in all_rows),
            sum(row["recorded_row_is_end_state_runs"][1] for row in all_rows),
        ],
        "readings": {
            a: account_reading(sigma_rows, structure_rows, issuance_rows, a) for a in names
        },
    }
    if "net_worth" in names and "claims_settled" in names:
        accounts_block["net_worth_against_claims"] = net_worth_against_claims(all_rows)
    done, total = accounts_block["recorded_row_is_end_state_runs"]
    print(f"\naccounts, printed and not scored. The last history row is the "
          f"end state in {done}/{total} runs.")
    for a in names:
        x = accounts_block["readings"][a]
        print(f"  {a}: sigma width {x['sigma']['width']}, structure width "
              f"{x['structure']['width']}, ratio {x['structural_over_sigma_width']}, "
              f"structure larger in {x['seeds_with_structural_span_larger']}/"
              f"{args.seeds} seeds; on-off gap {x['on_off_gap']} "
              f"({x['state_on_the_mean']}; {x['state_seed_by_seed']}); fixed entry pair "
              f"+{x['entry_pairs']['fixed']['seeds_positive']}/"
              f"-{x['entry_pairs']['fixed']['seeds_negative']}, below the gap in "
              f"{x['entry_pairs']['fixed']['seeds_below_the_on_off_gap']}/{args.seeds}")
    if "net_worth_against_claims" in accounts_block:
        x = accounts_block["net_worth_against_claims"]
        q = x["top1_ratio_net_worth_over_claims_settled"]
        print(f"  net worth top1 above settled claims top1 in "
              f"{x['cells_with_net_worth_top1_above']}/{x['cells']} cells and "
              f"{x['runs_with_net_worth_top1_above']}/{x['runs']} runs; ratio "
              f"{q['min']} to {q['max']}, median {q['median']}; held units "
              f"{x['held_units_share']['min']} to {x['held_units_share']['max']} "
              f"of net worth")

    by_seed = None
    if args.asset:
        by_seed = issuance_by_seed(args.rounds, ISSUANCE_SEEDS, True, issuance_rows)
        print(f"\nissuance grid on {ISSUANCE_SEEDS} seeds, printed and not scored. "
              f"First seeds equal the grid: {by_seed['first_seeds_equal_the_grid']}")
        for a in names:
            x = by_seed["readings"][a]
            f = x["top_node_minus_uniform"]["fixed"]
            print(f"  {a}: none {x['none']}; " + "; ".join(
                f"{k} {v['mean']:+.6f} (se {v['se_across_seeds']}, median "
                f"{v['median']:+.6f}, +{v['seeds_positive']}/-{v['seeds_negative']})"
                for k, v in x["minus_none"].items()))
            print(f"      gap of means {x['on_off_gap_of_means']}, positive in "
                  f"{x['seeds_with_gap_positive']}/{ISSUANCE_SEEDS} seeds")
            print(f"      fixed, top_node minus uniform {f['mean']:+.6f} "
                  f"(se {f['se_across_seeds']}, median {f['median']:+.6f}, "
                  f"+{f['seeds_positive']}/-{f['seeds_negative']}, below the gap in "
                  f"{f['seeds_below_the_on_off_gap']})")
        for k, v in by_seed.get("last_asset_step", {}).items():
            print(f"  last asset step, {k} minus none: {v['mean']:+.6f} "
                  f"(se {v['se_across_seeds']}, +{v['seeds_positive']}/-{v['seeds_negative']})")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / (
        "a2d_terminal_selector.json" if not args.asset
        else "a2d_terminal_selector_asset.json"
    )
    path.write_text(
        json.dumps(
            {
                "stage": "A2d",
                **({"diagnostic_only": True,
                    "diagnostic_reason": (
                        "read on A3's asset layer, which is not this station's "
                        "registered carrier; the registered reading is "
                        "results/a2d_terminal_selector.json"
                    )} if args.asset else {}),
                "rounds": args.rounds,
                "seeds_tested": args.seeds,
                "retention_l1": list(RET_L1),
                "retention_l2": list(RET_L2),
                "sigma_grid": sigma_rows,
                "structure_grid": structure_rows,
                "issuance_grid": issuance_rows,
                "accounts": accounts_block,
                **({"issuance_by_seed": by_seed} if by_seed is not None else {}),
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
