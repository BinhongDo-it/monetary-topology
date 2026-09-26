"""A44: where new claims end up, read off the carrier's own rules.

Ruled 2026-09-16. The injection arm of A41 found that new claims added to any
class of A17's carrier end up split the same way at the end of a run: about
0.742 with the financial layer, 0.255 with the intermediate block and 0.0023
with the wage earners, across a hundredfold range of amounts, with the class
that received them keeping a few thousandths more. This station builds the
linear map that carries one marginal claim through one round of that carrier
and reads the split off the map instead of off a run.

Three versions of the map, all built from the network object's own routing,
propensities, payroll sets and history:

    path tangent, issuance on    the control's own propensity draws, payer caps,
                                 membership and issuance, round by round
    path tangent, issuance off   the same, with the carrier's issuance response
                                 set to zero
    mean field                   one fixed matrix: the midpoint of each
                                 propensity band, each payer's share of capped
                                 rounds, the control's closing membership

Four readouts, printed and not held to anything:

    I1  the mean field and the path tangent without issuance, against every run
        in the injection arm's record, by amount
    I2  the entry-point term, what a class keeps when the claims enter it above
        its median share when they enter another class, at four injection
        lengths, from the whole model and from the mean field, with the
        constant the deviation matrix gives it on the same map
    I3  ten changes to the carrier, each split predicted from the control run
        before any injection on that carrier, then run
    I4  the stationary split per class, the smallest node entry and its class,
        the unreached class's largest entry, and the earners' share against the
        wage elasticity

Steps:

    python experiments/a44_occupation_operator.py --gate            # A44-0
    python experiments/a44_occupation_operator.py --selftest        # seeded faults
    python experiments/a44_occupation_operator.py --check --smoke   # A44-1, A44-2 on seed 0
    python experiments/a44_occupation_operator.py --run --smoke     # and the readouts, seed 0
    python experiments/a44_occupation_operator.py --run             # five seeds, writes the record

``--check`` and ``--smoke`` write nothing. ``--run`` reads the injection arm's
record without rerunning it and writes ``results/a44_occupation.json``. The
criteria are written in this file.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from monetary_topology.config import LAYER_1, LAYER_2  # noqa: E402
from monetary_topology.network import Network, NetworkConfig  # noqa: E402

#: A41's carrier, classes, field comparison and control, imported rather than
#: restated. The control is A41's ticket network with the ticket off, which
#: A41-0 showed is bitwise the plain network and which keeps each round's
#: membership.
from a41_same_ticket import (  # noqa: E402
    ALL_CLASSES,
    ELASTICITY,
    F2I,
    OPEN_FROM,
    ROUNDS,
    SEEDS,
    WALLS,
    TicketNetwork,
    TicketSpec,
    base_config,
    classes_of,
    diff_fields,
    _record_value,
)
from a41b_credit_inject import INJECT_RECORD, TARGETS, InjectNetwork  # noqa: E402

GATE_SEEDS = (0, 1)

#: A44-1's finite difference: claims added a round to the whole model. Small
#: enough that no payer crosses its cap and no round crosses the issuance
#: floor on the grid's cells, large enough to stand well above the rounding in
#: a gain of two hundred holdings (measured before this file: a gain of
#: ``2.5e-5`` in total against holdings of order ``10``).
FD_EPS = 1e-7

TOL_TANGENT = 1e-5
TOL_CONSERVE = 1e-12
TOL_IDENTITY = 1e-10
TOL_UNIT = 1e-9

HORIZON = ROUNDS - OPEN_FROM


# --------------------------------------------------------------------------
# the control's own path


class RecordingGenerator:
    """Forwards every call to the network's generator and keeps what
    ``uniform`` returned. The carrier's only draw from that generator is the
    per-round propensity, so one entry is kept per round. A44-0 shows the proxy
    touches nothing."""

    def __init__(self, generator: np.random.Generator) -> None:
        self._g = generator
        self.draws: list[np.ndarray] = []

    def uniform(self, *args, **kwargs):
        x = self._g.uniform(*args, **kwargs)
        self.draws.append(np.array(x, dtype=float, copy=True))
        return x

    def __getattr__(self, name):
        return getattr(self._g, name)


@dataclass
class PathRecord:
    seed: int
    wall: float
    net: Network
    hist: object
    draws: np.ndarray
    alive_rows: np.ndarray
    classes: dict


def record_path(seed: int, wall: float, config: NetworkConfig | None = None,
                recorder=RecordingGenerator) -> PathRecord:
    """The control run, with its propensity draws and membership kept."""
    cfg = base_config(seed, need=wall) if config is None else config
    net = TicketNetwork(cfg, TicketSpec())
    proxy = recorder(net.rng)
    net.rng = proxy
    hist = net.run()
    if len(proxy.draws) != ROUNDS:
        raise AssertionError(f"{len(proxy.draws)} propensity draws in "
                             f"{ROUNDS} rounds")
    return PathRecord(seed=seed, wall=wall, net=net, hist=hist,
                      draws=np.vstack(proxy.draws),
                      alive_rows=np.asarray(net._alive_rows, dtype=bool),
                      classes=classes_of(net))


def scope_problems(net: Network) -> list[str]:
    """The switches this map does not linearize. Any one of them on, and the
    maps refuse to be built."""
    cfg = net.config
    out = []
    if cfg.spec.uniform_access:
        out.append("spec.uniform_access")
    if cfg.injection_target != "top_node":
        out.append("injection_target")
    if cfg.authority.rule not in ("endogenous", "fixed", "none"):
        out.append("authority.rule")
    if not 0.0 <= cfg.wages.elasticity <= 1.0:
        out.append("wages.elasticity outside [0, 1]")
    if cfg.wages.floor_share > 0.0:
        out.append("wages.floor_share")
    if cfg.subsistence.active and (cfg.subsistence.mode != "exit"
                                   or cfg.subsistence.cut_payroll):
        out.append("subsistence other than exit with the payroll kept")
    for name in ("rewire", "hub_debt", "edge_cut", "resupply", "park",
                 "sovereign", "withdraw", "writeoff"):
        if getattr(cfg, name).active:
            out.append(name)
    if cfg.park.returns:
        out.append("park.returns")
    if cfg.sovereign.serves_debt:
        out.append("sovereign.serves_debt")
    if cfg.industry.enabled:
        out.append("industry")
    if cfg.broadcast.weight != 0.0 and cfg.broadcast.phi:
        out.append("broadcast")
    if cfg.greedy.enabled:
        out.append("greedy")
    if net._wage_weights is not None:
        out.append("wage weights")
    return out


def class_shares(vec: np.ndarray, classes: dict) -> dict:
    total = float(vec.sum())
    return {c: (float(vec[classes[c]].sum()) / total if total else float("nan"))
            for c in ALL_CLASSES}


# --------------------------------------------------------------------------
# the path tangent


class PathTangent:
    """One marginal claim carried through the control's own rounds.

    **The four places the carrier is not linear**, each taken as its code reads:

    1. The wage bill is ``bill * ((1 - e) + e * S / S0)``, ``S`` the layer-2
       spending of the round before. Its derivative ``bill * e / S0`` acts one
       round late.
    2. A payer pays ``min(bill / payers, max(h, 0))``. A payer whose holding
       covers its share pays the marginal share of the bill; one whose holding
       does not pays its marginal holding, all of it, when the holding is not
       negative.
    3. Spending is ``p * max(h, 0)``. At a holding of exactly zero the
       derivative is taken from the right, since an injection is positive.
    4. Issuance is ``max(0, gain * (base - layer-2 inflow))``, credited at the
       injection node the next round. In a round the control issued, the
       marginal is minus the gain times the marginal layer-2 inflow.

    Every other switch that moves claims is refused (``scope_problems``).
    Payroll is not masked by membership on this carrier, so a payer that has
    left still pays and an earner that has left still receives, as in the
    network.

    Four one-line hooks, so that a seeded fault replaces a line rather than a
    copy of the round.
    """

    def __init__(self, path: PathRecord) -> None:
        problems = scope_problems(path.net)
        if problems:
            raise ValueError(f"not linearized here: {problems}")
        net, hist = path.net, path.hist
        self.path = path
        self.n = net._n
        self.payers = np.asarray(net._wage_payers, dtype=int)
        self.receivers = np.asarray(net._wage_receivers, dtype=int)
        self.l2 = np.zeros(self.n, dtype=bool)
        self.l2[np.asarray(net._l2, dtype=int)] = True
        self.top = int(net.injection_node)
        self.route0 = np.asarray(net._route, dtype=float)
        self.has_out = np.asarray(net._has_out, dtype=bool)
        self.H = np.asarray(hist.holdings, dtype=float)
        self.owed = np.asarray(hist.wage_owed, dtype=float)
        self.issued = np.asarray(hist.issuance, dtype=float)
        wc = net.config.wages
        base = float(net._baseline_l2_spending)
        self.bill_slope = (wc.bill * wc.elasticity / base
                           if wc.elasticity > 0.0 and base > 0.0 else 0.0)
        auth = net.config.authority
        self.issuance_gain = auth.gain if auth.rule == "endogenous" else 0.0

    def _bill_response(self) -> float:
        return self.bill_slope

    def _capped(self, held: np.ndarray, share: float) -> np.ndarray:
        return held < share

    def _spends_at_zero(self, after_wages: np.ndarray) -> np.ndarray:
        return after_wages >= 0.0

    def _issuance_response(self, layer2_inflow: float) -> float:
        return -self.issuance_gain * layer2_inflow

    def occupation(self, target: str, open_from: int = OPEN_FROM
                   ) -> tuple[np.ndarray, int]:
        """The end-of-run marginal holdings when one claim a round is split
        over the target class's nodes trading at each round's opening, and the
        number of rounds in which anything was added."""
        n = self.n
        payers, receivers = self.payers, self.receivers
        target_ix = self.path.classes[target]
        dh = np.zeros(n)
        d_spend_l2 = 0.0
        d_pending = 0.0
        injected = 0
        for t in range(open_from, ROUNDS):
            alive = self.path.alive_rows[t - 1]
            here = target_ix[alive[target_ix]]
            if here.size:
                dh[here] += 1.0 / here.size
                injected += 1
            held = self.H[t - 1].copy()
            if self.issued[t] > 0.0:
                dh[self.top] += d_pending
                held[self.top] += self.issued[t]
            share = self.owed[t] / payers.size
            capped = self._capped(held[payers], share)
            d_bill = self._bill_response() * d_spend_l2
            d_paid = np.where(capped,
                              np.where(held[payers] >= 0.0, dh[payers], 0.0),
                              d_bill / payers.size)
            dh[payers] -= d_paid
            dh[receivers] += d_paid.sum() / receivers.size
            after = held.copy()
            paid = np.minimum(share, np.maximum(held[payers], 0.0))
            after[payers] -= paid
            after[receivers] += paid.sum() / receivers.size
            route = self.route0 * alive[None, :]
            sums = route.sum(axis=1, keepdims=True)
            route = np.divide(route, sums, out=np.zeros_like(route),
                              where=sums > 0)
            q = (self.path.draws[t] * self.has_out * alive
                 * (sums.ravel() > 0) * self._spends_at_zero(after))
            d_spent = q * dh
            inflow = route.T @ d_spent
            dh = dh - d_spent + inflow
            d_spend_l2 = float(d_spent[self.l2].sum())
            d_pending = self._issuance_response(
                float(d_paid.sum()) + float(inflow[self.l2].sum()))
        return dh, injected


class PathTangentNoIssuance(PathTangent):
    """The path tangent with the issuance response set to zero: an injection
    large against the carrier's own issuance shuts that issuance off, so this is
    the tangent at such an injection."""

    def _issuance_response(self, layer2_inflow: float) -> float:
        return 0.0


# --------------------------------------------------------------------------
# the mean field


class MeanField:
    """One fixed matrix for a round of the carrier, from its control run.

    The state is ``(dh, dS)``: each node's marginal holding and the marginal
    layer-2 spending of the round before. A round pays the marginal bill
    ``bill * e / S0 * dS``, lets each capped payer pass its marginal holding to
    the earners, then lets each node spend the midpoint of its propensity band
    along its routes, renormalized over the nodes trading at the end of the
    control run. Each payer is capped in the share of rounds from ``open_from``
    in which the control's holding fell short of its share of the bill. The
    issuance response is zero.

    Claims injected into trading nodes stay among the trading nodes and the
    state variable, so the stationary vector and the deviation matrix are taken
    on that block.

    Four one-line hooks for the seeded faults.
    """

    def __init__(self, path: PathRecord, open_from: int = OPEN_FROM) -> None:
        problems = scope_problems(path.net)
        if problems:
            raise ValueError(f"not linearized here: {problems}")
        net, hist = path.net, path.hist
        self.path = path
        n = self.n = net._n
        self.alive = path.alive_rows[-1].copy()
        payers = self.payers = np.asarray(net._wage_payers, dtype=int)
        receivers = self.receivers = np.asarray(net._wage_receivers, dtype=int)
        l2 = np.zeros(n, dtype=bool)
        l2[np.asarray(net._l2, dtype=int)] = True
        self.route0 = np.asarray(net._route, dtype=float)
        self.has_out = np.asarray(net._has_out, dtype=bool)
        pbar = 0.5 * (np.asarray(net._p_low, dtype=float)
                      + np.asarray(net._p_high, dtype=float))
        reach = (self.route0 * self.alive[None, :]).sum(axis=1) > 0
        q = pbar * self.has_out * self.alive * reach
        q = self._spenders(q)
        R = self._routes(self.alive)
        G = np.eye(n) - np.diag(q) + R.T * q[None, :]
        H = np.asarray(hist.holdings, dtype=float)
        owed = np.asarray(hist.wage_owed, dtype=float)
        rounds = np.arange(open_from, ROUNDS)
        self.capped = (H[rounds - 1][:, payers]
                       < (owed[rounds] / payers.size)[:, None]).mean(axis=0)
        B = np.eye(n)
        for k, j in enumerate(payers):
            B[j, j] -= self.capped[k]
            B[receivers, j] += self._receiver_share(self.capped[k])
        bill_part = np.zeros(n)
        bill_part[payers] -= (1.0 - self.capped) / payers.size
        bill_part[receivers] += ((1.0 - self.capped).sum() / payers.size
                                 / receivers.size)
        wc = net.config.wages
        base = float(net._baseline_l2_spending)
        self.bill_slope = (wc.bill * wc.elasticity / base
                           if wc.elasticity > 0.0 and base > 0.0 else 0.0)
        spend_l2 = l2 * q
        A = np.zeros((n + 1, n + 1))
        A[:n, :n] = G @ B
        A[:n, n] = (G @ bill_part) * self.bill_slope
        A[n, :n] = spend_l2 @ B
        A[n, n] = float(spend_l2 @ bill_part) * self.bill_slope
        self.A = A
        self.live = np.concatenate([np.flatnonzero(self.alive), [n]])
        self.block = A[np.ix_(self.live, self.live)]

    def _routes(self, alive: np.ndarray) -> np.ndarray:
        route = self.route0 * alive[None, :]
        sums = route.sum(axis=1, keepdims=True)
        return np.divide(route, sums, out=np.zeros_like(route), where=sums > 0)

    def _receiver_share(self, capped: float) -> float:
        return capped / self.receivers.size

    def _spenders(self, q: np.ndarray) -> np.ndarray:
        return q

    def _deviation(self, block: np.ndarray, proj: np.ndarray,
                   fundamental: np.ndarray) -> np.ndarray:
        return (block - proj) @ fundamental

    def mass_functional(self) -> np.ndarray:
        ell = np.ones(self.block.shape[0])
        ell[-1] = 0.0
        return ell

    def stationary(self) -> tuple[np.ndarray, float]:
        """The eigenvalue-1 vector of the block with unit mass, by least
        squares, and its residual."""
        m = self.block.shape[0]
        lhs = np.vstack([self.block - np.eye(m), self.mass_functional()[None, :]])
        rhs = np.zeros(m + 1)
        rhs[-1] = 1.0
        x = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
        return x, float(np.abs(self.block @ x - x).max())

    def deviation(self, pi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """``D = (A - P) Z`` with ``Z = (I - A + P)^-1``. When eigenvalue 1 is
        not simple ``I - A + P`` is singular, and the three come back as NaN so
        that the identity reads as failed rather than raising."""
        m = self.block.shape[0]
        proj = np.outer(pi, self.mass_functional())
        try:
            fundamental = np.linalg.inv(np.eye(m) - self.block + proj)
        except np.linalg.LinAlgError:
            fundamental = np.full((m, m), np.nan)
        return self._deviation(self.block, proj, fundamental), proj, fundamental

    def injection(self, target: str) -> np.ndarray:
        """One claim split over the target class's trading nodes, on the block."""
        ix = self.path.classes[target]
        ix = ix[self.alive[ix]]
        v = np.zeros(self.n + 1)
        if ix.size:
            v[ix] = 1.0 / ix.size
        return v[self.live]

    def occupation(self, v: np.ndarray, horizon: int = HORIZON) -> np.ndarray:
        acc = np.zeros_like(v)
        cur = v.copy()
        for _ in range(horizon):
            cur = self.block @ cur
            acc += cur
        return acc

    def block_classes(self) -> dict:
        """Class membership as positions in the block."""
        pos = {int(node): k for k, node in enumerate(self.live[:-1])}
        return {c: np.array([pos[int(i)] for i in ix if int(i) in pos], dtype=int)
                for c, ix in self.path.classes.items()}


