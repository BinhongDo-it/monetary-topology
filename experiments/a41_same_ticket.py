"""A41: one ticket on the same terms for every node, and who gets to play it.

Ruled 2026-09-15. A bet is offered to every node on identical terms: a fixed
stake, a fixed chance of winning, and a house outside the graph that pays a
win by issuing claims and takes a loss by destroying them. The price on the
edge is therefore the same for everyone, so the term stage A3 measured, the
same claim buying different terms for different holders, is zero here by
construction. What differs is how many times a node plays in a round. A node
holding less than the stake cannot play at all, and a node with a larger
stock gets through more of its attempts before it reaches that line.

For one bettor in isolation the closed forms are textbook: ruin at
``(q/p)**m`` for a stock of ``m`` stakes, and a net loss after ``N`` plays
governed by ``N * (2p - 1)**2``. They are cited, not rerun. What they cannot
say is what the network does with the outcome: whether a loss taken by a node
that pays wages reaches the nodes that never bet, how the receiving set moves,
and how much of what the ticket paid out is still held by the class that won
it when the run ends.

Steps, one at a time and in this order:

    python experiments/a41_same_ticket.py --gate            # A41-0
    python experiments/a41_same_ticket.py --selftest        # seeded faults, gate and criteria
    python experiments/a41_same_ticket.py --time            # seconds per cell tier (D38)
    python experiments/a41_same_ticket.py --run --smoke     # seed 0, nothing written
    python experiments/a41_same_ticket.py --run             # the grid, writes the record

``--run`` without ``--smoke`` refuses until ``--time`` has written its file.
The criteria are written in this file and the record carries their text, so
the quantities a run produces are all reported.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import Network, NetworkConfig  # noqa: E402

#: A17's carrier, imported at run time rather than restated, so the control
#: arm is bitwise the arm A17 and A37 ran: 20 financial nodes, a 30-node
#: intermediate block, 150 production nodes, ``F2I = 30``, ``ELASTICITY = 0.5``,
#: ``ROUNDS = 300``. ``base_config(seed, need)`` attaches an exit floor when
#: ``need > 0``.
from a17_edge_cut import (  # noqa: E402
    ELASTICITY,
    F2I,
    ROUNDS,
    base_config,
    gini,
    top_share,
)

#: The first round the ticket settles. It is A17's shock round, and it is past
#: the first payroll's transient: in round 0 the payers fund 5.15 to 5.74 of a
#: bill of 8.0, so a ticket settled before that payroll reads the opening
#: rather than the bet. Measured before this script existed: opened at round 0,
#: p 0.51, stake 0.09 and ten attempts cleared the wage earners on a floor of
#: 0.05; opened at round 50, the same cell cleared nobody on 0.06 at any of
#: five seeds.
OPEN_FROM = 50

#: Uniforms drawn per ticket round, per node, whatever a cell's caps are. Every
#: cell of one seed therefore reads the same uniform for the same (round,
#: attempt, node), and because a win is ``u < p`` every win at 0.51 is also a
#: win at 0.55. No cap may exceed it.
DRAW_ROWS = 100

#: The ticket's own random stream. The network's generator is never read, so
#: a treated run and its control share every propensity draw.
STREAM = 4141

#: The floors. 0.0 is none. 0.06 is the highest of the two that all five
#: control seeds survive: in round 0 the wage earners receive 0.069 to 0.077,
#: and a floor of 0.07 clears them in that round on three seeds of five. After
#: round 0 their inflow does not fall below 0.088, which leaves 0.03 and 0.06
#: margins of 66% and 32%.
WALLS = (0.0, 0.03, 0.06)

#: The ruin probability an ``aware`` node accepts before it plays.
RUIN_TARGET = 0.01

#: Whether the grid's readings are written into RESULTS.md. While they are not,
#: the record carries ``diagnostic_only`` and a reason; once they are, it
#: carries neither. Closed 2026-09-15 for the grid below. A change to the grid
#: sets this back to False until the new readings are written.
CLOSED = True


def ruin_reserve(p: float, target: float = RUIN_TARGET) -> int:
    """Smallest whole number of stakes ``m`` with ``(q/p)**m <= target``.

    The gambler's-ruin closed form for a stock of ``m`` stakes against an
    unbounded horizon: 116 at p = 0.51 and 23 at p = 0.55. The ceiling is
    guarded on both sides because a ratio of logarithms that is an integer in
    exact arithmetic can land a hair either side of it in floating point.
    """
    if not 0.5 < p < 1.0:
        raise ValueError("a ruin reserve needs 0.5 < p < 1")
    if not 0.0 < target < 1.0:
        raise ValueError("target must lie in (0, 1)")
    r = (1.0 - p) / p
    m = max(0, math.ceil(math.log(target) / math.log(r)))
    while r ** m > target:
        m += 1
    while m > 0 and r ** (m - 1) <= target:
        m -= 1
    return m


@dataclass(frozen=True)
class TicketSpec:
    """One ticket, on the same terms for every node.

    ``attempts`` is how many times a node may try to play in one ticket round;
    ``attempts_l1`` replaces it on the financial layer, and ``None`` means the
    same. Every attempt reads the node's holdings at that moment. Below the
    stake the attempt is stopped by the capital line. Under ``aware``, a node
    that covers the stake but holds fewer than ``ruin_reserve(p)`` stakes
    abstains. Otherwise it plays.

    The default is off, and an off ticket draws nothing.
    """

    stake: float = 0.0
    p: float = 0.5
    attempts: int = 0
    attempts_l1: int | None = None
    rule: str = "naive"
    open_from: int = OPEN_FROM
    stream: int = STREAM
    draw_rows: int = DRAW_ROWS

    def __post_init__(self) -> None:
        if not self.stake >= 0.0:
            raise ValueError("stake must be non-negative")
        if not 0.0 <= self.p <= 1.0:
            raise ValueError("p must lie in [0, 1]")
        if self.attempts < 0 or (self.attempts_l1 is not None
                                 and self.attempts_l1 < 0):
            raise ValueError("attempts must be non-negative")
        if self.rule not in ("naive", "aware"):
            raise ValueError("rule must be 'naive' or 'aware'")
        if self.open_from < 0:
            raise ValueError("open_from must be non-negative")
        if max(self.attempts, self.attempts_l1 or 0) > self.draw_rows:
            raise ValueError("a cap above draw_rows would read uniforms "
                             "nobody drew")
        if self.rule == "aware":
            ruin_reserve(self.p)

    @property
    def active(self) -> bool:
        return max(self.attempts, self.attempts_l1 or 0) > 0

    @property
    def m_star(self) -> int | None:
        return ruin_reserve(self.p) if self.rule == "aware" else None

    @property
    def required(self) -> float:
        """The holdings an attempt must see to be played."""
        return self.stake * self.m_star if self.rule == "aware" else self.stake


class TicketNetwork(Network):
    """The carrier, with one ticket settled at the start of each ticket round.

    **Where it settles.** ``_pre_round`` runs before the round's issuance is
    credited and outside the round's stock-flow assertion, which is the zone
    where this module already lets claims come into existence and leave it.
    A settlement moves the claim total by what it issued less what it
    destroyed and by nothing else, so it closes its own ledger here and books
    the net into ``_total_claims``, which the write-off's trigger reads.

    **Order.** Attempts are settled one index at a time across all nodes, so a
    node's second attempt reads the holdings its first one left.

    **Who plays.** A node that has left the market (the carrier's ``_alive``)
    is not a counterparty, to the house any more than to another node, so it
    does not play, and the attempts it would have had are counted as absent.
    The carrier applies that mask inside its own round, and ``_pre_round`` runs
    before the round, so the mask is applied here: nothing a hook does
    inherits it.

    What the ticket did is kept per ticket round and handed back by
    ``ticket_record``. The network's own history is not touched.
    """

    def __init__(self, config: NetworkConfig, ticket: TicketSpec) -> None:
        super().__init__(config)
        self.ticket = ticket
        caps = np.full(self._n, ticket.attempts, dtype=np.int64)
        if ticket.attempts_l1 is not None:
            caps[np.asarray(self._l1)] = ticket.attempts_l1
        self._caps = caps
        self._ticket_rng = np.random.default_rng([config.seed, ticket.stream])
        self._draws = 0
        self._alive_rows: list[np.ndarray] = []
        self._inflow_rows: list[np.ndarray] = []
        self._rec: dict[str, list] = {key: [] for key in (
            "round", "h0", "h1", "plays", "wins", "stops", "abstains",
            "absent", "alive", "created", "destroyed")}

    # Five one-line hooks, so that a seeded fault replaces a line rather than
    # a copy of the settlement.

    def _ticket_open(self, t: int) -> bool:
        return self.ticket.active and t >= self.ticket.open_from

    def _ticket_draws(self) -> np.ndarray:
        self._draws += 1
        return self._ticket_rng.random((self.ticket.draw_rows, self._n))

    def _present(self) -> np.ndarray:
        return self._alive

    def _stopped(self, h: np.ndarray, stake: float) -> np.ndarray:
        return h < stake

    def _book_total(self, net: float) -> None:
        self._total_claims += net

    def _pre_round(self, t: int) -> None:
        super()._pre_round(t)
        if not self._ticket_open(t):
            return
        tk = self.ticket
        n = self._n
        u = self._ticket_draws()
        h0 = np.array(self.holdings, dtype=float, copy=True)
        h = h0.copy()
        # ``alive`` is read off the carrier and kept for the record; ``present``
        # comes through the hook and is what the settlement obeys. They are
        # the same array unless a fault replaces the hook, and the record is
        # how such a fault is seen.
        alive = np.array(self._alive, dtype=bool, copy=True)
        present = np.array(self._present(), dtype=bool, copy=True)
        plays = np.zeros(n, dtype=np.int64)
        wins = np.zeros(n, dtype=np.int64)
        stops = np.zeros(n, dtype=np.int64)
        abstains = np.zeros(n, dtype=np.int64)
        absents = np.zeros(n, dtype=np.int64)
        created = 0.0
        destroyed = 0.0
        stake, required = tk.stake, tk.required
        for k in range(int(self._caps.max())):
            capped = k < self._caps
            allowed = capped & present
            gone = capped & ~present
            stop = allowed & self._stopped(h, stake)
            # Only an aware node abstains. Under naive the required holding is
            # the stake itself, so testing it here would be a second copy of
            # the capital line, and a fault that removed the first would leave
            # the second standing.
            if tk.rule == "aware":
                abstain = allowed & ~stop & (h < required)
            else:
                abstain = np.zeros(n, dtype=bool)
            play = allowed & ~stop & ~abstain
            win = play & (u[k] < tk.p)
            lose = play & ~win
            # ``where`` rather than an in-place add, so a node that did not
            # play keeps its holding bit for bit.
            h = np.where(win, h + stake, np.where(lose, h - stake, h))
            plays += play
            wins += win
            stops += stop
            abstains += abstain
            absents += gone
            created += stake * int(win.sum())
            destroyed += stake * int(lose.sum())
        before, after = float(h0.sum()), float(h.sum())
        tol = 1e-9 * max(1.0, abs(before))
        if abs((after - before) - (created - destroyed)) > tol:
            raise AssertionError(
                f"ticket ledger does not close at round {t}: holdings moved "
                f"{after - before!r} against issued less destroyed "
                f"{created - destroyed!r}")
        self.holdings = h
        self._book_total(created - destroyed)
        rec = self._rec
        rec["round"].append(t)
        rec["h0"].append(h0)
        rec["h1"].append(h.copy())
        rec["plays"].append(plays)
        rec["wins"].append(wins)
        rec["stops"].append(stops)
        rec["abstains"].append(abstains)
        rec["absent"].append(absents)
        rec["alive"].append(alive)
        rec["created"].append(created)
        rec["destroyed"].append(destroyed)

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        # Read only: who is still trading and what each node received this
        # round, for the transmission readout. Nothing here writes to the model.
        self._alive_rows.append(self._alive.copy())
        self._inflow_rows.append(
            np.array(self._last_inflow, dtype=float, copy=True))

    def ticket_record(self) -> dict:
        """Everything the ticket did, one row per ticket round."""
        rec, n = self._rec, self._n
        out: dict = {
            "rounds": np.asarray(rec["round"], dtype=np.int64),
            "draws": self._draws,
            "caps": self._caps.copy(),
            "required": self.ticket.required,
            "m_star": self.ticket.m_star,
            "created": np.asarray(rec["created"], dtype=float),
            "destroyed": np.asarray(rec["destroyed"], dtype=float),
        }
        for key in ("h0", "h1"):
            out[key] = np.vstack(rec[key]) if rec[key] else np.zeros((0, n))
        for key in ("plays", "wins", "stops", "abstains", "absent"):
            out[key] = (np.vstack(rec[key]) if rec[key]
                        else np.zeros((0, n), dtype=np.int64))
        out["alive"] = (np.vstack(rec["alive"]) if rec["alive"]
                        else np.zeros((0, n), dtype=bool))
        return out


# --------------------------------------------------------------------------
# A41-0: the gate


def diff_fields(a, b, before: int | None = None) -> list[str]:
    """History fields on which two runs differ, bitwise.

    With ``before`` set, a field indexed by round is compared on its first
    ``before`` rows and the snapshot dict on the rounds below it. The potential
    graph and the scalar fields are compared whole either way.
    """
    rounds = int(np.asarray(a.total_volume).shape[0])
    bad = []
    for f in dataclasses.fields(a):
        name = f.name
        x, y = getattr(a, name), getattr(b, name)
        if x is None or y is None:
            if (x is None) != (y is None):
                bad.append(name)
            continue
        if isinstance(x, dict):
            kx = {k for k in x if before is None or k < before}
            ky = {k for k in y if before is None or k < before}
            if kx != ky or any(not np.array_equal(x[k], y[k]) for k in kx):
                bad.append(name)
            continue
        if isinstance(x, np.ndarray):
            if (before is not None and name != "adjacency" and x.ndim >= 1
                    and x.shape[0] == rounds):
                x, y = x[:before], y[:before]
            if x.shape != y.shape or not np.array_equal(x, y):
                bad.append(name)
            continue
        if x != y:
            bad.append(name)
    return bad


GATE_SEEDS = (0, 1)

#: The second half's tickets: the heaviest naive cell of the grid, and an
#: aware cell whose reserve, 23 stakes or 5.75 at a stake of 0.25, financial
#: nodes reach and the intermediate block does not, so the abstain branch runs.
GATE_ON = (
    TicketSpec(stake=0.25, p=0.51, attempts=10, attempts_l1=100, rule="naive"),
    TicketSpec(stake=0.25, p=0.55, attempts=10, attempts_l1=100, rule="aware"),
)

#: The third half's ticket: every uniform drawn and every attempt played, for
#: a stake of zero. Nothing can move, so any difference from the control is
#: the ticket reaching into the network rather than its own stream.
GATE_ZERO = TicketSpec(stake=0.0, p=0.51, attempts=10, attempts_l1=100,
                       rule="naive")


@dataclass
class GateResult:
    ok: bool = True
    rows: dict = field(default_factory=lambda: {"one": [], "two": [], "three": []})


def run_gate(net_class=TicketNetwork) -> GateResult:
    """A41-0, three halves. Prints one line per run.

    **One**, rule 19: a ticket that is off leaves every history field bitwise
    the plain network's, and draws nothing. **Two**: a ticket that is on leaves
    every row before ``OPEN_FROM`` bitwise the control's, and does move the
    run after it, or the half would compare nothing. **Three**: a ticket with a
    stake of zero draws every uniform and plays every attempt, and the whole
    run is bitwise the control's. That half is the one that can see the ticket
    reading the network's own generator, which the first two cannot.

    ``net_class`` is the selftest's hook: a subclass carrying a seeded fault.
    """
    res = GateResult()
    twins: dict = {}

    def twin(seed: int, wall: float):
        if (seed, wall) not in twins:
            twins[(seed, wall)] = Network(base_config(seed, need=wall)).run()
        return twins[(seed, wall)]

    def report(half: str, label: str, bad: list, notes: list) -> None:
        good = not bad and not notes
        res.ok = res.ok and good
        res.rows[half].append({"label": label, "bad": bad, "notes": notes})
        tail = (f"   {'; '.join(bad[:4])}" if bad else "") + (
            f"   {'; '.join(notes)}" if notes else "")
        print(f"  {'ok  ' if good else 'FAIL'} {label:34s} differing fields: "
              f"{len(bad)}{tail}")

    print("A41-0: the ticket does not touch the network\n")
    t0 = time.time()

    print("one: ticket off, every history field")
    for wall in WALLS:
        for seed in GATE_SEEDS:
            net = net_class(base_config(seed, need=wall), TicketSpec())
            hist = net.run()
            rec = net.ticket_record()
            notes = []
            if rec["draws"]:
                notes.append(f"an off ticket drew {rec['draws']} times")
            if rec["rounds"].size:
                notes.append("an off ticket recorded rounds")
            report("one", f"wall {wall:.2f} seed {seed}",
                   diff_fields(hist, twin(seed, wall)), notes)

    print(f"\ntwo: ticket on, every row before round {OPEN_FROM}")
    for spec in GATE_ON:
        for wall in WALLS:
            for seed in GATE_SEEDS:
                net = net_class(base_config(seed, need=wall), spec)
                hist = net.run()
                rec = net.ticket_record()
                ctrl = twin(seed, wall)
                notes = []
                first = int(rec["rounds"][0]) if rec["rounds"].size else None
                if first != spec.open_from:
                    notes.append(f"first ticket round {first}, "
                                 f"expected {spec.open_from}")
                if not int(rec["plays"].sum()):
                    notes.append("nothing was played, so the half is empty")
                if np.array_equal(hist.holdings[-1], ctrl.holdings[-1]):
                    notes.append("closing holdings equal the control's, so "
                                 "the ticket moved nothing")
                report("two", f"{spec.rule} p {spec.p} wall {wall:.2f} "
                              f"seed {seed}",
                       diff_fields(hist, ctrl, before=spec.open_from), notes)

    print("\nthree: stake zero, every history field, the whole run")
    for wall in WALLS:
        for seed in GATE_SEEDS:
            net = net_class(base_config(seed, need=wall), GATE_ZERO)
            hist = net.run()
            rec = net.ticket_record()
            notes = []
            if not int(rec["plays"].sum()):
                notes.append("no attempt was played, so the half is empty")
            if rec["draws"] != ROUNDS - GATE_ZERO.open_from:
                notes.append(f"drew {rec['draws']} times, expected "
                             f"{ROUNDS - GATE_ZERO.open_from}")
            report("three", f"wall {wall:.2f} seed {seed}",
                   diff_fields(hist, twin(seed, wall)), notes)

    print(f"\nA41-0: {'PASS' if res.ok else 'FAIL'}   ({time.time() - t0:.1f} s)")
    return res


class _EarlyTicket(TicketNetwork):
    """Seeded fault: the ticket opens one round early."""

    def _ticket_open(self, t: int) -> bool:
        return self.ticket.active and t >= self.ticket.open_from - 1


class _NetworkStreamTicket(TicketNetwork):
    """Seeded fault: the ticket draws from the network's own generator."""

    used_network_stream = False

    def _ticket_draws(self) -> np.ndarray:
        type(self).used_network_stream = True
        self._draws += 1
        return self.rng.random((self.ticket.draw_rows, self._n))


def selftest() -> bool:
    """Each seeded fault must be planted and must make the gate fail (11f).

    **Planted first.** A gate that did not fail and a fault that was never
    planted print the same thing, so each fault is checked for having done
    what it says before the gate's verdict on it is read. **And failed on the
    half that is meant to see it**: the early opening on the second half's
    field comparison, the borrowed stream on the third half's.
    """
    ok = []

    got = [ruin_reserve(0.51), ruin_reserve(0.55)]
    ok.append(got == [116, 23])
    print(f"ruin_reserve(0.51), ruin_reserve(0.55) = {got}   (want [116, 23])")

    try:
        TicketSpec(stake=0.1, p=0.51, attempts=DRAW_ROWS + 1)
        ok.append(False)
        print("a cap above DRAW_ROWS was accepted   (want rejected)")
    except ValueError:
        ok.append(True)
        print("a cap above DRAW_ROWS is rejected")

    probe = _EarlyTicket(base_config(0, need=0.0), GATE_ON[0])
    probe.run()
    first = int(probe.ticket_record()["rounds"][0])
    planted = first == OPEN_FROM - 1
    ok.append(planted)
    print(f"\n--- fault: early   planted: first ticket round {first}   "
          f"(want {OPEN_FROM - 1})")
    res = run_gate(_EarlyTicket)
    seen = any(row["bad"] for row in res.rows["two"])
    ok.append(not res.ok and seen)
    print(f"--- caught: {not res.ok}, on the second half's field comparison: "
          f"{seen}\n")

    _NetworkStreamTicket.used_network_stream = False
    res = run_gate(_NetworkStreamTicket)
    planted = _NetworkStreamTicket.used_network_stream
    seen = any(row["bad"] for row in res.rows["three"])
    ok.append(planted and not res.ok and seen)
    print(f"--- fault: network stream   planted: {planted}   caught: "
          f"{not res.ok}, on the third half's field comparison: {seen}\n")

    print("selftest:", "PASS" if all(ok) else "FAIL")
    return all(ok)


# --------------------------------------------------------------------------
# the grid

#: Two edges. ``ln(p/q)`` is 0.0400 and 0.2007, five times apart. An edge of
#: 0.00001 cannot be told from a fair coin in 250 ticket rounds: holding a net
#: loss under one per cent takes about 1.35e10 plays.
P_GRID = (0.51, 0.55)

#: Three stakes, each named by what it is against this carrier's stocks at
#: round 49. 0.005 is about a wage earner's holding, so an earner holds one
#: ticket. 0.09 is about one earner's wage for a round, which no earner holds,
#: so the intermediate block becomes the poorest class that plays. 0.25 is
#: about one payer's share of a round's wage bill.
STAKES = (0.005, 0.09, 0.25)

#: Attempts per ticket round for everyone, and the multiplier on the financial
#: layer's attempts. The first is how fast a stake comes back for every node;
#: the second is how much more the edge carries for one position than for the
#: others.
ATTEMPTS = (1, 10)
L1_MULTIPLIERS = (1, 10)

RULES = ("naive", "aware")
SEEDS = (0, 1, 2, 3, 4)

#: The support readout is the median over the last ``TAIL`` rounds, so one
#: round's draw does not become the reading.
TAIL = 30

TIMING = RESULTS / "a41_timing.json"
RECORD = RESULTS / "a41_same_ticket.json"

#: Class pairs for the decomposition, (a, b) with b the class holding more.
PAIRS = (("mid", "l1"), ("earners", "l1"), ("earners", "mid"))
PLAYING = ("l1", "mid", "earners")
ALL_CLASSES = ("l1", "mid", "earners", "unreached")

TOL_LEDGER = 1e-9
TOL_SETTLE = 1e-9
TOL_IDENTITY = 1e-12


def cell_spec(p: float, stake: float, attempts: int, l1_mult: int,
              rule: str) -> TicketSpec:
    return TicketSpec(stake=stake, p=p, attempts=attempts,
                      attempts_l1=attempts * l1_mult, rule=rule)


def grid(seeds=SEEDS) -> list[tuple]:
    """(seed, wall, p, stake, attempts, l1_mult, rule), seed outermost, so a
    seed's three controls are built once and dropped before the next seed."""
    return [(seed, wall, p, stake, a, m, rule)
            for seed in seeds for wall in WALLS for p in P_GRID
            for stake in STAKES for a in ATTEMPTS for m in L1_MULTIPLIERS
            for rule in RULES]


def classes_of(net: Network) -> dict[str, np.ndarray]:
    """The four classes, read off the module rather than redefined here.

    Financial layer, intermediate block, the wage earners, and the production
    nodes that are neither. On this carrier the intermediate block is exactly
    the set of wage payers, and the readout of how a loss reaches the earners
    rests on that, so it is asserted rather than assumed.
    """
    l1 = np.asarray(net._l1, dtype=int)
    mid = np.asarray(net._mid, dtype=int)
    payers = np.asarray(net._wage_payers, dtype=int)
    earners = np.asarray(net._wage_receivers, dtype=int)
    if set(payers.tolist()) != set(mid.tolist()):
        raise AssertionError("the wage payers are not the intermediate block")
    production = np.setdiff1d(np.asarray(net._l2, dtype=int), mid)
    if not set(earners.tolist()) <= set(production.tolist()):
        raise AssertionError("a wage earner sits outside the production layer")
    unreached = np.setdiff1d(production, earners)
    if l1.size + mid.size + earners.size + unreached.size != net._n:
        raise AssertionError("the four classes do not partition the nodes")
    return {"l1": l1, "mid": mid, "earners": earners, "unreached": unreached}


def decompose(na: float, ga: float, mua: float, nb: float, gb: float,
              mub: float, weighted: bool = False) -> dict:
    """``N_b g_b - N_a g_a`` as a price term, a stopping term and a count term.

    ``N`` is plays per node, ``g`` the realized return per play, ``mu`` the
    expected return per play the terms set. ``weighted`` is a seeded fault for
    the selftest: it averages the realized returns by play count, and then the
    three terms no longer add up to the gap.
    """
    nbar = 0.5 * (na + nb)
    if weighted and (na + nb) > 0:
        gbar = (na * ga + nb * gb) / (na + nb)
    else:
        gbar = 0.5 * (ga + gb)
    return {"gap": nb * gb - na * ga,
            "price": nbar * (mub - mua),
            "stopping": nbar * ((gb - mub) - (ga - mua)),
            "count": (nb - na) * gbar}


def run_control(seed: int, wall: float):
    """A cell's control: the carrier with the ticket off. A41-0 shows it is
    bitwise the plain network; it is built this way so that it carries the same
    per-round record of who is trading."""
    net = TicketNetwork(base_config(seed, need=wall), TicketSpec())
    return net, net.run()


def _first_row(mask: np.ndarray) -> int | None:
    rows = mask.any(axis=1)
    return int(np.argmax(rows)) if rows.any() else None


def _shortfall(owed: np.ndarray, paid: np.ndarray) -> tuple[float, float]:
    s = np.divide(owed - paid, owed, out=np.zeros_like(owed), where=owed > 0)
    return float(s.mean()), float(s.max())


def one_cell(cell: tuple, control, net_class=TicketNetwork) -> dict:
    """One treated run read against its control. Everything a readout or a
    criterion needs is put in the row, so the criteria never rerun anything."""
    seed, wall, p, stake, attempts, l1_mult, rule = cell
    spec = cell_spec(p, stake, attempts, l1_mult, rule)
    cnet, chist = control
    net = net_class(base_config(seed, need=wall), spec)
    hist = net.run()
    rec = net.ticket_record()
    cls = classes_of(net)
    n_rounds = ROUNDS - spec.open_from
    P, W, S, A = rec["plays"], rec["wins"], rec["stops"], rec["abstains"]
    X, L = rec["absent"], rec["alive"]
    H0, H1 = rec["h0"], rec["h1"]
    caps = rec["caps"][None, :]
    mu = stake * (2.0 * p - 1.0)
    row: dict = {"seed": seed, "wall": wall, "p": p, "stake": stake,
                 "attempts": attempts, "l1_mult": l1_mult, "rule": rule,
                 "m_star": rec["m_star"], "required": rec["required"]}

    # A41-1: the ledger, measured off the accounts at the end.
    m_t = float(net.holdings.sum()) + float(net._parked.sum())
    row["M_t"] = m_t
    row["ledger_drift"] = abs(float(net._total_claims) - m_t)

    # A41-2: the capital line and the caps, on every recorded attempt.
    has = P.size > 0
    row["rounds_ok"] = bool(np.array_equal(
        rec["rounds"], np.arange(spec.open_from, ROUNDS)))
    row["cap_viol"] = int((P > caps).sum()) if has else 0
    row["acct_viol"] = int((P + S + A + X != caps).sum()) if has else 0
    row["gone_viol"] = int(((P > 0) & ~L).sum()) if has else 0
    row["line_viol"] = int(((H0 < rec["required"]) & (P > 0)).sum()) if has else 0
    row["neg_viol"] = int(((P > 0) & (H1 < 0.0)).sum()) if has else 0
    row["still_viol"] = int(((P == 0) & (H1 != H0)).sum()) if has else 0
    row["wins_viol"] = int((W > P).sum()) if has else 0
    row["settle_err"] = (float(np.abs(H1 - H0 - stake * (2 * W - P)).max())
                         if has else 0.0)

    # R1 and the decomposition's inputs, per playing class.
    played_node = P.sum(axis=0) > 0 if has else np.zeros(net._n, dtype=bool)
    for name in PLAYING:
        ix = cls[name]
        n_c = int(ix.size)
        plays_c = int(P[:, ix].sum()) if has else 0
        wins_c = int(W[:, ix].sum()) if has else 0
        pnl = stake * (2 * wins_c - plays_c)
        row[f"n_{name}"] = n_c
        row[f"plays_{name}"] = plays_c
        row[f"N_{name}"] = plays_c / n_c
        row[f"g_{name}"] = pnl / plays_c if plays_c else mu
        row[f"mu_{name}"] = mu
        row[f"pnl_{name}"] = pnl
        row[f"pnl_ledger_{name}"] = float((H1[:, ix] - H0[:, ix]).sum()) if has else 0.0
        denom = n_c * max(n_rounds, 1)
        row[f"plays_rd_{name}"] = plays_c / denom
        row[f"stops_rd_{name}"] = (int(S[:, ix].sum()) if has else 0) / denom
        row[f"abstains_rd_{name}"] = (int(A[:, ix].sum()) if has else 0) / denom
        row[f"absent_rd_{name}"] = (int(X[:, ix].sum()) if has else 0) / denom
        row[f"ever_played_{name}"] = float(played_node[ix].mean())

    # R2: the wage shortfall and who left.
    o = spec.open_from
    row["short_mean_t"], row["short_max_t"] = _shortfall(hist.wage_owed[o:], hist.wage_paid[o:])
    row["short_mean_c"], row["short_max_c"] = _shortfall(chist.wage_owed[o:], chist.wage_paid[o:])
    alive_t, alive_c = np.array(net._alive_rows), np.array(cnet._alive_rows)
    e = cls["earners"]
    row["earners_alive_t"] = int(alive_t[-1, e].sum())
    row["earners_alive_c"] = int(alive_c[-1, e].sum())
    row["earners_first_exit_t"] = _first_row(~alive_t[:, e])
    row["earners_first_exit_c"] = _first_row(~alive_c[:, e])
    for name in ALL_CLASSES:
        ix = cls[name]
        left_t, left_c = ~alive_t[-1, ix], ~alive_c[-1, ix]
        row[f"left_{name}_t"] = int(left_t.sum())
        row[f"left_{name}_c"] = int(left_c.sum())
        row[f"left_{name}_never_played_t"] = int((left_t & ~played_node[ix]).sum())
    u = cls["unreached"]
    row["unreached_inflow_c"] = float(np.array(cnet._inflow_rows)[:, u].sum())
    row["unreached_first_exit_c"] = _first_row(~alive_c[:, u])

    # R3: the receiving set against the stock.
    sup_t = float(np.median(hist.effective_support[-TAIL:]))
    sup_c = float(np.median(chist.effective_support[-TAIL:]))
    m_c = float(cnet.holdings.sum()) + float(cnet._parked.sum())
    row.update({
        "support_t": sup_t, "support_c": sup_c,
        "support_ratio": sup_t / sup_c if sup_c > 0 else float("nan"),
        "M_c": m_c, "M_ratio": m_t / m_c if m_c > 0 else float("nan"),
        "issuance_t": float(hist.issuance.sum()),
        "issuance_c": float(chist.issuance.sum()),
        "trade_t": float(hist.total_volume[-TAIL:].sum() - hist.wage_paid[-TAIL:].sum()),
        "trade_c": float(chist.total_volume[-TAIL:].sum() - chist.wage_paid[-TAIL:].sum()),
        "created": float(rec["created"].sum()),
        "destroyed": float(rec["destroyed"].sum()),
    })

    # R4: what stayed with whom at the end.
    ht, hc = hist.holdings[-1], chist.holdings[-1]
    for name in PLAYING:
        ix = cls[name]
        row[f"share_{name}_t"] = float(ht[ix].sum() / ht.sum())
        row[f"share_{name}_c"] = float(hc[ix].sum() / hc.sum())
        pnl = row[f"pnl_{name}"]
        row[f"retained_{name}"] = (float(ht[ix].sum() - hc[ix].sum()) / pnl
                                   if pnl != 0 else float("nan"))
    row["top10_t"], row["top10_c"] = top_share(ht, 10), top_share(hc, 10)
    row["gini_t"], row["gini_c"] = gini(ht), gini(hc)

    # A41-4: a cell that played nothing is a third state.
    row["plays_total"] = int(P.sum()) if has else 0
    row["inert"] = row["plays_total"] == 0
    row["diff_to_control"] = len(diff_fields(hist, chist))
    return row


def run_grid(seeds=SEEDS) -> list[dict]:
    cells = grid(seeds)
    controls: dict = {}
    rows = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        seed, wall = cell[0], cell[1]
        if (seed, wall) not in controls:
            controls = {k: v for k, v in controls.items() if k[0] == seed}
            controls[(seed, wall)] = run_control(seed, wall)
        rows.append(one_cell(cell, controls[(seed, wall)]))
        if i % 48 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}  ({time.time() - t0:.0f} s)", flush=True)
    return rows


