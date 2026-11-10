"""A53: A50's wage lock put on A44's carrier. Block one: the full model.

A50 read that locking a share of wages in an account raises the production
layer's net-worth share only because the authority reissues what the lock
takes out of circulation, and that with no issuance the account drains the
economy. A44 and A45 read, on a different carrier, where a new claim settles
and how long it stays: a class holds its inflow divided by its outflow rate.

This station puts the lock on A44's carrier so that the two can be read in one
place. Block one runs the full model only. The mean-field decomposition is
block two.

**The lock.** Each wage earner moves ``c`` of the wages it received this round
into its own account, after wages are paid and before discretionary spending,
the same position ``ParkSpec`` uses. Each deposit comes back to its owner's
holdings, whole, ``hold`` rounds later, at the same position; ``hold = None``
never returns. The account is kept in the network's parked stock, so the
module's own conservation assertion counts it, and it is owned by the node
that paid it in. ``ParkSpec`` itself stays off: its targets are the financial
layer, everyone, or the recapitalised set, and its release is keyed to the
circulation shortfall rather than to a clock.

**With ``c = 0`` the subclass is the network, bit for bit** (A53-0).

Run from the repository root with the project's virtual environment:

    python experiments/a53_wage_lock.py --selftest
    python experiments/a53_wage_lock.py --run --no-write [--smoke]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import Network, NetworkConfig  # noqa: E402

#: A44's carrier and classes, imported rather than restated.
from a41_same_ticket import (  # noqa: E402
    ALL_CLASSES,
    ELASTICITY,
    ROUNDS,
    SEEDS,
    base_config,
    classes_of,
    diff_fields,
    _record_value,
)

CLOSED = True
RESULTS = ROOT / "results"
RECORD = RESULTS / "a53_wage_lock.json"

#: The grid. ``None`` in HOLDS is "never returned".
SHARES = (0.05, 0.12)
HOLDS = (1, 5, 25, 100, None)
AUTHORITIES = ("endogenous", "none")
#: The station's declared knob: A44 I3 already varies the wage elasticity.
ELASTICITIES = (ELASTICITY, 0.0, 1.0)

#: A cell whose last fifty rounds paid less than half the wages its own
#: control paid has stalled, and its share gap is not read as distribution.
#: Against the control rather than against the bill owed: with a wage
#: elasticity the bill owed falls with layer-2 spending, so paid over owed
#: stays near one while the wages actually paid collapse.
TAIL = 50
STALL = 0.5

TOL_LEDGER = 1e-9

FAULTS = ("off_ignored", "extra_draw", "before_wages", "on_holdings",
          "half_release")


# --------------------------------------------------------------------------
# the lock


class LockNetwork(Network):
    """The network with a wage lock. ``fault`` is for the selftest only."""

    def __init__(self, config: NetworkConfig, c: float = 0.0,
                 hold: int | None = None, fault: str | None = None,
                 start: int = 0) -> None:
        super().__init__(config)
        if not 0.0 <= c < 1.0:
            raise ValueError("c must lie in [0, 1)")
        if hold is not None and hold < 1:
            raise ValueError("hold must be at least one round, or None")
        if fault is not None and fault not in FAULTS:
            raise ValueError(f"unknown fault {fault!r}")
        self.lock_c = float(c)
        self.lock_hold = hold
        self._fault = fault
        self.lock_start = int(start)
        self._lock_round = 0
        self._wage_in = np.zeros(self._n)
        self._prev_wage_in = np.zeros(self._n)
        self._vintages: list[np.ndarray] = []
        rounds = config.rounds
        self.lock_deposit = np.zeros(rounds)
        self.lock_release = np.zeros(rounds)
        self.lock_account = np.zeros((rounds, self._n))
        self.lock_deposit_vec = np.zeros((rounds, self._n))
        self.lock_release_vec = np.zeros((rounds, self._n))

    def _wage_flow(self):
        matrix, bill = super()._wage_flow()
        self._prev_wage_in = self._wage_in
        # Column sums of the wage matrix are what each node received; the
        # sum is read-only, so with the lock off nothing changes.
        self._wage_in = matrix.sum(axis=0)
        return matrix, bill

    def _park_claims(self) -> None:
        super()._park_claims()
        t = self._lock_round
        self._lock_round += 1
        c = self.lock_c
        if c == 0.0:
            if self._fault == "extra_draw":
                self.rng.uniform()
            if self._fault != "off_ignored":
                return
            c = 0.05
        if t < self.lock_start:
            self._vintages.append(np.zeros(self._n))
            return
        hold = self.lock_hold
        if hold is not None and t - hold >= self.lock_start:
            back = self._vintages[t - hold]
            if self._fault == "half_release":
                back = 0.5 * back
            self.holdings += back
            self._parked -= back
            self.lock_release[t] = float(back.sum())
            self.lock_release_vec[t] = back
        if self._fault == "before_wages":
            base = self._prev_wage_in
        elif self._fault == "on_holdings":
            base = np.maximum(self.holdings, 0.0) * (self._wage_in > 0.0)
        else:
            base = self._wage_in
        dep = np.minimum(c * np.maximum(base, 0.0),
                         np.maximum(self.holdings, 0.0))
        self.holdings -= dep
        self._parked += dep
        self._vintages.append(dep)
        self.lock_deposit[t] = float(dep.sum())
        self.lock_deposit_vec[t] = dep
        self.lock_account[t] = self._parked


def cell_config(seed: int, authority: str, elasticity: float) -> NetworkConfig:
    cfg = base_config(seed)
    if authority != cfg.authority.rule:
        cfg = dataclasses.replace(
            cfg, authority=dataclasses.replace(cfg.authority, rule=authority))
    if elasticity != cfg.wages.elasticity:
        cfg = dataclasses.replace(
            cfg, wages=dataclasses.replace(cfg.wages, elasticity=elasticity))
    return cfg


def run_lock(seed: int, authority: str, elasticity: float, c: float,
             hold: int | None, fault: str | None = None):
    net = LockNetwork(cell_config(seed, authority, elasticity), c, hold, fault)
    hist = net.run()
    return net, hist


# --------------------------------------------------------------------------
# A53-0: the lock off is the network


def criterion_off(seeds=SEEDS, fault: str | None = None) -> dict:
    bad = []
    for seed in seeds:
        cfg = base_config(seed)
        plain = Network(cfg)
        hp = plain.run()
        lock = LockNetwork(cfg, 0.0, None, fault)
        hl = lock.run()
        fields = diff_fields(hp, hl)
        if plain.rng.bit_generator.state != lock.rng.bit_generator.state:
            fields.append("generator state")
        if fields:
            bad.append((seed, fields))
    return {"name": "A53-0  the lock off is the network: with c = 0 every "
                    "history field and the generator state match bit for bit",
            "kind": "instrument", "passed": not bad,
            "detail": ("c = 0 reproduces the network bit for bit on seeds "
                       f"{list(seeds)}" if not bad else f"differs: {bad}")}


# --------------------------------------------------------------------------
# A53-1: the ledger


def ledger_problems(net: LockNetwork, hist, authority: str) -> list[str]:
    out = []
    c = net.lock_c
    hold = net.lock_hold
    m0 = float(net.config.initial_claims)
    held = np.asarray(hist.holdings, dtype=float).sum(axis=1)
    acct = net.lock_account.sum(axis=1)
    issued = np.cumsum(np.asarray(hist.issuance, dtype=float))
    scale = max(1.0, float(np.max(held + acct)) / m0)
    if np.max(np.abs(held + acct - (m0 + issued))) > TOL_LEDGER * m0 * scale:
        out.append("holdings plus accounts against claims plus issuance")
    paid = np.asarray(hist.wage_paid, dtype=float)
    if np.max(np.abs(net.lock_deposit - c * paid)) > TOL_LEDGER * scale:
        out.append("deposit against c times the wages paid")
    expect = np.zeros_like(net.lock_release)
    if hold is not None and hold < len(expect):
        expect[hold:] = net.lock_deposit[:-hold]
    if np.max(np.abs(net.lock_release - expect)) > TOL_LEDGER * scale:
        out.append("release against the deposit hold rounds earlier")
    book = np.cumsum(net.lock_deposit) - np.cumsum(net.lock_release)
    if np.max(np.abs(acct - book)) > TOL_LEDGER * scale:
        out.append("account against deposits less releases")
    # Per node: each deposit is c of that earner's equal share of the bill
    # paid, and each release goes back to the node that paid it in.
    recv = np.asarray(net._wage_receivers, dtype=int)
    want = np.zeros_like(net.lock_deposit_vec)
    want[:, recv] = (c * paid / recv.size)[:, None]
    if np.max(np.abs(net.lock_deposit_vec - want)) > TOL_LEDGER * scale:
        out.append("deposit per node against the earner's wage")
    want_rel = np.zeros_like(net.lock_release_vec)
    if hold is not None and hold < len(want_rel):
        want_rel[hold:] = net.lock_deposit_vec[:-hold]
    if np.max(np.abs(net.lock_release_vec - want_rel)) > TOL_LEDGER * scale:
        out.append("release per node against its owner's deposit")
    per_node = (np.cumsum(net.lock_deposit_vec, axis=0)
                - np.cumsum(net.lock_release_vec, axis=0))
    if np.max(np.abs(net.lock_account - per_node)) > TOL_LEDGER * scale:
        out.append("account per node against its deposits less releases")
    if net.lock_account.min() < -TOL_LEDGER:
        out.append("negative account")
    if authority == "none" and np.any(np.asarray(hist.issuance) != 0.0):
        out.append("issuance under no authority")
    return out


def criterion_ledger(cells: list[tuple], fault: str | None = None) -> dict:
    """``cells`` are (seed, authority, elasticity, c, hold). Every hold of 300
    is also run against never, which on 300 rounds is the same run."""
    bad = []
    for seed, auth, el, c, hold in cells:
        net, hist = run_lock(seed, auth, el, c, hold, fault)
        probs = ledger_problems(net, hist, auth)
        if probs:
            bad.append(((seed, auth, el, c, hold), probs))
    for seed in sorted({cell[0] for cell in cells}):
        n1, h1 = run_lock(seed, "endogenous", ELASTICITY, 0.12, ROUNDS, fault)
        n2, h2 = run_lock(seed, "endogenous", ELASTICITY, 0.12, None, fault)
        fields = diff_fields(h1, h2)
        for name in ("lock_deposit", "lock_release", "lock_account"):
            if not np.array_equal(getattr(n1, name), getattr(n2, name)):
                fields.append(name)
        if fields:
            bad.append(((seed, "hold 300 against never"), fields))
    return {"name": "A53-1  the lock's ledger closes: holdings and accounts "
                    "against claims and issuance, each deposit c of its "
                    "earner's wage, each release its owner's deposit hold "
                    "rounds earlier, a hold of 300 the never-returned run",
            "kind": "instrument", "passed": not bad,
            "detail": (f"ledger closes on {len(cells)} cells, and a hold of "
                       f"{ROUNDS} is the never-returned run" if not bad
                       else f"fails: {bad[:4]}")}


# --------------------------------------------------------------------------
# readings


def shares(net: Network, hist, account: np.ndarray, t: int) -> dict:
    cls = classes_of(net)
    held = np.asarray(hist.holdings[t], dtype=float)
    with_acct = held + account
    out = {}
    for tag, vec in (("net", with_acct), ("circ", held)):
        total = float(vec.sum())
        for c_ in ALL_CLASSES:
            out[f"{tag}_{c_}"] = float(vec[cls[c_]].sum()) / total
        out[f"{tag}_l2"] = 1.0 - out[f"{tag}_l1"]
    return out


def reading(seed: int, auth: str, el: float, c: float, hold: int | None,
            control: dict) -> dict:
    net, hist = run_lock(seed, auth, el, c, hold)
    probs = ledger_problems(net, hist, auth)
    t = ROUNDS - 1
    acct_vec = net.lock_account[t]
    row = {"seed": seed, "auth": auth, "el": el, "c": c, "hold": hold,
           "ledger": probs}
    row.update(shares(net, hist, acct_vec, t))
    acct = float(acct_vec.sum())
    window = ROUNDS if hold is None else min(hold, ROUNDS)
    paid = np.asarray(hist.wage_paid, dtype=float)
    little = c * float(paid[-window:].mean()) * window
    issued = float(np.asarray(hist.issuance, dtype=float).sum())
    owed = np.asarray(hist.wage_owed, dtype=float)
    row.update({
        "account": acct,
        "little": little,
        "deposited": float(net.lock_deposit.sum()),
        "issued": issued,
        "reissue_per_deposit": ((issued - control["issued"])
                                / max(float(net.lock_deposit.sum()), 1e-300)),
        "reissue_per_account": (issued - control["issued"]) / max(acct, 1e-300),
        "circ_m_ratio": float(hist.holdings[t].sum()) / float(
            net.config.initial_claims),
        "tail_paid_over_owed": float(paid[-TAIL:].sum()
                                     / max(owed[-TAIL:].sum(), 1e-300)),
        "tail_paid_over_control": float(paid[-TAIL:].sum()
                                        / max(control["tail_paid"], 1e-300)),
    })
    row["stalled"] = row["tail_paid_over_control"] < STALL
    row["series"] = {"deposit": net.lock_deposit.copy(),
                     "release": net.lock_release.copy(),
                     "issuance": np.asarray(hist.issuance, dtype=float).copy()}
    for k in ("net_l2", "circ_l2", "net_l1", "net_earners", "net_mid",
              "net_unreached"):
        row[f"d_{k}"] = row[k] - control[k]
    # Where the extra claims sit, in claims, against the control.
    cls = classes_of(net)
    held = np.asarray(hist.holdings[t], dtype=float)
    for c_ in ALL_CLASSES:
        row[f"dclaims_{c_}"] = (float(held[cls[c_]].sum())
                                - control[f"claims_{c_}"])
    return row


def control_row(seed: int, auth: str, el: float) -> dict:
    net, hist = run_lock(seed, auth, el, 0.0, None)
    t = ROUNDS - 1
    row = shares(net, hist, np.zeros(net._n), t)
    row["issued"] = float(np.asarray(hist.issuance, dtype=float).sum())
    row["issuance"] = np.asarray(hist.issuance, dtype=float).copy()
    row["tail_paid"] = float(np.asarray(hist.wage_paid, dtype=float)[-TAIL:]
                             .sum())
    row["tail_paid_over_owed"] = float(
        row["tail_paid"] / np.asarray(hist.wage_owed, dtype=float)[-TAIL:]
        .sum())
    cls = classes_of(net)
    held = np.asarray(hist.holdings[t], dtype=float)
    for c_ in ALL_CLASSES:
        row[f"claims_{c_}"] = float(held[cls[c_]].sum())
    return row


def grid_rows(seeds, elasticities, tick=None) -> tuple[list, dict]:
    rows, controls = [], {}
    for el in elasticities:
        shares_ = SHARES if el == ELASTICITY else (0.12,)
        for auth in AUTHORITIES:
            for seed in seeds:
                ctl = control_row(seed, auth, el)
                controls[(seed, auth, el)] = ctl
                for c in shares_:
                    for hold in HOLDS:
                        rows.append(reading(seed, auth, el, c, hold, ctl))
                        if tick:
                            tick()
    return rows, controls



# --------------------------------------------------------------------------
# block two: the lock's path tangent (A53-2) and the mean field (A53-4)

from a44_occupation_operator import (  # noqa: E402
    MeanField,
    PathTangent,
    record_path,
)

#: A53-2's step: a deposit of about ``8e-8`` a round, the scale of A44-1's
#: ``1e-7`` injection, so no payer crosses its cap and no round crosses the
#: issuance floor.
FD_C = 1e-8
TOL_TANGENT = 1e-5
TANGENT_START = 1
TANGENT_FAULTS = ("late", "spread", "owed")


class LockTangent(PathTangent):
    """A44's path tangent with the lock's forcing instead of an injection.

    The round is A44's, line for line, with two lines added after the wages
    and before the spending: each earner loses its share of the wages paid
    (per unit of ``c``), and gets back what it paid in ``hold`` rounds
    earlier. To first order in ``c`` the deposit is ``c`` times the control's
    wages paid, since the wages themselves move only at second order.
    """

    def lock_occupation(self, hold: int | None, start: int = TANGENT_START,
                        fault: str | None = None) -> tuple[np.ndarray, float]:
        n = self.n
        payers, receivers = self.payers, self.receivers
        base = (self.owed if fault == "owed"
                else np.asarray(self.path.hist.wage_paid, dtype=float))
        spread = np.flatnonzero(self.l2) if fault == "spread" else receivers
        lag = None if hold is None else hold + (1 if fault == "late" else 0)
        dh = np.zeros(n)
        dep = np.zeros(ROUNDS)
        released = 0.0
        d_spend_l2 = 0.0
        d_pending = 0.0
        for t in range(start, ROUNDS):
            alive = self.path.alive_rows[t - 1]
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
            dep[t] = base[t]
            dh[spread] -= dep[t] / spread.size
            if lag is not None and t - lag >= start:
                dh[receivers] += dep[t - lag] / receivers.size
                released += dep[t - lag]
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
        return dh, float(dep.sum() - released)


def tangent_cell(seed: int, auth: str, el: float, hold: int | None,
                 fault: str | None = None, path=None) -> dict:
    cfg = cell_config(seed, auth, el)
    path = record_path(seed, 0.0, cfg) if path is None else path
    dh, acct = LockTangent(path).lock_occupation(hold, fault=fault)
    lock = LockNetwork(cfg, FD_C, hold, None, start=TANGENT_START)
    lh = lock.run()
    fd = (np.asarray(lh.holdings[-1], dtype=float)
          - np.asarray(path.hist.holdings[-1], dtype=float)) / FD_C
    fd_acct = float(lock.lock_account[-1].sum()) / FD_C
    scale = float(np.asarray(path.hist.wage_paid, dtype=float)
                  [TANGENT_START:].sum())
    cls = path.classes
    diffs = {c_: abs(float(fd[cls[c_]].sum()) - float(dh[cls[c_]].sum()))
             / scale for c_ in ALL_CLASSES}
    diffs["account"] = abs(fd_acct - acct) / scale
    return {"seed": seed, "auth": auth, "el": el, "hold": hold,
            "worst": max(diffs.values()), "diffs": diffs,
            "issued_rounds": int((np.asarray(path.hist.issuance) > 0).sum())}


def criterion_tangent(seeds=SEEDS, elasticities=ELASTICITIES,
                      fault: str | None = None) -> tuple[dict, list]:
    rows = []
    for el in elasticities:
        for auth in AUTHORITIES:
            for seed in seeds:
                path = record_path(seed, 0.0, cell_config(seed, auth, el))
                for hold in (5, None):
                    rows.append(tangent_cell(seed, auth, el, hold, fault,
                                             path))
    worst = max(r["worst"] for r in rows)
    ok = worst <= TOL_TANGENT
    return ({"name": "A53-2  the lock's path tangent is the carrier's rule: "
                     "against the whole model's finite difference, class by "
                     "class, within the tolerance of A44-1",
             "kind": "instrument", "passed": bool(ok),
             "detail": (f"lock path tangent against the whole model at c = "
                        f"{FD_C:g} on {len(rows)} cells, largest class gap "
                        f"over wages paid {worst:.2e} (tolerance "
                        f"{TOL_TANGENT:g})")}, rows)


class LockField:
    """A44's mean field, opened into its steps so a forcing can be applied
    between the wages and the spending.

    The steps are rebuilt from the mean field's own parts and checked against
    its matrix. The round is: reissue lands on the injection node, wages move
    with ``B`` and the bill term, the lock takes and returns at the earners,
    spending moves with ``G``.
    """

    def __init__(self, path) -> None:
        mf = MeanField(path)
        net = path.net
        n = mf.n
        if not mf.alive.all():
            raise ValueError("the lock's mean field is built with every node "
                             "trading")
        pbar = 0.5 * (np.asarray(net._p_low, dtype=float)
                      + np.asarray(net._p_high, dtype=float))
        reach = (mf.route0 * mf.alive[None, :]).sum(axis=1) > 0
        q = pbar * mf.has_out * mf.alive * reach
        R = mf._routes(mf.alive)
        G = np.eye(n) - np.diag(q) + R.T * q[None, :]
        B = np.eye(n)
        for k, j in enumerate(mf.payers):
            B[j, j] -= mf.capped[k]
            B[mf.receivers, j] += mf.capped[k] / mf.receivers.size
        bill_part = np.zeros(n)
        bill_part[mf.payers] -= (1.0 - mf.capped) / mf.payers.size
        bill_part[mf.receivers] += ((1.0 - mf.capped).sum()
                                    / mf.payers.size / mf.receivers.size)
        l2 = np.zeros(n, dtype=bool)
        l2[np.asarray(net._l2, dtype=int)] = True
        spend_l2 = l2 * q
        self.rebuild_gap = max(
            float(np.abs(G @ B - mf.A[:n, :n]).max()),
            float(np.abs((G @ bill_part) * mf.bill_slope - mf.A[:n, n]).max()),
            float(np.abs(spend_l2 @ B - mf.A[n, :n]).max()))
        self.n, self.G, self.B = n, G, B
        self.bill_col = bill_part * mf.bill_slope
        self.spend_l2 = spend_l2
        self.top = int(net.injection_node)
        self.receivers = mf.receivers
        self.classes = path.classes
        self.mf = mf

    def propagate(self, reissue: np.ndarray, lock: np.ndarray) -> np.ndarray:
        """End-of-run holdings gap for a reissue series (claims landing on the
        injection node at the start of each round) and a lock series (net
        claims put back at the earners after the wages: release minus
        deposit)."""
        x = np.zeros(self.n)
        s = 0.0
        for t in range(ROUNDS):
            x[self.top] += reissue[t]
            y = self.B @ x + self.bill_col * s
            y[self.receivers] += lock[t] / self.receivers.size
            s = float(self.spend_l2 @ y)
            x = self.G @ y
        return x


def decompose(row: dict, ctl: dict, field: LockField) -> dict:
    ser = row["series"]
    reissue = ser["issuance"] - ctl["issuance"]
    lock = ser["release"] - ser["deposit"]
    parts = {"reissue": field.propagate(reissue, np.zeros(ROUNDS)),
             "lock": field.propagate(np.zeros(ROUNDS), lock)}
    parts["both"] = parts["reissue"] + parts["lock"]
    cls = field.classes
    m_ctl = sum(ctl[f"claims_{c_}"] for c_ in ALL_CLASSES)
    l2_ctl = m_ctl - ctl["claims_l1"]
    a = row["account"]
    s_ctl = l2_ctl / m_ctl
    base = (l2_ctl + a) / (m_ctl + a)
    out = {"stock": base - s_ctl, "circ": row["d_net_l2"] - (base - s_ctl)}
    for k, x in parts.items():
        dl2 = float(x.sum() - x[cls["l1"]].sum())
        dm = float(x.sum())
        out[f"circ_mf_{k}"] = (l2_ctl + dl2 + a) / (m_ctl + dm + a) - base
        for c_ in ALL_CLASSES:
            out[f"mf_{k}_{c_}"] = float(x[cls[c_]].sum())
    out["resid"] = out["circ"] - out["circ_mf_both"]
    loss_l1, loss_mid = -out["mf_both_l1"], -out["mf_both_mid"]
    out["mf_loss_l1_share"] = (loss_l1 / (loss_l1 + loss_mid)
                               if loss_l1 + loss_mid > 0 else float("nan"))
    m_l1, m_mid = -row["dclaims_l1"], -row["dclaims_mid"]
    out["loss_l1_share"] = (m_l1 / (m_l1 + m_mid)
                            if m_l1 + m_mid > 0 else float("nan"))
    pi, _ = field.mf.stationary()
    pos = {int(node): k for k, node in enumerate(field.mf.live[:-1])}
    pl1 = sum(pi[pos[int(i)]] for i in cls["l1"])
    pmid = sum(pi[pos[int(i)]] for i in cls["mid"])
    out["pi_l1_share"] = pl1 / (pl1 + pmid)
    return out


def decompose_rows(rows: list[dict], controls: dict) -> list[dict]:
    fields = {}
    out = []
    for r in rows:
        key = (r["seed"], r["auth"], r["el"])
        if key not in fields:
            fields[key] = LockField(record_path(
                r["seed"], 0.0, cell_config(*key)))
        d = decompose(r, controls[key], fields[key])
        d.update({k: r[k] for k in ("seed", "auth", "el", "c", "hold",
                                    "stalled", "d_net_l2")})
        d["rebuild_gap"] = fields[key].rebuild_gap
        for c_ in ALL_CLASSES:
            d[f"meas_{c_}"] = r[f"dclaims_{c_}"]
        out.append(d)
    return out


def print_decomposition(drows: list[dict]) -> None:
    cells = {}
    for d in drows:
        cells.setdefault((d["el"], d["auth"], d["c"], _hold(d["hold"])),
                         []).append(d)
    order = sorted(cells, key=lambda k: (k[0], k[1], k[2],
                                         HOLDS.index(None if k[3] == "never"
                                                     else int(k[3]))))
    gap = max(d["rebuild_gap"] for d in drows)
    print(f"\nrebuilt mean-field steps against A44's matrix: largest gap "
          f"{gap:.1e}")
    print("\nR4  gap in production share = stock + circulation; circulation "
          "measured against the mean field (medians over seeds)")
    print("    mf split into the reissue branch and the lock branch; "
          "resid = circ - mf; stalled cells counted")
    for key in order:
        ds = cells[key]
        el, auth, c, hold = key
        med = lambda k: float(np.median([d[k] for d in ds]))  # noqa: E731
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}:"
              f" total {med('d_net_l2'):+.4f} stock {med('stock'):+.4f}"
              f" circ {med('circ'):+.4f} | mf {med('circ_mf_both'):+.4f}"
              f" (reissue {med('circ_mf_reissue'):+.4f}"
              f" lock {med('circ_mf_lock'):+.4f})"
              f" resid {med('resid'):+.4f}"
              f"  stalled {sum(d['stalled'] for d in ds)}/{len(ds)}")
    print("\nR6  the mean field's two branches in claims by class (medians): "
          "reissue branch | lock branch")
    for key in order:
        ds = cells[key]
        el, auth, c, hold = key
        med = lambda k: float(np.median([d[k] for d in ds]))  # noqa: E731
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}:"
              + "".join(f" {c_[:4]} {med(f'mf_reissue_{c_}'):+8.3f}"
                        for c_ in ALL_CLASSES)
              + " |"
              + "".join(f" {c_[:4]} {med(f'mf_lock_{c_}'):+8.3f}"
                        for c_ in ALL_CLASSES))
    print("\nR5  claims gap by class, measured / mean field (medians), and "
          "the l1 share of the l1+mid loss against pi")
    for key in order:
        ds = cells[key]
        el, auth, c, hold = key
        med = lambda k: float(np.median([d[k] for d in ds]))  # noqa: E731
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}:"
              f" l1 {med('meas_l1'):+8.3f}/{med('mf_both_l1'):+8.3f}"
              f" mid {med('meas_mid'):+8.3f}/{med('mf_both_mid'):+8.3f}"
              f" earn {med('meas_earners'):+7.3f}/"
              f"{med('mf_both_earners'):+7.3f}"
              f"  loss l1 share {med('loss_l1_share'):.3f}"
              f" mf {med('mf_loss_l1_share'):.3f}"
              f" pi {med('pi_l1_share'):.3f}")


# --------------------------------------------------------------------------
# A53-3 and A53-4: the printed objects are there, and the record


READ_FIELDS = ("d_net_l2", "account", "little", "reissue_per_account",
               "circ_m_ratio", "tail_paid_over_control")
DECOMP_FIELDS = ("stock", "circ", "circ_mf_both", "resid", "loss_l1_share",
                 "mf_loss_l1_share")


def expected_rows(seeds, elasticities) -> int:
    per = sum(len(SHARES if el == ELASTICITY else (0.12,)) for el in elasticities)
    return per * len(HOLDS) * len(AUTHORITIES) * len(seeds)


def criterion_reading(rows: list[dict], seeds, elasticities) -> dict:
    """Every cell of the grid printed on every seed, its objects finite, its
    ledger closed. A dropped row, an empty ledger or a NaN fails it."""
    want = expected_rows(seeds, elasticities)
    keys = {(r["seed"], r["auth"], r["el"], r["c"], r["hold"]) for r in rows}
    finite = all(math.isfinite(r[k]) for r in rows for k in READ_FIELDS)
    closed = all(not r["ledger"] for r in rows)
    ok = len(rows) == want and len(keys) == want and finite and closed
    return {"name": "A53-3  the lock's readings are printed on every cell and "
                    "seed: shares with and without the account, the account "
                    "against Little, reissue per unit locked, circulation, the "
                    "wage tail against the control",
            "kind": "own_reading", "passed": bool(ok),
            "detail": (f"{len(rows)} of {want} cell-seed rows, "
                       f"{'all finite' if finite else 'NaN present'}, "
                       f"{'every ledger closed' if closed else 'ledger open'}; "
                       f"{sum(r['stalled'] for r in rows)} rows stalled against "
                       "the control and not read as distribution")}


def criterion_decomposition(drows: list[dict], rows: list[dict]) -> dict:
    """Every grid row decomposed, on mean-field steps equal to A44's matrix."""
    finite = all(math.isfinite(d[k]) for d in drows for k in DECOMP_FIELDS
                 if not (k.endswith("l1_share") and math.isnan(d[k])))
    gap = max((d["rebuild_gap"] for d in drows), default=float("nan"))
    ok = (len(drows) == len(rows) and len(rows) > 0 and finite
          and gap == 0.0)
    return {"name": "A53-4  the gap in the production share splits into the "
                    "account stock and a circulation term, and the circulation "
                    "term is read against A44's mean field driven by the "
                    "cell's own deposits, releases and reissue",
            "kind": "own_reading", "passed": bool(ok),
            "detail": (f"{len(drows)} of {len(rows)} rows decomposed; rebuilt "
                       f"mean-field steps against A44's matrix, largest gap "
                       f"{gap:.1e}; the reissue is an input taken from each "
                       "cell's run, the mean field says where it lands")}


