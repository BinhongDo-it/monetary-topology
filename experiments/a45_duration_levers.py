"""A45: how long new claims stay ahead where they enter, and which parts set where they end up.

Ruled 2026-09-16. A44 read the end-of-run split of new claims on A17's carrier
off one round's linear map: the split is the map's stationary vector, and the
class the claims enter keeps a fixed amount more, so its advantage in share
falls as 1/T. This station reads what sets that amount and how long it lasts,
and the derivative of the split with respect to each part of the map.

Three objects, all built from A44's mean field without changing A44's code:

    the rebuilt map      the mean field assembled in this file from A44's own
                         parts (routes, spending bands, payroll sets, the
                         payers' short shares, the bill slope), so that one
                         part can be moved at a time
    the derivative       dpi = Z (dB/dtheta) pi, with Z the fundamental matrix
                         of the map on its block of trading nodes and spending
                         state, P = pi ell' its stationary projector
    the class chain      the map aggregated into its classes, each class's
                         nodes weighted by their stationary mass

Eleven levers: the spending propensity of the financial layer, of the
intermediate block and of the households (the wage earners and the nodes with
no in-edges share one band); the wage elasticity; the pass-on strength of
payers short of their share of the bill; and the weight of six kinds of edge,
financial to financial, financial to intermediate, intermediate to
intermediate, intermediate to financial, households to intermediate and
households to financial, rescaled per source node.

Readings, printed and recorded without verdicts: M1 the entry term three ways
(full map, class chain, node reading) beside the chain's second eigenvalue, on
the default carriers, three sweeps and an out-rate grid, and against the whole
model on four carriers at three horizons; M2 each class's elasticity to each
lever, and the first-order prediction of eight of A44's variants split into its
steps; M3 the class chains and the earners' closed form.

Steps:

    python experiments/a45_duration_levers.py --gate            # A45-0
    python experiments/a45_duration_levers.py --selftest        # seeded faults
    python experiments/a45_duration_levers.py --check --smoke   # A45-1, A45-2, A45-3 on seed 0
    python experiments/a45_duration_levers.py --check           # the same on five seeds
    python experiments/a45_duration_levers.py --run --smoke     # criteria and readings on seed 0
    python experiments/a45_duration_levers.py --run             # all of it, writes the record

Only ``--run`` without ``--smoke`` or ``--no-write`` writes, to
results/a45_duration_levers.json. The criteria are written in this file.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

#: A44's carrier, classes, control paths, variants and mean field, imported
#: rather than restated. A44's matrix is the reference A45-0 compares against.
from a44_occupation_operator import (  # noqa: E402
    ALL_CLASSES,
    ELASTICITY,
    F2I,
    HOME_CLASSES,
    OPEN_FROM,
    RESULTS,
    ROUNDS,
    SEEDS,
    VARIANTS,
    WALLS,
    MeanField,
    PathRecord,
    apply_variant,
    base_config,
    deviation_constants,
    field_shares,
    home_bias,
    record_path,
    resolved_changes,
    run_shares,
)
from a44_occupation_operator import RECORD as A44_RECORD  # noqa: E402

#: The central difference for both sides of A45-1. Small enough that the
#: difference's truncation is below the tolerance, large enough that the
#: re-solved stationary vectors differ well above their rounding (measured
#: before this file: a largest disagreement of 7.9e-9 at this step).
LEVER_STEP = 1e-6

TOL_DERIVATIVE = 1e-6
TOL_CHAIN = 1e-12

#: A stationary entry whose magnitude is below this is rounding, and reads as
#: zero wherever a class's mass is summed or used as a weight. The floor is
#: taken node by node: a node with no inflow reads 1e-17 on one build and
#: -1e-17 on another, and the seventy-five such nodes on a carrier sum past
#: 1e-15 on both builds, each to its own value.
ROUNDING_FLOOR = 1e-12


def floored(vec: np.ndarray) -> np.ndarray:
    return np.where(np.abs(vec) < ROUNDING_FLOOR, 0.0, vec)

LEVERS = (
    ("propensity, financial layer", "propensity", "l1"),
    ("propensity, intermediate block", "propensity", "mid"),
    ("propensity, households", "propensity", "households"),
    ("wage elasticity", "elasticity", None),
    ("pass-on of short payers", "passon", None),
    ("edges, financial to financial", "edge", ("l1", "l1")),
    ("edges, financial to intermediate", "edge", ("l1", "mid")),
    ("edges, intermediate to intermediate", "edge", ("mid", "mid")),
    ("edges, intermediate to financial", "edge", ("mid", "l1")),
    ("edges, households to intermediate", "edge", ("households", "mid")),
    ("edges, households to financial", "edge", ("households", "l1")),
)

#: The readings' sweeps. A45-2 runs on every point of them, so that the chain
#: is checked on the maps it is read on.
COUPLING_SCALES = (1.0, 0.5, 0.2, 0.1, 0.05, 0.02)
WITHIN_SCALES = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
FINANCIAL_PROPENSITIES = (0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
GRID_PROPENSITIES = (0.2, 0.35, 0.5, 0.65, 0.8)
GRID_WITHIN = (0.5, 1.0, 2.0, 4.0, 8.0)
COUPLING_EDGES = (("l1", "mid"), ("mid", "l1"), ("households", "l1"))


# --------------------------------------------------------------------------
# the mean field's parts, and the map rebuilt from them


@dataclass
class Parts:
    seed: int
    wall: float
    variant: str | None
    n: int
    alive: np.ndarray
    live: np.ndarray
    route0: np.ndarray
    has_out: np.ndarray
    pbar: np.ndarray
    payers: np.ndarray
    receivers: np.ndarray
    capped: np.ndarray
    bill: float
    base_spending: float
    elasticity: float
    bill_slope: float
    l2: np.ndarray
    labels: np.ndarray
    reference: np.ndarray


def parts_of(path: PathRecord, variant: str | None = None) -> Parts:
    """Everything A44's mean field reads, taken from the mean field and its
    network, and A44's own matrix to compare the rebuild against."""
    fm = MeanField(path)
    net = path.net
    n = fm.n
    l2 = np.zeros(n, dtype=bool)
    l2[np.asarray(net._l2, dtype=int)] = True
    labels = np.empty(n, dtype=object)
    for c in ALL_CLASSES:
        labels[path.classes[c]] = c
    wc = net.config.wages
    return Parts(
        seed=path.seed, wall=path.wall, variant=variant, n=n,
        alive=fm.alive, live=fm.live, route0=fm.route0, has_out=fm.has_out,
        pbar=0.5 * (np.asarray(net._p_low, dtype=float)
                    + np.asarray(net._p_high, dtype=float)),
        payers=fm.payers, receivers=fm.receivers, capped=fm.capped,
        bill=float(wc.bill), base_spending=float(net._baseline_l2_spending),
        elasticity=float(wc.elasticity), bill_slope=float(fm.bill_slope),
        l2=l2, labels=labels, reference=fm.A)


def group_mask(parts: Parts, group: str) -> np.ndarray:
    if group == "households":
        return np.isin(parts.labels, ("earners", "unreached"))
    return parts.labels == group


class FieldBuilder:
    """A44's mean field assembled from its parts, line for line as A44 builds
    it. Keyword arguments replace one part; with none, A45-0 holds the result
    bitwise equal to A44's matrix.

    **The pass-on strength moves the payers still trading.** A payer that has
    left the market sits outside the block of trading nodes, and on this
    carrier each such payer is short in every round, so its share of the bill
    is zero and nothing it pays reaches the block. Scaling its short share too
    would give it a share of the bill paid from outside the block into the
    earners inside it, and the map would no longer conserve claims.

    Three one-line hooks, so that a seeded fault replaces a line rather than a
    copy of the assembly."""

    def _receiver_share(self, parts: Parts, capped: float) -> float:
        return capped / parts.receivers.size

    def _short_shares(self, parts: Parts, kappa: float) -> np.ndarray:
        return np.where(parts.alive[parts.payers], parts.capped * kappa, parts.capped)

    def _spending_row(self, spend_l2: np.ndarray, wage_step: np.ndarray) -> np.ndarray:
        return spend_l2 @ wage_step

    def matrix(self, parts: Parts, pbar: np.ndarray | None = None,
               weights: np.ndarray | None = None, bill_slope: float | None = None,
               kappa: float = 1.0) -> np.ndarray:
        n = parts.n
        alive = parts.alive
        route0 = parts.route0 if weights is None else parts.route0 * weights
        pbar = parts.pbar if pbar is None else pbar
        reach = (route0 * alive[None, :]).sum(axis=1) > 0
        q = pbar * parts.has_out * alive * reach
        route = route0 * alive[None, :]
        sums = route.sum(axis=1, keepdims=True)
        R = np.divide(route, sums, out=np.zeros_like(route), where=sums > 0)
        G = np.eye(n) - np.diag(q) + R.T * q[None, :]
        capped = parts.capped if kappa == 1.0 else self._short_shares(parts, kappa)
        wage_step = np.eye(n)
        for k, j in enumerate(parts.payers):
            wage_step[j, j] -= capped[k]
            wage_step[parts.receivers, j] += self._receiver_share(parts, capped[k])
        bill_part = np.zeros(n)
        bill_part[parts.payers] -= (1.0 - capped) / parts.payers.size
        bill_part[parts.receivers] += ((1.0 - capped).sum() / parts.payers.size
                                       / parts.receivers.size)
        slope = parts.bill_slope if bill_slope is None else bill_slope
        spend_l2 = parts.l2 * q
        A = np.zeros((n + 1, n + 1))
        A[:n, :n] = G @ wage_step
        A[:n, n] = (G @ bill_part) * slope
        A[n, :n] = self._spending_row(spend_l2, wage_step)
        A[n, n] = float(spend_l2 @ bill_part) * slope
        return A

    def block(self, parts: Parts, **kwargs) -> np.ndarray:
        return self.matrix(parts, **kwargs)[np.ix_(parts.live, parts.live)]


def mass_functional(parts: Parts) -> np.ndarray:
    ell = np.ones(parts.live.size)
    ell[-1] = 0.0
    return ell


def stationary(block: np.ndarray, ell: np.ndarray) -> np.ndarray:
    """The eigenvalue-1 vector with unit mass, by least squares, as A44 takes it."""
    m = block.shape[0]
    lhs = np.vstack([block - np.eye(m), ell[None, :]])
    rhs = np.zeros(m + 1)
    rhs[-1] = 1.0
    return np.linalg.lstsq(lhs, rhs, rcond=None)[0]


def block_positions(parts: Parts) -> dict:
    """Each class's nodes as positions in the block; the spending state last."""
    pos = {int(node): k for k, node in enumerate(parts.live[:-1])}
    out = {}
    for c in ALL_CLASSES:
        nodes = np.flatnonzero(parts.labels == c)
        out[c] = np.array([pos[int(i)] for i in nodes if int(i) in pos], dtype=int)
    return out


# --------------------------------------------------------------------------
# the levers and the derivative


def lever_base(parts: Parts, lever: tuple) -> float:
    _, kind, arg = lever
    if kind == "propensity":
        values = np.unique(parts.pbar[group_mask(parts, arg)])
        if values.size != 1:
            raise ValueError(f"{arg} carries {values.size} propensity bands")
        return float(values[0])
    if kind == "elasticity":
        return parts.elasticity
    return 1.0