# --------------------------------------------------------------------------
# A44-0: the gate


@dataclass
class GateResult:
    ok: bool = True
    rows: list = field(default_factory=list)


def generator_states_differ(a: Network, b: Network) -> list[str]:
    """Names of the generators whose state differs at the end of two runs,
    looking through a recording proxy."""
    out = []
    for name in sorted(vars(b)):
        gb = getattr(b, name)
        if not isinstance(gb, np.random.Generator):
            continue
        ga = getattr(a, name, None)
        if isinstance(ga, RecordingGenerator):
            ga = ga._g
        if (not isinstance(ga, np.random.Generator)
                or ga.bit_generator.state != gb.bit_generator.state):
            out.append(name)
    return out


def run_gate(recorder=RecordingGenerator) -> GateResult:
    """A44-0: the recording proxy touches nothing. Each control run through the
    proxy against the plain network: every history field bitwise, and every
    generator the network holds in the same state at the end."""
    res = GateResult()
    print("A44-0: the recording proxy does not touch the network\n")
    t0 = time.time()
    for wall in WALLS:
        for seed in GATE_SEEDS:
            plain = Network(base_config(seed, need=wall))
            ph = plain.run()
            path = record_path(seed, wall, recorder=recorder)
            fields = diff_fields(path.hist, ph)
            gens = generator_states_differ(path.net, plain)
            good = not fields and not gens
            res.ok = res.ok and good
            res.rows.append({"seed": seed, "wall": wall, "fields": fields,
                             "generators": gens})
            print(f"  {'ok  ' if good else 'FAIL'} wall {wall:.2f} seed {seed}   "
                  f"differing fields {len(fields)}   generators {gens}")
    print(f"\nA44-0: {'PASS' if res.ok else 'FAIL'}   ({time.time() - t0:.1f} s)")
    return res