def _rv(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    return _record_value(x)


def _within(value: float, tol: float):
    """A residue inside its tolerance is written as the tolerance, since its
    last digits belong to the machine; outside it, as the value."""
    return _rv(tol) if abs(value) <= tol else _rv(value)


CELL_KEYS = ("seed", "auth", "el", "c", "stalled", "account", "deposited",
             "issued", "reissue_per_deposit", "reissue_per_account",
             "circ_m_ratio", "tail_paid_over_owed", "tail_paid_over_control")


def build_record(crits, rows, controls, drows, trows) -> dict:
    dmap = {(d["seed"], d["auth"], d["el"], d["c"], d["hold"]): d
            for d in drows}
    cells = []
    for r in rows:
        key = (r["seed"], r["auth"], r["el"], r["c"], r["hold"])
        d = dmap[key]
        out = {k: _rv(r[k]) for k in CELL_KEYS}
        out["hold"] = _hold(r["hold"])
        for tag in ("net", "circ"):
            for c_ in ALL_CLASSES + ("l2",):
                out[f"{tag}_{c_}"] = _rv(r[f"{tag}_{c_}"])
        for k in ("d_net_l2", "d_circ_l2"):
            out[k] = _rv(r[k])
        out["account_against_little"] = _within(
            r["account"] / r["little"] - 1.0 if r["little"] else 0.0, 1e-12)
        for c_ in ALL_CLASSES:
            out[f"dclaims_{c_}"] = _rv(r[f"dclaims_{c_}"])
            for k in ("reissue", "lock", "both"):
                out[f"mf_{k}_{c_}"] = _rv(d[f"mf_{k}_{c_}"])
        for k in ("stock", "circ", "circ_mf_both", "resid", "loss_l1_share",
                  "mf_loss_l1_share", "pi_l1_share"):
            out[k] = _rv(d[k])
        cells.append(out)
    ctl = []
    for (seed, auth, el), c in sorted(controls.items(),
                                      key=lambda kv: (kv[0][2], kv[0][1],
                                                      kv[0][0])):
        row = {"seed": seed, "auth": auth, "el": _rv(el),
               "net_l2": _rv(c["net_l2"]), "issued": _rv(c["issued"]),
               "tail_paid": _rv(c["tail_paid"]),
               "tail_paid_over_owed": _rv(c["tail_paid_over_owed"])}
        for c_ in ALL_CLASSES:
            row[f"claims_{c_}"] = _rv(c[f"claims_{c_}"])
        ctl.append(row)
    tangent = [{"seed": t["seed"], "auth": t["auth"], "el": _rv(t["el"]),
                "hold": _hold(t["hold"]),
                "issued_rounds": t["issued_rounds"],
                "worst": _within(t["worst"], TOL_TANGENT)} for t in trows]
    rec = {
        "stage": "A53",
        "config": {
            "carrier": "a17_edge_cut.base_config via a41_same_ticket, no wall",
            "rounds": ROUNDS, "seeds": list(SEEDS),
            "lock": ("each wage earner moves c of the wages it received this "
                     "round into its own account, after wages and before "
                     "spending; each deposit returns whole to its owner hold "
                     "rounds later at the same position; the account is the "
                     "network's parked stock, owned by the node that paid in"),
            "shares_c": list(SHARES),
            "holds": [_hold(h) for h in HOLDS],
            "authority.rule": list(AUTHORITIES),
            "wages.elasticity": [_rv(e) for e in ELASTICITIES],
            "knob_cells": ("elasticity 0 and 1 run at c 0.12 only; "
                           "elasticity 0.5 at both shares"),
            "stall": (f"last {TAIL} rounds' wages paid below {STALL} of the "
                      "same seed's control"),
            "tangent_c": FD_C, "tangent_start": TANGENT_START,
            "tangent_tolerance": TOL_TANGENT,
            "tangent_cells": "every seed, elasticity and authority, hold 5 and never",
            "mean_field": ("A44's MeanField, opened into its steps; forcing "
                           "per round: reissue gap against the control at the "
                           "injection node, then wages, then release minus "
                           "deposit at the earners, then spending"),
        },
        "criteria": [{k: c[k] for k in ("name", "kind", "passed", "detail")}
                     for c in crits],
        "controls": ctl,
        "cells": cells,
        "tangent": tangent,
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the readings are not "
                                    "yet written into RESULTS.md.")
    return rec


def write_record(rec: dict, path: Path | None = None) -> None:
    path = RECORD if path is None else path
    text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"\nwrote {path.name}")