def lever_kwargs(parts: Parts, lever: tuple, theta: float) -> dict:
    _, kind, arg = lever
    if kind == "propensity":
        pbar = parts.pbar.copy()
        pbar[group_mask(parts, arg)] = theta
        return {"pbar": pbar}
    if kind == "elasticity":
        slope = (parts.bill * theta / parts.base_spending
                 if parts.base_spending > 0.0 else 0.0)
        return {"bill_slope": slope}
    if kind == "passon":
        return {"kappa": theta}
    if kind == "edge":
        weights = np.ones((parts.n, parts.n))
        weights[np.ix_(group_mask(parts, arg[0]), group_mask(parts, arg[1]))] = theta
        return {"weights": weights}
    raise ValueError(f"unknown lever kind {kind}")


class Derivative:
    """The derivative of the stationary vector, dpi = Z (dB/dtheta) pi.

    Three one-line hooks for the seeded faults."""

    def _fundamental(self, block: np.ndarray, pi: np.ndarray, ell: np.ndarray) -> np.ndarray:
        m = block.shape[0]
        return np.linalg.inv(np.eye(m) - block + np.outer(pi, ell))

    def _rate(self, d_block: np.ndarray) -> np.ndarray:
        return d_block

    def _apply(self, fundamental: np.ndarray, d_block: np.ndarray, pi: np.ndarray) -> np.ndarray:
        return fundamental @ d_block @ pi

    def of(self, block: np.ndarray, d_block: np.ndarray, pi: np.ndarray,
           ell: np.ndarray) -> np.ndarray:
        return self._apply(self._fundamental(block, pi, ell), self._rate(d_block), pi)


def derivative_rows(parts: Parts, builder: FieldBuilder | None = None,
                    derivative: Derivative | None = None, levers=LEVERS) -> list[dict]:
    """A45-1's rows: for each lever, the formula against re-solving the
    stationary vector at theta plus and minus the step."""
    builder = FieldBuilder() if builder is None else builder
    derivative = Derivative() if derivative is None else derivative
    ell = mass_functional(parts)
    block = builder.block(parts)
    pi = stationary(block, ell)
    pos = block_positions(parts)
    split = class_sums(parts, pi, floor=True)
    rows = []
    for lever in levers:
        theta = lever_base(parts, lever)
        up = builder.block(parts, **lever_kwargs(parts, lever, theta + LEVER_STEP))
        down = builder.block(parts, **lever_kwargs(parts, lever, theta - LEVER_STEP))
        d_block = (up - down) / (2.0 * LEVER_STEP)
        formula = derivative.of(block, d_block, pi, ell)
        resolved = (stationary(up, ell) - stationary(down, ell)) / (2.0 * LEVER_STEP)
        row = {"seed": parts.seed, "wall": parts.wall, "lever": lever[0],
               "theta": theta, "diff": float(np.abs(formula - resolved).max())}
        for c in HOME_CLASSES:
            row[f"dpi_{c}"] = float(formula[pos[c]].sum()) if pos[c].size else 0.0
            row[f"pi_{c}"] = split[c]
            row[f"elasticity_{c}"] = (theta * row[f"dpi_{c}"] / split[c]
                                      if split[c] > 0.0 else float("nan"))
        rows.append(row)
    return rows


def routes_of(parts: Parts, weights: np.ndarray | None = None) -> np.ndarray:
    """The spending routes over the trading nodes, as the builder renormalizes them."""
    route0 = parts.route0 if weights is None else parts.route0 * weights
    route = route0 * parts.alive[None, :]
    sums = route.sum(axis=1, keepdims=True)
    return np.divide(route, sums, out=np.zeros_like(route), where=sums > 0)


def spend_rates(parts: Parts, pbar: np.ndarray) -> np.ndarray:
    reach = (parts.route0 * parts.alive[None, :]).sum(axis=1) > 0
    return pbar * parts.has_out * parts.alive * reach


#: A45-3 moves each lever by this much, a finite step whose effect is plain.
FOOTPRINT_STEP = 0.5


def footprint_row(parts: Parts, lever: tuple, kwargs_of=None) -> dict:
    """A45-3's row: moving the lever changes the part it names and nothing else,
    in the direction its name says. Read off the builder's inputs (routes, spend
    rates, bill slope, short shares), not off the map, so that it checks what a
    lever is rather than what the map does with it."""
    kwargs_of = lever_kwargs if kwargs_of is None else kwargs_of
    _, kind, arg = lever
    theta = lever_base(parts, lever)
    new = theta * (1.0 + FOOTPRINT_STEP) if kind in ("edge", "passon", "elasticity") \
        else theta * (1.0 - FOOTPRINT_STEP)
    before, after = kwargs_of(parts, lever, theta), kwargs_of(parts, lever, new)
    row = {"seed": parts.seed, "wall": parts.wall, "lever": lever[0]}
    if kind == "edge":
        src, dst = group_mask(parts, arg[0]), group_mask(parts, arg[1])
        r0, r1 = routes_of(parts, before["weights"]), routes_of(parts, after["weights"])
        changed = np.abs(r1 - r0).max(axis=1) > 0.0
        rows = np.flatnonzero(src & parts.alive & (r0[:, dst].sum(axis=1) > 0.0))
        row["moved"] = bool(changed.any())
        row["inside"] = bool(not (changed & ~src).any())
        row["direction"] = bool(rows.size and np.all(r1[rows][:, dst].sum(axis=1)
                                                     >= r0[rows][:, dst].sum(axis=1))
                                and np.any(r1[rows][:, dst].sum(axis=1)
                                           > r0[rows][:, dst].sum(axis=1)))
    elif kind == "propensity":
        group = group_mask(parts, arg)
        q0, q1 = spend_rates(parts, before["pbar"]), spend_rates(parts, after["pbar"])
        changed = q1 != q0
        row["moved"] = bool(changed.any())
        row["inside"] = bool(not (changed & ~group).any())
        row["direction"] = bool(np.all(q1[changed] < q0[changed]))
    elif kind == "elasticity":
        row["moved"] = after["bill_slope"] != before["bill_slope"]
        row["inside"] = True
        row["direction"] = after["bill_slope"] > before["bill_slope"]
    else:
        builder = FieldBuilder()
        s0 = builder._short_shares(parts, before["kappa"])
        s1 = builder._short_shares(parts, after["kappa"])
        changed = s1 != s0
        trading_short = parts.alive[parts.payers] & (parts.capped > 0.0)
        row["moved"] = bool(changed.any()) or not trading_short.any()
        row["inside"] = bool(not (changed & ~trading_short).any())
        row["direction"] = bool(np.all(s1[changed] > s0[changed]))
    return row


# --------------------------------------------------------------------------
# the class chain


class ClassChain:
    """The map aggregated into classes. Column d of the chain is the class
    d's nodes' columns, weighted by their stationary mass and summed over the
    rows of each class. A class with no stationary mass above the rounding
    floor (the nodes nothing flows into) is weighted by node count; its column
    never meets any mass.

    One hook for the seeded fault."""

    def _weights(self, pi_class: np.ndarray) -> np.ndarray:
        mass = floored(pi_class)
        total = float(mass.sum())
        if total == 0.0:
            return np.full(pi_class.size, 1.0 / pi_class.size)
        return mass / total

    def build(self, parts: Parts, block: np.ndarray, pi: np.ndarray
              ) -> tuple[list[str], np.ndarray, list[np.ndarray]]:
        pos = block_positions(parts)
        names = [c for c in ALL_CLASSES if pos[c].size] + ["spending state"]
        groups = [pos[c] for c in ALL_CLASSES if pos[c].size] + [np.array([block.shape[0] - 1])]
        g = len(groups)
        chain = np.zeros((g, g))
        for d, cols in enumerate(groups):
            column = block[:, cols] @ self._weights(pi[cols])
            for c, rows_ in enumerate(groups):
                chain[c, d] = column[rows_].sum()
        return names, chain, groups


def chain_row(parts: Parts, label: str, builder: FieldBuilder | None = None,
              chain_class=ClassChain, functional=mass_functional, **kwargs) -> dict:
    """A45-2's row on one map: the chain's column sums, the class sums of the
    stationary vector carried through the chain, and whether those sums over
    the classes that hold claims add to one. Every share the readings print is
    one of these sums."""
    builder = FieldBuilder() if builder is None else builder
    ell = functional(parts)
    block = builder.block(parts, **kwargs)
    pi = stationary(block, ell)
    names, chain, groups = chain_class().build(parts, block, pi)
    sums = np.array([pi[grp].sum() for grp in groups])
    mass = np.array([name != "spending state" for name in names])
    col = chain[mass].sum(axis=0)
    conserve = max(float(np.abs(col[mass] - 1.0).max()), float(np.abs(col[~mass]).max()))
    identity = float(np.abs(chain @ sums - sums).max())
    return {"seed": parts.seed, "wall": parts.wall, "map": label,
            "classes": len(names) - 1, "conserve_err": conserve, "identity_err": identity,
            "mass_err": abs(float(sums[mass].sum()) - 1.0),
            "stationary_err": float(np.abs(block @ pi - pi).max())}


def type_weights(parts: Parts, scaled: dict) -> np.ndarray:
    weights = np.ones((parts.n, parts.n))
    for (src, dst), factor in scaled.items():
        weights[np.ix_(group_mask(parts, src), group_mask(parts, dst))] *= factor
    return weights


def sweep_points(parts: Parts) -> list[tuple[str, str, dict, dict]]:
    """The readings' sweep points on a carrier without a floor: label, family,
    the swept values, and the builder arguments."""
    points = []
    for s in COUPLING_SCALES:
        points.append((f"coupling x{s:g}", "coupling", {"coupling_scale": s},
                       {"weights": type_weights(parts, {e: s for e in COUPLING_EDGES})}))
    for w in WITHIN_SCALES:
        points.append((f"financial within x{w:g}", "financial within", {"within_scale": w},
                       {"weights": type_weights(parts, {("l1", "l1"): w})}))
    fin = group_mask(parts, "l1")
    for p in FINANCIAL_PROPENSITIES:
        pbar = parts.pbar.copy()
        pbar[fin] = p
        points.append((f"financial propensity {p:g}", "financial propensity",
                       {"propensity": p}, {"pbar": pbar}))
    for p in GRID_PROPENSITIES:
        for w in GRID_WITHIN:
            pbar = parts.pbar.copy()
            pbar[fin] = p
            points.append((f"grid propensity {p:g} within x{w:g}", "grid",
                           {"propensity": p, "within_scale": w},
                           {"pbar": pbar,
                            "weights": type_weights(parts, {("l1", "l1"): w})}))
    return points


def sweep_maps(parts: Parts) -> list[tuple[str, dict]]:
    """The sweep points as builder arguments, for A45-2, which checks the chain
    on every map the readings read."""
    return [(label, kwargs) for label, _, _, kwargs in sweep_points(parts)]


# --------------------------------------------------------------------------
# rows and criteria


def _label(r: dict) -> str:
    head = f"{r['variant']}, " if r.get("variant") else ""
    tail = (f" {r['map']}" if "map" in r else "") + (f" {r['lever']}" if "lever" in r else "")
    return f"{head}seed {r['seed']} wall {r['wall']}{tail}"


def rebuild_row(parts: Parts, builder: FieldBuilder | None = None) -> dict:
    builder = FieldBuilder() if builder is None else builder
    rebuilt = builder.matrix(parts)
    same_shape = rebuilt.shape == parts.reference.shape
    return {"seed": parts.seed, "wall": parts.wall, "variant": parts.variant,
            "equal": bool(same_shape and np.array_equal(rebuilt, parts.reference)),
            "largest": (float(np.abs(rebuilt - parts.reference).max())
                        if same_shape else float("inf")),
            "capped_payers": int((parts.capped > 0.0).sum())}