# --------------------------------------------------------------------------
# criteria, all four about the instrument (the station registers no reading
# with a direction; the readouts are printed below them)


def _label(r: dict) -> str:
    return (f"seed {r['seed']} wall {r['wall']} p {r['p']} stake {r['stake']} "
            f"attempts {r['attempts']}x{r['l1_mult']} {r['rule']}")


def identity_residues(rows: list[dict], weighted: bool = False) -> tuple:
    """The worst miss of each identity A41-3 reads, and the pair-cells that
    carry a price term. One computation, read by the criterion and printed."""
    worst_id = worst_tie = worst_ledger = 0.0
    priced = []
    for r in rows:
        for a, b in PAIRS:
            d = decompose(r[f"N_{a}"], r[f"g_{a}"], r[f"mu_{a}"],
                          r[f"N_{b}"], r[f"g_{b}"], r[f"mu_{b}"],
                          weighted=weighted)
            resid = abs(d["gap"] - d["price"] - d["stopping"] - d["count"])
            worst_id = max(worst_id, resid / max(1.0, abs(d["gap"])))
            if d["price"] != 0.0:
                priced.append((r, a, b, d["price"]))
        for name in PLAYING:
            per_node = r[f"pnl_{name}"] / r[f"n_{name}"]
            tie = abs(r[f"N_{name}"] * r[f"g_{name}"] - per_node)
            worst_tie = max(worst_tie, tie / max(1.0, abs(per_node)))
            gap = abs(r[f"pnl_{name}"] - r[f"pnl_ledger_{name}"])
            worst_ledger = max(worst_ledger,
                               gap / max(1.0, abs(r[f"pnl_{name}"])))
    return worst_id, worst_tie, worst_ledger, priced


