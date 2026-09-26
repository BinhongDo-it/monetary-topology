"""A41, second block: new claims put into one class, and a line of credit on the ticket.

Ruled 2026-09-15. In the first block a ticket on identical terms paid out a
net amount, and at the end of a run that amount was held about three quarters
by the financial layer, a quarter by the intermediate block and a fraction of
a per cent by the wage earners, whichever class had won it. Two arms follow.

**Injection.** Whether that split belongs to the carrier. No ticket is
offered. From round 50 a fixed amount of new claims is added in every round to
one class, divided equally over the nodes of that class still trading when the
round opens, and each run's closing holdings are read against a control that
shares every random draw.

**Credit.** What changes when the house lends the stake. The first block's
naive ticket is run again with a line of credit of one stake, four stakes or
no limit: a node plays while its holding is at least the stake less the line.
Nothing a node does is changed, only the terms of its edge to the house, and
the capital line that decided in the first block who played how often is
lowered in steps.

Steps, one at a time and in this order:

    python experiments/a41b_credit_inject.py --arm inject --gate          # A41-9
    python experiments/a41b_credit_inject.py --arm inject --selftest      # seeded faults
    python experiments/a41b_credit_inject.py --arm inject --run --smoke   # seed 0, nothing written
    python experiments/a41b_credit_inject.py --arm inject --run           # 150 runs, writes the record

    python experiments/a41b_credit_inject.py --arm credit --gate          # A41-5
    python experiments/a41b_credit_inject.py --arm credit --selftest      # seeded faults
    python experiments/a41b_credit_inject.py --arm credit --time          # seconds per cell tier (D38)
    python experiments/a41b_credit_inject.py --arm credit --run --smoke   # seed 0, nothing written
    python experiments/a41b_credit_inject.py --arm credit --run           # 1080 cells, writes the record

``--run --arm credit`` without ``--smoke`` refuses until ``--time`` has
written its file. The criteria are written in this file and the record
carries their text, so the quantities a run produces are all reported.
"""

from __future__ import annotations

import argparse
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

from monetary_topology.network import Network, NetworkConfig  # noqa: E402

#: The first block's carrier, classes, field comparison and record helpers,
#: imported rather than restated, so both blocks read one definition of each.
#: The carrier is A17's: 20 financial nodes, a 30-node intermediate block that
#: is exactly the set of wage payers, 150 production nodes, 300 rounds.
from a41_same_ticket import (  # noqa: E402
    ALL_CLASSES,
    ATTEMPTS,
    DRAW_ROWS,
    ELASTICITY,
    F2I,
    GONE_CELL,
    L1_MULTIPLIERS,
    OPEN_FROM,
    P_GRID,
    PAIRS,
    PLAYING,
    ROUNDS,
    SEEDS,
    STAKES,
    STREAM,
    TAIL,
    TOL_IDENTITY,
    TOL_LEDGER,
    TOL_SETTLE,
    WALLS,
    TicketNetwork,
    TicketSpec,
    _fmt,
    _record_value,
    base_config,
    classes_of,
    decompose,
    diff_fields,
    gini,
    identity_residues,
    print_residues as print_ticket_residues,
    top_share,
)
from a41_same_ticket import RECORD as TICKET_RECORD  # noqa: E402
from a41_same_ticket import grid as ticket_grid  # noqa: E402
from a41_same_ticket import one_cell as ticket_cell  # noqa: E402
from a41_same_ticket import record_run as ticket_record_run  # noqa: E402
from a41_same_ticket import run_control as ticket_control  # noqa: E402

# ==========================================================================
# the injection arm

#: Where the new claims go: the first block's four classes.
TARGETS = ALL_CLASSES

#: Claims added per round. Measured on five seeds before this script, they
#: leave the closing stock about 1.1, 11 and 100 times the control's: three
#: points from the low end of the first block's stock ratios, which ran from
#: 1.006 to 153, to its high end.
PER_ROUND = (0.04, 4.0, 40.0)

INJECT_RECORD = RESULTS / "a41_inject.json"

#: A node's landing is ``(h + a) - h``, which can miss ``a`` in the last places
#: of ``h``, so landings are held to an absolute tolerance.
TOL_LAND = 1e-9

#: Whether this arm's readings are written into RESULTS.md. While they are not,
#: the record carries ``diagnostic_only`` and a reason; once they are, neither.
#: Closed 2026-09-16 for the grid below. A change to the grid sets this back to
#: False until the new readings are written.
CLOSED_INJECT = True


class InjectNetwork(Network):
    """The carrier, with new claims added to one class at the start of each
    injection round.

    **Where it lands.** ``_pre_round`` runs before the round's issuance is
    credited and outside the round's stock-flow assertion, the zone the ticket
    settles in. The amount is divided equally over the target class's nodes
    still trading when the round opens. A node that has left the market
    receives nothing, and a round in which no node of the class is trading adds
    nothing and is recorded as empty. The claim total is booked by what was
    added and by nothing else.

    **Not inflow.** The claims arrive without an edge, so they never count as
    a node's inflow, and a node that has left is not brought back by them.

    **Nothing drawn.** The injection reads no random number, so a treated run
    and its control share every propensity draw.

    ``target = None`` is off: the branch is never entered and nothing is
    recorded. With a target and an amount of zero the branch is entered in
    every round from ``open_from`` and adds zeros, which is what the gate's
    first half compares.
    """

    def __init__(self, config: NetworkConfig, target: str | None = None,
                 per_round: float = 0.0, open_from: int = OPEN_FROM) -> None:
        super().__init__(config)
        if target is not None and target not in TARGETS:
            raise ValueError(f"target must be one of {TARGETS} or None")
        if not per_round >= 0.0:
            raise ValueError("per_round must be non-negative")
        if open_from < 0:
            raise ValueError("open_from must be non-negative")
        self.target = target
        self.per_round = float(per_round)
        self.open_from = int(open_from)
        self._target_ix = (classes_of(self)[target] if target is not None
                           else np.zeros(0, dtype=int))
        self._rec: dict[str, list] = {key: [] for key in (
            "round", "h0", "h1", "alive", "k", "amount", "empty")}

    # Four one-line hooks, so that a seeded fault replaces a line rather than
    # a copy of the landing.

    def _inject_open(self, t: int) -> bool:
        return self.target is not None and t >= self.open_from

    def _recipients(self) -> np.ndarray:
        ix = self._target_ix
        return ix[self._alive[ix]]

    def _land(self, h: np.ndarray) -> None:
        self.holdings = h

    def _book_total(self, amount: float) -> None:
        self._total_claims += amount

    def _pre_round(self, t: int) -> None:
        super()._pre_round(t)
        if not self._inject_open(t):
            return
        n = self._n
        h0 = np.array(self.holdings, dtype=float, copy=True)
        # ``alive`` is read off the carrier and kept for the record; the
        # recipients come through the hook and are what the landing obeys.
        # They are the same set unless a fault replaces the hook, and the
        # record is how such a fault is seen.
        alive = np.array(self._alive, dtype=bool, copy=True)
        ix = np.asarray(self._recipients(), dtype=int)
        k = int(ix.size)
        amount = self.per_round if k else 0.0
        mask = np.zeros(n, dtype=bool)
        mask[ix] = True
        # ``where`` rather than an in-place add, so a node outside the split
        # keeps its holding bit for bit.
        h = np.where(mask, h0 + (amount / k if k else 0.0), h0)
        before, after = float(h0.sum()), float(h.sum())
        tol = 1e-9 * max(1.0, abs(before))
        if abs((after - before) - amount) > tol:
            raise AssertionError(
                f"injection ledger does not close at round {t}: holdings moved "
                f"{after - before!r} against {amount!r} added")
        self._land(h)
        self._book_total(amount)
        rec = self._rec
        rec["round"].append(t)
        rec["h0"].append(h0)
        # Read back off the network rather than the array computed above, so
        # the record shows what landed and not what was meant to.
        rec["h1"].append(np.array(self.holdings, dtype=float, copy=True))
        rec["alive"].append(alive)
        rec["k"].append(k)
        rec["amount"].append(amount)
        rec["empty"].append(k == 0)

    def inject_record(self) -> dict:
        """Everything the injection did, one row per injection round."""
        rec, n = self._rec, self._n
        out: dict = {
            "rounds": np.asarray(rec["round"], dtype=np.int64),
            "k": np.asarray(rec["k"], dtype=np.int64),
            "amount": np.asarray(rec["amount"], dtype=float),
            "empty": np.asarray(rec["empty"], dtype=bool),
        }
        for key in ("h0", "h1"):
            out[key] = np.vstack(rec[key]) if rec[key] else np.zeros((0, n))
        out["alive"] = (np.vstack(rec["alive"]) if rec["alive"]
                        else np.zeros((0, n), dtype=bool))
        return out


# --------------------------------------------------------------------------
# A41-9: the gate

GATE_SEEDS = (0, 1)