def criterion_rebuild(rows: list[dict]) -> dict:
    name = ("A45-0  the rebuilt map is A44's mean field: assembled here from "
            "A44's parts, it equals A44's matrix bitwise on every carrier")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no carriers, nothing was evaluated")
    bad = [r for r in rows if not r["equal"]]
    variants = sum(1 for r in rows if r.get("variant"))
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} carriers, {len(rows) - variants} "
                f"defaults and {variants} of A44's variants: the matrix assembled "
                f"in this file from the mean field's routes, spending bands, "
                f"payroll sets, short-payer shares and bill slope is bitwise "
                f"equal to the matrix A44 builds." if not bad else
                f"Fails on {len(bad)} of {len(rows)} carriers: "
                + "; ".join(f"{_label(r)} largest entry difference {r['largest']:.3e}"
                            for r in bad[:4])))


def criterion_derivative(rows: list[dict]) -> dict:
    name = ("A45-1  the derivative of the stationary split is Z dB pi: it matches "
            "re-solving the split on either side of every lever")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no levers, nothing was evaluated")
    bad = [r for r in rows if not r["diff"] <= TOL_DERIVATIVE]
    carriers = len({(r["seed"], r["wall"]) for r in rows})
    levers = len({r["lever"] for r in rows})
    m3 = sum(1 for r in rows if r.get("map"))
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} pairs of {carriers} carriers and "
                f"{levers} levers, {m3} of them on M3's maps: the stationary vector's derivative from the "
                f"fundamental matrix with its projector, Z (dB/dtheta) pi with "
                f"dB a central difference at step {LEVER_STEP:g}, differs from "
                f"the central difference of the re-solved stationary vector by "
                f"at most {TOL_DERIVATIVE:.0e} in every entry." if not bad else
                f"Fails on {len(bad)} of {len(rows)} pairs, against "
                f"{TOL_DERIVATIVE:.0e}: "
                + "; ".join(f"{_label(r)} {r['diff']:.3e}" for r in bad[:4])))


def criterion_footprint(rows: list[dict]) -> dict:
    name = ("A45-3  every lever moves what it names: the part of the map it is "
            "named for changes, in the named direction, and no other part does")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no levers, nothing was evaluated")
    bad = [r for r in rows if not (r["moved"] and r["inside"] and r["direction"])]
    carriers = len({(r["seed"], r["wall"]) for r in rows})
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} pairs of {carriers} carriers and "
                f"{len({r['lever'] for r in rows})} levers: moving an edge lever "
                f"changes only the routes out of its source class and raises the "
                f"share they send into its destination class; a propensity lever "
                f"changes only its class's spending rates; the elasticity lever "
                f"raises the bill slope; the pass-on lever scales only the short "
                f"shares of payers still trading." if not bad else
                f"Fails on {len(bad)} of {len(rows)} pairs: "
                + "; ".join(f"{_label(r)} moved {r['moved']} inside {r['inside']} "
                            f"direction {r['direction']}" for r in bad[:4])))


def criterion_chain(rows: list[dict]) -> dict:
    name = ("A45-2  the class chain keeps the stationary split: the stationary "
            "vector solves the map, and weighted by stationary mass the chain "
            "conserves claims and returns the class sums, which add to one")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no maps, nothing was evaluated")
    bad = [r for r in rows
           if not (r["conserve_err"] <= TOL_CHAIN and r["identity_err"] <= TOL_CHAIN
                   and r["mass_err"] <= TOL_CHAIN and r["stationary_err"] <= TOL_CHAIN)]
    m3 = sum(1 for r in rows if r["map"].startswith("M3 "))
    sweeps = sum(1 for r in rows if r["map"] != "carrier") - m3
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} maps, {len(rows) - sweeps - m3} carriers, "
                f"{sweeps} sweep points and {m3} of M3's maps: the stationary "
                f"vector solves the map to within {TOL_CHAIN:.0e}, every column of "
                f"the class chain conserves claims to within {TOL_CHAIN:.0e}, and "
                f"the chain carries the class sums of the stationary vector to "
                f"themselves to within {TOL_CHAIN:.0e}, and the sums over the "
                f"classes that hold claims add to one to within {TOL_CHAIN:.0e}."
                if not bad else
                f"Fails on {len(bad)} of {len(rows)} maps: "
                + "; ".join(f"{_label(r)} conserve {r['conserve_err']:.2e}, "
                            f"identity {r['identity_err']:.2e}, mass {r['mass_err']:.2e}, "
                            f"stationary {r['stationary_err']:.2e}"
                            for r in bad[:4])))


# --------------------------------------------------------------------------
# runs


def default_parts(seeds=SEEDS) -> list[Parts]:
    return [parts_of(record_path(seed, wall)) for seed in seeds for wall in WALLS]


def variant_parts(seeds=SEEDS) -> list[Parts]:
    out = []
    for name, changes in VARIANTS:
        for seed in seeds:
            cfg = apply_variant(base_config(seed, need=0.0), changes)
            out.append(parts_of(record_path(seed, 0.0, config=cfg), variant=name))
    return out


def run_gate(builder: FieldBuilder | None = None, seeds=SEEDS,
             with_variants: bool = True) -> tuple[list[dict], dict]:
    t0 = time.time()
    parts = default_parts(seeds) + (variant_parts(seeds) if with_variants else [])
    rows = [rebuild_row(p, builder) for p in parts]
    crit = criterion_rebuild(rows)
    print(f"A45-0 on {len(rows)} carriers ({time.time() - t0:.1f} s)")
    return rows, crit


def run_check(seeds=SEEDS, parts: list[Parts] | None = None
              ) -> tuple[list[dict], list[dict], list[dict]]:
    t0 = time.time()
    d_rows, c_rows, f_rows = [], [], []
    for p in (default_parts(seeds) if parts is None else parts):
        d_rows += derivative_rows(p)
        f_rows += [footprint_row(p, lever) for lever in LEVERS]
        c_rows.append(chain_row(p, "carrier"))
        if p.wall == 0.0:
            for label, kwargs in sweep_maps(p):
                c_rows.append(chain_row(p, label, **kwargs))
        print(f"  seed {p.seed} wall {p.wall} done ({time.time() - t0:.0f} s)", flush=True)
    return d_rows, c_rows, f_rows


def _print_criteria(crit: list[dict]) -> None:
    print()
    for x in crit:
        print(f"  {'PASS' if x['passed'] else 'FAIL'}[{x['kind']}] {x['name']}")
        print(f"        {x['detail'][:700]}")


def print_check(d_rows: list[dict], c_rows: list[dict]) -> None:
    print("\nA45-1 by lever: largest difference over carriers | derivative of the "
          "l1 / mid / earners stationary shares, median over carriers")
    for lever in [lv[0] for lv in LEVERS]:
        rs = [r for r in d_rows if r["lever"] == lever]
        if not rs:
            continue
        med = {c: float(np.median([r[f"dpi_{c}"] for r in rs])) for c in HOME_CLASSES}
        print(f"  {lever:38s} {max(r['diff'] for r in rs):.2e} | "
              + " / ".join(f"{med[c]:+.4f}" for c in HOME_CLASSES))
    print("\nA45-2 by family of maps: count, largest conservation error, largest identity "
          "error, largest distance of the class sums' total from one")
    families = {}
    for r in c_rows:
        key = next((f for f in ("coupling", "financial within", "financial propensity", "grid")
                    if r["map"].startswith(f)), r["map"])
        families.setdefault(key, []).append(r)
    for key, rs in families.items():
        print(f"  {key:28s} {len(rs):4d}  {max(r['conserve_err'] for r in rs):.2e}  "
              f"{max(r['identity_err'] for r in rs):.2e}  {max(r['mass_err'] for r in rs):.2e}")
    if d_rows:
        print(f"\n  residues on this machine: derivative {max(r['diff'] for r in d_rows):.3e}")
    if c_rows:
        print(f"  chain conservation {max(r['conserve_err'] for r in c_rows):.3e}, "
              f"identity {max(r['identity_err'] for r in c_rows):.3e}, "
              f"stationary {max(r['stationary_err'] for r in c_rows):.3e}")


def print_ablation_check(d_rows: list[dict], c_rows: list[dict]) -> None:
    print("\nM3's maps under A45-1 and A45-2: count, largest derivative difference | "
          "largest conservation error, largest stationary residue")
    for label in ("no_bill", "no_pass_on", "neither"):
        ds = [r for r in d_rows if r["map"] == f"M3 {label}"]
        cs = [r for r in c_rows if r["map"] == f"M3 {label}"]
        if not (ds and cs):
            continue
        print(f"  {label:12s} {len(ds):3d}  {max(r['diff'] for r in ds):.2e} | "
              f"{max(r['conserve_err'] for r in cs):.2e}  "
              f"{max(r['stationary_err'] for r in cs):.2e}")


# --------------------------------------------------------------------------
# the readings: M1 to M3, printed and recorded, no verdicts


#: M1c: two grid points whose financial out-rates differ by less than this,
#: relative to the smaller, while their propensities differ, print as a pair.
PAIR_TOLERANCE = 0.03

#: M1: maps where the entry term and the class chain's summed rounds differ by
#: more than this, relative to the rounds, are counted and named.
MIXING_GAP = 0.07

#: M1d: the whole model against the mean field's entry term on four carriers,
#: from the default to thin coupling between the financial layer and the rest.
CHECK_CARRIERS = (
    ("default", {}),
    ("thick financial layer", {"spec.layer1_out_degree": 18}),
    ("thin coupling", {"spec.layer1_out_degree": 18,
                       "spec.intermediate_out_degree": 12,
                       "spec.upward_out_degree": 1}),
    ("thinner coupling", {"spec.layer1_out_degree": 30,
                          "spec.intermediate_out_degree": 20,
                          "spec.upward_out_degree": 1,
                          "spec.intermediate_upward_degree": 1}),
)
HORIZONS = (25, 75, 250)
CHECK_AMOUNT = 4.0

#: M2b: eight of A44's variants, each with the levers that move the default
#: carrier toward it and their new values. A propensity is the variant band's
#: midpoint, computed as the network computes it, so that the moved map carries
#: the variant's propensities bit for bit. An edge lever's value multiplies the
#: weight of the edges it names; the record carries the ratio of the variant's
#: edge count to the default's beside it.
VARIANT_LEVERS = (
    ("financial propensity 0.3", (("propensity, financial layer", 0.3),)),
    ("financial propensity 0.7", (("propensity, financial layer", 0.7),)),
    ("production propensity 0.55 to 0.65", (("propensity, intermediate block", 0.5 * (0.55 + 0.65)),
                                            ("propensity, households", 0.5 * (0.55 + 0.65)))),
    ("wage elasticity 0", (("wage elasticity", 0.0),)),
    ("wage elasticity 1", (("wage elasticity", 1.0),)),
    ("upward out-degree 4", (("edges, households to financial", 2.0),)),
    ("f2i 10", (("edges, financial to intermediate", 1.0 / 3.0),)),
    ("f2i 60", (("edges, financial to intermediate", 2.0),)),
)

#: M2b's own column against A44's record of the same carriers, whose shares
#: are rounded to ten places.
RECORD_AGREEMENT = 1e-9

#: The fields that must be the same on a default carrier and a variant for the
#: variant's control run to be put on the default's graph.
NODE_FIELDS = ("payers", "receivers", "l2", "has_out", "alive", "labels")

SWEEP_KEYS = ("coupling_scale", "within_scale", "propensity")


def lever_named(name: str) -> tuple:
    for lever in LEVERS:
        if lever[0] == name:
            return lever
    raise KeyError(name)