class _LastRoundDrawRecorder(RecordingGenerator):
    """Seeded fault: the proxy reads the network's generator once after the
    last propensity draw. No later draw shows it, so the history is unchanged
    and only the generator's state can see it."""

    extra = 0

    def uniform(self, *args, **kwargs):
        x = super().uniform(*args, **kwargs)
        if len(self.draws) == ROUNDS:
            self._g.random()
            type(self).extra += 1
        return x


class _ExtraDrawRecorder(RecordingGenerator):
    """Seeded fault: the proxy draws one number more than the network asked for."""

    extra = 0

    def uniform(self, *args, **kwargs):
        x = super().uniform(*args, **kwargs)
        self._g.random()
        type(self).extra += 1
        return x


# --------------------------------------------------------------------------
# A44-1 and A44-2: rows and criteria


def tangent_cells(seeds=SEEDS) -> list[tuple]:
    """(seed, wall, target), the injection arm's cells without the amount."""
    return [(seed, wall, target) for seed in seeds for wall in WALLS
            for target in TARGETS if wall == 0.0 or target != "unreached"]


def fd_gain(path: PathRecord, target: str, eps: float = FD_EPS) -> np.ndarray:
    """The whole model's end-of-run gain for ``eps`` claims a round."""
    treated = InjectNetwork(path.net.config, target, eps)
    th = treated.run()
    return (np.asarray(th.holdings[-1], dtype=float)
            - np.asarray(path.hist.holdings[-1], dtype=float))


def tangent_row(path: PathRecord, target: str, fd: np.ndarray,
                tangent_class=PathTangent) -> dict:
    tan = tangent_class(path)
    dh, injected = tan.occupation(target)
    st = class_shares(dh, path.classes)
    sf = class_shares(fd, path.classes)
    row = {"seed": path.seed, "wall": path.wall, "target": target,
           "injected_rounds": injected}
    for c in ALL_CLASSES:
        row[f"tangent_{c}"] = st[c]
        row[f"fd_{c}"] = sf[c]
    if injected and float(fd.sum()) and float(dh.sum()):
        row["class_diff"] = max(abs(st[c] - sf[c]) for c in ALL_CLASSES)
        row["node_diff"] = float(np.abs(dh / dh.sum() - fd / fd.sum()).max())
        row["mass_tangent"] = float(dh.sum()) / injected
        row["mass_fd"] = float(fd.sum()) / (FD_EPS * injected)
    else:
        row["class_diff"] = row["node_diff"] = float("nan")
        row["mass_tangent"] = row["mass_fd"] = float("nan")
    return row


def identity_error(field_map: MeanField, v: np.ndarray, pi: np.ndarray,
                   dev: np.ndarray, proj: np.ndarray, fundamental: np.ndarray,
                   horizon: int = HORIZON) -> float:
    """``sum_{k=1..T} A^k v`` against ``T pi (ell.v) + D v - (A^{T+1} - P) Z v``."""
    block = field_map.block
    lhs = field_map.occupation(v, horizon)
    zv = fundamental @ v
    tail = zv.copy()
    for _ in range(horizon + 1):
        tail = block @ tail
    rhs = (horizon * pi * float(field_map.mass_functional() @ v) + dev @ v
           - (tail - proj @ zv))
    return float(np.abs(lhs - rhs).max() / max(1.0, float(np.abs(lhs).max())))


def operator_row(path: PathRecord, targets, field_class=MeanField) -> dict:
    fm = field_class(path)
    block = fm.block
    k = block.shape[0] - 1
    conserve = max(float(np.abs(block[:k, :k].sum(axis=0) - 1.0).max()),
                   float(abs(block[:k, k].sum())))
    ev = np.linalg.eigvals(block)
    unit = int((np.abs(ev - 1.0) < TOL_UNIT).sum())
    moduli = np.sort(np.abs(ev))
    pi, resid = fm.stationary()
    dev, proj, fundamental = fm.deviation(pi)
    ident = 0.0
    for t in targets:
        v = fm.injection(t)
        if float(v.sum()):
            ident = max(ident, identity_error(fm, v, pi, dev, proj, fundamental))
    row = {"seed": path.seed, "wall": path.wall, "trading_nodes": k,
           "conserve_err": conserve, "unit_eigenvalues": unit,
           "second_modulus": float(moduli[-2]) if moduli.size > 1 else float("nan"),
           "pi_resid": resid,
           "identity_err": ident,
           "capped_payers": int((fm.capped > 0.0).sum()),
           "capped_share_mean": float(fm.capped.mean())}
    cls = fm.block_classes()
    nodes = np.where(np.abs(pi[:k]) < ROUNDING_FLOOR, 0.0, pi[:k])
    where = np.full(k, "", dtype=object)
    for c in ALL_CLASSES:
        row[f"pi_{c}"] = float(nodes[cls[c]].sum()) if cls[c].size else 0.0
        where[cls[c]] = c
    row["pi_min"] = float(nodes.min())
    at_min = {str(where[i]) for i in np.flatnonzero(nodes == nodes.min())}
    row["pi_min_class"] = "/".join(c for c in ALL_CLASSES if c in at_min)
    row["pi_negative_nodes"] = int((nodes < 0.0).sum())
    row["pi_unreached_max_abs"] = (float(np.abs(nodes[cls["unreached"]]).max())
                                   if cls["unreached"].size else float("nan"))
    return row


