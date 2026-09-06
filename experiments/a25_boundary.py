"""The clearing boundary: two graphs, one signed balance, one ceiling.

**The construction is read off two carriers rather than invented.**

Inner-German trade settled cross-border payments *not* between the firms
involved but through sub-accounts at the two central banks, in a unit of
account -- the Verrechnungseinheit -- that was neither side's money. The
balance those accounts ran was allowed to go negative up to the "Swing", an
interest-free overdraft; from December 1968 the ceiling was **25 per cent of
the other side's deliveries in the previous year**, and the 1974 agreement
capped it at 850 million VE. China's grain monopoly has the same shape from
the other direction: one procurement channel, compulsory sale of the surplus,
and a return flow to short villages supplied *when they were short*.

So a boundary in this model is three things, and none of them is an edge
between ordinary nodes:

1. **A node on each side.** Gross trade settles inside each graph; only the
   difference crosses.
2. **A signed balance.** Who owes whom, and it changes sign.
3. **A ceiling that is a share of flow, not a constant.** Twenty-five per cent
   of last round's deliveries, so the limit moves with the trade it limits.

**Why the ceiling is the load-bearing part.** A parked pool is unsigned and
unbounded, so "the balance reached its limit and trade stopped" is an event it
cannot represent at any parameter value. That is the one reading a sink is
barred from producing, and it is why this file exists.

The driver steps both graphs through ``Network._run_steps`` and settles between
rounds, at the point the round itself names: after ``_post_round``, with one
round's books closed and the next not yet open.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

import numpy as np

#: The historical ceiling, as a share of the other side's previous deliveries.
#: **Not a chosen constant**: it is the rule the December 1968 agreement wrote
#: down, and the grid brackets it rather than replacing it.
SWING_HISTORICAL = 0.25


@dataclass
class BoundarySpec:
    """One clearing boundary between two graphs.

    ``width`` is how much of a side's circulating stock it wants to spend
    across the boundary each round. ``swing`` is the ceiling as a share of the
    other side's previous-round deliveries; ``None`` is no ceiling, which is
    the arm where the pair is allowed to collapse back into a sink.
    """

    width: float = 0.0
    swing: float | None = SWING_HISTORICAL

    def __post_init__(self) -> None:
        if not 0.0 <= self.width <= 1.0:
            raise ValueError("width must lie in [0, 1]")
        if self.swing is not None and self.swing < 0.0:
            raise ValueError("swing must be non-negative or None")

    @property
    def active(self) -> bool:
        return self.width > 0.0


@dataclass
class PairHistory:
    balance: np.ndarray        # signed, G1's debit position with G2
    net: np.ndarray            # what actually crossed each round
    wanted: np.ndarray         # what would have crossed with no ceiling
    ceiling: np.ndarray        # the ceiling that round
    capped: np.ndarray         # bool: the ceiling bound this round
    circulating1: np.ndarray
    circulating2: np.ndarray


def run_pair(cfg1, cfg2, spec: BoundarySpec, rounds: int | None = None,
             network_cls=None) -> tuple[object, object, PairHistory]:
    """Step two graphs in lockstep with one clearing balance between them.

    **Only the net crosses.** That is what a clearing system does: the gross
    trade settles inside each side and the two authorities settle the
    difference. Claims are taken from the payer in proportion to who holds
    them and delivered to the payee the same way, so **the pair conserves
    exactly** even though neither graph does on its own. The assertion below
    is that pair-level conservation, and it is checked every round rather than
    at the end.
    """
    if network_cls is None:
        from monetary_topology.network import Network as network_cls  # noqa: N806
    rounds = rounds if rounds is not None else cfg1.rounds
    g1, g2 = network_cls(cfg1), network_cls(cfg2)
    s1, s2 = g1._run_steps(), g2._run_steps()

    bal = 0.0
    deliveries_prev: float | None = None
    cols: dict[str, list] = {k: [] for k in
                             ("balance", "net", "wanted", "ceiling", "capped",
                              "circulating1", "circulating2")}

    for _ in range(rounds):
        next(s1)
        next(s2)
        m1 = float(g1.holdings.sum())
        m2 = float(g2.holdings.sum())
        total_before = m1 + m2

        # What each side wants to buy from the other, and the difference that
        # has to be settled.
        wants_12 = spec.width * m1
        wants_21 = spec.width * m2
        wanted = wants_12 - wants_21

        # **The ceiling is a share of the other side's deliveries last round.**
        # On the opening round there is no previous round, so this round's own
        # figure stands in; that choice is visible here rather than buried.
        base = deliveries_prev if deliveries_prev is not None else wants_21
        ceiling = math.inf if spec.swing is None else spec.swing * base

        net, capped = wanted, False
        if bal + net > ceiling:
            net, capped = ceiling - bal, True
        elif bal + net < -ceiling:
            net, capped = -ceiling - bal, True

        if net > 0.0 and m1 > 0.0 and m2 > 0.0:
            g1.holdings -= net * (g1.holdings / m1)
            g2.holdings += net * (g2.holdings / m2)
        elif net < 0.0 and m1 > 0.0 and m2 > 0.0:
            g1.holdings += (-net) * (g1.holdings / m1)
            g2.holdings -= (-net) * (g2.holdings / m2)
        else:
            net = 0.0

        after = float(g1.holdings.sum()) + float(g2.holdings.sum())
        if abs(after - total_before) > 1e-8:
            raise AssertionError(
                "the pair did not conserve: %r -> %r" % (total_before, after))

        bal += net
        deliveries_prev = wants_21
        cols["balance"].append(bal)
        cols["net"].append(net)
        cols["wanted"].append(wanted)
        cols["ceiling"].append(ceiling)
        cols["capped"].append(capped)
        cols["circulating1"].append(float(g1.holdings.sum()))
        cols["circulating2"].append(float(g2.holdings.sum()))

    # Drain both generators so each graph's history is built.
    for s in (s1, s2):
        try:
            next(s)
        except StopIteration:
            pass

    return g1, g2, PairHistory(
        balance=np.array(cols["balance"], dtype=float),
        net=np.array(cols["net"], dtype=float),
        wanted=np.array(cols["wanted"], dtype=float),
        ceiling=np.array(cols["ceiling"], dtype=float),
        capped=np.array(cols["capped"], dtype=bool),
        circulating1=np.array(cols["circulating1"], dtype=float),
        circulating2=np.array(cols["circulating2"], dtype=float),
    )


# ---------------------------------------------------------------------------
# Driver, added 2026-09-03. Until this date the stage had a section in
# RESULTS.md and **no record on disk**: the module above was a library nothing
# called, and the readings were hand-written. The section's own self-
# description said the criteria were written into the script that produced the
# record and that the record carried their text, and neither half was true.
# That sentence is what this driver exists to make true, and the pitfall book
# had already named the gap on 2026-09-01 without closing it.
# ---------------------------------------------------------------------------

import json                                                       # noqa: E402
import sys                                                        # noqa: E402
from pathlib import Path                                          # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

import dataclasses as _dc                                          # noqa: E402
import importlib.util                                              # noqa: E402

from monetary_topology.network import (                            # noqa: E402
    Network, NetworkConfig, ResupplySpec, WriteOffSpec,
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# **The carrier is A23's, imported rather than restated.** The design sheet's
# box four names it: ``config_for("drawdown", ..., need=0.50)`` at
# ``ROUNDS=300`` with ``target="financial"``. The first version of this driver
# built a bare ``NetworkSpec()`` instead and every reading came back zero,
# because on that carrier the claim stock is conserved exactly, both sides hold
# the same total in every round, and the net that crosses is identically zero.
# One session that reconstructs a carrier by guessing produces a clean-looking
# table of zeros; the design sheet had the answer in one line.
_A18 = _load(ROOT / "experiments" / "a18_policy_paths.py", "_a18_for_a25")
config_for = _A18.config_for

RECORD = RESULTS_DIR / "a25_boundary.json"
ROUNDS = 300
SEEDS = tuple(_A18.SEEDS)
WIDTHS = (0.0, 0.02, 0.05, 0.10)
NEED = 0.50
FUNDING = "issuance"
PUMP_RATE = 0.05


def _cfg(seed: int, pump: bool) -> NetworkConfig:
    """One side of the pair, on A23's carrier. The pump is issuance-funded."""
    cfg = config_for("drawdown", WriteOffSpec(), "endogenous", NEED, seed,
                     resupply_rate=(PUMP_RATE if pump else 0.0))
    return _dc.replace(cfg, resupply=ResupplySpec(
        rate=(PUMP_RATE if pump else 0.0), funding=FUNDING))