def class_sums(parts: Parts, vec: np.ndarray, floor: bool = False) -> dict:
    """A vector on the block summed over each class's trading nodes. With
    ``floor``, entries below the rounding floor read as zero first."""
    pos = block_positions(parts)
    x = floored(vec) if floor else vec
    return {c: float(x[pos[c]].sum()) if pos[c].size else 0.0 for c in ALL_CLASSES}


def injections(parts: Parts) -> dict:
    """One claim spread evenly over each home class's trading nodes, as A44
    injects it, on the block."""
    pos = block_positions(parts)
    out = {}
    for c in HOME_CLASSES:
        v = np.zeros(parts.live.size)
        if pos[c].size:
            v[pos[c]] = 1.0 / pos[c].size
        out[c] = v
    return out


def deviation_matrix(block: np.ndarray, pi: np.ndarray, ell: np.ndarray) -> np.ndarray:
    """``D = (B - P) Z`` with ``P = pi ell'`` and ``Z = (I - B + P)^-1``."""
    m = block.shape[0]
    proj = np.outer(pi, ell)
    return (block - proj) @ np.linalg.inv(np.eye(m) - block + proj)


def entry_terms(columns: dict) -> dict:
    """``K_c``: class c's term when the claims enter c, less the median of its
    term when they enter each of the other two home classes. ``columns[t][c]``
    is class c's term for claims entering t. The comparison set is the same on
    every carrier and every floor."""
    return {c: columns[c][c] - statistics.median(columns[o][c] for o in HOME_CLASSES
                                                 if o != c)
            for c in HOME_CLASSES}


def chain_entry_terms(names: list[str], chain: np.ndarray, sums: np.ndarray) -> dict:
    """The entry term off the class chain's own deviation matrix, the claims
    entering a class's state."""
    idx = {name: i for i, name in enumerate(names)}
    if any(c not in idx for c in HOME_CLASSES):
        return {c: float("nan") for c in HOME_CLASSES}
    ell = np.array([0.0 if name == "spending state" else 1.0 for name in names])
    dev = deviation_matrix(chain, sums, ell)
    return entry_terms({t: {c: float(dev[idx[c], idx[t]]) for c in HOME_CLASSES}
                        for t in HOME_CLASSES})


def node_terms(parts: Parts, pbar: np.ndarray) -> dict:
    """The node reading, ``(1 - p)/p`` with p the class's own propensity."""
    out = {}
    for c in HOME_CLASSES:
        values = np.unique(pbar[(parts.labels == c) & parts.alive])
        out[c] = (float((1.0 - values[0]) / values[0])
                  if values.size == 1 and values[0] > 0.0 else float("nan"))
    return out


def out_rates(parts: Parts, pi: np.ndarray, pbar: np.ndarray,
              weights: np.ndarray | None) -> dict:
    """``a_c``: the share of class c's claims that leave the class in a round,
    its nodes' spend rates times the part of their routes outside c, weighted
    by stationary mass."""
    routes = routes_of(parts, weights)
    rates = spend_rates(parts, pbar)
    mass = np.zeros(parts.n)
    mass[parts.live[:-1]] = floored(pi[:-1])
    out = {}
    for c in HOME_CLASSES:
        members = (parts.labels == c) & parts.alive
        total = float(mass[members].sum())
        leaving = rates[members] * (1.0 - routes[np.ix_(members, members)].sum(axis=1))
        out[c] = (float((leaving * mass[members]).sum()) / total
                  if total != 0.0 else float("nan"))
    return out


def field_reading(parts: Parts, label: str, **kwargs) -> tuple[dict, dict]:
    """M1's numbers on one map: the entry term from the full map, from the class
    chain and from the node reading; the full map's second modulus; the chain's
    second eigenvalue and its summed rounds; the stationary split; each home
    class's out-rate. The chain comes back for M3."""
    block = FieldBuilder().block(parts, **kwargs)
    ell = mass_functional(parts)
    pi = stationary(block, ell)
    dev = deviation_matrix(block, pi, ell)
    columns = {t: class_sums(parts, dev @ v) for t, v in injections(parts).items()}
    names, chain, groups = ClassChain().build(parts, block, pi)
    sums = np.array([pi[grp].sum() for grp in groups])
    moduli = np.sort(np.abs(np.linalg.eigvals(block)))
    chain_ev = np.linalg.eigvals(chain)
    second = chain_ev[np.argsort(np.abs(chain_ev), kind="stable")[-2]]
    lam = float(abs(second))
    pbar = kwargs.get("pbar", parts.pbar)
    row = {"seed": parts.seed, "wall": parts.wall, "map": label,
           "second_modulus": float(moduli[-2]), "chain_second": lam,
           "chain_second_imag": float(abs(second.imag)),
           "chain_rounds": lam / (1.0 - lam) if lam < 1.0 else float("nan")}
    if parts.variant:
        row["carrier"] = parts.variant
    readings = (("k", entry_terms(columns)),
                ("k_chain", chain_entry_terms(names, chain, sums)),
                ("k_node", node_terms(parts, pbar)),
                ("outrate", out_rates(parts, pi, pbar, kwargs.get("weights"))))
    for key, values in readings:
        for c in HOME_CLASSES:
            row[f"{key}_{c}"] = values[c]
    split = class_sums(parts, pi, floor=True)
    for c in ALL_CLASSES:
        row[f"pi_{c}"] = split[c]
    row["pi_spending"] = float(pi[-1])
    return row, {"seed": parts.seed, "wall": parts.wall, "classes": names,
                 "matrix": chain}


def sweep_rows(defaults: list[Parts]) -> list[dict]:
    """M1b and M1c: every sweep point on every carrier without a floor."""
    rows = []
    for p in defaults:
        if p.wall != 0.0:
            continue
        for label, family, values, kwargs in sweep_points(p):
            row, _ = field_reading(p, label, **kwargs)
            row["family"] = family
            row.update({key: values.get(key) for key in SWEEP_KEYS})
            rows.append(row)
    return rows


def outrate_pairs(rows: list[dict]) -> list[dict]:
    """M1c: grid points of one seed whose financial out-rates differ by less
    than ``PAIR_TOLERANCE`` of the smaller while their propensities differ."""
    grid = sorted((r for r in rows if r["family"] == "grid"),
                  key=lambda r: (r["seed"], r["propensity"], r["within_scale"]))
    pairs = []
    for i, a in enumerate(grid):
        for b in grid[i + 1:]:
            if a["seed"] != b["seed"] or a["propensity"] == b["propensity"]:
                continue
            low = min(a["outrate_l1"], b["outrate_l1"])
            if low > 0.0 and abs(a["outrate_l1"] - b["outrate_l1"]) < PAIR_TOLERANCE * low:
                pairs.append({"seed": a["seed"],
                              "propensity_a": a["propensity"], "within_scale_a": a["within_scale"],
                              "propensity_b": b["propensity"], "within_scale_b": b["within_scale"],
                              "outrate_a": a["outrate_l1"], "outrate_b": b["outrate_l1"],
                              "pi_a": a["pi_l1"], "pi_b": b["pi_l1"],
                              "k_a": a["k_l1"], "k_b": b["k_l1"]})
    return pairs


def check_rows(seeds, tick=None) -> tuple[list[dict], list[dict]]:
    """M1d: on each check carrier and seed, the default map's numbers; then at
    each horizon T the whole model's entry term and the mean field's, both
    times T, beside the constant K. An injection of T rounds opens at round
    ``ROUNDS - T``, and the map for it takes each payer's short share from that
    round on, as A44's I2 does."""
    carriers, horizons = [], []
    for name, changes in CHECK_CARRIERS:
        for seed in seeds:
            cfg = apply_variant(base_config(seed, need=0.0), changes)
            path = record_path(seed, 0.0, config=cfg)
            row, _ = field_reading(parts_of(path, variant=name), "carrier")
            carriers.append(row)
            for horizon in HORIZONS:
                fm = MeanField(path, open_from=ROUNDS - horizon)
                constants = deviation_constants(fm, HOME_CLASSES)
                pi, _ = fm.stationary()
                cls = fm.block_classes()
                nodes = floored(pi[:-1])
                model = {t: run_shares(path, t, CHECK_AMOUNT, open_from=ROUNDS - horizon)
                         for t in HOME_CLASSES}
                field_ = {t: field_shares(fm, t, horizon) for t in HOME_CLASSES}
                model_entry = home_bias(model, HOME_CLASSES)
                field_entry = home_bias(field_, HOME_CLASSES)
                hrow = {"carrier": name, "seed": seed, "horizon": horizon,
                        "capped_share_mean": float(fm.capped.mean())}
                for c in HOME_CLASSES:
                    hrow[f"model_entry_{c}"] = horizon * model_entry[c]
                    hrow[f"field_entry_{c}"] = horizon * field_entry[c]
                    hrow[f"k_{c}"] = constants[c]
                for c in ALL_CLASSES:
                    hrow[f"pi_{c}"] = float(nodes[cls[c]].sum()) if cls[c].size else 0.0
                for t in HOME_CLASSES:
                    for c in ALL_CLASSES:
                        hrow[f"model_{t}_{c}"] = model[t][c]
                        hrow[f"field_{t}_{c}"] = field_[t][c]
                horizons.append(hrow)
        if tick is not None:
            tick(f"M1d {name}")
    return carriers, horizons


def moved_kwargs(parts: Parts, moves) -> dict:
    """Builder arguments with every move applied at once on these parts."""
    pbar = parts.pbar.copy()
    weights = np.ones((parts.n, parts.n))
    kwargs = {"pbar": pbar, "weights": weights}
    for lever_name, value in moves:
        _, kind, arg = lever_named(lever_name)
        if kind == "propensity":
            pbar[group_mask(parts, arg)] = value
        elif kind == "edge":
            weights[np.ix_(group_mask(parts, arg[0]), group_mask(parts, arg[1]))] *= value
        elif kind == "elasticity":
            kwargs["bill_slope"] = (parts.bill * value / parts.base_spending
                                    if parts.base_spending > 0.0 else 0.0)
        else:
            raise ValueError(f"no variant moves {lever_name}")
    return kwargs


def split_of(parts: Parts, **kwargs) -> dict:
    block = FieldBuilder().block(parts, **kwargs)
    return class_sums(parts, stationary(block, mass_functional(parts)), floor=True)


def load_a44_record() -> dict | None:
    if not A44_RECORD.exists():
        print(f"  {A44_RECORD.name} is not on disk: M2b's own column is not "
              f"compared with it")
        return None
    return json.loads(A44_RECORD.read_text(encoding="utf-8"))