#: The second half's amount: the heaviest of the grid.
INJECT_GATE_ON = PER_ROUND[-1]


@dataclass
class GateResult:
    ok: bool = True
    rows: dict = field(default_factory=lambda: {"one": [], "two": [], "three": []})


def generators_differ(net: Network, ctrl: Network) -> list[str]:
    """Names of the random generators a run holds whose state differs from
    the control's at the end of the run."""
    out = []
    for name in sorted(vars(ctrl)):
        g = getattr(ctrl, name)
        if not isinstance(g, np.random.Generator):
            continue
        other = getattr(net, name, None)
        if (not isinstance(other, np.random.Generator)
                or other.bit_generator.state != g.bit_generator.state):
            out.append(name)
    return out


def run_inject_gate(net_class=InjectNetwork) -> GateResult:
    """A41-9, three halves. Prints one line per run.

    **One**, rule 19: an injection that is off, and an injection of zero into
    each class with its branch entered in every round from ``OPEN_FROM``,
    leave every history field bitwise the plain network's. **Two**: an
    injection of ``INJECT_GATE_ON`` a round leaves every row before ``OPEN_FROM``
    bitwise the control's, and does move the run after it, or the half would
    compare nothing. **Three**: every random generator the network holds ends
    each run of the first two halves in the state the control's ends in. The
    carrier's only draw from its own generator is the per-round propensity,
    whose size is the node count whatever the holdings, so an injection that
    read a generator even once is seen here whether or not a later draw would
    have shown it.

    Under a floor the unreached class leaves in round 0 (it has no in-edge),
    so the second half does not inject into it there: nothing could land.

    ``net_class`` is the selftest's hook: a subclass carrying a seeded fault.
    """
    res = GateResult()
    twins: dict = {}
    streams: list = []

    def twin(seed: int, wall: float):
        if (seed, wall) not in twins:
            net = Network(base_config(seed, need=wall))
            twins[(seed, wall)] = (net, net.run())
        return twins[(seed, wall)]

    def report(half: str, label: str, bad: list, notes: list) -> None:
        good = not bad and not notes
        res.ok = res.ok and good
        res.rows[half].append({"label": label, "bad": bad, "notes": notes})
        tail = (f"   {'; '.join(bad[:4])}" if bad else "") + (
            f"   {'; '.join(notes)}" if notes else "")
        print(f"  {'ok  ' if good else 'FAIL'} {label:34s} differing: "
              f"{len(bad)}{tail}")

    print("A41-9: the injection does not touch the network\n")
    t0 = time.time()

    print("one: off, and zero into each class with the branch entered, "
          "every history field")
    for wall in WALLS:
        for seed in GATE_SEEDS:
            cnet, ctrl = twin(seed, wall)
            for target in (None,) + tuple(TARGETS):
                net = net_class(base_config(seed, need=wall), target, 0.0)
                hist = net.run()
                rec = net.inject_record()
                notes = []
                want = 0 if target is None else ROUNDS - OPEN_FROM
                if rec["rounds"].size != want:
                    notes.append(f"branch entered {rec['rounds'].size} times, "
                                 f"expected {want}")
                if rec["amount"].size and float(np.abs(rec["amount"]).max()):
                    notes.append("a zero injection recorded a non-zero amount")
                label = f"{target or 'off'} wall {wall:.2f} seed {seed}"
                report("one", label, diff_fields(hist, ctrl), notes)
                streams.append((f"zero {label}", generators_differ(net, cnet)))

    print(f"\ntwo: {INJECT_GATE_ON:g} a round into each class, every row before "
          f"round {OPEN_FROM}")
    for wall in WALLS:
        for seed in GATE_SEEDS:
            cnet, ctrl = twin(seed, wall)
            for target in TARGETS:
                if wall > 0.0 and target == "unreached":
                    continue
                net = net_class(base_config(seed, need=wall), target, INJECT_GATE_ON)
                hist = net.run()
                rec = net.inject_record()
                notes = []
                first = int(rec["rounds"][0]) if rec["rounds"].size else None
                if first != OPEN_FROM:
                    notes.append(f"first injection round {first}, "
                                 f"expected {OPEN_FROM}")
                if not float(rec["amount"].sum()):
                    notes.append("nothing landed, so the half is empty")
                if np.array_equal(hist.holdings[-1], ctrl.holdings[-1]):
                    notes.append("closing holdings equal the control's, so "
                                 "the injection moved nothing")
                label = f"{target} wall {wall:.2f} seed {seed}"
                report("two", label,
                       diff_fields(hist, ctrl, before=OPEN_FROM), notes)
                streams.append((f"on {label}", generators_differ(net, cnet)))

    print("\nthree: every generator's state at the end of the runs above")
    for label, bad in streams:
        report("three", label, bad, [])

    print(f"\nA41-9: {'PASS' if res.ok else 'FAIL'}   ({time.time() - t0:.1f} s)")
    return res


class _EarlyInject(InjectNetwork):
    """Seeded fault: the injection opens one round early."""

    def _inject_open(self, t: int) -> bool:
        return self.target is not None and t >= self.open_from - 1


class _NoLandInject(InjectNetwork):
    """Seeded fault: the split is computed and booked and never lands."""

    planted = False

    def _land(self, h: np.ndarray) -> None:
        type(self).planted = True


class _NetworkStreamInject(InjectNetwork):
    """Seeded fault: choosing the recipients reads the network's generator."""

    used_network_stream = False

    def _recipients(self) -> np.ndarray:
        type(self).used_network_stream = True
        self.rng.random()
        ix = self._target_ix
        return ix[self._alive[ix]]


def selftest_inject_gate() -> bool:
    """The clean gate passes, and each seeded fault is planted and makes the
    gate fail on the half meant to see it (11f).

    **Clean first**, since a gate that failed on clean code would "catch"
    every fault. **Planted next**, since a gate that did not fail and a fault
    that was never planted print the same thing. **Then the half**: the early
    opening on the second half's field comparison, a split that never lands
    on the second half's note that the run moved nothing, the borrowed
    generator on the third half's generator states.
    """
    ok = []

    res = run_inject_gate()
    ok.append(res.ok)
    print(f"--- clean gate passes: {res.ok}\n")

    probe = _EarlyInject(base_config(0, need=0.0), "mid", INJECT_GATE_ON)
    probe.run()
    first = int(probe.inject_record()["rounds"][0])
    planted = first == OPEN_FROM - 1
    ok.append(planted)
    print(f"--- fault: early   planted: first injection round {first}   "
          f"(want {OPEN_FROM - 1})")
    res = run_inject_gate(_EarlyInject)
    seen = any(row["bad"] for row in res.rows["two"])
    ok.append(not res.ok and seen)
    print(f"--- caught: {not res.ok}, on the second half's field comparison: "
          f"{seen}\n")

    # Planted is read off the amount the fault's run recorded, which the note
    # that catches it does not read.
    _NoLandInject.planted = False
    probe = _NoLandInject(base_config(0, need=0.0), "mid", INJECT_GATE_ON)
    probe.run()
    booked = float(probe.inject_record()["amount"].sum())
    planted = _NoLandInject.planted and booked > 0.0
    ok.append(planted)
    print(f"--- fault: never lands   planted: {planted} (recorded {booked:g} "
          f"as injected)")
    res = run_inject_gate(_NoLandInject)
    seen = any("moved nothing" in note for row in res.rows["two"]
               for note in row["notes"])
    ok.append(not res.ok and seen)
    print(f"--- caught: {not res.ok}, on the second half's note that the run "
          f"moved nothing: {seen}\n")

    _NetworkStreamInject.used_network_stream = False
    res = run_inject_gate(_NetworkStreamInject)
    planted = _NetworkStreamInject.used_network_stream
    seen = any(row["bad"] for row in res.rows["three"])
    also = any(row["bad"] for row in res.rows["one"])
    ok.append(planted and not res.ok and seen)
    print(f"--- fault: network generator   planted: {planted}   caught: "
          f"{not res.ok}, on the third half's generator states: {seen} "
          f"(and on the first half's fields: {also})\n")

    print("gate selftest:", "PASS" if all(ok) else "FAIL")
    return all(ok)


# --------------------------------------------------------------------------
# the grid


def inject_grid(seeds=SEEDS) -> list[tuple]:
    """(seed, wall, target, per_round), seed outermost, so a seed's controls
    are built once and dropped before the next seed.

    The unreached class is injected into only without a floor. It has no
    in-edge on this carrier, so under a floor every node of it leaves in round
    0, and since the injection is not inflow none comes back: a run that
    injects into it there is its control. ``run_inject_grid`` checks the in-edges.
    """
    return [(seed, wall, target, q)
            for seed in seeds for wall in WALLS for target in TARGETS
            if wall == 0.0 or target != "unreached"
            for q in PER_ROUND]


def inject_control(seed: int, wall: float):
    """A run's control: the carrier with the injection off, which A41-9 shows
    is bitwise the plain network."""
    net = InjectNetwork(base_config(seed, need=wall))
    return net, net.run()