def _label(r: dict) -> str:
    head = f"{r['variant']}, " if "variant" in r else ""
    tail = f" {r['target']}" if "target" in r else ""
    return f"{head}seed {r['seed']} wall {r['wall']}{tail}"


def criterion_tangent(rows: list[dict]) -> dict:
    name = ("A44-1  the path tangent is the carrier's rule: its split matches a "
            "finite difference of the whole model on every cell")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no cells, nothing was evaluated")
    bad = [r for r in rows if not r["class_diff"] <= TOL_TANGENT]
    finite = [r["class_diff"] for r in rows if math.isfinite(r["class_diff"])]
    worst = max(finite) if finite else float("nan")
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} cells: with {FD_EPS:g} claims added "
                f"a round to the whole model, each of the four classes' shares "
                f"of the end-of-run gain from the model and from the tangent "
                f"differ by at most {TOL_TANGENT:.0e}." if not bad else
                f"Fails on {len(bad)} of {len(rows)} cells, largest class share "
                f"difference {worst:.3e} against {TOL_TANGENT:.0e}: "
                + "; ".join(f"{_label(r)} {r['class_diff']:.3e}"
                            for r in bad[:4])))


def operator_clauses(r: dict) -> set[str]:
    """The clauses of A44-2 a carrier fails, by name. Several faults break more
    than one clause, since a map that loses claims or has two closed classes no
    longer closes the finite sum either; the selftest reads the clause each
    fault is meant to break, so that no clause rides on another.

    Two quantities are printed and not held to anything. The stationary
    vector's residual is implied by the identity, which is derived from it. Its
    sign is a reading: the map has negative entries, where a payer pays more of
    a larger bill, so a payer's stationary marginal holding may be negative on
    a carrier without anything being wrong with the map."""
    out = set()
    if not r["conserve_err"] <= TOL_CONSERVE:
        out.add("conserve")
    if r["unit_eigenvalues"] != 1:
        out.add("unit")
    if not r["identity_err"] <= TOL_IDENTITY:
        out.add("identity")
    return out


def _carrier_scope(rows: list[dict]) -> str:
    variants = sum("variant" in r for r in rows)
    if not variants:
        return f"{len(rows)} carriers"
    return (f"{len(rows)} carriers, {len(rows) - variants} of them the default "
            f"and {variants} variants of it")


def criterion_operator(rows: list[dict]) -> dict:
    name = ("A44-2  the mean-field map conserves claims, has one stationary "
            "split, and its deviation matrix closes the finite sum")
    if not rows:
        return dict(name=name, kind="instrument", passed=False,
                    detail="Void: no carriers, nothing was evaluated")

    bad = [r for r in rows if operator_clauses(r)]
    return dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {_carrier_scope(rows)}: on the block of trading "
                f"nodes and the spending state every column moves its claims "
                f"without loss to within {TOL_CONSERVE:.0e}; exactly one "
                f"eigenvalue lies within {TOL_UNIT:.0e} of 1; for each target "
                f"the sum of {HORIZON} "
                f"rounds equals the horizon times the stationary vector plus the "
                f"deviation matrix's term less its tail, to {TOL_IDENTITY:.0e} "
                f"relative." if not bad else
                f"Fails on {len(bad)} of {len(rows)} carriers: "
                + "; ".join(f"{_label(r)} fails {sorted(operator_clauses(r))}: "
                            f"conserve {r['conserve_err']:.2e}, "
                            f"unit eigenvalues {r['unit_eigenvalues']}, "
                            f"identity {r['identity_err']:.2e}"
                            for r in bad[:3])))


def run_check(seeds=SEEDS) -> tuple[list[dict], list[dict]]:
    t0 = time.time()
    rows = criterion_rows(base_paths(seeds))
    print(f"  {len(seeds)} seeds done ({time.time() - t0:.0f} s)", flush=True)
    return rows


def print_check(tan_rows: list[dict], op_rows: list[dict]) -> None:
    print("\nA44-1 cells: tangent l1/mid/earners/unreached | finite difference | "
          "largest class difference, largest node difference, claims kept a "
          "round (tangent, finite difference)")
    for r in tan_rows:
        print(f"  {_label(r):28s} "
              + "/".join(f"{r['tangent_' + c]:.5f}" for c in ALL_CLASSES) + " | "
              + "/".join(f"{r['fd_' + c]:.5f}" for c in ALL_CLASSES)
              + f" | {r['class_diff']:.1e} {r['node_diff']:.1e} "
              f"{r['mass_tangent']:.6f} {r['mass_fd']:.6f}")
    print("\nA44-2 carriers: trading nodes, capped payers, conservation, unit "
          "eigenvalues, second modulus, pi min, identity | stationary "
          "l1/mid/earners/unreached")
    width = max((len(_label(r)) for r in op_rows), default=18)
    for r in op_rows:
        print(f"  {_label(r):{width}s} {r['trading_nodes']:3d} {r['capped_payers']:2d} "
              f"{r['conserve_err']:.1e} {r['unit_eigenvalues']} "
              f"{r['second_modulus']:.6f} {r['pi_min']:+.1e} "
              f"{r['identity_err']:.1e} | "
              + "/".join(f"{r['pi_' + c]:.5f}" for c in ALL_CLASSES))
    if tan_rows:
        print(f"\n  residues on this machine: class share difference "
              f"{max(r['class_diff'] for r in tan_rows):.3e}, node "
              f"{max(r['node_diff'] for r in tan_rows):.3e}")
    if op_rows:
        print(f"  conservation {max(r['conserve_err'] for r in op_rows):.3e}, "
              f"identity {max(r['identity_err'] for r in op_rows):.3e}, "
              f"stationary residual {max(r['pi_resid'] for r in op_rows):.3e}")


# --------------------------------------------------------------------------
# readouts (block two): against the injection record, duration, variants


#: How many rounds the injection runs before round 300, for I2. The first is
#: the injection arm's own and is read off its record at 4 a round.
DURATIONS = (HORIZON, 150, 75, 25)
DURATION_AMOUNT = 4.0

#: I3: ten changes to the carrier, each applied to the default without a floor.
#: The propensity bands are per stratum, ordered bottom 49, middle 40, upper 10,
#: top 1; the financial layer is the upper two and the production layer the
#: lower two (``LAYER_1`` and ``LAYER_2`` in the configuration module), and a
#: change names the layer and the band it is given. The intermediate block spends
#: at the production layer's band.
VARIANTS = (
    ("f2i 10", {"spec.financial_to_intermediate_edges": 10}),
    ("f2i 60", {"spec.financial_to_intermediate_edges": 60}),
    ("intermediate 15", {"spec.intermediate_size": 15}),
    ("intermediate 60", {"spec.intermediate_size": 60}),
    ("wage elasticity 0", {"wages.elasticity": 0.0}),
    ("wage elasticity 1", {"wages.elasticity": 1.0}),
    ("financial propensity 0.3", {"band.financial": (0.3, 0.3)}),
    ("financial propensity 0.7", {"band.financial": (0.7, 0.7)}),
    ("production propensity 0.55 to 0.65", {"band.production": (0.55, 0.65)}),
    ("upward out-degree 4", {"spec.upward_out_degree": 4}),
)
VARIANT_AMOUNT = 4.0
VARIANT_TARGETS = ("l1", "mid", "earners")
HOME_CLASSES = ("l1", "mid", "earners")

RECORD = RESULTS / "a44_occupation.json"

#: Whether the readings are written into RESULTS.md. While they are not, the
#: record carries ``diagnostic_only`` and a reason; once they are, neither.
CLOSED = True

#: Stationary entries below this are rounding and are taken as zero before the
#: class sums, the smallest entry and its class are read: a node with no inflow
#: reads ``1e-17`` on one build and ``-1e-17`` on another.
ROUNDING_FLOOR = 1e-12