def print_residues(rows: list[dict]) -> None:
    """The machine-precision residues on the machine that ran, to stdout only.

    The criteria and the record carry the tolerance each residue is held to,
    not the residue: its last digits belong to the build that computed it, and
    on seed 0 a Windows build and a Linux one differed in them on 106 cells of
    144 while every other field agreed to the digit.
    """
    if not rows:
        return
    rel = max(r["ledger_drift"] / max(1.0, abs(r["M_t"])) for r in rows)
    settle = max(r["settle_err"] for r in rows)
    worst_id, worst_tie, worst_ledger, _ = identity_residues(rows)
    print(f"\n  residues on this machine, not written: ledger {rel:.3e}, "
          f"settlement {settle:.3e}, decomposition {worst_id:.3e}, "
          f"plays times return {worst_tie:.3e}, count against ledger "
          f"{worst_ledger:.3e}")


def criteria(rows: list[dict], weighted: bool = False) -> list[dict]:
    names = ("A41-1  the claim total the module tracks equals holdings plus "
             "parked at the end of every cell",
             "A41-2  the capital line, the caps and who is still in hold on "
             "every recorded attempt",
             "A41-3  the decomposition is an identity and ties to the ledger",
             "A41-4  a cell that played nothing is bitwise its control, and "
             "only such cells are flagged inert")
    if not rows:
        return [dict(name=nm, kind="instrument", passed=False,
                     detail="Void: no cells, nothing was evaluated")
                for nm in names]
    out = []

    rel = [r["ledger_drift"] / max(1.0, abs(r["M_t"])) for r in rows]
    bad = [r for r, x in zip(rows, rel) if not x <= TOL_LEDGER]
    out.append(dict(
        name=names[0], kind="instrument", passed=not bad,
        detail=(f"Closes on all {len(rows)} cells: the drift relative to "
                f"the stock is at most {TOL_LEDGER:.0e} on every one." if not bad else
                f"Does not close on {len(bad)} of {len(rows)} cells, largest "
                f"relative drift {max(rel):.3e}: "
                + "; ".join(_label(r) for r in bad[:4]))))

    keys = ("cap_viol", "acct_viol", "gone_viol", "line_viol", "neg_viol",
            "still_viol", "wins_viol")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    worst = max(r["settle_err"] for r in rows)
    bad = [r for r in rows if any(r[k] for k in keys) or not r["rounds_ok"]
           or not r["settle_err"] <= TOL_SETTLE]
    out.append(dict(
        name=names[1], kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} cells: no play above a cap; stops, "
                f"abstentions, absences and plays add up to the cap on every "
                f"node and round; no play from a node that had left when the "
                f"round opened; no play from holdings below what the rule "
                f"requires; "
                f"no playing node below zero; no idle node moved; no more wins "
                f"than plays; every settlement equals the stake times wins "
                f"less losses to within {TOL_SETTLE:.0e}; every cell recorded rounds "
                f"{OPEN_FROM} to {ROUNDS - 1}." if not bad else
                f"Fails on {len(bad)} of {len(rows)} cells, violations {totals}, "
                f"largest settlement error {worst:.3e}: "
                + "; ".join(_label(r) for r in bad[:4]))))

    worst_id, worst_tie, worst_ledger, priced = identity_residues(rows, weighted)
    ok3 = (worst_id <= TOL_IDENTITY and worst_tie <= TOL_IDENTITY
           and worst_ledger <= TOL_LEDGER and not priced)
    out.append(dict(
        name=names[2], kind="instrument", passed=ok3,
        detail=((f"Holds: over {len(rows)} cells and {len(PAIRS)} class pairs "
                 f"the three terms miss the gap by at most {TOL_IDENTITY:.0e} "
                 f"of it; plays per node times return per play misses the "
                 f"counted result per node by at most {TOL_IDENTITY:.0e}; the "
                 f"counted result misses the ledger's by at most "
                 f"{TOL_LEDGER:.0e}; no pair-cell carries a price term, where "
                 f"every class faces one price and the term must be exactly "
                 f"zero") if ok3 else
                (f"Fails: over {len(rows)} cells and {len(PAIRS)} class pairs "
                 f"the three terms miss the gap by up to {worst_id:.3e} of it "
                 f"(tolerance {TOL_IDENTITY:.0e}); plays per node times return "
                 f"per play misses the counted result per node by up to "
                 f"{worst_tie:.3e}; the counted result misses the ledger's by "
                 f"up to {worst_ledger:.3e} (tolerance {TOL_LEDGER:.0e}); "
                 f"{len(priced)} pair-cells carry a price term"
                 + ("" if not priced else ": " + "; ".join(
                     f"{_label(r)} {a}-{b} {x:.3e}"
                     for r, a, b, x in priced[:3]))))))

    zero_bad = [r for r in rows if r["plays_total"] == 0
                and (r["diff_to_control"] or not r["inert"])]
    flag_bad = [r for r in rows if r["inert"] and r["plays_total"] != 0]
    inert = [r for r in rows if r["inert"]]
    kinds = sorted({(r["p"], r["stake"], r["rule"]) for r in inert})
    ok4 = not zero_bad and not flag_bad
    out.append(dict(
        name=names[3], kind="instrument", passed=ok4,
        detail=((f"Holds: {len(inert)} of {len(rows)} cells played nothing, "
                 f"each is bitwise its control and flagged inert, and no cell "
                 f"that played is flagged. Inert cells by (p, stake, rule): "
                 f"{kinds}. They carry no reading.") if ok4 else
                (f"Fails: {len(zero_bad)} cells played nothing and differ from "
                 f"their control or are not flagged, {len(flag_bad)} cells that "
                 f"played are flagged inert: "
                 + "; ".join(_label(r) for r in (zero_bad + flag_bad)[:4])))))
    return out