def inject_run(cell: tuple, control, net_class=InjectNetwork) -> dict:
    """One treated run read against its control. Everything a readout or the
    criterion needs is put in the row, so the criterion never reruns anything."""
    seed, wall, target, q = cell
    cnet, chist = control
    net = net_class(base_config(seed, need=wall), target, q)
    hist = net.run()
    rec = net.inject_record()
    cls = classes_of(net)
    row: dict = {"seed": seed, "wall": wall, "target": target, "per_round": q}

    # A41-10: the ledger, measured off the accounts at the end.
    m_t = float(net.holdings.sum()) + float(net._parked.sum())
    row["M_t"] = m_t
    row["ledger_drift"] = abs(float(net._total_claims) - m_t)

    # A41-10: where each round's amount landed. Who should have received it is
    # read off the module's partition and the carrier's membership record,
    # not off the hook that chose the recipients.
    amount, H0, H1 = rec["amount"], rec["h0"], rec["h1"]
    member = np.zeros(net._n, dtype=bool)
    member[cls[target]] = True
    due = rec["alive"] & member[None, :]
    n_due = due.sum(axis=1)
    landed = H1 - H0
    share = np.divide(amount, n_due, out=np.zeros_like(amount),
                      where=n_due > 0)
    node_err = np.where(due, np.abs(landed - share[:, None]), 0.0)
    sum_err = np.abs(landed.sum(axis=1) - amount)
    row["rounds_ok"] = bool(np.array_equal(
        rec["rounds"], np.arange(OPEN_FROM, ROUNDS)))
    row["off_viol"] = int(((H1 != H0) & ~due).sum())
    row["amount_viol"] = int((((n_due > 0) & (amount != q))
                              | ((n_due == 0) & (amount != 0.0))).sum())
    row["flag_viol"] = int((rec["empty"] != (n_due == 0)).sum())
    row["empty_rounds"] = int((n_due == 0).sum())
    row["land_err"] = float(max(node_err.max(initial=0.0),
                                sum_err.max(initial=0.0)))
    row["injected"] = float(amount.sum())
    row["recipients"] = int(rec["k"].sum())

    # I1: each class's closing holdings against the control, and its share of
    # the four classes' total gain. The four partition the nodes.
    ht, hc = hist.holdings[-1], chist.holdings[-1]
    gain = {name: float(ht[cls[name]].sum() - hc[cls[name]].sum())
            for name in ALL_CLASSES}
    total = sum(gain.values())
    for name in ALL_CLASSES:
        row[f"dh_{name}"] = gain[name]
        row[f"gain_{name}"] = gain[name] / total if total else float("nan")

    # I2: what stayed in holdings against what was injected, and the stock,
    # the receiving set and the trade against the control. The carrier issues
    # claims of its own in some rounds, and the control's issuance is kept
    # beside the treated run's, since what an injection displaces of it is
    # what the four classes' gain falls short of the injected amount by.
    m_c = float(cnet.holdings.sum()) + float(cnet._parked.sum())
    sup_t = float(np.median(hist.effective_support[-TAIL:]))
    sup_c = float(np.median(chist.effective_support[-TAIL:]))
    trade_t = float(hist.total_volume[-TAIL:].sum()
                    - hist.wage_paid[-TAIL:].sum())
    trade_c = float(chist.total_volume[-TAIL:].sum()
                    - chist.wage_paid[-TAIL:].sum())
    row.update({
        "kept": total / row["injected"] if row["injected"] else float("nan"),
        "M_c": m_c, "M_ratio": m_t / m_c if m_c > 0 else float("nan"),
        "support_t": sup_t, "support_c": sup_c,
        "support_ratio": sup_t / sup_c if sup_c > 0 else float("nan"),
        "trade_t": trade_t, "trade_c": trade_c,
        "trade_ratio": trade_t / trade_c if trade_c > 0 else float("nan"),
        "issuance_t": float(hist.issuance[OPEN_FROM:].sum()),
        "issuance_c": float(chist.issuance[OPEN_FROM:].sum()),
    })
    for name in ALL_CLASSES:
        ix = cls[name]
        row[f"left_{name}_t"] = int((~net._alive[ix]).sum())
        row[f"left_{name}_c"] = int((~cnet._alive[ix]).sum())

    # A run that injected nothing is a third state and carries no reading.
    row["inert"] = row["injected"] == 0.0
    row["diff_to_control"] = len(diff_fields(hist, chist))
    return row


def run_inject_grid(seeds=SEEDS) -> list[dict]:
    cells = inject_grid(seeds)
    controls: dict = {}
    rows = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        seed, wall = cell[0], cell[1]
        if (seed, wall) not in controls:
            controls = {k: v for k, v in controls.items() if k[0] == seed}
            controls[(seed, wall)] = inject_control(seed, wall)
            if wall > 0.0:
                cnet = controls[(seed, wall)][0]
                u = classes_of(cnet)["unreached"]
                if np.asarray(cnet.adjacency)[:, u].any():
                    raise AssertionError(
                        f"seed {seed}: an unreached node has an in-edge, so the "
                        f"runs this grid skips under a floor are not controls")
        rows.append(inject_run(cell, controls[(seed, wall)]))
        if i % 30 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}  ({time.time() - t0:.0f} s)", flush=True)
    return rows


# --------------------------------------------------------------------------
# the criterion, about the instrument (the arm registers no reading with a
# direction; the readouts are printed below it)


def _inject_label(r: dict) -> str:
    return (f"seed {r['seed']} wall {r['wall']} {r['target']} "
            f"{r['per_round']:g} a round")


def inject_criteria(rows: list[dict]) -> list[dict]:
    name = ("A41-10  every injected amount is booked into the claim total and "
            "lands, split equally, on the target class's nodes still trading")
    if not rows:
        return [dict(name=name, kind="instrument", passed=False,
                     detail="Void: no runs, nothing was evaluated")]
    rel = [r["ledger_drift"] / max(1.0, abs(r["M_t"])) for r in rows]
    keys = ("off_viol", "amount_viol", "flag_viol")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    worst_land = max(r["land_err"] for r in rows)
    bad = [r for r, x in zip(rows, rel)
           if not x <= TOL_LEDGER or not r["rounds_ok"]
           or any(r[k] for k in keys) or not r["land_err"] <= TOL_LAND]
    empty = sum(r["empty_rounds"] for r in rows)
    inert = sum(1 for r in rows if r["inert"])
    return [dict(
        name=name, kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} runs: the claim total the module "
                f"tracks equals holdings plus parked at the end to within "
                f"{TOL_LEDGER:.0e} of the stock; every run recorded rounds "
                f"{OPEN_FROM} to {ROUNDS - 1}; no node outside the target "
                f"class's nodes trading at a round's opening moved in that "
                f"round; each of those received the round's amount divided by "
                f"their number, and a round's landings add up to its amount, "
                f"both to within {TOL_LAND:.0e}; a round with none of them "
                f"added nothing and is recorded empty ({empty} such rounds, "
                f"{inert} runs in which nothing landed)." if not bad else
                f"Fails on {len(bad)} of {len(rows)} runs, violations {totals}, "
                f"largest relative drift {max(rel):.3e}, largest landing error "
                f"{worst_land:.3e}: " + "; ".join(_inject_label(r) for r in bad[:4])))]


def print_inject_residues(rows: list[dict]) -> None:
    """The machine-precision residues on the machine that ran, to stdout only;
    the record carries the tolerance each is held to."""
    if not rows:
        return
    rel = max(r["ledger_drift"] / max(1.0, abs(r["M_t"])) for r in rows)
    land = max(r["land_err"] for r in rows)
    print(f"\n  residues on this machine, not written: ledger {rel:.3e}, "
          f"landing {land:.3e}")


# --------------------------------------------------------------------------
# readouts, per run and per seed, never averaged across seeds


def ticket_split() -> dict | None:
    """The first block's split, read off its record when this runs: each
    playing class's closing gain against the control over the three classes'
    total, on the cells in which all three played. The record carries each
    class's gain as its retention times its net result."""
    if not TICKET_RECORD.exists():
        return None
    runs = json.loads(TICKET_RECORD.read_text(encoding="utf-8"))["runs"]
    sel = [r for r in runs
           if all(r[f"plays_{c}"] > 0 and r.get(f"retained_{c}") is not None
                  for c in PLAYING)]
    shares: dict = {c: [] for c in PLAYING}
    for r in sel:
        g = {c: r[f"retained_{c}"] * r[f"pnl_{c}"] for c in PLAYING}
        s = sum(g.values())
        for c in PLAYING:
            shares[c].append(g[c] / s)
    return {"cells": len(sel), "shares": shares}


def _range(vals: list, spec: str) -> str:
    vals = [v for v in vals if v is not None and math.isfinite(v)]
    if not vals:
        return "-"
    return f"[{format(min(vals), spec)}, {format(max(vals), spec)}]"