#: The record's floats are rounded to a fixed number of decimal places, an
#: absolute grid, so that a small reading carries no digit from below the
#: build's rounding. Shares off a finite difference of two whole-model runs
#: get six: that difference agrees with the tangent to a few parts in ten
#: billion, and the places past the sixth belong to the build.
DECIMALS = 10
FD_DECIMALS = 6


def apply_variant(config: NetworkConfig, changes: dict) -> NetworkConfig:
    groups: dict = {}
    for key, value in changes.items():
        head, attr = key.split(".")
        if head == "band":
            idx = {"financial": LAYER_1, "production": LAYER_2}[attr]
            spend = groups.get("spend", {})
            low = list(spend.get("low", config.spend.low))
            high = list(spend.get("high", config.spend.high))
            for i in idx:
                low[i], high[i] = value
            groups["spend"] = {"low": tuple(low), "high": tuple(high)}
        else:
            groups.setdefault(head, {})[attr] = value
    return dataclasses.replace(config, **{
        head: dataclasses.replace(getattr(config, head), **attrs)
        for head, attrs in groups.items()})


def resolved_changes(changes: dict) -> dict:
    """What a variant sets, as the configuration carries it, for the record."""
    cfg = apply_variant(base_config(SEEDS[0], need=0.0), changes)
    out = {}
    for key in changes:
        head, attr = key.split(".")
        if head == "band":
            out["spend.low"] = list(cfg.spend.low)
            out["spend.high"] = list(cfg.spend.high)
        else:
            value = getattr(getattr(cfg, head), attr)
            out[key] = list(value) if isinstance(value, tuple) else value
    return out


def targets_on(seed: int, wall: float) -> list[str]:
    return [t for (s, w, t) in tangent_cells((seed,)) if w == wall]


def field_shares(fm: MeanField, target: str, horizon: int = HORIZON) -> dict:
    acc = fm.occupation(fm.injection(target), horizon)[:-1]
    cls = fm.block_classes()
    total = float(acc.sum())
    return {c: (float(acc[cls[c]].sum()) / total if cls[c].size and total else 0.0)
            for c in ALL_CLASSES}


def run_shares(path: PathRecord, target: str, amount: float,
               open_from: int = OPEN_FROM) -> dict:
    treated = InjectNetwork(path.net.config, target, amount, open_from=open_from)
    th = treated.run()
    gain = (np.asarray(th.holdings[-1], dtype=float)
            - np.asarray(path.hist.holdings[-1], dtype=float))
    return class_shares(gain, path.classes)


def home_bias(shares: dict, targets) -> dict:
    """A class's share when the injection enters it, less the median of its
    share when the injection enters each other target."""
    return {c: shares[c][c] - statistics.median(shares[o][c] for o in targets if o != c)
            for c in HOME_CLASSES if c in targets}


def deviation_constants(fm: MeanField, targets) -> dict:
    """The same difference taken on the deviation matrix's term. With the tail
    gone, a class's share at horizon ``T`` is its stationary share plus
    ``(D v)_c / T``, so the entry-point term times ``T`` tends to this."""
    pi, _ = fm.stationary()
    dev, _, _ = fm.deviation(pi)
    cls = fm.block_classes()
    dv = {t: dev @ fm.injection(t) for t in targets}
    return {c: float(dv[c][cls[c]].sum())
            - statistics.median(float(dv[o][cls[c]].sum()) for o in targets if o != c)
            for c in HOME_CLASSES if c in targets}


def load_injection_record() -> dict | None:
    if not INJECT_RECORD.exists():
        print(f"  {INJECT_RECORD.name} is not on disk: I1 is not read and I2 "
              f"runs its first horizon")
        return None
    rec = json.loads(INJECT_RECORD.read_text(encoding="utf-8"))
    inj = rec.get("config", {}).get("injection", {})
    problems = []
    if inj.get("open_from") != OPEN_FROM:
        problems.append(f"open_from {inj.get('open_from')}")
    if DURATION_AMOUNT not in inj.get("per_round", []):
        problems.append(f"no runs at {DURATION_AMOUNT:g} a round")
    if rec.get("diagnostic_only"):
        problems.append("the record is not closed")
    if problems:
        print(f"  {INJECT_RECORD.name} does not fit ({'; '.join(problems)}): "
              f"I1 is not read and I2 runs its first horizon")
        return None
    return rec


def against_record(paths: dict, rec: dict | None) -> list[dict]:
    """I1: the mean field and the path tangent without the issuance response,
    each against every injection-arm run on the same carrier."""
    if rec is None:
        return []
    idx = {(r["seed"], r["wall"], r["target"], r["per_round"]): r for r in rec["runs"]}
    amounts = rec["config"]["injection"]["per_round"]
    rows = []
    for (seed, wall), path in sorted(paths.items()):
        fm = MeanField(path)
        tan = PathTangentNoIssuance(path)
        for target in targets_on(seed, wall):
            fs = field_shares(fm, target)
            ts = class_shares(tan.occupation(target)[0], path.classes)
            for q in amounts:
                r = idx.get((seed, wall, target, q))
                if r is None:
                    continue
                row = {"seed": seed, "wall": wall, "target": target, "per_round": q,
                       "displaced_issuance_share": (
                           (r["issuance_c"] - r["issuance_t"]) / r["injected"]
                           if r["injected"] else float("nan"))}
                for c in ALL_CLASSES:
                    row[f"record_{c}"] = r[f"gain_{c}"]
                    row[f"field_{c}"] = fs[c]
                    row[f"tangent_{c}"] = ts[c]
                rows.append(row)
    return rows


def duration_rows(paths: dict, rec: dict | None) -> list[dict]:
    """I2: the entry-point term at four horizons, from the whole model and from
    the mean field, beside the deviation matrix's constant.

    An injection of ``T`` rounds opens at round ``ROUNDS - T``, and the mean
    field for it takes each payer's capped share from that round on, so that
    the map reads the rounds the claims travel through. The constant is taken
    on the same map."""
    idx = ({} if rec is None else
           {(r["seed"], r["wall"], r["target"], r["per_round"]): r for r in rec["runs"]})
    rows = []
    for (seed, wall), path in sorted(paths.items()):
        targets = targets_on(seed, wall)
        for horizon in DURATIONS:
            fm = MeanField(path, open_from=ROUNDS - horizon)
            consts = deviation_constants(fm, targets)
            model, field_ = {}, {}
            from_record = True
            for t in targets:
                r = idx.get((seed, wall, t, DURATION_AMOUNT)) if horizon == HORIZON else None
                if r is not None:
                    model[t] = {c: float(r[f"gain_{c}"]) for c in ALL_CLASSES}
                else:
                    from_record = False
                    model[t] = run_shares(path, t, DURATION_AMOUNT,
                                          open_from=ROUNDS - horizon)
                field_[t] = field_shares(fm, t, horizon)
            mh, fh = home_bias(model, targets), home_bias(field_, targets)
            row = {"seed": seed, "wall": wall, "horizon": horizon,
                   "model_from_record": from_record,
                   "capped_share_mean": float(fm.capped.mean())}
            for c in mh:
                row[f"model_home_{c}"] = mh[c]
                row[f"field_home_{c}"] = fh[c]
                row[f"constant_{c}"] = consts[c]
            rows.append(row)
    return rows


def variant_runs(seeds, tick=None) -> tuple[list[dict], list[dict]]:
    """I3: each variant's split predicted from its control run, by the mean
    field and by the path tangent without the issuance response, and then run.
    The predictions are computed before any injection on that carrier."""
    rows, carriers = [], []
    for name, changes in VARIANTS:
        for seed in seeds:
            cfg = apply_variant(base_config(seed, need=0.0), changes)
            path = record_path(seed, 0.0, config=cfg)
            fm = MeanField(path)
            tan = PathTangentNoIssuance(path)
            field_ = {t: field_shares(fm, t) for t in VARIANT_TARGETS}
            tangent = {t: class_shares(tan.occupation(t)[0], path.classes)
                       for t in VARIANT_TARGETS}
            carrier = operator_row(path, VARIANT_TARGETS)
            carrier["variant"] = name
            carriers.append(carrier)
            for t in VARIANT_TARGETS:
                run = run_shares(path, t, VARIANT_AMOUNT)
                row = {"variant": name, "seed": seed, "target": t}
                for c in ALL_CLASSES:
                    row[f"field_{c}"] = field_[t][c]
                    row[f"tangent_{c}"] = tangent[t][c]
                    row[f"run_{c}"] = run[c]
                rows.append(row)
        if tick is not None:
            tick(f"I3 {name}")
    return rows, carriers