def variant_rows(defaults: dict, variants: dict, d_rows: list[dict],
                 a44_record: dict | None) -> list[dict]:
    """M2b: for each variant and seed, four splits. First order from the default
    carrier's derivative; the default carrier's map with the levers moved; the
    same with the variant's own control run put in (its payers' short shares
    and its bill slope); the variant carrier's own map. The steps between them
    are the linearization, the control run and the graph."""
    deriv = {(r["seed"], r["wall"], r["lever"]): r for r in d_rows}
    recorded = ({} if a44_record is None else
                {(r["variant"], r["seed"]): r
                 for r in a44_record.get("variant_carriers", [])})
    rows = []
    for name, moves in VARIANT_LEVERS:
        for seed, d in sorted(defaults.items()):
            v = variants[(name, seed)]
            base = split_of(d)
            first = dict(base)
            for lever_name, value in moves:
                r = deriv[(seed, 0.0, lever_name)]
                for c in HOME_CLASSES:
                    first[c] += r[f"dpi_{c}"] * (value - r["theta"])
            moved = moved_kwargs(d, moves)
            exact = split_of(d, **moved)
            nodes_same = d.n == v.n and all(np.array_equal(getattr(d, f), getattr(v, f))
                                            for f in NODE_FIELDS)
            path_split = None
            if nodes_same:
                h = dataclasses.replace(d, capped=v.capped, base_spending=v.base_spending,
                                        bill_slope=v.bill_slope)
                path_split = split_of(h, **moved_kwargs(h, moves))
            own = split_of(v)
            row = {"variant": name, "seed": seed,
                   "graph_same": bool(np.array_equal(d.route0, v.route0)),
                   "nodes_same": bool(nodes_same),
                   "propensities_match": bool(np.array_equal(moved["pbar"], v.pbar)),
                   "short_payers_changed": (int((d.capped != v.capped).sum())
                                            if d.capped.shape == v.capped.shape else None),
                   "bill_slope_default": d.bill_slope, "bill_slope_variant": v.bill_slope}
            for c in HOME_CLASSES:
                row[f"base_{c}"] = base[c]
                row[f"first_{c}"] = first[c]
                row[f"exact_{c}"] = exact[c]
                row[f"path_{c}"] = path_split[c] if path_split else float("nan")
                row[f"own_{c}"] = own[c]
            rec = recorded.get((name, seed))
            row["own_matches_a44_record"] = (
                None if rec is None else
                bool(max(abs(own[c] - rec[f"pi_{c}"]) for c in ALL_CLASSES)
                     <= RECORD_AGREEMENT))
            rows.append(row)
    return rows


def _others_gap(row: dict, own: str, value: float) -> float:
    return max(abs(row[f"elasticity_{c}"] - value) for c in HOME_CLASSES if c != own)


def ablation_maps(parts: Parts, builder: FieldBuilder | None = None
                  ) -> list[tuple[str, Parts]]:
    """M3's three maps for the intermediate block: the bill slope at zero, the
    pass-on removed, and both. The pass-on is removed through the lever's own
    entry, the short shares at strength zero, so a payer that has left the
    market keeps its share and stays out of the bill (see FieldBuilder)."""
    builder = FieldBuilder() if builder is None else builder
    live_zero = builder._short_shares(parts, 0.0)
    return [("no_bill", dataclasses.replace(parts, bill_slope=0.0)),
            ("no_pass_on", dataclasses.replace(parts, capped=live_zero)),
            ("neither", dataclasses.replace(parts, bill_slope=0.0, capped=live_zero))]


def ablation_checks(defaults: list[Parts], builder: FieldBuilder | None = None
                    ) -> tuple[list[dict], list[dict]]:
    """A45-1 and A45-2 on the maps M3 reads: the intermediate block's lever on
    each, and each map's chain. M3 reads its gaps from these same rows."""
    mid = [lever_named("propensity, intermediate block")]
    d_rows, c_rows = [], []
    for p in defaults:
        for label, q in ablation_maps(p, builder):
            d_rows += [r | {"map": f"M3 {label}"} for r in derivative_rows(q, levers=mid)]
            c_rows.append(chain_row(q, f"M3 {label}"))
    return d_rows, c_rows


def holding_time_rows(defaults: list[Parts], carriers: list[dict],
                      d_rows: list[dict], m3_rows: list[dict]) -> list[dict]:
    """M3: each propensity lever's elasticities against the holding-time form.

    The earners: no route enters them, so after wages each keeps ``1 - p`` of
    what it holds and its stationary holding is ``(1 - p)/p`` times its wages
    a round. With wages fixed, their share's elasticity to p is ``-1/(1 - p)``,
    ``-(1 - pi)/(1 - p)`` once the other classes take up the change, and every
    other class's is ``+pi/(1 - p)``. The financial layer: its inflow arrives
    by routes after its own spending and all its claims leave by spending, so it
    holds its inflow over its out-rate; its share's elasticity to its propensity
    is ``-(1 - pi)`` and every other class's ``+pi``. The same two numbers are
    printed for the intermediate block, where every payer sits. Before it
    spends, each payer pays its share of the marginal bill, which follows the
    layer-two spending its own spending is part of, and a short payer passes its
    marginal claims to the earners; both leave the block before the spending
    step. Its gaps are also taken with the bill slope at zero, with the pass-on
    removed, and with both."""
    reading = {(r["seed"], r["wall"]): r for r in carriers}
    deriv = {(r["seed"], r["wall"], r["lever"]): r for r in d_rows}
    ablated = {(r["seed"], r["wall"], r["map"]): r for r in m3_rows}
    rows = []
    for p in defaults:
        earners = (p.labels == "earners") & p.alive
        rates = spend_rates(p, p.pbar)[earners]
        values = np.unique(rates)
        rate = float(values[0]) if values.size == 1 else float("nan")
        split = reading[(p.seed, p.wall)]
        households = deriv.get((p.seed, p.wall, "propensity, households"))
        financial = deriv.get((p.seed, p.wall, "propensity, financial layer"))
        intermediate = deriv.get((p.seed, p.wall, "propensity, intermediate block"))
        row = {"seed": p.seed, "wall": p.wall,
               "payer_classes": "/".join(sorted({str(c) for c in p.labels[p.payers]})),
               "earner_rate": rate, "earners_not_spending": int((rates == 0.0).sum()),
               "routes_into_earners": float(routes_of(p)[:, earners].sum()),
               "closed": -1.0 / (1.0 - rate),
               "closed_with_share": -(1.0 - split["pi_earners"]) / (1.0 - rate),
               "measured": households["elasticity_earners"] if households else float("nan")}
        nan = float("nan")
        row["gap_households_own"] = row["measured"] - row["closed_with_share"]
        row["gap_households_others"] = (
            _others_gap(households, "earners", split["pi_earners"] / (1.0 - rate))
            if households else nan)
        for key, lever, own in (("financial", financial, "l1"),
                                ("intermediate", intermediate, "mid")):
            share = split[f"pi_{own}"]
            row[f"gap_{key}_own"] = (lever[f"elasticity_{own}"] + (1.0 - share)
                                     if lever else nan)
            row[f"gap_{key}_others"] = _others_gap(lever, own, share) if lever else nan
        for label in ("no_bill", "no_pass_on", "neither"):
            r = ablated[(p.seed, p.wall, f"M3 {label}")]
            row[f"gap_intermediate_own_{label}"] = r["elasticity_mid"] + (1.0 - r["pi_mid"])
            row[f"gap_intermediate_others_{label}"] = _others_gap(r, "mid", r["pi_mid"])
        rows.append(row)
    return rows


def run_all(seeds) -> dict:
    t0 = time.time()

    def tick(what: str) -> None:
        print(f"  {what} ({time.time() - t0:.0f} s)", flush=True)

    defaults = default_parts(seeds)
    variants = variant_parts(seeds)
    tick(f"{len(defaults)} default and {len(variants)} variant carriers")
    rebuild = [rebuild_row(p) for p in defaults + variants]
    tick(f"A45-0 on {len(rebuild)} carriers")
    d_rows, c_rows, f_rows = run_check(seeds, parts=defaults)
    tick(f"A45-1 and A45-3 on {len(d_rows)} pairs, A45-2 on {len(c_rows)} maps")
    carriers, chains = [], []
    for p in defaults:
        row, chain = field_reading(p, "carrier")
        carriers.append(row)
        chains.append(chain)
    sweeps = sweep_rows(defaults)
    tick(f"M1a on {len(carriers)} carriers, M1b and M1c on {len(sweeps)} sweep points")
    check_carriers, check_horizons = check_rows(seeds, tick)
    by_seed = {p.seed: p for p in defaults if p.wall == 0.0}
    by_variant = {(p.variant, p.seed): p for p in variants}
    predictions = variant_rows(by_seed, by_variant, d_rows, load_a44_record())
    m3_d, m3_c = ablation_checks(defaults)
    closed = holding_time_rows(defaults, carriers, d_rows, m3_d)
    tick(f"M2b on {len(predictions)} variant carriers, M3 on {len(closed)} carriers")
    return {"seeds": list(seeds), "rebuild": rebuild, "derivative": d_rows,
            "chain_checks": c_rows, "footprint": f_rows, "carriers": carriers,
            "chains": chains, "sweeps": sweeps, "outrate_pairs": outrate_pairs(sweeps),
            "check_carriers": check_carriers, "check_horizons": check_horizons,
            "variants": predictions, "holding_time": closed,
            "holding_time_derivative": m3_d, "holding_time_chains": m3_c}

# --------------------------------------------------------------------------
# printing the readings


def _finite(vals) -> list[float]:
    return [float(v) for v in vals if v is not None and math.isfinite(v)]


def _med(vals) -> float:
    vals = _finite(vals)
    return statistics.median(vals) if vals else float("nan")


def _rng(vals, spec: str) -> str:
    vals = _finite(vals)
    if not vals:
        return "-"
    return (f"{format(statistics.median(vals), spec)} "
            f"[{format(min(vals), spec)}, {format(max(vals), spec)}]")


def _apart(r: dict) -> bool:
    rounds = r["chain_rounds"]
    return (math.isfinite(rounds) and rounds > 0.0
            and abs(r["k_l1"] - rounds) > MIXING_GAP * rounds)