def print_inject_readouts(rows: list[dict]) -> None:
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["target"], r["per_round"], r["wall"]), []).append(r)
    live = [r for r in rows if not r["inert"]]

    print("\nI1  each class's share of the closing gain against the control, "
          "l1 / mid / earners / unreached, per seed")
    base = ticket_split()
    if base is None:
        print("  the first block's record is not on disk, so its split is not "
              "printed")
    else:
        parts = []
        for c in PLAYING:
            v = base["shares"][c]
            parts.append(f"{c} {statistics.median(v):.4f} "
                         f"[{min(v):.4f}, {max(v):.4f}]")
        print(f"  first block, the {base['cells']} cells in which all three "
              f"classes played (three classes, median and range): "
              + "  ".join(parts))
    for key, rs in groups.items():
        target, q, wall = key
        cols = " | ".join(
            "-" if r["inert"] else
            (f"{r['gain_l1']:.3f}/{r['gain_mid']:.3f}/"
             f"{r['gain_earners']:.4f}/{r['gain_unreached']:+.4f}")
            for r in rs)
        print(f"  {target:9s} {q:>5g} wall {wall:.2f}  {cols}")
    print(f"  this arm, range over {len(live)} runs: " + "  ".join(
        f"{c} {_range([r['gain_' + c] for r in live], '.4f')}"
        for c in ALL_CLASSES))
    for t in TARGETS:
        sub = [r for r in live if r["target"] == t]
        if sub:
            print(f"    into {t:9s} ({len(sub)} runs): " + "  ".join(
                f"{c} {_range([r['gain_' + c] for r in sub], '.4f')}"
                for c in ALL_CLASSES))

    print("\nI2  kept (the four classes' gain over what was injected), the "
          "carrier's own issuance from round 50 treated (control), the stock, "
          "the support and the trade against the control, and earners out at "
          "the end treated (control), per seed")
    for key, rs in groups.items():
        target, q, wall = key
        cols = " | ".join(
            "-" if r["inert"] else
            (f"kept {_fmt(r['kept'], '.4f')} "
             f"iss {r['issuance_t']:.4f}({r['issuance_c']:.4f}) "
             f"M {_fmt(r['M_ratio'], '.2f')} "
             f"sup {_fmt(r['support_ratio'], '.3f')} "
             f"trade {_fmt(r['trade_ratio'], '.2f')} "
             f"out {r['left_earners_t']}({r['left_earners_c']})")
            for r in rs)
        print(f"  {target:9s} {q:>5g} wall {wall:.2f}  {cols}")


# --------------------------------------------------------------------------
# the record


def inject_record_run(r: dict) -> dict:
    """One row as the record carries it. The two residue fields are written as
    the tolerance they were held to when they are inside it, and as the value
    when they are not, since a residue outside its tolerance is no longer
    machine noise."""
    out = {k: _record_value(v) for k, v in r.items()
           if k not in ("ledger_drift", "land_err")}
    if r["ledger_drift"] / max(1.0, abs(r["M_t"])) <= TOL_LEDGER:
        out["ledger_drift_relative_at_most"] = TOL_LEDGER
    else:
        out["ledger_drift"] = _record_value(r["ledger_drift"])
    if r["land_err"] <= TOL_LAND:
        out["land_err_at_most"] = TOL_LAND
    else:
        out["land_err"] = _record_value(r["land_err"])
    return out


def write_inject_record(rows: list[dict], crit: list[dict]) -> None:
    rec = {
        "stage": "A41",
        "arm": "inject",
        "config": {
            "carrier": "a17_edge_cut.base_config",
            "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
            "subsistence": {"mode": "exit", "grace": 1, "needs": list(WALLS)},
            "injection": {
                "open_from": OPEN_FROM,
                "targets": list(TARGETS),
                "per_round": list(PER_ROUND),
                "split": "equal over the target class's nodes trading at the "
                         "round's opening",
                "booked": "claim total",
                "unreached": "without a floor only",
            },
            "seeds": list(SEEDS), "tail": TAIL,
        },
        "criteria": crit,
        "runs": [inject_record_run(r) for r in rows],
    }
    if not CLOSED_INJECT:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Arm not closed: the grid has run and its "
                                    "readouts are not yet written into "
                                    "RESULTS.md.")
    INJECT_RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"\nwrote {INJECT_RECORD.name}")


# --------------------------------------------------------------------------
# the criterion's seeded faults


class _AllNodesInject(InjectNetwork):
    """Seeded fault: the amount is split over every node still trading."""

    planted = False

    def _recipients(self) -> np.ndarray:
        type(self).planted = True
        return np.flatnonzero(self._alive)


class _GoneInject(InjectNetwork):
    """Seeded fault: a node of the class that has left the market still
    receives its part."""

    planted = False

    def _recipients(self) -> np.ndarray:
        type(self).planted = True
        return self._target_ix


class _NoBookInject(InjectNetwork):
    """Seeded fault: the injection never books the claim total."""

    planted = False

    def _book_total(self, amount: float) -> None:
        type(self).planted = True


def selftest_inject_criteria() -> bool:
    """The criterion passes on a clean base and fails on each seeded fault.

    The base is real: one run that lands every round, and one whose target
    class has left the market before the injection opens, so every round is
    empty and the run is its control. A criterion that failed on the base
    would "catch" every fault, so the base has to pass first. Each fault's
    planting is read off a quantity the criterion does not read.
    """
    ok = []
    wall = WALLS[-1]
    control = inject_control(0, wall)
    lands = (0, wall, "mid", PER_ROUND[1])
    empty = (0, wall, "unreached", PER_ROUND[1])
    base = [inject_run(lands, control), inject_run(empty, control)]
    got = inject_criteria(base)[0]
    shape = (base[0]["injected"] > 0.0 and base[0]["empty_rounds"] == 0
             and base[1]["inert"]
             and base[1]["empty_rounds"] == ROUNDS - OPEN_FROM
             and base[1]["diff_to_control"] == 0)
    ok += [got["passed"], shape]
    print(f"clean base: A41-10 passes {got['passed']}; one run landed "
          f"{base[0]['injected']:g} and one had every round empty and is "
          f"bitwise its control {shape}")

    # Planted is read off the hook's recipient count against the clean run.
    _AllNodesInject.planted = False
    row = inject_run(lands, control, net_class=_AllNodesInject)
    got = inject_criteria([row, base[1]])[0]
    planted = (_AllNodesInject.planted
               and row["recipients"] > base[0]["recipients"])
    ok.append(planted and not got["passed"])
    print(f"  split over every node        planted {planted} (recipients "
          f"{row['recipients']} against {base[0]['recipients']})   A41-10 "
          f"passed={got['passed']} (want False)")

    # Planted is read off the hook's recipient count against the clean empty
    # run, whose class has left the market before the injection opens.
    _GoneInject.planted = False
    row = inject_run(empty, control, net_class=_GoneInject)
    got = inject_criteria([base[0], row])[0]
    planted = (_GoneInject.planted
               and row["recipients"] > base[1]["recipients"])
    ok.append(planted and not got["passed"])
    print(f"  a departed node receives     planted {planted} (recipients "
          f"{row['recipients']} against {base[1]['recipients']})   A41-10 "
          f"passed={got['passed']} (want False)")

    # Planted is read off the amount the run recorded as landed.
    _NoBookInject.planted = False
    row = inject_run(lands, control, net_class=_NoBookInject)
    got = inject_criteria([row, base[1]])[0]
    planted = _NoBookInject.planted and row["injected"] > 0.0
    ok.append(planted and not got["passed"])
    print(f"  claim total not booked       planted {planted} (landed "
          f"{row['injected']:g})   A41-10 passed={got['passed']} (want False)")

    got = inject_criteria([])[0]
    ok.append((not got["passed"]) and got["detail"].startswith("Void"))
    print(f"  no runs at all               Void and not passed: {ok[-1]}")
    return all(ok)


# ==========================================================================
# the credit arm

#: Credit lines, in stakes. A node attempts a play while it holds at least the
#: stake less its line, so a loss leaves it no lower than minus the line. A
#: line of zero is the first block's ticket: that column is not run again, and
#: A41-5 checks on seed 0 that the credit arm with a line of zero reproduces
#: the first block's record field by field. A line of ``m*`` stakes is not run:
#: on the two probe seeds it equalled the unbounded line cell by cell except
#: where the unreached class played without a floor.
CREDITS = (("1s", 1.0), ("4s", 4.0), ("unbounded", math.inf))
CREDIT_STAKES = dict(CREDITS)

CREDIT_RECORD = RESULTS / "a41_credit.json"
CREDIT_TIMING = RESULTS / "a41_credit_timing.json"

#: Whether this arm's readings are written into RESULTS.md. While they are not,
#: the record carries ``diagnostic_only`` and a reason; once they are, neither.
#: Closed 2026-09-16 for the grid below. A change to the grid sets this back to
#: False until the new readings are written.
CLOSED_CREDIT = True