def base_paths(seeds) -> dict:
    return {(seed, wall): record_path(seed, wall) for seed in seeds for wall in WALLS}


def criterion_rows(paths: dict) -> tuple[list[dict], list[dict]]:
    tan_rows, op_rows = [], []
    for (seed, wall), path in sorted(paths.items()):
        targets = targets_on(seed, wall)
        for target in targets:
            tan_rows.append(tangent_row(path, target, fd_gain(path, target)))
        op_rows.append(operator_row(path, targets))
    return tan_rows, op_rows


def run_all(seeds) -> dict:
    t0 = time.time()

    def tick(what):
        print(f"  {what} ({time.time() - t0:.0f} s)", flush=True)

    paths = base_paths(seeds)
    tick(f"{len(paths)} control paths")
    tan_rows, op_rows = criterion_rows(paths)
    tick(f"A44-1 on {len(tan_rows)} cells, A44-2 on {len(op_rows)} carriers")
    rec = load_injection_record()
    rec_rows = against_record(paths, rec)
    tick(f"I1 against {len(rec_rows)} injection-arm runs")
    dur_rows = duration_rows(paths, rec)
    tick(f"I2 at {len(DURATIONS)} horizons")
    var_rows, var_carriers = variant_runs(seeds, tick)
    tick(f"I3 on {len(VARIANTS)} variants")
    return {"seeds": list(seeds), "tangent": tan_rows, "carriers": op_rows,
            "record": rec_rows,
            "duration": dur_rows, "variants": var_rows,
            "variant_carriers": var_carriers}


# --------------------------------------------------------------------------
# printing


def _rng(vals, spec: str) -> str:
    vals = [v for v in vals if v is not None and math.isfinite(v)]
    if not vals:
        return "-"
    return (f"{format(statistics.median(vals), spec)} "
            f"[{format(min(vals), spec)}, {format(max(vals), spec)}]")


def print_readouts(out: dict) -> None:
    rec_rows = out["record"]
    print("\nI1  the mean field and the path tangent without issuance against the "
          "injection arm's record: model minus record, median [range], by amount")
    if not rec_rows:
        print("  not read")
    for q in sorted({r["per_round"] for r in rec_rows}):
        sub = [r for r in rec_rows if r["per_round"] == q]
        print(f"  {q:g} a round, {len(sub)} runs; displaced issuance "
              f"{_rng([r['displaced_issuance_share'] for r in sub], '.4f')} of what "
              f"was injected")
        for kind in ("field", "tangent"):
            print(f"    {kind:8s} " + "  ".join(
                f"{c} {_rng([r[kind + '_' + c] - r['record_' + c] for r in sub], '+.5f')}"
                for c in ALL_CLASSES))

    print("\nI2  the entry-point term (a class's share when the injection enters "
          "it, less its median share when it enters another target), per class "
          "l1 / mid / earners: model / mean field, the horizon times each, and "
          "the deviation matrix's constant on the same map; last, the payers' "
          "mean capped share of rounds on that map")
    for r in out["duration"]:
        mark = "*" if r["model_from_record"] else " "
        cols = "  ".join(
            f"{r['model_home_' + c]:+.5f}/{r['field_home_' + c]:+.5f} "
            f"T* {r['horizon'] * r['model_home_' + c]:.3f}/"
            f"{r['horizon'] * r['field_home_' + c]:.3f} K {r['constant_' + c]:.3f}"
            for c in HOME_CLASSES if ("model_home_" + c) in r)
        print(f"  seed {r['seed']} wall {r['wall']:.2f} T {r['horizon']:3d}{mark} {cols}"
              f"  capped {r['capped_share_mean']:.3f}")
    print("  (* the model's shares at that horizon are the injection arm's record)")

    print("\nI3  variants: l1 / mid / earners shares, mean field | tangent without "
          "issuance | the run, when the injection enters the named class")
    by_variant: dict = {}
    for r in out["variants"]:
        by_variant.setdefault(r["variant"], []).append(r)
    for name, rs in by_variant.items():
        print(f"  {name}")
        for r in rs:
            print(f"    seed {r['seed']} into {r['target']:8s} "
                  + "/".join(f"{r['field_' + c]:.4f}" for c in HOME_CLASSES) + " | "
                  + "/".join(f"{r['tangent_' + c]:.4f}" for c in HOME_CLASSES) + " | "
                  + "/".join(f"{r['run_' + c]:.4f}" for c in HOME_CLASSES))
        for kind in ("field", "tangent"):
            print(f"    {kind} minus run, all classes and targets: "
                  f"{_rng([r[kind + '_' + c] - r['run_' + c] for r in rs for c in ALL_CLASSES], '+.5f')}")

    carrier_of = {(r["variant"], r["seed"]): r for r in out["variant_carriers"]}

    def furthest(r):
        return max(abs(r["field_" + c] - r["run_" + c]) for c in ALL_CLASSES)

    print("  the three cells where the mean field is furthest from the run: "
          "largest class difference, payers capped in some round and their mean "
          "capped share of rounds, trading nodes")
    for r in sorted(out["variants"], key=furthest, reverse=True)[:3]:
        k = carrier_of[(r["variant"], r["seed"])]
        print(f"    {r['variant']:36s} seed {r['seed']} into {r['target']:8s} "
              f"{furthest(r):.5f}  capped {k['capped_payers']} "
              f"({k['capped_share_mean']:.3f})  trading {k['trading_nodes']}")

    print("\nI4  stationary split per carrier: l1 / mid / earners / unreached; "
          "smallest node entry, the classes holding it and the number of "
          "negative entries; "
          "largest unreached entry")
    for r in out["carriers"] + out["variant_carriers"]:
        tag = r.get("variant", "carrier")
        print(f"  {tag:34s} seed {r['seed']} wall {r['wall']:.2f}  "
              + "/".join(f"{r['pi_' + c]:.5f}" for c in ALL_CLASSES)
              + f"  min {r['pi_min']:+.2e} ({r['pi_min_class']}, "
              f"{r['pi_negative_nodes']} negative)  unreached "
              + (f"{r['pi_unreached_max_abs']:.1e}"
                 if math.isfinite(r["pi_unreached_max_abs"]) else "none trading"))
    base0 = {r["seed"]: r for r in out["carriers"] if r["wall"] == 0.0}
    elastic = {(r["variant"], r["seed"]): r for r in out["variant_carriers"]
               if r["variant"].startswith("wage elasticity")}
    print("  earners' stationary share at wage elasticity 0 / 0.5 (the default) / 1, per seed:")
    for seed in sorted(base0):
        e0 = elastic.get(("wage elasticity 0", seed))
        e1 = elastic.get(("wage elasticity 1", seed))
        print(f"    seed {seed}: "
              f"{e0['pi_earners'] if e0 else float('nan'):.5f} / "
              f"{base0[seed]['pi_earners']:.5f} / "
              f"{e1['pi_earners'] if e1 else float('nan'):.5f}")


# --------------------------------------------------------------------------
# the record


def _clip(x, decimals: int = DECIMALS):
    if x is None:
        return None
    x = float(x)
    if not math.isfinite(x):
        return None
    y = round(x, decimals)
    return 0.0 if y == 0.0 else y


def record_tangent_row(r: dict) -> dict:
    """Shares from the finite difference to ``FD_DECIMALS`` places, the
    tangent's to ``DECIMALS``."""
    out = {"seed": r["seed"], "wall": _record_value(r["wall"]),
           "target": r["target"], "injected_rounds": r["injected_rounds"]}
    for c in ALL_CLASSES:
        out[f"tangent_{c}"] = _clip(r[f"tangent_{c}"])
        out[f"fd_{c}"] = _clip(r[f"fd_{c}"], FD_DECIMALS)
    out["mass_tangent"] = _clip(r["mass_tangent"])
    out["mass_fd"] = _clip(r["mass_fd"], FD_DECIMALS)
    if r["class_diff"] <= TOL_TANGENT:
        out["class_diff_at_most"] = TOL_TANGENT
    else:
        out["class_diff"] = _record_value(r["class_diff"])
    return out