def print_entry(out: dict) -> None:
    carriers, sweeps = out["carriers"], out["sweeps"]
    print("\nM1a  entry term K on the default carriers: full map / class chain / node "
          "reading, for l1, mid, earners | full map's second modulus, chain's second "
          "eigenvalue, its summed rounds | pi l1/mid/earners")
    for r in carriers:
        print(f"  seed {r['seed']} wall {r['wall']:.2f}  "
              + "  ".join(f"{c} {r[f'k_{c}']:.3f}/{r[f'k_chain_{c}']:.3f}/"
                          f"{r[f'k_node_{c}']:.3f}" for c in HOME_CLASSES)
              + f" | {r['second_modulus']:.4f} {r['chain_second']:.4f} "
                f"{r['chain_rounds']:.3f} | "
              + "/".join(f"{r[f'pi_{c}']:.4f}" for c in HOME_CLASSES))

    print("\nM1b  sweeps without a floor, median [range] over seeds: value | K_l1 full | "
          "K_l1 chain | K_l1 node | chain rounds | full second modulus / chain second | "
          "pi_l1 | K mid / earners")
    for family, key, reverse in (("coupling", "coupling_scale", True),
                                 ("financial within", "within_scale", False),
                                 ("financial propensity", "propensity", False)):
        print(f"  {family}")
        fam = [r for r in sweeps if r["family"] == family]
        for value in sorted({r[key] for r in fam}, reverse=reverse):
            rs = [r for r in fam if r[key] == value]
            print(f"    {value:<5g} | {_rng([r['k_l1'] for r in rs], '.3f')} | "
                  f"{_rng([r['k_chain_l1'] for r in rs], '.3f')} | "
                  f"{_med([r['k_node_l1'] for r in rs]):.3f} | "
                  f"{_rng([r['chain_rounds'] for r in rs], '.3f')} | "
                  f"{_med([r['second_modulus'] for r in rs]):.4f} / "
                  f"{_med([r['chain_second'] for r in rs]):.4f} | "
                  f"{_rng([r['pi_l1'] for r in rs], '.4f')} | "
                  f"{_med([r['k_mid'] for r in rs]):.3f} / "
                  f"{_med([r['k_earners'] for r in rs]):.3f}")
    points = {}
    for r in sweeps:
        if r["family"] != "grid":
            points.setdefault(r["map"], []).append(r)
    on_medians = []
    for label, rs in points.items():
        k, rounds = _med([r["k_l1"] for r in rs]), _med([r["chain_rounds"] for r in rs])
        if abs(k - rounds) > MIXING_GAP * rounds:
            on_medians.append((label, k, rounds))
    maps = sweeps + carriers
    apart = [r for r in maps if _apart(r)]
    print(f"  K_l1 and the chain's summed rounds further apart than {MIXING_GAP:.0%} of the "
          f"rounds: {len(on_medians)} of {len(points)} sweep points on seed medians; "
          f"{len(apart)} of {len(maps)} maps seed by seed (sweeps, grid and default "
          f"carriers)")
    for label, k, rounds in on_medians:
        print(f"    median {label}: K_l1 {k:.3f}, rounds {rounds:.3f}")
    for r in apart[:8]:
        print(f"    {_label(r)}: K_l1 {r['k_l1']:.3f}, rounds {r['chain_rounds']:.3f}")
    if len(apart) > 8:
        print(f"    and {len(apart) - 8} more")

    grid = [r for r in sweeps if r["family"] == "grid"]
    cells = {}
    for r in grid:
        cells.setdefault((r["propensity"], r["within_scale"]), []).append(r)
    table = sorted(((p, w, _med([r["outrate_l1"] for r in rs]),
                     _med([r["pi_l1"] for r in rs]), _med([r["k_l1"] for r in rs]),
                     _med([r["k_mid"] for r in rs]))
                    for (p, w), rs in cells.items()), key=lambda t: t[2])
    print("\nM1c  out-rate grid, medians over seeds, by out-rate: financial propensity, "
          "within scale | a_l1 | pi_l1 | K_l1 | K_mid")
    for p, w, a, share, k1, km in table:
        print(f"  {p:<4g} x{w:<4g} | {a:.4f} | {share:.4f} | {k1:.3f} | {km:.3f}")
    print(f"  pairs on the medians, out-rates within {PAIR_TOLERANCE:.0%} and "
          f"propensities different:")
    for i, a in enumerate(table):
        for b in table[i + 1:]:
            if a[0] != b[0] and abs(a[2] - b[2]) < PAIR_TOLERANCE * min(a[2], b[2]):
                print(f"    ({a[0]:g}, x{a[1]:g}) a {a[2]:.4f} pi {a[3]:.4f} K {a[4]:.3f}"
                      f"   ({b[0]:g}, x{b[1]:g}) a {b[2]:.4f} pi {b[3]:.4f} K {b[4]:.3f}")
    pairs = out["outrate_pairs"]
    if pairs:
        print(f"  seed by seed: {len(pairs)} pairs; largest pi_l1 difference "
              f"{max(abs(q['pi_a'] - q['pi_b']) for q in pairs):.4f}, largest K_l1 "
              f"difference {max(abs(q['k_a'] - q['k_b']) for q in pairs):.3f}")
    else:
        print("  seed by seed: no pairs")


def print_check_carriers(out: dict) -> None:
    print("\nM1d  whole model against the mean field. Per carrier: the default map's K, "
          "chain rounds and pi, medians over seeds. Per horizon T: T x entry term, whole "
          "model / mean field with its tail / K on that horizon's map; the whole model's "
          "l1 share, median over the three injections, against pi_l1")
    for name, _ in CHECK_CARRIERS:
        cr = [r for r in out["check_carriers"] if r["carrier"] == name]
        if not cr:
            continue
        print(f"  {name}: K " + "/".join(f"{_med([r[f'k_{c}'] for r in cr]):.3f}"
                                         for c in HOME_CLASSES)
              + f", chain rounds {_med([r['chain_rounds'] for r in cr]):.3f}, pi "
              + "/".join(f"{_med([r[f'pi_{c}'] for r in cr]):.4f}" for c in HOME_CLASSES))
        hrs = [r for r in out["check_horizons"] if r["carrier"] == name]
        for horizon in HORIZONS:
            hr = [r for r in hrs if r["horizon"] == horizon]
            print(f"    T {horizon:3d}: " + "  ".join(
                f"{c} {_med([r[f'model_entry_{c}'] for r in hr]):.3f}/"
                f"{_med([r[f'field_entry_{c}'] for r in hr]):.3f}/"
                f"{_med([r[f'k_{c}'] for r in hr]):.3f}" for c in HOME_CLASSES)
                + f"   l1 share "
                  f"{_med([_med([r[f'model_{t}_l1'] for t in HOME_CLASSES]) for r in hr]):.4f}"
                  f" against pi {_med([r['pi_l1'] for r in hr]):.4f}")
        print("    largest whole model minus mean field, T x entry term, over seeds and "
              "horizons: " + "  ".join(
                  f"{c} {max(abs(r[f'model_entry_{c}'] - r[f'field_entry_{c}']) for r in hrs):.3f}"
                  for c in HOME_CLASSES))


def print_levers(out: dict) -> None:
    d_rows = out["derivative"]
    print("\nM2a  elasticity of each home class's stationary share to each lever, "
          "theta/pi dpi/dtheta, median [range] over the default carriers, by the "
          "earners' magnitude")
    levers = sorted({r["lever"] for r in d_rows},
                    key=lambda lv: -abs(_med([r["elasticity_earners"] for r in d_rows
                                              if r["lever"] == lv])))
    for lever in levers:
        rs = [r for r in d_rows if r["lever"] == lever]
        print(f"  {lever:38s} " + "  ".join(
            f"{c} {_rng([r[f'elasticity_{c}'] for r in rs], '+.3f')}" for c in HOME_CLASSES))

    print("\nM2b  A44's variants, medians over seeds, l1 / earners: default | first order | "
          "default map, levers moved | plus the variant's control run | the variant's "
          "own map")
    for name, _ in VARIANT_LEVERS:
        rs = [r for r in out["variants"] if r["variant"] == name]
        if not rs:
            continue
        print(f"  {name:36s} " + " | ".join(
            f"{_med([r[f'{k}_l1'] for r in rs]):.4f}/{_med([r[f'{k}_earners'] for r in rs]):.4f}"
            for k in ("base", "first", "exact", "path", "own")))
        steps = "; ".join(
            f"{c} linearization {_med([r[f'first_{c}'] - r[f'exact_{c}'] for r in rs]):+.4f}, "
            f"control run {_med([r[f'exact_{c}'] - r[f'path_{c}'] for r in rs]):+.4f}, "
            f"graph {_med([r[f'path_{c}'] - r[f'own_{c}'] for r in rs]):+.4f}"
            for c in ("l1", "earners"))
        print(f"  {'':36s} {steps}")
        print(f"  {'':36s} graph same {sorted({r['graph_same'] for r in rs})}, nodes same "
              f"{sorted({r['nodes_same'] for r in rs})}, propensities match "
              f"{sorted({r['propensities_match'] for r in rs})}, payers whose short share "
              f"changed {_rng([r['short_payers_changed'] for r in rs], 'g')}, own map "
              f"matches A44's record {sorted({str(r['own_matches_a44_record']) for r in rs})}")


def print_chains(out: dict) -> None:
    chains = out["chains"]
    first = next((ch for ch in chains if ch["wall"] == 0.0), None)
    if first is not None:
        print(f"\nM3  class chain, seed {first['seed']} wall 0 (column: from, row: to)")
        names = first["classes"]
        print("    " + " ".join(f"{name[:9]:>10s}" for name in names))
        for i, name in enumerate(names):
            print(f"    {name[:9]:>9s} " + " ".join(f"{x:10.6f}" for x in first["matrix"][i]))
    rows = out["holding_time"]
    print("\n    earners: rate p | routes into earners | -1/(1-p) | -(1-pi)/(1-p) | "
          "measured elasticity to the households' propensity, median [range] over the "
          "default carriers")
    print(f"    {_rng([r['earner_rate'] for r in rows], '.4f')} | "
          f"{max((r['routes_into_earners'] for r in rows), default=float('nan')):.3g} | "
          f"{_rng([r['closed'] for r in rows], '+.3f')} | "
          f"{_rng([r['closed_with_share'] for r in rows], '+.3f')} | "
          f"{_rng([r['measured'] for r in rows], '+.3f')}; earners not spending "
          f"{sum(r['earners_not_spending'] for r in rows)}")
    print("    each propensity lever against the holding-time form, largest gap over the "
          "default carriers, own share | other classes' shares: payers in "
          f"{sorted({r['payer_classes'] for r in rows})}")
    for key, form in (("households", "-(1-pi)/(1-p) | +pi/(1-p)"),
                      ("financial", "-(1-pi) | +pi"),
                      ("intermediate", "-(1-pi) | +pi"),
                      ("intermediate_own_no_bill", "bill slope at zero"),
                      ("intermediate_own_no_pass_on", "pass-on removed"),
                      ("intermediate_own_neither", "both")):
        if key.startswith("intermediate_own_"):
            label = key[len("intermediate_own_"):]
            own = _finite([abs(r[f"gap_intermediate_own_{label}"]) for r in rows])
            others = _finite([r[f"gap_intermediate_others_{label}"] for r in rows])
            key = f"  {label}"
        else:
            own = _finite([abs(r[f"gap_{key}_own"]) for r in rows])
            others = _finite([r[f"gap_{key}_others"] for r in rows])
        print(f"      {key:13s} {form:28s} "
              f"{max(own, default=float('nan')):.2e} | {max(others, default=float('nan')):.2e}")


def print_readouts(out: dict) -> None:
    print_entry(out)
    print_check_carriers(out)
    print_levers(out)
    print_chains(out)

# --------------------------------------------------------------------------
# the record


RECORD = RESULTS / "a45_duration_levers.json"

#: Whether the readings are written into RESULTS.md. While they are not, the
#: record carries ``diagnostic_only`` and a reason; once they are, neither.
CLOSED = True

#: Fixed decimal places by kind of number, an absolute grid, so that no digit
#: from below a build's rounding reaches the record. Splits, shares and entry
#: terms are solved directly and get ten. Eigenvalue moduli come from a general
#: eigensolver, where a close pair can move in the ninth place, and get eight.
#: Derivatives carry the central difference's rounding, a few parts in a
#: billion (A45-1's floor), and get six; elasticities divide them by shares as
#: small as 0.002 and get four.
DECIMALS = 10
EIGEN_DECIMALS = 8
DERIVATIVE_DECIMALS = 6
ELASTICITY_DECIMALS = 4
PLACES_BY_PREFIX = (
    ("second_modulus", EIGEN_DECIMALS),
    ("chain_second", EIGEN_DECIMALS),
    ("chain_rounds", EIGEN_DECIMALS),
    ("dpi_", DERIVATIVE_DECIMALS),
    ("first_", DERIVATIVE_DECIMALS),
    ("elasticity_", ELASTICITY_DECIMALS),
    ("measured", ELASTICITY_DECIMALS),
    ("gap_", DERIVATIVE_DECIMALS),
)


def _clip(x, decimals: int = DECIMALS):
    if x is None or isinstance(x, str):
        return x
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    x = float(x)
    if not math.isfinite(x):
        return None
    y = round(x, decimals)
    return 0.0 if y == 0.0 else y


def record_row(r: dict, drop=()) -> dict:
    out = {}
    for key, value in r.items():
        if key in drop:
            continue
        places = next((d for prefix, d in PLACES_BY_PREFIX if key.startswith(prefix)),
                      DECIMALS)
        out[key] = _clip(value, places)
    return out


def record_within(r: dict, key: str, tol: float) -> dict:
    """A residue within its tolerance is written as the tolerance it was held to;
    outside it, as the value."""
    return {f"{key}_at_most": tol} if r[key] <= tol else {key: float(f"{r[key]:.3e}")}