#: How the first block's record names a cell.
TICKET_KEYS = ("seed", "wall", "p", "stake", "attempts", "l1_mult", "rule")

#: The size of the column a line of zero is: seed 0's naive cells.
ZERO_LINE_CELLS = (len(WALLS) * len(P_GRID) * len(STAKES) * len(ATTEMPTS)
                   * len(L1_MULTIPLIERS))

_ABSENT = object()


class CreditTicketNetwork(TicketNetwork):
    """The first block's ticket with a line of credit, and nothing else changed.

    **One hook.** The capital line reads ``h < stake - line`` in place of
    ``h < stake``. A line of zero leaves the expression the first block's to
    the bit, since ``stake - 0.0`` is ``stake``. Node rules are untouched: only
    the terms of the edge to the house change.

    **What a negative holding is.** A debt to the house, with no interest,
    which the house never calls. Every mechanism this carrier runs that reads
    holdings for spending or for wages reads ``max(h, 0)``, so a node in debt
    spends nothing and pays no wages, and what flows in fills the debt before
    any of it can be spent. A play is attempted only from a holding of at
    least the stake less the line, so no node goes below minus the line.

    The naive rule only: the first block has read what the aware rule does.
    """

    def __init__(self, config: NetworkConfig, ticket: TicketSpec,
                 credit_stakes: float = 0.0) -> None:
        if ticket.rule != "naive":
            raise ValueError("the credit arm runs the naive rule only")
        if not credit_stakes >= 0.0:
            raise ValueError("credit_stakes must be non-negative")
        super().__init__(config, ticket)
        self.credit_stakes = float(credit_stakes)
        self.line = (math.inf if math.isinf(self.credit_stakes)
                     else ticket.stake * self.credit_stakes)

    def _stopped(self, h: np.ndarray, stake: float) -> np.ndarray:
        return h < stake - self.line


def credit_grid(seeds=SEEDS) -> list[tuple]:
    """(seed, wall, credit, p, stake, attempts, l1_mult): the first block's
    naive cells once per line, seed outermost, so a seed's controls are built
    once and dropped before the next seed."""
    return [(seed, wall, label, p, stake, a, m)
            for seed in seeds for wall in WALLS for label, _ in CREDITS
            for p in P_GRID for stake in STAKES for a in ATTEMPTS
            for m in L1_MULTIPLIERS]


def credit_cell(cell: tuple, control, net_class=CreditTicketNetwork) -> dict:
    """One treated cell read against its control. The first block's readout
    is run as it stands, the two of its checks that a line of credit changes
    are replaced, and the debt, the class the first block did not read and the
    shares are added. Everything a readout or a criterion needs is in the row."""
    seed, wall, label, p, stake, attempts, l1_mult = cell
    k = CREDIT_STAKES[label]
    built: list = []

    def build(config: NetworkConfig, spec: TicketSpec):
        net = net_class(config, spec, k)
        built.append(net)
        return net

    row = ticket_cell((seed, wall, p, stake, attempts, l1_mult, "naive"),
                      control, net_class=build)
    net = built[0]
    cnet, chist = control
    hist = net._history
    rec = net.ticket_record()
    cls = classes_of(net)
    line = net.line
    P, W, S, X = rec["plays"], rec["wins"], rec["stops"], rec["absent"]
    H0, H1 = rec["h0"], rec["h1"]
    has = P.size > 0
    row["credit"] = label

    # A41-7: the credit line in place of the capital line. The first block's
    # two checks on that line, no play from below the stake and no playing
    # node below zero, are what a line of credit allows, so they are replaced.
    del row["line_viol"], row["neg_viol"]
    row["credit_line_viol"] = (int(((H0 < stake - line) & (P > 0)).sum())
                               if has else 0)
    row["debt_viol"] = (int(((P > 0) & (H1 < -line - TOL_SETTLE)).sum())
                        if has else 0)

    # C1: the class the first block did not read, which a line lets play.
    u = cls["unreached"]
    denom = u.size * max(ROUNDS - OPEN_FROM, 1)
    plays_u = int(P[:, u].sum()) if has else 0
    row["plays_unreached"] = plays_u
    row["plays_rd_unreached"] = plays_u / denom
    row["stops_rd_unreached"] = (int(S[:, u].sum()) if has else 0) / denom
    row["absent_rd_unreached"] = (int(X[:, u].sum()) if has else 0) / denom
    row["pnl_unreached"] = (stake * (2 * int(W[:, u].sum()) - plays_u)
                            if has else 0.0)

    # C3: what is owed to the house. Between two settlements a node in debt
    # neither spends nor pays wages, so its lowest holding is one a settlement
    # left, and the lowest settlement is read off the ticket's record.
    ht, hc = hist.holdings[-1], chist.holdings[-1]
    low = H1.min(axis=0) if has else np.array(net.holdings, dtype=float)
    for name in ALL_CLASSES:
        ix = cls[name]
        row[f"debt_{name}"] = float(np.maximum(-ht[ix], 0.0).sum())
        row[f"debtors_{name}"] = int((ht[ix] < 0.0).sum())
        row[f"ever_owed_{name}"] = int((low[ix] < 0.0).sum())
        row[f"deepest_{name}"] = float(low[ix].min())

    # C4: each class's share of the closing gain, on net holdings, and
    # concentration on positive holdings, the debt being reported above.
    gain = {name: float(ht[cls[name]].sum() - hc[cls[name]].sum())
            for name in ALL_CLASSES}
    total = sum(gain.values())
    for name in ALL_CLASSES:
        row[f"dh_{name}"] = gain[name]
        row[f"gain_{name}"] = gain[name] / total if total else float("nan")
    pos_t, pos_c = np.maximum(ht, 0.0), np.maximum(hc, 0.0)
    row["top10_t"], row["top10_c"] = top_share(pos_t, 10), top_share(pos_c, 10)
    row["gini_t"], row["gini_c"] = gini(pos_t), gini(pos_c)
    row["debt_t"] = float(np.maximum(-ht, 0.0).sum())
    row["debt_c"] = float(np.maximum(-hc, 0.0).sum())
    return row


def run_credit_grid(seeds=SEEDS) -> list[dict]:
    cells = credit_grid(seeds)
    controls: dict = {}
    rows = []
    t0 = time.time()
    for i, cell in enumerate(cells, 1):
        seed, wall = cell[0], cell[1]
        if (seed, wall) not in controls:
            controls = {k: v for k, v in controls.items() if k[0] == seed}
            controls[(seed, wall)] = ticket_control(seed, wall)
        rows.append(credit_cell(cell, controls[(seed, wall)]))
        if i % 72 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}  ({time.time() - t0:.0f} s)", flush=True)
    return rows


# --------------------------------------------------------------------------
# A41-5: a line of zero is the first block's ticket


def zero_line_rows(cells=None, net_class=CreditTicketNetwork) -> list[tuple]:
    """The first block's naive cells on seed 0, run with a line of zero
    through the first block's own readout. ``cells`` narrows them for the
    selftest; ``net_class`` carries a seeded fault."""
    if cells is None:
        cells = [c for c in ticket_grid(SEEDS[:1]) if c[6] == "naive"]
    controls: dict = {}
    out = []
    for cell in cells:
        key = (cell[0], cell[1])
        if key not in controls:
            controls[key] = ticket_control(*key)
        row = ticket_cell(cell, controls[key],
                          net_class=lambda config, spec: net_class(config, spec, 0.0))
        out.append((tuple(cell), row))
    return out


def zero_line_check(pairs: list[tuple], expected: int) -> dict:
    """Each run's record entry, as the first block's writer makes it, against
    the first block's record entry for the same cell, field by field."""
    out = {"record": TICKET_RECORD.exists(), "cells": len(pairs),
           "expected": expected, "found": 0, "fields": 0, "missing": [],
           "differ": []}
    if not out["record"]:
        return out
    runs = json.loads(TICKET_RECORD.read_text(encoding="utf-8"))["runs"]
    index = {tuple(r[key] for key in TICKET_KEYS): r for r in runs}
    for cell, row in pairs:
        ref = index.get(cell)
        if ref is None:
            out["missing"].append(cell)
            continue
        out["found"] += 1
        out["fields"] = max(out["fields"], len(ref))
        got = ticket_record_run(row)
        keys = sorted(k for k in set(got) | set(ref)
                      if got.get(k, _ABSENT) != ref.get(k, _ABSENT))
        if keys:
            out["differ"].append((cell, keys, {k: (got.get(k), ref.get(k))
                                               for k in keys[:4]}))
    return out


def _ticket_cell_label(c: tuple) -> str:
    seed, wall, p, stake, a, m, rule = c
    return f"seed {seed} wall {wall} p {p} stake {stake} attempts {a}x{m} {rule}"


def _credit_label(r: dict) -> str:
    return (f"seed {r['seed']} wall {r['wall']} {r['credit']} p {r['p']} "
            f"stake {r['stake']} attempts {r['attempts']}x{r['l1_mult']}")