def record_operator_row(r: dict) -> dict:
    out = {"seed": r["seed"], "wall": _record_value(r["wall"]),
           "trading_nodes": r["trading_nodes"], "capped_payers": r["capped_payers"],
           "capped_share_mean": _clip(r["capped_share_mean"]),
           "unit_eigenvalues": r["unit_eigenvalues"],
           "second_modulus": _clip(r["second_modulus"]),
           "pi_min": _clip(r["pi_min"]), "pi_min_class": r["pi_min_class"],
           "pi_negative_nodes": r["pi_negative_nodes"],
           "pi_unreached_max_abs": _clip(r["pi_unreached_max_abs"])}
    if "variant" in r:
        out["variant"] = r["variant"]
    for c in ALL_CLASSES:
        out[f"pi_{c}"] = _clip(r[f"pi_{c}"])
    for key, tol in (("conserve_err", TOL_CONSERVE), ("identity_err", TOL_IDENTITY)):
        if r[key] <= tol:
            out[f"{key}_at_most"] = tol
        else:
            out[key] = _record_value(r[key])
    return out


def record_plain_row(r: dict) -> dict:
    """Readout rows, every float to ``DECIMALS`` places."""
    out = {}
    for k, v in r.items():
        if isinstance(v, (bool, np.bool_, str)) or k in ("seed", "horizon"):
            out[k] = _record_value(v)
        else:
            out[k] = _clip(v)
    return out


def write_record(out: dict, crit: list[dict]) -> None:
    rec = {
        "stage": "A44",
        "config": {
            "carrier": "a17_edge_cut.base_config",
            "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
            "subsistence": {"mode": "exit", "grace": 1, "needs": list(WALLS)},
            "open_from": OPEN_FROM, "horizon": HORIZON, "seeds": out["seeds"],
            "path_tangent": ("the control's own propensity draws, payer caps, "
                             "membership and issuance, round by round; the "
                             "issuance response on for A44-1 and off for I1 and I3"),
            "mean_field": ("propensity at the midpoint of each band; each payer "
                           "capped in the share of rounds from open_from with "
                           "the control's holding below its share of the bill; "
                           "the control's closing membership; issuance response "
                           "zero"),
            "finite_difference": {"per_round": FD_EPS, "tolerance": TOL_TANGENT},
            "operator_tolerances": {"conserve": TOL_CONSERVE,
                                    "identity": TOL_IDENTITY, "unit": TOL_UNIT},
            "injection_record": INJECT_RECORD.name,
            "durations": list(DURATIONS), "duration_amount": DURATION_AMOUNT,
            "variants": {name: resolved_changes(ch) for name, ch in VARIANTS},
            "variant_wall": 0.0, "variant_amount": VARIANT_AMOUNT,
            "variant_targets": list(VARIANT_TARGETS),
            "stationary_rounding_floor": ROUNDING_FLOOR,
            "decimals": DECIMALS, "fd_decimals": FD_DECIMALS,
        },
        "criteria": crit,
        "tangent_cells": [record_tangent_row(r) for r in out["tangent"]],
        "carriers": [record_operator_row(r) for r in out["carriers"]],
        "variant_carriers": [record_operator_row(r) for r in out["variant_carriers"]],
        "against_injection_record": [record_plain_row(r) for r in out["record"]],
        "duration": [record_plain_row(r) for r in out["duration"]],
        "variants": [record_plain_row(r) for r in out["variants"]],
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the readouts are not yet "
                                    "written into RESULTS.md.")
    RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"\nwrote {RECORD.name}")


# --------------------------------------------------------------------------
# the seeded faults


class _NoBillResponse(PathTangent):
    """Seeded fault: the wage bill does not answer layer-2 spending."""

    planted = False

    def _bill_response(self) -> float:
        type(self).planted = True
        return 0.0


class _LeftAtZero(PathTangent):
    """Seeded fault: a node holding exactly zero spends none of a marginal claim."""

    planted = False
    zeros = 0

    def _spends_at_zero(self, after_wages: np.ndarray) -> np.ndarray:
        type(self).planted = True
        type(self).zeros += int((after_wages == 0.0).sum())
        return after_wages > 0.0


class _NoIssuanceResponse(PathTangent):
    """Seeded fault: the carrier's issuance does not answer layer-2 inflow."""

    planted = False

    def _issuance_response(self, layer2_inflow: float) -> float:
        type(self).planted = True
        return 0.0


class _CapIgnored(PathTangent):
    """Seeded fault: every payer pays its share of the marginal bill, covered or not."""

    planted = False
    capped = 0

    def _capped(self, held: np.ndarray, share: float) -> np.ndarray:
        type(self).planted = True
        type(self).capped += int((held < share).sum())
        return np.zeros(held.shape, dtype=bool)


class _NoRenormalize(MeanField):
    """Seeded fault: routes into departed nodes are removed and the rest not rescaled."""

    planted = False

    def _routes(self, alive: np.ndarray) -> np.ndarray:
        type(self).planted = True
        return self.route0 * alive[None, :]


class _ReceiverSplitByPayers(MeanField):
    """Seeded fault: what a capped payer passes on is divided by the payers' count."""

    planted = False

    def _receiver_share(self, capped: float) -> float:
        type(self).planted = True
        return capped / self.payers.size


class _TwoTradingNodesStill(MeanField):
    """Seeded fault: two trading financial nodes with routes spend nothing.

    Two, because one such node is a single closed class and the stationary
    vector stays unique (all of it on that node): that is a wrong map, which the
    readouts against the injection record see, and not a second stationary
    split, which is what this clause reads. Two still nodes that both receive
    make two closed classes."""

    planted = False

    def _spenders(self, q: np.ndarray) -> np.ndarray:
        l1 = np.asarray(self.path.net._l1, dtype=int)
        receives = (self.route0 * self.alive[None, :]).sum(axis=0) > 0
        movable = l1[(q[l1] > 0.0) & receives[l1]]
        if movable.size >= 2:
            type(self).planted = True
            q = q.copy()
            q[movable[:2]] = 0.0
        return q


class _DeviationWithoutProjector(MeanField):
    """Seeded fault: the deviation matrix leaves the stationary term in."""

    planted = False

    def _deviation(self, block, proj, fundamental):
        type(self).planted = True
        return block @ fundamental


def selftest_gate() -> bool:
    ok = []
    res = run_gate()
    ok.append(res.ok)
    print(f"--- clean gate passes: {res.ok}\n")
    _ExtraDrawRecorder.extra = 0
    res = run_gate(_ExtraDrawRecorder)
    planted = _ExtraDrawRecorder.extra > 0
    seen_fields = any(r["fields"] for r in res.rows)
    seen_gens = any(r["generators"] for r in res.rows)
    ok.append(planted and not res.ok and seen_fields and seen_gens)
    print(f"--- fault: one draw more   planted: {planted} "
          f"({_ExtraDrawRecorder.extra} extra draws)   caught: {not res.ok}, on "
          f"fields {seen_fields}, on generator states {seen_gens}\n")

    _LastRoundDrawRecorder.extra = 0
    res = run_gate(_LastRoundDrawRecorder)
    planted = _LastRoundDrawRecorder.extra == len(res.rows)
    seen_fields = any(r["fields"] for r in res.rows)
    seen_gens = all(r["generators"] for r in res.rows)
    ok.append(planted and not res.ok and seen_gens and not seen_fields)
    print(f"--- fault: one read after the last draw   planted: {planted} "
          f"({_LastRoundDrawRecorder.extra} reads in {len(res.rows)} runs)   "
          f"caught: {not res.ok}, on generator states in every run {seen_gens}, "
          f"fields untouched {not seen_fields}\n")
    return all(ok)