# --------------------------------------------------------------------------
# readouts, per cell and per seed, never averaged across seeds


def _fmt(v, spec: str) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "-"
    return format(v, spec)


def _groups(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        key = (r["wall"], r["p"], r["stake"], r["attempts"], r["l1_mult"], r["rule"])
        out.setdefault(key, []).append(r)
    return out


def _head(key) -> str:
    wall, p, stake, a, m, rule = key
    return f"wall {wall:.2f} p {p} s {stake:<5} {a:>2}x{m:<2} {rule:5s}"


def print_readouts(rows: list[dict]) -> None:
    groups = _groups(rows)
    live = lambda rs: [r for r in rs if not r["inert"]]  # noqa: E731

    print("\nR1  plays per node per ticket round (l1 / mid / earners), and "
          "stops and abstentions for mid, per seed, floor off")
    for key, rs in groups.items():
        if key[0] != 0.0 or not live(rs):
            continue
        cols = " | ".join(
            f"{_fmt(r['plays_rd_l1'], '.2f')}/{_fmt(r['plays_rd_mid'], '.2f')}/"
            f"{_fmt(r['plays_rd_earners'], '.2f')} stop {_fmt(r['stops_rd_mid'], '.2f')} "
            f"abst {_fmt(r['abstains_rd_mid'], '.2f')}" for r in live(rs))
        print(f"  {_head(key)}  {cols}")

    print("\nR2  earners still in at the end, round of the first earner exit, "
          "and the wage shortfall treated minus control (mean, and the worst "
          "treated round), per seed")
    for key, rs in groups.items():
        if key[0] == 0.0 or not live(rs):
            continue
        cols = " | ".join(
            f"{r['earners_alive_t']:>2}({r['earners_alive_c']}) "
            f"{_fmt(r['earners_first_exit_t'], 'd')} "
            f"{_fmt(r['short_mean_t'] - r['short_mean_c'], '+.3f')} "
            f"max {_fmt(r['short_max_t'], '.3f')}" for r in live(rs))
        print(f"  {_head(key)}  {cols}")

    print("\nR3  support against the control, and the stock against the "
          "control, per seed (a cell whose trade has ended is marked *)")
    for key, rs in groups.items():
        if not live(rs):
            continue
        cols = " | ".join(
            f"{_fmt(r['support_ratio'], '.3f')}{'*' if r['trade_t'] <= 1e-9 * max(1.0, r['trade_c']) else ''} "
            f"M {_fmt(r['M_ratio'], '.2f')}" for r in live(rs))
        print(f"  {_head(key)}  {cols}")

    print("\nR4  per node: mid against l1 (gap, stopping, count), earners "
          "against l1 (gap, count), retained by l1 and mid, and the share "
          "change of mid and earners, per seed, floor off")
    for key, rs in groups.items():
        if key[0] != 0.0 or not live(rs):
            continue
        parts = []
        for r in live(rs):
            d1 = decompose(r["N_mid"], r["g_mid"], r["mu_mid"], r["N_l1"], r["g_l1"], r["mu_l1"])
            d2 = decompose(r["N_earners"], r["g_earners"], r["mu_earners"], r["N_l1"], r["g_l1"], r["mu_l1"])
            parts.append(
                f"{d1['gap']:+.3g} {d1['stopping']:+.2g} {d1['count']:+.3g}; "
                f"{d2['gap']:+.3g} {d2['count']:+.3g}; "
                f"ret {_fmt(r['retained_l1'], '.2f')}/{_fmt(r['retained_mid'], '.2f')}; "
                f"d {r['share_mid_t'] - r['share_mid_c']:+.4f}/"
                f"{r['share_earners_t'] - r['share_earners_c']:+.4f}")
        print(f"  {_head(key)}  " + " | ".join(parts))


def _record_value(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        x = float(v)
        return float(f"{x:.10g}") if math.isfinite(x) else None
    return v


def record_run(r: dict) -> dict:
    """One row as the record carries it. The two residue fields are written as
    the tolerance they were held to when they are inside it, and as the value
    when they are not, since a residue outside its tolerance is no longer
    machine noise."""
    out = {k: _record_value(v) for k, v in r.items()
           if k not in ("ledger_drift", "settle_err")}
    if r["ledger_drift"] / max(1.0, abs(r["M_t"])) <= TOL_LEDGER:
        out["ledger_drift_relative_at_most"] = TOL_LEDGER
    else:
        out["ledger_drift"] = _record_value(r["ledger_drift"])
    if r["settle_err"] <= TOL_SETTLE:
        out["settle_err_at_most"] = TOL_SETTLE
    else:
        out["settle_err"] = _record_value(r["settle_err"])
    return out


def write_record(rows: list[dict], crit: list[dict]) -> None:
    rec = {
        "stage": "A41",
        "config": {
            "carrier": "a17_edge_cut.base_config",
            "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
            "subsistence": {"mode": "exit", "grace": 1, "needs": list(WALLS)},
            "house": "off_graph", "open_from": OPEN_FROM, "stream": STREAM,
            "draw_rows": DRAW_ROWS, "ruin_target": RUIN_TARGET,
            "p": list(P_GRID), "stakes": list(STAKES),
            "attempts": list(ATTEMPTS), "l1_multipliers": list(L1_MULTIPLIERS),
            "rules": list(RULES), "seeds": list(SEEDS), "tail": TAIL,
            "m_star": {str(p): ruin_reserve(p) for p in P_GRID},
        },
        "criteria": crit,
        "runs": [record_run(r) for r in rows],
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the grid has run and its "
                                    "readouts are not yet written into RESULTS.md.")
    RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"\nwrote {RECORD.name}")


def measure_time(write: bool) -> int:
    """D38: the heaviest cell of each cap tier, measured, not assumed."""
    wall = WALLS[-1]
    t0 = time.time()
    control = run_control(0, wall)
    t_control = time.time() - t0
    tiers = {}
    for a in ATTEMPTS:
        for m in L1_MULTIPLIERS:
            cell = (0, wall, P_GRID[0], STAKES[-1], a, m, "naive")
            t0 = time.time()
            one_cell(cell, control)
            tiers[f"attempts {a} x {m}"] = time.time() - t0
    per_tier = len(WALLS) * len(P_GRID) * len(STAKES) * len(RULES)
    per_seed = per_tier * sum(tiers.values()) + len(WALLS) * t_control
    out = {
        "control_seconds": round(t_control, 3),
        "cell_seconds": {k: round(v, 3) for k, v in tiers.items()},
        "cells_per_seed_per_tier": per_tier,
        "cells_total": len(grid()),
        "estimate_seconds": round(per_seed * len(SEEDS), 1),
        "note": ("measured on the machine that ran --time, on the heaviest "
                 "cell of each tier (D38); --run reads this file and refuses "
                 "without it"),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    if write:
        TIMING.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
        print(f"wrote {TIMING.name}")
    return 0


class _NoBookTicket(TicketNetwork):
    """Seeded fault: the settlement never books its net into the claim total."""

    planted = False

    def _book_total(self, net: float) -> None:
        type(self).planted = True


class _NoLineTicket(TicketNetwork):
    """Seeded fault: the capital line is removed."""

    planted = False

    def _stopped(self, h: np.ndarray, stake: float) -> np.ndarray:
        type(self).planted = True
        return np.zeros(h.shape, dtype=bool)


class _GoneTicket(TicketNetwork):
    """Seeded fault: a node that has left the market still plays."""

    planted = False

    def _present(self) -> np.ndarray:
        type(self).planted = True
        return np.ones(self._n, dtype=bool)


#: A cell in which nodes leave and would still hold a stake: on seed 3 at a
#: floor of 0.06, three financial nodes are out before the ticket opens and,
#: without the membership mask, play 750 times in this cell (measured on the
#: code before the mask, whose record is kept beside this file).
GONE_CELL = (3, 0.06, 0.51, 0.005, 1, 1, "naive")


def selftest_criteria() -> bool:
    """Every criterion passes on a clean base and fails on its seeded faults.

    The base is real: one cell that plays and one that cannot (at p 0.51 the
    aware reserve is 116 stakes, 29.0 at a stake of 0.25, which no node on
    this carrier holds). A criterion that failed on the base would "catch"
    every fault, so the base has to pass first.
    """
    def pick(crit, prefix):
        return next(x for x in crit if x["name"].startswith(prefix))

    ok = []
    control = run_control(0, 0.0)
    played = (0, 0.0, 0.51, 0.25, 10, 1, "naive")
    idle = (0, 0.0, 0.51, 0.25, 1, 1, "aware")
    base = [one_cell(played, control), one_cell(idle, control)]
    crit = criteria(base)
    clean = all(x["passed"] for x in crit)
    shape = (not base[0]["inert"]) and base[1]["inert"]
    ok += [clean, shape]
    print(f"clean base: all four pass {clean}; one cell played and one is "
          f"inert {shape}")

    # Planted means the override ran and there was a net amount to book.
    _NoBookTicket.planted = False
    row = one_cell(played, control, net_class=_NoBookTicket)
    got = pick(criteria([row, base[1]]), "A41-1")
    planted = _NoBookTicket.planted and row["created"] != row["destroyed"]
    ok.append(planted and not got["passed"])
    print(f"  claim total not booked   planted {planted} (net issued "
          f"{row['created'] - row['destroyed']:+.3f})   A41-1 passed="
          f"{got['passed']} (want False)")

    # Planted is read off the play count against the clean cell, which is not
    # the quantity the criterion reads, so the two cannot agree by construction.
    _NoLineTicket.planted = False
    row = one_cell(played, control, net_class=_NoLineTicket)
    got = pick(criteria([row, base[1]]), "A41-2")
    planted = (_NoLineTicket.planted
               and row["plays_total"] > base[0]["plays_total"])
    ok.append(planted and not got["passed"])
    print(f"  capital line removed     planted {planted} (plays "
          f"{row['plays_total']} against {base[0]['plays_total']})   A41-2 "
          f"passed={got['passed']} (want False)")

    # Planted is read off the play count against the clean cell, as above. The
    # clean cell has to pass first, since this base is not the one above.
    wcontrol = run_control(GONE_CELL[0], GONE_CELL[1])
    wclean = one_cell(GONE_CELL, wcontrol)
    wclean_ok = pick(criteria([wclean]), "A41-2")["passed"]
    _GoneTicket.planted = False
    row = one_cell(GONE_CELL, wcontrol, net_class=_GoneTicket)
    got = pick(criteria([row]), "A41-2")
    planted = (_GoneTicket.planted
               and row["plays_total"] > wclean["plays_total"])
    ok.append(wclean_ok and planted and not got["passed"])
    print(f"  a departed node plays    clean cell passes {wclean_ok}; planted "
          f"{planted} (plays {row['plays_total']} against "
          f"{wclean['plays_total']})   A41-2 passed={got['passed']} (want False)")

    d_plain = decompose(base[0]["N_earners"], base[0]["g_earners"],
                        base[0]["mu_earners"], base[0]["N_l1"],
                        base[0]["g_l1"], base[0]["mu_l1"])
    d_weighted = decompose(base[0]["N_earners"], base[0]["g_earners"],
                           base[0]["mu_earners"], base[0]["N_l1"],
                           base[0]["g_l1"], base[0]["mu_l1"], weighted=True)
    planted = d_plain["count"] != d_weighted["count"]
    got = pick(criteria(base, weighted=True), "A41-3")
    ok.append(planted and not got["passed"])
    print(f"  mean return by play count   planted {planted}   A41-3 passed="
          f"{got['passed']} (want False)")

    seeded = [dict(base[0], mu_mid=base[0]["mu_mid"] * 1.5), base[1]]
    got = pick(criteria(seeded), "A41-3")
    ok.append(not got["passed"])
    print(f"  one class another price     A41-3 passed={got['passed']} "
          f"(want False)")

    seeded = [dict(base[0], pnl_ledger_mid=base[0]["pnl_ledger_mid"] + 0.5),
              base[1]]
    got = pick(criteria(seeded), "A41-3")
    ok.append(not got["passed"])
    print(f"  ledger off the count        A41-3 passed={got['passed']} "
          f"(want False)")

    seeded = [dict(base[0], inert=True), base[1]]
    got = pick(criteria(seeded), "A41-4")
    ok.append(not got["passed"])
    print(f"  a played cell flagged inert A41-4 passed={got['passed']} "
          f"(want False)")

    seeded = [base[0], dict(base[1], diff_to_control=3)]
    got = pick(criteria(seeded), "A41-4")
    ok.append(not got["passed"])
    print(f"  an idle cell off control    A41-4 passed={got['passed']} "
          f"(want False)")

    got = criteria([])
    ok.append(all((not x["passed"]) and x["detail"].startswith("Void")
                  for x in got))
    print(f"  no cells at all             every criterion Void and not "
          f"passed: {ok[-1]}")
    return all(ok)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true", help="A41-0")
    ap.add_argument("--selftest", action="store_true",
                    help="seeded faults the gate and the criteria must catch")
    ap.add_argument("--time", action="store_true",
                    help="seconds per cell tier, measured (D38)")
    ap.add_argument("--run", action="store_true", help="the grid")
    ap.add_argument("--smoke", action="store_true",
                    help="with --run: seed 0 only, nothing written")
    ap.add_argument("--no-write", action="store_true",
                    help="with --time or --run: write nothing")
    args = ap.parse_args()

    if args.selftest:
        a = selftest()
        print("\ncriteria selftest:")
        b = selftest_criteria()
        print("criteria selftest:", "PASS" if b else "FAIL")
        return 0 if (a and b) else 1
    if args.gate:
        return 0 if run_gate().ok else 1
    if args.time:
        return measure_time(write=not args.no_write)
    if args.run:
        if not args.smoke and not TIMING.exists():
            print("refusing: run --time first (D38)")
            return 1
        rows = run_grid(seeds=SEEDS[:1] if args.smoke else SEEDS)
        crit = criteria(rows)
        print()
        for x in crit:
            print(f"  {'PASS' if x['passed'] else 'FAIL'}[{x['kind']}] {x['name']}")
            print(f"        {x['detail'][:600]}")
        print_residues(rows)
        print_readouts(rows)
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
        else:
            write_record(rows, crit)
        return 0 if all(x["passed"] for x in crit) else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