# --------------------------------------------------------------------------
# criteria, all four about the instrument (the arm registers no reading with a
# direction; the readouts are printed below them)


def credit_criteria(rows: list[dict], zero: dict | None,
                    weighted: bool = False) -> list[dict]:
    names = ("A41-5  with a line of zero the credit arm reproduces the first "
             "block's record on seed 0's naive cells, field by field",
             "A41-6  the claim total the module tracks equals holdings plus "
             "parked at the end of every cell",
             "A41-7  the credit line, the caps and who is still in hold on "
             "every recorded attempt",
             "A41-8  the decomposition is an identity and ties to the ledger")
    out = []

    if zero is None:
        out.append(dict(name=names[0], kind="instrument", passed=False,
                        detail="Void: A41-5 was not run, nothing was compared"))
    elif not zero["record"]:
        out.append(dict(name=names[0], kind="instrument", passed=False,
                        detail="Void: the first block's record is not on disk, "
                               "nothing was compared"))
    else:
        ok5 = (zero["cells"] == zero["expected"] == zero["found"]
               and not zero["missing"] and not zero["differ"])
        out.append(dict(
            name=names[0], kind="instrument", passed=ok5,
            detail=(f"Holds: all {zero['found']} of seed 0's naive cells, run "
                    f"with a line of zero through the first block's readout "
                    f"and record writer, equal the first block's record in "
                    f"all {zero['fields']} fields of every cell." if ok5 else
                    f"Fails: {zero['cells']} cells run against "
                    f"{zero['expected']} expected, {len(zero['missing'])} not "
                    f"in the record, {len(zero['differ'])} differing: "
                    + "; ".join(f"{_ticket_cell_label(c)} on {', '.join(k[:4])}"
                                for c, k, _ in zero["differ"][:3]))))

    if not rows:
        out += [dict(name=nm, kind="instrument", passed=False,
                     detail="Void: no cells, nothing was evaluated")
                for nm in names[1:]]
        return out

    rel = [r["ledger_drift"] / max(1.0, abs(r["M_t"])) for r in rows]
    bad = [r for r, x in zip(rows, rel) if not x <= TOL_LEDGER]
    out.append(dict(
        name=names[1], kind="instrument", passed=not bad,
        detail=(f"Closes on all {len(rows)} cells: the drift relative to the "
                f"stock is at most {TOL_LEDGER:.0e} on every one." if not bad else
                f"Does not close on {len(bad)} of {len(rows)} cells, largest "
                f"relative drift {max(rel):.3e}: "
                + "; ".join(_credit_label(r) for r in bad[:4]))))

    keys = ("cap_viol", "acct_viol", "gone_viol", "credit_line_viol",
            "debt_viol", "still_viol", "wins_viol")
    totals = {k: sum(r[k] for r in rows) for k in keys}
    worst = max(r["settle_err"] for r in rows)
    bad = [r for r in rows if any(r[k] for k in keys) or not r["rounds_ok"]
           or not r["settle_err"] <= TOL_SETTLE]
    out.append(dict(
        name=names[2], kind="instrument", passed=not bad,
        detail=(f"Holds on all {len(rows)} cells: no play above a cap; stops, "
                f"absences and plays add up to the cap on every node and round "
                f"(the naive rule abstains from nothing); no play from a node "
                f"that had left when the round opened; no play from a holding "
                f"below the stake less the line; no node that played is left "
                f"below minus the line by more than {TOL_SETTLE:.0e}; no idle "
                f"node moved; no more wins than plays; every settlement equals "
                f"the stake times wins less losses to within {TOL_SETTLE:.0e}; "
                f"every cell recorded rounds {OPEN_FROM} to {ROUNDS - 1}."
                if not bad else
                f"Fails on {len(bad)} of {len(rows)} cells, violations {totals}, "
                f"largest settlement error {worst:.3e}: "
                + "; ".join(_credit_label(r) for r in bad[:4]))))

    worst_id, worst_tie, worst_ledger, priced = identity_residues(rows, weighted)
    ok8 = (worst_id <= TOL_IDENTITY and worst_tie <= TOL_IDENTITY
           and worst_ledger <= TOL_LEDGER and not priced)
    out.append(dict(
        name=names[3], kind="instrument", passed=ok8,
        detail=((f"Holds: over {len(rows)} cells and {len(PAIRS)} class pairs "
                 f"the three terms miss the gap by at most {TOL_IDENTITY:.0e} "
                 f"of it; plays per node times return per play misses the "
                 f"counted result per node by at most {TOL_IDENTITY:.0e}; the "
                 f"counted result misses the ledger's by at most "
                 f"{TOL_LEDGER:.0e}; no pair-cell carries a price term, where "
                 f"every class faces one price and the term must be exactly "
                 f"zero") if ok8 else
                (f"Fails: over {len(rows)} cells and {len(PAIRS)} class pairs "
                 f"the three terms miss the gap by up to {worst_id:.3e} of it "
                 f"(tolerance {TOL_IDENTITY:.0e}); plays per node times return "
                 f"per play misses the counted result per node by up to "
                 f"{worst_tie:.3e}; the counted result misses the ledger's by "
                 f"up to {worst_ledger:.3e} (tolerance {TOL_LEDGER:.0e}); "
                 f"{len(priced)} pair-cells carry a price term"))))
    return out


# --------------------------------------------------------------------------
# readouts, per cell and per seed, never averaged across seeds


def split_baseline() -> tuple[str, dict] | None:
    """The split the credit arm's shares are printed against: the injection
    arm's, when its record is on disk, else the first block's."""
    if INJECT_RECORD.exists():
        runs = [r for r in json.loads(INJECT_RECORD.read_text(
            encoding="utf-8"))["runs"] if not r["inert"]]
        if runs:
            return (f"injection arm, median over its {len(runs)} runs",
                    {c: statistics.median(r[f"gain_{c}"] for r in runs)
                     for c in ALL_CLASSES})
    base = ticket_split()
    if base is None:
        return None
    return (f"first block, median over its {base['cells']} cells in which all "
            f"three classes played (three classes)",
            {c: statistics.median(base["shares"][c]) for c in PLAYING})