def selftest_tangent() -> bool:
    """A44-1 passes on clean cells and fails on each seeded fault. Each fault's
    planting is read off the control's path, which the criterion does not read."""
    ok = []
    cells = []
    # Seed 1 carries a payer that is capped in some rounds and not in others,
    # the one condition under which reading the state a round late shows; seed
    # 2 under the higher floor carries a payer that has left the market.
    for seed, wall in ((0, 0.0), (0, 0.06), (1, 0.0), (2, 0.06)):
        path = record_path(seed, wall)
        for (s, w, t) in tangent_cells((seed,)):
            if w == wall:
                cells.append((path, t, fd_gain(path, t)))
    clean = [tangent_row(p, t, fd) for p, t, fd in cells]
    got = criterion_tangent(clean)
    ok.append(got["passed"])
    print(f"A44-1 clean on {len(clean)} cells: passes {got['passed']}, largest "
          f"class difference {max(r['class_diff'] for r in clean):.2e}")

    faults = []
    _NoBillResponse.planted = False
    rows = [tangent_row(p, t, fd, _NoBillResponse) for p, t, fd in cells]
    slope = PathTangent(cells[0][0]).bill_slope
    faults.append(("the bill does not answer spending", _NoBillResponse.planted
                   and slope > 0.0, f"bill slope {slope:.4f}", rows))

    _LeftAtZero.planted, _LeftAtZero.zeros = False, 0
    rows = [tangent_row(p, t, fd, _LeftAtZero) for p, t, fd in cells]
    faults.append(("zero holdings spend nothing", _LeftAtZero.planted
                   and _LeftAtZero.zeros > 0,
                   f"{_LeftAtZero.zeros} node-rounds at exactly zero", rows))

    _NoIssuanceResponse.planted = False
    rows = [tangent_row(p, t, fd, _NoIssuanceResponse) for p, t, fd in cells]
    issuing = sum(int((p.hist.issuance[OPEN_FROM:] > 0.0).sum())
                  for p in {id(c[0]): c[0] for c in cells}.values())
    faults.append(("issuance does not answer inflow",
                   _NoIssuanceResponse.planted and issuing > 0,
                   f"{issuing} issuing rounds across the carriers", rows))

    _CapIgnored.planted, _CapIgnored.capped = False, 0
    rows = [tangent_row(p, t, fd, _CapIgnored) for p, t, fd in cells]
    faults.append(("capped payers pay the bill share", _CapIgnored.planted
                   and _CapIgnored.capped > 0,
                   f"{_CapIgnored.capped} capped payer-rounds", rows))

    for label, planted, note, rows in faults:
        got = criterion_tangent(rows)
        worst = max(r["class_diff"] for r in rows)
        ok.append(planted and not got["passed"])
        print(f"  {label:36s} planted {planted} ({note})   A44-1 passed="
              f"{got['passed']} (want False), largest difference {worst:.2e}")
    got = criterion_tangent([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no cells at all                      Void and not passed: {ok[-1]}")
    return all(ok)


def selftest_operator() -> bool:
    """A44-2 passes on clean carriers and fails on each seeded fault."""
    ok = []
    paths = [record_path(seed, wall) for seed in (0, 1, 2) for wall in WALLS]

    def targets_of(p):
        return [t for (s, w, t) in tangent_cells((p.seed,)) if w == p.wall]

    clean = [operator_row(p, targets_of(p)) for p in paths]
    got = criterion_operator(clean)
    ok.append(got["passed"])
    print(f"A44-2 clean on {len(clean)} carriers: passes {got['passed']}")

    def routes_into_departed(p):
        alive = p.alive_rows[-1]
        route0 = np.asarray(p.net._route, dtype=float)
        return int((route0[alive][:, ~alive] > 0).sum())

    def caught(rows, clause):
        got = criterion_operator(rows)
        failed = set().union(*(operator_clauses(r) for r in rows)) if rows else set()
        return (not got["passed"]) and clause in failed, got["passed"], sorted(failed)

    departed = [p for p in paths if routes_into_departed(p) > 0]
    _NoRenormalize.planted = False
    rows = [operator_row(p, targets_of(p), _NoRenormalize) for p in departed[:1]]
    planted = _NoRenormalize.planted and bool(departed)
    note = (f"seed {departed[0].seed} wall {departed[0].wall}, "
            f"{routes_into_departed(departed[0])} routes into departed nodes"
            if departed else "no carrier with a route into a departed node")
    hit, passed, failed = caught(rows, "conserve")
    ok.append(planted and hit)
    print(f"  routes not rescaled          planted {planted} ({note})   A44-2 "
          f"passed={passed} (want False), clauses {failed} (want conserve)")

    _ReceiverSplitByPayers.planted = False
    rows = [operator_row(paths[0], targets_of(paths[0]), _ReceiverSplitByPayers)]
    capped = operator_row(paths[0], targets_of(paths[0]))["capped_payers"]
    planted = _ReceiverSplitByPayers.planted and capped > 0
    hit, passed, failed = caught(rows, "conserve")
    ok.append(planted and hit)
    print(f"  pass-on split by payers      planted {planted} ({capped} payers "
          f"capped in some round)   A44-2 passed={passed} (want False), "
          f"clauses {failed} (want conserve)")

    _TwoTradingNodesStill.planted = False
    rows = [operator_row(paths[0], targets_of(paths[0]), _TwoTradingNodesStill)]
    hit, passed, failed = caught(rows, "unit")
    ok.append(_TwoTradingNodesStill.planted and hit)
    print(f"  two trading nodes still      planted {_TwoTradingNodesStill.planted} "
          f"(unit eigenvalues {rows[0]['unit_eigenvalues']})   A44-2 passed="
          f"{passed} (want False), clauses {failed} (want unit)")

    _DeviationWithoutProjector.planted = False
    rows = [operator_row(paths[0], targets_of(paths[0]),
                         _DeviationWithoutProjector)]
    hit, passed, failed = caught(rows, "identity")
    ok.append(_DeviationWithoutProjector.planted and hit)
    print(f"  stationary term left in      planted "
          f"{_DeviationWithoutProjector.planted} (identity "
          f"{rows[0]['identity_err']:.2e})   A44-2 passed={passed} "
          f"(want False), clauses {failed} (want identity)")

    got = criterion_operator([])
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no carriers at all           Void and not passed: {ok[-1]}")
    return all(ok)


def _print_criteria(crit: list[dict]) -> None:
    print()
    for x in crit:
        print(f"  {'PASS' if x['passed'] else 'FAIL'}[{x['kind']}] {x['name']}")
        print(f"        {x['detail'][:700]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true", help="A44-0")
    ap.add_argument("--selftest", action="store_true",
                    help="seeded faults the gate and the criteria must catch")
    ap.add_argument("--check", action="store_true",
                    help="A44-1 and A44-2 on the default carriers, nothing written")
    ap.add_argument("--run", action="store_true",
                    help="A44-1, A44-2 and the four readouts")
    ap.add_argument("--smoke", action="store_true",
                    help="with --check or --run: seed 0 only, nothing written")
    ap.add_argument("--no-write", action="store_true",
                    help="with --run: write nothing")
    args = ap.parse_args()

    if args.selftest:
        a = selftest_gate()
        print("tangent selftest:")
        b = selftest_tangent()
        print("\noperator selftest:")
        c = selftest_operator()
        print("\nselftest:", "PASS" if (a and b and c) else "FAIL")
        return 0 if (a and b and c) else 1
    if args.gate:
        return 0 if run_gate().ok else 1
    if args.check:
        tan_rows, op_rows = run_check(SEEDS[:1] if args.smoke else SEEDS)
        crit = [criterion_tangent(tan_rows), criterion_operator(op_rows)]
        _print_criteria(crit)
        print_check(tan_rows, op_rows)
        print("\n(--check: nothing written)")
        return 0 if all(x["passed"] for x in crit) else 1
    if args.run:
        out = run_all(SEEDS[:1] if args.smoke else SEEDS)
        carriers = out["carriers"] + out["variant_carriers"]
        crit = [criterion_tangent(out["tangent"]), criterion_operator(carriers)]
        _print_criteria(crit)
        print_check(out["tangent"], carriers)
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