def record_config(seeds) -> dict:
    return {
        "carrier": "a17_edge_cut.base_config",
        "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
        "subsistence": {"mode": "exit", "grace": 1, "needs": list(WALLS)},
        "open_from": OPEN_FROM, "seeds": list(seeds),
        "mean_field": ("A44's: propensity at the midpoint of each band; each payer "
                       "short in the share of rounds from open_from with the "
                       "control's holding below its share of the bill; the "
                       "control's closing membership; issuance response zero. "
                       "Rebuilt here from its parts (A45-0)"),
        "levers": [[name, kind, list(arg) if isinstance(arg, tuple) else arg]
                   for name, kind, arg in LEVERS],
        "lever_step": LEVER_STEP, "footprint_step": FOOTPRINT_STEP,
        "tolerances": {"derivative": TOL_DERIVATIVE, "chain": TOL_CHAIN},
        "pass_on": "multiplies the short shares of payers still trading",
        "edge_lever": "multiplies the weight of edges from the source class to the "
                      "destination class, routes renormalized per source node",
        "entry_term": ("K_c = (D v_c)_c - median over the other two home classes o "
                       "of (D v_o)_c; v_t one claim spread evenly over t's trading "
                       "nodes; D = (B - P) Z, P = pi ell', ell one on trading nodes "
                       "and zero on the spending state"),
        "comparison_set": list(HOME_CLASSES),
        "node_reading": "(1 - p_c) / p_c, p_c the class's propensity",
        "class_chain": ("classes and the spending state; each class's nodes weighted "
                        "by stationary mass, by node count where the class has none"),
        "chain_rounds": "lambda / (1 - lambda), lambda the chain's second largest modulus",
        "out_rate": ("a_c = sum over c's nodes of stationary mass times spend rate "
                     "times the share of routes leaving c, over c's mass"),
        "sweeps": {"coupling_scales": list(COUPLING_SCALES),
                   "coupling_edges": [list(e) for e in COUPLING_EDGES],
                   "within_scales": list(WITHIN_SCALES),
                   "financial_propensities": list(FINANCIAL_PROPENSITIES),
                   "grid_propensities": list(GRID_PROPENSITIES),
                   "grid_within_scales": list(GRID_WITHIN)},
        "pair_tolerance": PAIR_TOLERANCE, "mixing_gap": MIXING_GAP,
        "check_carriers": {name: resolved_changes(changes)
                           for name, changes in CHECK_CARRIERS},
        "horizons": list(HORIZONS), "check_amount": CHECK_AMOUNT,
        "check_map": "each horizon T opens at ROUNDS - T and its map takes the "
                     "payers' short shares from that round on",
        "variant_levers": {name: {"moves": [[lever, _clip(value)] for lever, value in moves],
                                  "changes": resolved_changes(dict(VARIANTS)[name]),
                                  "edge_ratio": _edge_ratio(dict(VARIANTS)[name])}
                           for name, moves in VARIANT_LEVERS},
        "a44_record": A44_RECORD.name, "record_agreement": RECORD_AGREEMENT,
        "stationary_rounding_floor": ROUNDING_FLOOR,
        "decimals": {"default": DECIMALS, "eigen": EIGEN_DECIMALS,
                     "derivative": DERIVATIVE_DECIMALS, "elasticity": ELASTICITY_DECIMALS},
    }


def _edge_ratio(changes: dict):
    """The variant's edge count over the default's, for a variant that changes one."""
    base = base_config(SEEDS[0], need=0.0).spec
    for key, value in changes.items():
        head, attr = key.split(".")
        if head == "spec":
            return _clip(value / getattr(base, attr))
    return None


def chain_record(r: dict) -> dict:
    keys = ("conserve_err", "identity_err", "mass_err", "stationary_err")
    out = record_row(r, drop=keys)
    for key in keys:
        out |= record_within(r, key, TOL_CHAIN)
    return out


def build_record(out: dict, crit: list[dict]) -> dict:
    rec = {
        "stage": "A45",
        "config": record_config(out["seeds"]),
        "criteria": crit,
        "rebuild": [{"seed": r["seed"], "wall": _clip(r["wall"]), "variant": r["variant"],
                     "equal": r["equal"], "capped_payers": r["capped_payers"]}
                    for r in out["rebuild"]],
        "derivative": [record_row(r, drop=("diff",))
                       | record_within(r, "diff", TOL_DERIVATIVE)
                       for r in out["derivative"]],
        "footprint": [record_row(r) for r in out["footprint"]],
        "chain_checks": [chain_record(r) for r in out["chain_checks"]],
        "holding_time_checks": {
            "derivative": [record_row(r, drop=("diff",))
                           | record_within(r, "diff", TOL_DERIVATIVE)
                           for r in out["holding_time_derivative"]],
            "chains": [chain_record(r) for r in out["holding_time_chains"]]},
        "carriers": [record_row(r) for r in out["carriers"]],
        "chains": [{"seed": ch["seed"], "wall": _clip(ch["wall"]), "classes": ch["classes"],
                    "matrix": [[_clip(x) for x in row] for row in ch["matrix"]]}
                   for ch in out["chains"]],
        "sweeps": [record_row(r) for r in out["sweeps"]],
        "outrate_pairs": [record_row(r) for r in out["outrate_pairs"]],
        "check_carriers": [record_row(r) for r in out["check_carriers"]],
        "check_horizons": [record_row(r) for r in out["check_horizons"]],
        "variants": [record_row(r) for r in out["variants"]],
        "holding_time": [record_row(r) for r in out["holding_time"]],
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the readings are not yet "
                                    "written into RESULTS.md.")
    return rec


def write_record(out: dict, crit: list[dict], path: Path | None = None) -> None:
    path = RECORD if path is None else path
    text = json.dumps(build_record(out, crit), indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"\nwrote {path.name}")


# --------------------------------------------------------------------------
# the seeded faults


class _ReceiverSplitByPayers(FieldBuilder):
    """Seeded fault: what a short payer passes on is divided by the payers' count."""

    planted = False

    def _receiver_share(self, parts, capped):
        type(self).planted = True
        return capped / parts.payers.size


class _SpendingRowSkipsWages(FieldBuilder):
    """Seeded fault: the spending state reads spending before the wage step."""

    planted = False

    def _spending_row(self, spend_l2, wage_step):
        type(self).planted = True
        return spend_l2.copy()


class _PassOnMovesDepartedPayers(FieldBuilder):
    """Seeded fault: the pass-on strength also scales the short shares of payers
    that have left the market. This is how the lever was first written, and
    A45-1 caught it on the three carriers where a departed payer is short. M3's
    pass-on map first carried the same fault through its own copy of the
    shares, outside the maps A45-1 ran on; it now takes them from the builder,
    and its maps are checked (selftest_ablation)."""

    planted = False

    def _short_shares(self, parts, kappa):
        type(self).planted = True
        return parts.capped * kappa


class _PseudoInverse(Derivative):
    """Seeded fault: the pseudo-inverse of I - B in place of the fundamental
    matrix with its projector."""

    planted = False

    def _fundamental(self, block, pi, ell):
        type(self).planted = True
        return np.linalg.pinv(np.eye(block.shape[0]) - block)


class _Transposed(Derivative):
    """Seeded fault: the formula applied to the transposed map."""

    planted = False

    def _apply(self, fundamental, d_block, pi):
        type(self).planted = True
        return fundamental.T @ d_block.T @ pi


class _NoSpendingState(Derivative):
    """Seeded fault: the derivative of the map without its spending state's row and column."""

    planted = False
    moved = 0

    def _rate(self, d_block):
        type(self).planted = True
        type(self).moved += int(np.abs(d_block[-1, :]).max() > 0.0
                                or np.abs(d_block[:, -1]).max() > 0.0)
        out = d_block.copy()
        out[-1, :] = 0.0
        out[:, -1] = 0.0
        return out


class _NodeCountWeights(ClassChain):
    """Seeded fault: a class's nodes weighted equally rather than by stationary mass."""

    planted = False

    def _weights(self, pi_class):
        type(self).planted = True
        return np.full(pi_class.size, 1.0 / pi_class.size)


class _SummedMassTest(ClassChain):
    """Seeded fault: a class counts as massless when its summed mass is below
    1e-15, so the rounding of seventy-five nodes that nothing flows into passes
    as mass and weights their column."""

    planted = False

    def _weights(self, pi_class):
        total = float(pi_class.sum())
        if abs(total) < 1e-15:
            return np.full(pi_class.size, 1.0 / pi_class.size)
        if float(floored(pi_class).sum()) == 0.0:
            type(self).planted = True
        return pi_class / total


def massless_column_gap(parts: list[Parts], chain_class=ClassChain) -> tuple[int, float]:
    """The declared rule for a class with no mass above the floor: its chain
    column is its nodes' columns weighted by node count. Returns how many such
    classes the carriers have and the largest difference from that column."""
    count, gap = 0, 0.0
    for p in parts:
        block = FieldBuilder().block(p)
        pi = stationary(block, mass_functional(p))
        names, chain, groups = chain_class().build(p, block, pi)
        for d, cols in enumerate(groups[:-1]):
            if float(floored(pi[cols]).sum()) != 0.0:
                continue
            count += 1
            column = block[:, cols] @ np.full(cols.size, 1.0 / cols.size)
            expected = np.array([column[rows].sum() for rows in groups])
            gap = max(gap, float(np.abs(chain[:, d] - expected).max()))
    return count, gap


def _mass_with_spending_state(parts: Parts) -> np.ndarray:
    """Seeded fault: the unit-mass condition counts the spending state as claims."""
    return np.ones(parts.live.size)