def _credit_groups(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        key = (r["wall"], r["credit"], r["p"], r["stake"], r["attempts"],
               r["l1_mult"])
        out.setdefault(key, []).append(r)
    return out


def _credit_head(key) -> str:
    wall, credit, p, stake, a, m = key
    return f"wall {wall:.2f} {credit:9s} p {p} s {stake:<5} {a:>2}x{m:<2}"


def print_credit_readouts(rows: list[dict]) -> None:
    groups = _credit_groups(rows)

    print("\nC1  plays per node per ticket round, l1 / mid / earners / "
          "unreached, and stops per node per round for earners / unreached, "
          "per seed, floor off (the unbounded line is a check: everyone "
          "present plays every attempt)")
    for key, rs in groups.items():
        if key[0] != 0.0:
            continue
        cols = " | ".join(
            f"{r['plays_rd_l1']:.2f}/{r['plays_rd_mid']:.2f}/"
            f"{r['plays_rd_earners']:.2f}/{r['plays_rd_unreached']:.2f} "
            f"stop {r['stops_rd_earners']:.2f}/{r['stops_rd_unreached']:.2f}"
            for r in rs)
        print(f"  {_credit_head(key)}  {cols}")

    print("\nC2  the wage shortfall treated minus control, earners still in at "
          "the end treated (control) and the round of the first earner exit, "
          "and intermediate nodes out at the end treated (control), per seed, "
          "floors on")
    for key, rs in groups.items():
        if key[0] == 0.0:
            continue
        cols = " | ".join(
            f"{r['short_mean_t'] - r['short_mean_c']:+.3f} "
            f"e {r['earners_alive_t']}({r['earners_alive_c']}) "
            f"{_fmt(r['earners_first_exit_t'], 'd')} "
            f"mid out {r['left_mid_t']}({r['left_mid_c']})" for r in rs)
        print(f"  {_credit_head(key)}  {cols}")

    print("\nC3  owed at the end by l1 / mid / earners / unreached (nodes "
          "owing), and the deepest settlement of an earner / an unreached "
          "node, per seed; cells in which no settlement left a node below "
          "zero are not printed")
    for key, rs in groups.items():
        if not any(r[f"ever_owed_{c}"] for r in rs for c in ALL_CLASSES):
            continue
        cols = " | ".join(
            "/".join(f"{r['debt_' + c]:.3g}({r['debtors_' + c]})"
                     for c in ALL_CLASSES)
            + f" deep {r['deepest_earners']:.3g}/{r['deepest_unreached']:.3g}"
            for r in rs)
        print(f"  {_credit_head(key)}  {cols}")

    print("\nC4  each class's share of the closing gain against the control, "
          "l1 / mid / earners / unreached; the top-10 share and the Gini on "
          "positive holdings, treated minus control; the stock and the "
          "support against the control, per seed")
    base = split_baseline()
    if base is not None:
        label, shares = base
        print(f"  baseline, {label}: " + "  ".join(
            f"{c} {v:.4f}" for c, v in shares.items()))
    for key, rs in groups.items():
        cols = " | ".join(
            f"{_fmt(r['gain_l1'], '.3f')}/{_fmt(r['gain_mid'], '.3f')}/"
            f"{_fmt(r['gain_earners'], '.4f')}/{_fmt(r['gain_unreached'], '+.4f')} "
            f"top10 {_fmt(r['top10_t'] - r['top10_c'], '+.3f')} "
            f"gini {_fmt(r['gini_t'] - r['gini_c'], '+.3f')} "
            f"M {_fmt(r['M_ratio'], '.2f')} sup {_fmt(r['support_ratio'], '.3f')}"
            for r in rs)
        print(f"  {_credit_head(key)}  {cols}")

    print("\nC5  per node: mid against l1 (gap, stopping, count), earners "
          "against l1 (gap, count), per seed, floor off")
    for key, rs in groups.items():
        if key[0] != 0.0:
            continue
        parts = []
        for r in rs:
            d1 = decompose(r["N_mid"], r["g_mid"], r["mu_mid"], r["N_l1"],
                           r["g_l1"], r["mu_l1"])
            d2 = decompose(r["N_earners"], r["g_earners"], r["mu_earners"],
                           r["N_l1"], r["g_l1"], r["mu_l1"])
            parts.append(f"{d1['gap']:+.3g} {d1['stopping']:+.2g} "
                         f"{d1['count']:+.3g}; {d2['gap']:+.3g} "
                         f"{d2['count']:+.3g}")
        print(f"  {_credit_head(key)}  " + " | ".join(parts))


# --------------------------------------------------------------------------
# the record and the timing


def write_credit_record(rows: list[dict], crit: list[dict]) -> None:
    rec = {
        "stage": "A41",
        "arm": "credit",
        "config": {
            "carrier": "a17_edge_cut.base_config",
            "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
            "subsistence": {"mode": "exit", "grace": 1, "needs": list(WALLS)},
            "house": "off_graph", "open_from": OPEN_FROM, "stream": STREAM,
            "draw_rows": DRAW_ROWS, "rule": "naive",
            "p": list(P_GRID), "stakes": list(STAKES),
            "attempts": list(ATTEMPTS), "l1_multipliers": list(L1_MULTIPLIERS),
            "credit_lines": [label for label, _ in CREDITS],
            "credit_line_rule": ("a present node attempts a play while its "
                                 "holding is at least the stake less the "
                                 "line; 1s and 4s are one and four stakes; "
                                 "unbounded has no line"),
            "zero_line": ("not run; A41-5 runs seed 0's naive cells with a "
                          "line of zero against a41_same_ticket.json"),
            "readouts": ("top10 and gini on max(holdings, 0), debt reported "
                         "separately; gain shares on net holdings"),
            "seeds": list(SEEDS), "tail": TAIL,
        },
        "criteria": crit,
        "runs": [ticket_record_run(r) for r in rows],
    }
    if not CLOSED_CREDIT:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Arm not closed: the grid has run and its "
                                    "readouts are not yet written into "
                                    "RESULTS.md.")
    CREDIT_RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8", newline="\n")
    print(f"\nwrote {CREDIT_RECORD.name}")