# --------------------------------------------------------------------------
# printing


def _hold(h) -> str:
    return "never" if h is None else str(h)


def _signs(vals) -> str:
    s = {int(np.sign(v)) for v in vals if abs(v) > 1e-12}
    if not s:
        return "0"
    return "+" if s == {1} else "-" if s == {-1} else "mixed"


def print_controls(controls: dict) -> None:
    print("\nControls (lock off), per seed: net_l2, issued, tail paid/owed")
    for (seed, auth, el), ctl in sorted(controls.items(),
                                        key=lambda kv: (kv[0][2], kv[0][1],
                                                        kv[0][0])):
        print(f"  el {el:.1f} {auth:10s} seed {seed}: l2 {ctl['net_l2']:.4f}"
              f"  issued {ctl['issued']:9.3f}"
              f"  paid/owed {ctl['tail_paid_over_owed']:.3f}")


def print_rows(rows: list[dict]) -> None:
    cells = {}
    for r in rows:
        cells.setdefault((r["el"], r["auth"], r["c"], _hold(r["hold"])),
                         []).append(r)
    print("\nR1  production-layer share with the account, gap to control, "
          "per seed")
    print("    (seeds 0..4; stalled cells marked *, their gap is not read "
          "as distribution)")
    for key in sorted(cells, key=lambda k: (k[0], k[1], k[2],
                                            HOLDS.index(None if k[3] == "never"
                                                        else int(k[3])))):
        rs = cells[key]
        el, auth, c, hold = key
        gaps = " ".join(f"{r['d_net_l2']:+.4f}{'*' if r['stalled'] else ' '}"
                        for r in rs)
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}: {gaps}"
              f"  sign {_signs([r['d_net_l2'] for r in rs])}"
              f"  circ gap {np.median([r['d_circ_l2'] for r in rs]):+.4f}")
    print("\nR2  account against Little, reissue per unit locked, circulation "
          "(medians over seeds)")
    for key in sorted(cells, key=lambda k: (k[0], k[1], k[2],
                                            HOLDS.index(None if k[3] == "never"
                                                        else int(k[3])))):
        rs = cells[key]
        el, auth, c, hold = key
        med = lambda k: float(np.median([r[k] for r in rs]))  # noqa: E731
        ratio = max(abs(r["account"] / r["little"] - 1.0) for r in rs
                    if r["little"] > 0) if any(r["little"] > 0 for r in rs) \
            else float("nan")
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}:"
              f" account {med('account'):8.3f}"
              f"  |acct/Little-1| max {ratio:.1e}"
              f"  reissue/deposit {med('reissue_per_deposit'):6.3f}"
              f"  reissue/account {med('reissue_per_account'):6.3f}"
              f"  circ M/M0 {med('circ_m_ratio'):6.3f}")
    print("\nR3  where the claims sit against control (medians, claims), and "
          "the wage tail")
    for key in sorted(cells, key=lambda k: (k[0], k[1], k[2],
                                            HOLDS.index(None if k[3] == "never"
                                                        else int(k[3])))):
        rs = cells[key]
        el, auth, c, hold = key
        med = lambda k: float(np.median([r[k] for r in rs]))  # noqa: E731
        print(f"  el {el:.1f} {auth:10s} c {c:.2f} hold {hold:>5s}:"
              f" l1 {med('dclaims_l1'):+8.3f} mid {med('dclaims_mid'):+8.3f}"
              f" earn {med('dclaims_earners'):+8.3f}"
              f" unr {med('dclaims_unreached'):+8.3f}"
              f" acct {med('account'):8.3f}"
              f"  paid/owed {med('tail_paid_over_owed'):.3f}"
              f"  paid/ctl {med('tail_paid_over_control'):.3f}"
              f"  stalled {sum(r['stalled'] for r in rs)}/{len(rs)}")