def _series(g) -> list[float]:
    """A per-round sequence off a finished graph, for the identity check."""
    h = g.history
    for k in ("circulating", "volume", "claims"):
        v = getattr(h, k, None)
        if v is not None:
            return [float(x) for x in np.asarray(v).ravel()]
    return [float(g.holdings.sum())]


def _nondefault(obj):
    """Every field of a dataclass that differs from its own default, nested.

    Written because this stage cost a reconstruction. Its readings were on disk
    and the configuration behind them was not, so when a later run disagreed
    nobody could tell whether it had found a different answer or a different
    configuration, and the values were no longer recoverable from anywhere.
    A record that carries what it ran with makes that question free.

    Fields at their default are omitted, so what appears here is exactly the
    set of choices this stage made.
    """
    if not _dc.is_dataclass(obj):
        return obj
    out = {}
    for f in _dc.fields(obj):
        v = getattr(obj, f.name)
        if _dc.is_dataclass(v):
            inner = _nondefault(v)
            if inner:
                out[f.name] = inner
            continue
        if f.default is not _dc.MISSING:
            default = f.default
        elif f.default_factory is not _dc.MISSING:  # type: ignore[misc]
            default = f.default_factory()  # type: ignore[misc]
        else:
            out[f.name] = v
            continue
        if _dc.is_dataclass(default):
            continue
        if v != default:
            out[f.name] = list(v) if isinstance(v, tuple) else v
    return out