def selftest_gate() -> bool:
    ok = []
    parts = default_parts((0, 1))
    clean = criterion_rebuild([rebuild_row(p) for p in parts])
    ok.append(clean["passed"])
    print(f"A45-0 clean on {len(parts)} carriers: passes {clean['passed']}")
    short = sum(p.capped.size and int((p.capped > 0.0).sum()) for p in parts)
    for label, fault in (("pass-on split by payers", _ReceiverSplitByPayers),
                         ("spending state before wages", _SpendingRowSkipsWages)):
        fault.planted = False
        got = criterion_rebuild([rebuild_row(p, fault()) for p in parts])
        planted = fault.planted and short > 0
        ok.append(planted and not got["passed"])
        print(f"  {label:32s} planted {planted} ({short} short payers across the "
              f"carriers)   A45-0 passed={got['passed']} (want False)")
    got = criterion_rebuild([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no carriers at all               Void and not passed: {ok[-1]}")
    return all(ok)


def selftest_derivative() -> bool:
    ok = []
    parts = [p for p in default_parts((0, 1)) if p.wall in (0.0, 0.06)]
    clean = [r for p in parts for r in derivative_rows(p)]
    got = criterion_derivative(clean)
    ok.append(got["passed"])
    print(f"A45-1 clean on {len(clean)} pairs: passes {got['passed']}, largest "
          f"difference {max(r['diff'] for r in clean):.2e}")

    singular = min(float(np.linalg.svd(np.eye(b.shape[0]) - b, compute_uv=False)[-1])
                   for b in (FieldBuilder().block(p) for p in parts))
    asymmetric = max(float(np.abs(b - b.T).max())
                     for b in (FieldBuilder().block(p) for p in parts))
    faults = []
    _PseudoInverse.planted = False
    rows = [r for p in parts for r in derivative_rows(p, derivative=_PseudoInverse())]
    faults.append(("pseudo-inverse for Z", _PseudoInverse.planted and singular < 1e-9,
                   f"smallest singular value of I - B {singular:.1e}", rows))
    _Transposed.planted = False
    rows = [r for p in parts for r in derivative_rows(p, derivative=_Transposed())]
    faults.append(("transposed map", _Transposed.planted and asymmetric > 1e-6,
                   f"largest asymmetry {asymmetric:.2f}", rows))
    _NoSpendingState.planted, _NoSpendingState.moved = False, 0
    rows = [r for p in parts for r in derivative_rows(p, derivative=_NoSpendingState())]
    faults.append(("spending state dropped", _NoSpendingState.planted
                   and _NoSpendingState.moved > 0,
                   f"{_NoSpendingState.moved} lever-carrier pairs move that row or column",
                   rows))
    departed = [p for p in default_parts((2, 4))
                if p.wall > 0.0 and bool(((~p.alive[p.payers]) & (p.capped > 0.0)).any())]
    _PassOnMovesDepartedPayers.planted = False
    passon = [lv for lv in LEVERS if lv[1] == "passon"]
    rows = [r for p in departed
            for r in derivative_rows(p, builder=_PassOnMovesDepartedPayers(), levers=passon)]
    faults.append(("pass-on moves departed payers", _PassOnMovesDepartedPayers.planted
                   and bool(departed),
                   f"{len(departed)} carriers with a short payer that has left", rows))
    for label, planted, note, rows in faults:
        got = criterion_derivative(rows)
        worst = max((r["diff"] for r in rows), default=float("nan"))
        ok.append(planted and not got["passed"])
        print(f"  {label:30s} planted {planted} ({note})   A45-1 passed="
              f"{got['passed']} (want False), largest difference {worst:.2e}")
    got = criterion_derivative([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no levers at all           Void and not passed: {ok[-1]}")
    return all(ok)


def _swapped_edge_kwargs(parts: Parts, lever: tuple, theta: float) -> dict:
    """Seeded fault: an edge lever's mask built with source and destination swapped."""
    _swapped_edge_kwargs.planted = True
    _, kind, arg = lever
    if kind == "edge":
        return lever_kwargs(parts, (lever[0], kind, (arg[1], arg[0])), theta)
    return lever_kwargs(parts, lever, theta)


_swapped_edge_kwargs.planted = False


def _all_sources_kwargs(parts: Parts, lever: tuple, theta: float) -> dict:
    """Seeded fault: an edge lever reweights the edges into its destination class
    from every source, so the named routes move the right way and others move too."""
    _all_sources_kwargs.planted = True
    _, kind, arg = lever
    if kind != "edge":
        return lever_kwargs(parts, lever, theta)
    weights = np.ones((parts.n, parts.n))
    weights[:, group_mask(parts, arg[1])] = theta
    return {"weights": weights}


_all_sources_kwargs.planted = False


def selftest_footprint() -> bool:
    ok = []
    parts = [p for p in default_parts((0, 4)) if p.wall in (0.0, 0.03)]
    clean = [footprint_row(p, lever) for p in parts for lever in LEVERS]
    got = criterion_footprint(clean)
    ok.append(got["passed"])
    print(f"A45-3 clean on {len(clean)} pairs: passes {got['passed']}")
    crossing = sum(1 for lv in LEVERS if lv[1] == "edge" and lv[2][0] != lv[2][1])
    _swapped_edge_kwargs.planted = False
    rows = [footprint_row(p, lever, kwargs_of=_swapped_edge_kwargs)
            for p in parts for lever in LEVERS]
    got = criterion_footprint(rows)
    planted = _swapped_edge_kwargs.planted and crossing > 0
    failing = sorted({r["lever"] for r in rows if not (r["moved"] and r["inside"] and r["direction"])})
    ok.append(planted and not got["passed"] and len(failing) == crossing)
    print(f"  edge mask swapped          planted {planted} ({crossing} levers cross "
          f"classes)   A45-3 passed={got['passed']} (want False), levers caught "
          f"{len(failing)} of {crossing}")
    _all_sources_kwargs.planted = False
    rows = [footprint_row(p, lever, kwargs_of=_all_sources_kwargs)
            for p in parts for lever in LEVERS]
    got = criterion_footprint(rows)
    outside = sorted({r["lever"] for r in rows if not r["inside"]})
    planted = _all_sources_kwargs.planted
    ok.append(planted and not got["passed"] and bool(outside)
              and all(r["moved"] and r["direction"] for r in rows))
    print(f"  edges from every source    planted {planted}   A45-3 passed="
          f"{got['passed']} (want False), levers failing only on the inside clause "
          f"{len(outside)}")
    got = criterion_footprint([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no levers at all           Void and not passed: {ok[-1]}")
    return all(ok)


def selftest_chain() -> bool:
    ok = []
    parts = default_parts((0, 1))
    clean = [chain_row(p, "carrier") for p in parts]
    got = criterion_chain(clean)
    ok.append(got["passed"])
    print(f"A45-2 clean on {len(clean)} carriers: passes {got['passed']}")
    spread = 0.0
    for p in parts:
        pi = stationary(FieldBuilder().block(p), mass_functional(p))
        for grp in block_positions(p).values():
            masses = floored(pi[grp])
            if grp.size > 1 and float(masses.sum()) != 0.0:
                spread = max(spread, float(masses.max() - masses.min()))
    _NodeCountWeights.planted = False
    rows = [chain_row(p, "carrier", chain_class=_NodeCountWeights) for p in parts]
    got = criterion_chain(rows)
    planted = _NodeCountWeights.planted and spread > 0.0
    ok.append(planted and not got["passed"])
    print(f"  node-count weights         planted {planted} (largest spread of "
          f"stationary mass inside a class {spread:.2e})   A45-2 passed="
          f"{got['passed']} (want False), largest identity error "
          f"{max(r['identity_err'] for r in rows):.2e}")
    spending_mass = min(float(stationary(FieldBuilder().block(p), mass_functional(p))[-1])
                        for p in parts)
    rows = [chain_row(p, "carrier", functional=_mass_with_spending_state) for p in parts]
    got = criterion_chain(rows)
    planted = spending_mass > 0.0
    ok.append(planted and not got["passed"])
    print(f"  spending state counted as mass planted {planted} (smallest stationary "
          f"spending state {spending_mass:.3f})   A45-2 passed={got['passed']} "
          f"(want False), largest mass error {max(r['mass_err'] for r in rows):.2e}")
    count, gap = massless_column_gap(parts)
    ok.append(count > 0 and gap <= TOL_CHAIN)
    print(f"  massless classes weighted by node count: {count} classes, largest "
          f"difference from the node-count column {gap:.2e}")
    _SummedMassTest.planted = False
    count, gap = massless_column_gap(parts, chain_class=_SummedMassTest)
    ok.append(_SummedMassTest.planted and gap > TOL_CHAIN)
    print(f"  massless test on the summed mass planted {_SummedMassTest.planted}   "
          f"largest difference from the node-count column {gap:.2e} (want above "
          f"{TOL_CHAIN:.0e})")
    got = criterion_chain([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no maps at all             Void and not passed: {ok[-1]}")
    return all(ok)


def selftest_ablation() -> bool:
    """M3's maps on the carriers where a payer that has left is short. Seeded
    fault: the pass-on removed from every payer, departed ones too, which is how
    M3 first removed it; A45-1 and A45-2 must catch it on the pass-on map, and
    only there, since with the bill slope at zero a departed payer's share
    reaches nothing in the block."""
    ok = []
    departed = [p for p in default_parts((2, 4))
                if p.wall > 0.0 and bool(((~p.alive[p.payers]) & (p.capped > 0.0)).any())]
    d, c = ablation_checks(departed)
    got = [criterion_derivative(d), criterion_chain(c)]
    ok.append(bool(departed) and all(g["passed"] for g in got))
    print(f"M3 clean on {len(departed)} carriers with a short payer that has left: "
          f"A45-1 {got[0]['passed']}, A45-2 {got[1]['passed']}, largest derivative "
          f"difference {max(r['diff'] for r in d):.2e}, largest stationary residue "
          f"{max(r['stationary_err'] for r in c):.2e}")
    _PassOnMovesDepartedPayers.planted = False
    d, c = ablation_checks(departed, builder=_PassOnMovesDepartedPayers())
    got = [criterion_derivative(d), criterion_chain(c)]
    caught_d = {r["map"] for r in d if not r["diff"] <= TOL_DERIVATIVE}
    caught_c = {r["map"] for r in c
                if not (r["conserve_err"] <= TOL_CHAIN and r["stationary_err"] <= TOL_CHAIN)}
    planted = _PassOnMovesDepartedPayers.planted and bool(departed)
    ok.append(planted and not any(g["passed"] for g in got)
              and caught_d == caught_c == {"M3 no_pass_on"})
    print(f"  pass-on removed from departed payers planted {planted}   A45-1 passed="
          f"{got[0]['passed']}, A45-2 passed={got[1]['passed']} (want False, False), "
          f"maps caught {sorted(caught_d)} | {sorted(caught_c)}, largest conservation "
          f"error {max(r['conserve_err'] for r in c):.2e}")
    return all(ok)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true", help="A45-0")
    ap.add_argument("--selftest", action="store_true",
                    help="seeded faults the criteria must catch")
    ap.add_argument("--check", action="store_true",
                    help="A45-1, A45-2 and A45-3, nothing written")
    ap.add_argument("--run", action="store_true",
                    help="A45-0 to A45-3 and the readings M1 to M3")
    ap.add_argument("--smoke", action="store_true",
                    help="with --gate, --check or --run: seed 0 only, nothing written")
    ap.add_argument("--no-write", action="store_true",
                    help="with --run: write nothing")
    args = ap.parse_args()

    if args.selftest:
        a = selftest_gate()
        print("\nderivative selftest:")
        b = selftest_derivative()
        print("\nfootprint selftest:")
        f = selftest_footprint()
        print("\nchain selftest:")
        c = selftest_chain()
        print("\nM3 selftest:")
        m = selftest_ablation()
        print("\nselftest:", "PASS" if (a and b and f and c and m) else "FAIL")
        return 0 if (a and b and f and c and m) else 1
    seeds = SEEDS[:1] if args.smoke else SEEDS
    if args.gate:
        rows, crit = run_gate(seeds=seeds)
        _print_criteria([crit])
        capped = sum(1 for r in rows if r["capped_payers"] > 0)
        print(f"\n  carriers with short payers, where the pass-on lines matter: {capped} of {len(rows)}")
        return 0 if crit["passed"] else 1
    if args.check:
        d_rows, c_rows, f_rows = run_check(seeds)
        m3_d, m3_c = ablation_checks(default_parts(seeds))
        crit = [criterion_derivative(d_rows + m3_d), criterion_chain(c_rows + m3_c),
                criterion_footprint(f_rows)]
        _print_criteria(crit)
        print_check(d_rows, c_rows)
        print_ablation_check(m3_d, m3_c)
        print("\n(--check: nothing written)")
        return 0 if all(x["passed"] for x in crit) else 1
    if args.run:
        out = run_all(seeds)
        crit = [criterion_rebuild(out["rebuild"]),
                criterion_derivative(out["derivative"] + out["holding_time_derivative"]),
                criterion_chain(out["chain_checks"] + out["holding_time_chains"]),
                criterion_footprint(out["footprint"])]
        _print_criteria(crit)
        print_check(out["derivative"], out["chain_checks"])
        print_ablation_check(out["holding_time_derivative"], out["holding_time_chains"])
        print_readouts(out)
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
        else:
            write_record(out, crit)
        return 0 if all(x["passed"] for x in crit) else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