# --------------------------------------------------------------------------
# selftest


def selftest() -> bool:
    ok = True
    seeds = (0,)
    cells = [(0, "endogenous", ELASTICITY, 0.12, 5),
             (0, "endogenous", ELASTICITY, 0.12, None),
             (0, "none", ELASTICITY, 0.12, 5)]
    clean0 = criterion_off(seeds)
    clean1 = criterion_ledger(cells)
    print(f"  clean  A53-0 {clean0['passed']}  A53-1 {clean1['passed']}")
    ok &= clean0["passed"] and clean1["passed"]
    for fault in ("off_ignored", "extra_draw"):
        r = criterion_off(seeds, fault)
        print(f"  fault {fault:13s} A53-0 fails: {not r['passed']}"
              f"  {r['detail'][:110]}")
        ok &= not r["passed"]
    for fault in ("before_wages", "on_holdings", "half_release"):
        r = criterion_ledger(cells, fault)
        print(f"  fault {fault:13s} A53-1 fails: {not r['passed']}"
              f"  {r['detail'][:160]}")
        ok &= not r["passed"]
    rows, controls = grid_rows(seeds, (ELASTICITY,))
    drows = decompose_rows(rows, controls)
    c3 = criterion_reading(rows, seeds, (ELASTICITY,))
    c3_bad = criterion_reading(rows[1:], seeds, (ELASTICITY,))
    c4 = criterion_decomposition(drows, rows)
    c4_bad = criterion_decomposition(drows[1:], rows)
    print(f"  clean  A53-3 {c3['passed']}  dropped row fails: "
          f"{not c3_bad['passed']}")
    print(f"  clean  A53-4 {c4['passed']}  dropped row fails: "
          f"{not c4_bad['passed']}")
    ok &= c3["passed"] and not c3_bad["passed"]
    ok &= c4["passed"] and not c4_bad["passed"]
    clean2, _ = criterion_tangent(seeds, (ELASTICITY,))
    print(f"  clean  A53-2 {clean2['passed']}  {clean2['detail']}")
    ok &= clean2["passed"]
    for fault in TANGENT_FAULTS:
        r, _ = criterion_tangent(seeds, (ELASTICITY,), fault)
        print(f"  fault {fault:13s} A53-2 fails: {not r['passed']}"
              f"  {r['detail']}")
        ok &= not r["passed"]
    return bool(ok)