def measure_credit_time(write: bool) -> int:
    """D38: the heaviest cell of each cap tier, at the smallest line and at no
    line, measured, not assumed. The estimate takes the slower of the two for
    each tier and adds A41-5's column."""
    wall = WALLS[-1]
    t0 = time.time()
    control = ticket_control(0, wall)
    t_control = time.time() - t0
    tiers: dict = {}
    for label in (CREDITS[0][0], CREDITS[-1][0]):
        for a in ATTEMPTS:
            for m in L1_MULTIPLIERS:
                cell = (0, wall, label, P_GRID[0], STAKES[-1], a, m)
                t0 = time.time()
                credit_cell(cell, control)
                tiers[f"{label} attempts {a} x {m}"] = time.time() - t0
    slowest = {f"{a} x {m}": max(tiers[f"{label} attempts {a} x {m}"]
                                 for label in (CREDITS[0][0], CREDITS[-1][0]))
               for a in ATTEMPTS for m in L1_MULTIPLIERS}
    per_tier = len(WALLS) * len(P_GRID) * len(STAKES)
    per_seed = (per_tier * len(CREDITS) * sum(slowest.values())
                + len(WALLS) * t_control)
    zero = per_tier * sum(slowest.values()) + len(WALLS) * t_control
    out = {
        "control_seconds": round(t_control, 3),
        "cell_seconds": {k: round(v, 3) for k, v in tiers.items()},
        "cells_total": len(credit_grid()),
        "zero_line_cells": ZERO_LINE_CELLS,
        "estimate_seconds": round(per_seed * len(SEEDS) + zero, 1),
        "note": ("measured on the machine that ran --time, on the heaviest "
                 "cell of each tier at the smallest line and at no line (D38); "
                 "--run --arm credit reads this file and refuses without it"),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    if write:
        CREDIT_TIMING.write_text(json.dumps(out, indent=2, sort_keys=True)
                                 + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {CREDIT_TIMING.name}")
    return 0


# --------------------------------------------------------------------------
# the credit arm's seeded faults


class _ZeroIsOneCredit(CreditTicketNetwork):
    """Seeded fault: a line of zero stakes is built as a line of one.

    The fault the design first named for A41-5, the capital line written
    ``h <= stake``, cannot be planted on this carrier: over seed 0's naive
    cells no holding equals the stake to the bit at any attempt (measured
    before this class was written), so it moves nothing and would show
    nothing."""

    planted = False

    def __init__(self, config: NetworkConfig, ticket: TicketSpec,
                 credit_stakes: float = 0.0) -> None:
        if credit_stakes == 0.0:
            type(self).planted = True
            credit_stakes = 1.0
        super().__init__(config, ticket, credit_stakes)


class _NoBookCredit(CreditTicketNetwork):
    """Seeded fault: the settlement never books its net into the claim total."""

    planted = False

    def _book_total(self, net: float) -> None:
        type(self).planted = True


class _NoLineCredit(CreditTicketNetwork):
    """Seeded fault: the credit line is removed."""

    planted = False

    def _stopped(self, h: np.ndarray, stake: float) -> np.ndarray:
        type(self).planted = True
        return np.zeros(h.shape, dtype=bool)


class _OpeningLineCredit(CreditTicketNetwork):
    """Seeded fault: the line reads the holding the round opened with, so a
    node that opened above it plays every attempt however far it falls."""

    planted = False

    def _pre_round(self, t: int) -> None:
        self._opening = np.array(self.holdings, dtype=float, copy=True)
        super()._pre_round(t)

    def _stopped(self, h: np.ndarray, stake: float) -> np.ndarray:
        type(self).planted = True
        return self._opening < stake - self.line


class _GoneCredit(CreditTicketNetwork):
    """Seeded fault: a node that has left the market still plays."""

    planted = False

    def _present(self) -> np.ndarray:
        type(self).planted = True
        return np.ones(self._n, dtype=bool)


#: A41-5's selftest column: seed 0 without a floor at the thinner edge, twelve
#: cells, among them stakes the wage earners cannot cover, so a line of one
#: stake lets them play.
ZERO_SUBSET = tuple(c for c in ticket_grid(SEEDS[:1]) if c[6] == "naive"
                    and c[1] == WALLS[0] and c[2] == P_GRID[0])

#: The first block's cell in which nodes leave and would still hold a stake,
#: with the smallest line.
GONE_CREDIT_CELL = (GONE_CELL[0], GONE_CELL[1], CREDITS[0][0], GONE_CELL[2],
                    GONE_CELL[3], GONE_CELL[4], GONE_CELL[5])


def selftest_credit() -> bool:
    """Every criterion passes on a clean base and fails on its seeded faults.

    The bases are real. A criterion that failed on its base would "catch"
    every fault, so each base has to pass first, and each fault's planting is
    read off a quantity the criterion does not read.
    """
    def pick(crit, prefix):
        return next(x for x in crit if x["name"].startswith(prefix))

    ok = []

    clean = zero_line_rows(ZERO_SUBSET)
    got = pick(credit_criteria([], zero_line_check(clean, len(ZERO_SUBSET))),
               "A41-5")
    ok.append(got["passed"])
    print(f"A41-5 clean, {len(ZERO_SUBSET)} cells of seed 0: passes "
          f"{got['passed']}")
    # Planted is read off the play counts against the clean column.
    _ZeroIsOneCredit.planted = False
    faulty = zero_line_rows(ZERO_SUBSET, net_class=_ZeroIsOneCredit)
    grew = sum(1 for (_, b), (_, c) in zip(faulty, clean)
               if b["plays_total"] > c["plays_total"])
    planted = _ZeroIsOneCredit.planted and grew > 0
    got = pick(credit_criteria([], zero_line_check(faulty, len(ZERO_SUBSET))),
               "A41-5")
    ok.append(planted and not got["passed"])
    print(f"  a line of zero built as one  planted {planted} ({grew} cells "
          f"play more)   A41-5 passed={got['passed']} (want False)")

    control = ticket_control(0, 0.0)
    finite = (0, 0.0, CREDITS[0][0], P_GRID[0], STAKES[-1], ATTEMPTS[-1], 1)
    unbounded = (0, 0.0, CREDITS[-1][0], P_GRID[0], STAKES[-1], ATTEMPTS[-1], 1)
    base = [credit_cell(finite, control), credit_cell(unbounded, control)]
    crit = credit_criteria(base, None)
    clean_ok = all(pick(crit, p)["passed"] for p in ("A41-6", "A41-7", "A41-8"))
    owed = sum(base[0][f"ever_owed_{c}"] for c in ALL_CLASSES)
    stopped = sum(base[0][f"stops_rd_{c}"] for c in PLAYING)
    shape = owed > 0 and stopped > 0
    ok += [clean_ok, shape]
    print(f"clean base: A41-6, A41-7 and A41-8 pass {clean_ok}; with one stake "
          f"of credit, {owed} nodes owed after a settlement and the line "
          f"stopped plays {shape}")

    # Planted means the override ran and there was a net amount to book.
    _NoBookCredit.planted = False
    row = credit_cell(finite, control, net_class=_NoBookCredit)
    got = pick(credit_criteria([row, base[1]], None), "A41-6")
    planted = _NoBookCredit.planted and row["created"] != row["destroyed"]
    ok.append(planted and not got["passed"])
    print(f"  claim total not booked       planted {planted} (net issued "
          f"{row['created'] - row['destroyed']:+.3f})   A41-6 passed="
          f"{got['passed']} (want False)")

    # Planted is read off the play count against the clean cell.
    _NoLineCredit.planted = False
    row = credit_cell(finite, control, net_class=_NoLineCredit)
    got = pick(credit_criteria([row, base[1]], None), "A41-7")
    planted = (_NoLineCredit.planted
               and row["plays_total"] > base[0]["plays_total"])
    ok.append(planted and not got["passed"])
    print(f"  credit line removed          planted {planted} (plays "
          f"{row['plays_total']} against {base[0]['plays_total']})   A41-7 "
          f"passed={got['passed']} (want False)")

    # Planted is read off the play count against the clean cell. This fault
    # plays from no holding below the line when a round opens, so the check
    # on the opening holding cannot see it and the floor on the settled one
    # has to.
    _OpeningLineCredit.planted = False
    row = credit_cell(finite, control, net_class=_OpeningLineCredit)
    got = pick(credit_criteria([row, base[1]], None), "A41-7")
    planted = (_OpeningLineCredit.planted
               and row["plays_total"] > base[0]["plays_total"])
    ok.append(planted and row["credit_line_viol"] == 0 and not got["passed"])
    print(f"  line read at the opening     planted {planted} (plays "
          f"{row['plays_total']} against {base[0]['plays_total']}; from below "
          f"the line at the opening {row['credit_line_viol']}, left below "
          f"minus the line {row['debt_viol']})   A41-7 passed={got['passed']} "
          f"(want False)")

    # The departed-node cell's clean run has to pass first, since it is not
    # the base above.
    wcontrol = ticket_control(GONE_CREDIT_CELL[0], GONE_CREDIT_CELL[1])
    wclean = credit_cell(GONE_CREDIT_CELL, wcontrol)
    wclean_ok = pick(credit_criteria([wclean], None), "A41-7")["passed"]
    _GoneCredit.planted = False
    row = credit_cell(GONE_CREDIT_CELL, wcontrol, net_class=_GoneCredit)
    got = pick(credit_criteria([row], None), "A41-7")
    planted = _GoneCredit.planted and row["plays_total"] > wclean["plays_total"]
    ok.append(wclean_ok and planted and not got["passed"])
    print(f"  a departed node plays        clean cell passes {wclean_ok}; "
          f"planted {planted} (plays {row['plays_total']} against "
          f"{wclean['plays_total']})   A41-7 passed={got['passed']} "
          f"(want False)")

    d_plain = decompose(base[0]["N_earners"], base[0]["g_earners"],
                        base[0]["mu_earners"], base[0]["N_l1"],
                        base[0]["g_l1"], base[0]["mu_l1"])
    d_weighted = decompose(base[0]["N_earners"], base[0]["g_earners"],
                           base[0]["mu_earners"], base[0]["N_l1"],
                           base[0]["g_l1"], base[0]["mu_l1"], weighted=True)
    planted = d_plain["count"] != d_weighted["count"]
    got = pick(credit_criteria(base, None, weighted=True), "A41-8")
    ok.append(planted and not got["passed"])
    print(f"  mean return by play count    planted {planted}   A41-8 passed="
          f"{got['passed']} (want False)")

    seeded = [dict(base[0], mu_mid=base[0]["mu_mid"] * 1.5), base[1]]
    got = pick(credit_criteria(seeded, None), "A41-8")
    ok.append(not got["passed"])
    print(f"  one class another price      A41-8 passed={got['passed']} "
          f"(want False)")

    got = credit_criteria([], None)
    ok.append(all((not x["passed"]) and x["detail"].startswith("Void")
                  for x in got))
    print(f"  nothing run at all           every criterion Void and not "
          f"passed: {ok[-1]}")
    return all(ok)


# ==========================================================================
# entry


def _print_criteria(crit: list[dict]) -> None:
    print()
    for x in crit:
        print(f"  {'PASS' if x['passed'] else 'FAIL'}[{x['kind']}] {x['name']}")
        print(f"        {x['detail'][:600]}")


def main_inject(args, ap) -> int:
    if args.time:
        print("the injection arm has no timing step: its 150 runs take about "
              "half a minute")
        return 2
    if args.selftest:
        a = selftest_inject_gate()
        print("\ncriteria selftest:")
        b = selftest_inject_criteria()
        print("criteria selftest:", "PASS" if b else "FAIL")
        return 0 if (a and b) else 1
    if args.gate:
        return 0 if run_inject_gate().ok else 1
    if args.run:
        rows = run_inject_grid(seeds=SEEDS[:1] if args.smoke else SEEDS)
        crit = inject_criteria(rows)
        _print_criteria(crit)
        print_inject_residues(rows)
        print_inject_readouts(rows)
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
        else:
            write_inject_record(rows, crit)
        return 0 if all(x["passed"] for x in crit) else 1
    ap.print_help()
    return 0


def main_credit(args, ap) -> int:
    if args.selftest:
        ok = selftest_credit()
        print("credit selftest:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    if args.gate:
        t0 = time.time()
        zero = zero_line_check(zero_line_rows(), ZERO_LINE_CELLS)
        crit = credit_criteria([], zero)[:1]
        _print_criteria(crit)
        for cell, _, values in zero["differ"][:3]:
            print(f"  {_ticket_cell_label(cell)}: " + "; ".join(
                f"{k} ran {got!r}, recorded {ref!r}"
                for k, (got, ref) in values.items()))
        print(f"\n({time.time() - t0:.0f} s)")
        return 0 if crit[0]["passed"] else 1
    if args.time:
        return measure_credit_time(write=not args.no_write)
    if args.run:
        if not args.smoke and not CREDIT_TIMING.exists():
            print("refusing: run --arm credit --time first (D38)")
            return 1
        print("A41-5: seed 0's naive cells with a line of zero")
        zero = zero_line_check(zero_line_rows(), ZERO_LINE_CELLS)
        print("the grid")
        rows = run_credit_grid(seeds=SEEDS[:1] if args.smoke else SEEDS)
        crit = credit_criteria(rows, zero)
        _print_criteria(crit)
        print_ticket_residues(rows)
        print_credit_readouts(rows)
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
        else:
            write_credit_record(rows, crit)
        return 0 if all(x["passed"] for x in crit) else 1
    ap.print_help()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", choices=("inject", "credit"), required=True,
                    help="which arm")
    ap.add_argument("--gate", action="store_true",
                    help="inject: A41-9; credit: A41-5 alone")
    ap.add_argument("--selftest", action="store_true",
                    help="seeded faults the gate and the criteria must catch")
    ap.add_argument("--time", action="store_true",
                    help="credit: seconds per cell tier, measured (D38)")
    ap.add_argument("--run", action="store_true", help="the grid")
    ap.add_argument("--smoke", action="store_true",
                    help="with --run: seed 0 only, nothing written")
    ap.add_argument("--no-write", action="store_true",
                    help="with --time or --run: write nothing")
    args = ap.parse_args()
    if args.arm == "inject":
        return main_inject(args, ap)
    return main_credit(args, ap)


if __name__ == "__main__":
    raise SystemExit(main())