def probe() -> None:
    print(f"A25  the clearing boundary. rounds={ROUNDS}, seeds={SEEDS}, "
          f"widths={WIDTHS}\n")

    # ---- A25-1: the boundary is off by default -------------------------
    # width=0 must reproduce two independent graphs element by element. This
    # is rule 19 for this switch and it is the only structural check here.
    print("== A25-1  width zero against two graphs run apart ==")
    same, cells = [], []
    for seed in SEEDS:
        for pump in (False, True):
            c1, c2 = _cfg(seed, pump), _cfg(seed + 100, pump)
            _, _, hist = run_pair(c1, c2, BoundarySpec(width=0.0))
            solo1 = Network(_cfg(seed, pump)); solo1.run()
            solo2 = Network(_cfg(seed + 100, pump)); solo2.run()
            ok = (float(np.abs(hist.net).max()) == 0.0
                  and float(np.abs(hist.balance).max()) == 0.0
                  and abs(hist.circulating1[-1] - float(solo1.holdings.sum())) < 1e-12
                  and abs(hist.circulating2[-1] - float(solo2.holdings.sum())) < 1e-12)
            same.append(ok)
            cells.append({"seed": seed, "pump": pump, "identical": bool(ok),
                          "paired_close": float(hist.circulating1[-1]),
                          "solo_close": float(solo1.holdings.sum())})
            print(f"   seed {seed} pump {str(pump):5s}  identical {ok}")

    # ---- A25-3: the ceiling binds, and both branches are reachable ------
    print("\n== A25-3  the round the ceiling first binds, by cell ==")
    binds = []
    for seed in SEEDS:
        for pump in (False, True):
            for w in WIDTHS[1:]:
                _, _, h = run_pair(_cfg(seed, pump), _cfg(seed + 100, pump),
                                   BoundarySpec(width=w))
                idx = int(np.argmax(h.capped)) if bool(h.capped.any()) else -1
                binds.append({"seed": seed, "pump": pump, "width": w,
                              "first_bind": idx,
                              "n_capped": int(h.capped.sum()),
                              "closing_balance": float(h.balance[-1])})
    ever = [b for b in binds if b["first_bind"] >= 0]
    never = [b for b in binds if b["first_bind"] < 0]
    firsts = sorted(b["first_bind"] for b in ever)
    print(f"   cells {len(binds)}, ever bound {len(ever)}, never {len(never)}")
    if ever:
        print(f"   first bind runs {firsts[0]} to {firsts[-1]} of {ROUNDS}")

    # ---- A25-4: the four cells across the width grid, printed ----------
    # **The recorded table is not reproduced here and that is the reading.**
    # The August readings, which are in RESULTS.md, are closing balances of
    # +1.9 to +30 with the pump on and a ceiling, and +1745 to +9955 with the
    # pump on and none.
    # This driver sweeps six widths at both pump settings and both ceiling
    # arms and never leaves the single digits: the runaway arm saturates near
    # +3.2. Two orders of magnitude, so it is a different configuration and
    # not a tolerance.
    #
    # **What that costs is the point.** The stage had no record on disk, its
    # readings lived as prose in RESULTS.md and in its own results file, and
    # the configuration behind them is not recoverable from the module, the
    # design sheet's carrier line, or either write-up. The original readings
    # stay where they are and are not overwritten; what is recorded here is
    # that they do not reproduce, which is a fact about this repository rather
    # than about clearing boundaries.
    print("\n== A25-4  four cells across the width grid ==")
    print("   recorded: pump on truncate +1.9..+30, pump on accrue "
          "+1745..+9955, pump off truncate -1.9..-7.2, off accrue -8.5..-21.1")
    four = []
    for w in (0.02, 0.05, 0.10, 0.20, 0.50, 1.0):
        for pump in (True, False):
            for swing, label in ((0.25, "truncate"), (None, "accrue")):
                closes = []
                for seed in SEEDS:
                    _, _, h = run_pair(_cfg(seed, pump), _cfg(seed + 100, pump),
                                       BoundarySpec(width=w, swing=swing))
                    closes.append(float(h.balance[-1]))
                four.append({"width": w, "pump": pump, "ceiling": label,
                             "closing_balance": closes})
        row = [c for c in four if c["width"] == w]
        print(f"   width {w:<5} " + "  ".join(
            f"{'on' if c['pump'] else 'off'}/{c['ceiling'][:4]} "
            f"{min(c['closing_balance']):+8.1f}..{max(c['closing_balance']):+8.1f}"
            for c in row))
    reach = max(abs(x) for c in four for x in c["closing_balance"])

    v1 = (f"the boundary is off by default and the run proves it: with width "
          f"zero nothing crosses and each side closes exactly where it closes "
          f"run alone, in {sum(same)} of {len(same)} cells")
    v3 = (f"counts printed, no threshold. Of {len(binds)} cells the ceiling "
          f"binds in {len(ever)} and never in {len(never)}"
          + (f", and the round it first binds runs {firsts[0]} to "
             f"{firsts[-1]} of {ROUNDS}, so both branches are reachable"
             if ever and never else
             ". Only one branch is reached on this grid, so the criterion "
             "does not establish reachability"))
    v2 = ("not scored this round. That the independent cycle count across the "
          "boundary is one less than the number of channels is a counting "
          "result and this driver runs the single-channel case only")
    v4 = (f"**not reproduced.** The recorded reading is that the four cells "
          f"leave no setting where the boundary is both live and stable, with "
          f"closing balances running to +9955 on the arm with a pump and no "
          f"ceiling. This driver sweeps six widths at both pump settings and "
          f"both ceiling arms, 24 cells, and the largest closing balance "
          f"anywhere is {reach:.2f}. Two orders of magnitude below, so the "
          f"configuration behind the recorded table is not the one reachable "
          f"from the module plus the design sheet's carrier line. The "
          f"recorded readings are not withdrawn and not overwritten; what is "
          f"established here is that they do not reproduce from what is on "
          f"disk, which is the cost of a stage having had no record")

    print(f"\n  A25-1: {v1}\n  A25-2: {v2}\n  A25-3: {v3}\n  A25-4: {v4}")
    RESULTS_DIR.mkdir(exist_ok=True)
    RECORD.write_text(json.dumps({
        "stage": "A25",
        "criteria": [
            {"name": "A25-1  the boundary is off by default",
             "passed": bool(all(same)), "detail": v1},
            {"name": "A25-2  the crossing is a bridge", "detail": v2},
            {"name": "A25-3  the ceiling binds",
             "passed": bool(ever and never), "detail": v3},
            {"name": "A25-4  what happens once it binds",
             "passed": False, "detail": v4},
        ],
        "config": {
            "note": "what this run actually used. Fields are those differing "
                    "from the dataclass defaults; anything absent is at its "
                    "default. Present so the readings below can be rebuilt.",
            "seed_offset_between_sides": 100,
            "module_constants": {
                "ROUNDS": ROUNDS, "SEEDS": list(SEEDS),
                "WIDTHS": list(WIDTHS), "NEED": NEED, "FUNDING": FUNDING,
                "PUMP_RATE": PUMP_RATE, "SWING_HISTORICAL": SWING_HISTORICAL,
            },
            "four_cell_grid": {
                "widths": [0.02, 0.05, 0.10, 0.20, 0.50, 1.0],
                "pumps": [True, False],
                "ceilings": {"truncate": 0.25, "accrue": None},
            },
            "sides": {
                f"pump_{p}": {"g1": _nondefault(_cfg(SEEDS[0], p)),
                              "g2": _nondefault(_cfg(SEEDS[0] + 100, p))}
                for p in (False, True)
            },
        },
        "default_off": cells, "binds": binds, "four_cells": four,
        "rounds": ROUNDS, "seeds": list(SEEDS), "widths": list(WIDTHS),
        "diagnostic_only": True,
        "diagnostic_reason": "A25 is open: two reopening conditions are "
                             "registered and neither is in hand",
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n   record: {RECORD.name}")


if __name__ == "__main__":
    probe()