# --------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--block", type=int, choices=(1, 2), default=1)
    a = ap.parse_args(argv)
    if a.selftest:
        t0 = time.perf_counter()
        ok = selftest()
        print(f"selftest {'passed' if ok else 'FAILED'}"
              f" ({time.perf_counter() - t0:.1f} s)")
        return 0 if ok else 1
    if a.run:
        if a.block == 1 and not a.no_write:
            print("block one does not write; pass --no-write")
            return 2
        if a.smoke and not a.no_write:
            print("a smoke run does not write; pass --no-write")
            return 2
        seeds = (0,) if a.smoke else SEEDS
        els = (ELASTICITY,) if a.smoke else ELASTICITIES
        t0 = time.perf_counter()
        crit0 = criterion_off(seeds)
        ledger_cells = [(s, au, ELASTICITY, c, h) for s in seeds
                        for au in AUTHORITIES for c in SHARES for h in HOLDS]
        crit1 = criterion_ledger(ledger_cells)
        rows, controls = grid_rows(seeds, els)
        dt = time.perf_counter() - t0
        for cr in (crit0, crit1):
            print(f"{cr['name']} [{cr['kind']}] "
                  f"{'PASS' if cr['passed'] else 'FAIL'}: {cr['detail']}")
        leaks = [r for r in rows if r["ledger"]]
        print(f"ledger problems on grid rows: {len(leaks)}"
              + (f"  {leaks[0]['ledger']}" if leaks else ""))
        print_controls(controls)
        print_rows(rows)
        print(f"\n{len(rows)} lock runs, {len(controls)} controls, "
              f"{dt:.1f} s")
        if a.block == 1:
            return 0 if crit0["passed"] and crit1["passed"] else 1
        t1 = time.perf_counter()
        crit2, trows = criterion_tangent(seeds, els)
        print(f"\n{crit2['name']} [{crit2['kind']}] "
              f"{'PASS' if crit2['passed'] else 'FAIL'}: {crit2['detail']}")
        for r in sorted(trows, key=lambda r: -r["worst"])[:3]:
            print(f"  worst: seed {r['seed']} {r['auth']} el {r['el']} hold "
                  f"{_hold(r['hold'])} issued rounds {r['issued_rounds']}: "
                  + " ".join(f"{k} {v:.1e}" for k, v in r["diffs"].items()))
        drows = decompose_rows(rows, controls)
        print_decomposition(drows)
        crit3 = criterion_reading(rows, seeds, els)
        crit4 = criterion_decomposition(drows, rows)
        for cr in (crit3, crit4):
            print(f"\n{cr['name'][:5]} [{cr['kind']}] "
                  f"{'PASS' if cr['passed'] else 'FAIL'}: {cr['detail']}")
        print(f"\nblock two {time.perf_counter() - t1:.1f} s")
        crits = [crit0, crit1, crit2, crit3, crit4]
        if not a.no_write:
            write_record(build_record(crits, rows, controls, drows, trows))
        return 0 if all(x["passed"] for x in crits) else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
