"""A18: what the policy switches do to the time path.

Every station in this repository so far reads a closing value: a closing Gini, a
closing count below the line, a mean over the last twenty-five rounds. **No
station has read a trajectory.** A claim of the form "it looks steady for a
while and then releases something larger" is only falsifiable on one, because
closing values carry no order.

Four switches, all of them already in the model, and the code already says of
one of them that it is a political condition rather than a mechanism.

    subsistence.mode = "drawdown"   forbearance: nobody is forced out
    writeoff.rate                   whether losses are recognised at all
    writeoff.refill                 whether the head grows back
    authority.rule = "none"         the external top-up stops

**This stage changes no mechanism.** It changes what gets recorded.

The main reading is on ``M/R`` and total flow, not on the count below the line,
and A18-2 is the gate that says why: under ``exit`` that count is cumulative and
monotone, and under ``drawdown`` it is re-read every round. Comparing the two
would be comparing a running total with an instantaneous reading.

**The B arm carries the one mechanism the A arm named and did not have.**
Forbearance is dangerous in the world because the forborne party keeps receiving
new credit, and under ``drawdown`` a node here eats its own stock until it has
none with nobody feeding it. So the A arm's three readings hold for forbearance
without resupply, and ``resupply.rate`` is the other kind: whoever already lends
to a node below the floor keeps it going, out of their own holdings, along the
edges that are already there.

The two arms are recorded separately, in ``a18_policy_paths.json`` and
``a18_resupply.json``, because the A arm's grid has no rate axis and folding one
in would change every key in a record that is already written.

Usage

    python experiments/a18_policy_paths.py --plan
    python experiments/a18_policy_paths.py --smoke
    python experiments/a18_policy_paths.py
    python experiments/a18_policy_paths.py --resupply
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    MonetaryAuthority,
    Network,
    NetworkConfig,
    NetworkSpec,
    PARK_TARGETS,
    ParkSpec,
    RECAP_TARGETS,
    RESUPPLY_FUNDING,
    ResupplySpec,
    SubsistenceSpec,
    WageChannel,
    WriteOffSpec,
)

RECORD = RESULTS / "a18_policy_paths.json"
RECORD_B = RESULTS / "a18_resupply.json"
DIGITS = 6


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A12 = _load(ROOT / "experiments" / "a12_mechanisms.py", "_a12")
BASE_CARRIER = _A12.BASE_CARRIER
r = _A12.r
#: A10's mildest write-off, taken from A12 rather than restated.
WRITEOFF = _A12.WRITEOFF
WRITEOFF_REFILL = _A12.WRITEOFF_REFILL

F2I = 30
ELASTICITY = 0.5
ROUNDS = 300
SEEDS = (0, 1, 2, 3, 4)

#: Two floor depths, one on each side of the boundary A16-8 located between
#: 0.125 and 0.150. That boundary decides whether the nodes that go take their
#: stock with them, and what accumulates is this stage's subject.
NEED_MULTIPLES = (0.05, 0.20)

#: The rounds the curves are sampled at, for the criterion that prints the path
#: rather than its endpoint.
QUANTILE_ROUNDS = (50, 100, 150, 200, 250)

#: The six per-round series. All of them are recorded, whether or not a
#: criterion reads them.
SERIES = ("total_ratio", "total_volume", "frozen_holdings", "written_off",
          "effective_support", "starved")


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def policies() -> list:
    """(label, mode, writeoff, authority_rule). Twelve combinations."""
    out = []
    for mode in ("exit", "drawdown"):
        for wname, wspec in (("none", WriteOffSpec()),
                             ("on", WRITEOFF),
                             ("on+refill", WRITEOFF_REFILL)):
            for auth in ("endogenous", "none"):
                out.append(("%s/%s/%s" % (mode, wname, auth), mode, wspec, auth))
    return out


def config_for(mode: str, wspec: WriteOffSpec, auth: str,
               need_mult: float, seed: int,
               resupply_rate: float = 0.0,
               elasticity: float = ELASTICITY) -> NetworkConfig:
    """The A arm's config, plus the B arm's one switch.

    ``resupply_rate`` defaults to zero, which is ``ResupplySpec``'s own default
    and therefore the A arm untouched: every row of ``a18_policy_paths.json``
    comes back out of this function unchanged. ``elasticity`` defaults to the
    stage constant for the same reason.
    """
    c = BASE_CARRIER
    need = need_mult * 100.0 / c.nodes
    return NetworkConfig(
        spec=NetworkSpec(
            seed=seed,
            layer1_size=c.layer1_size,
            intermediate_size=c.intermediate_size,
            layer2_size=c.layer2_size,
            financial_to_intermediate_edges=F2I,
        ),
        seed=seed,
        rounds=ROUNDS,
        wages=WageChannel(elasticity=elasticity),
        subsistence=SubsistenceSpec(need=need, mode=mode),
        writeoff=wspec,
        authority=MonetaryAuthority(rule=auth),
        resupply=ResupplySpec(rate=resupply_rate),
    )


def _first_move(path: np.ndarray, tol: float = 1e-9) -> int:
    """The first round the series leaves its opening value. -1 if it never does.

    **No threshold on the size of the move**: it is the first round the number
    is not the number it started at, to floating tolerance.
    """
    moved = np.flatnonzero(np.abs(path - path[0]) > tol)
    return int(moved[0]) if moved.size else -1


def _largest_jump(path: np.ndarray, tol: float = 1e-9) -> tuple[int, float]:
    """The round of the largest single-round change, and its size.

    ``-1`` when the series never moves by more than floating tolerance, which
    is the same convention and the same tolerance ``_first_move`` uses.

    **Why the guard is here rather than left to the reader.** Under
    forbearance ``total_ratio`` is flat: the stabiliser never fires because
    inflow never collapses, so the series sits at its opening value for all
    three hundred rounds and its largest single-round change is one unit in the
    last place, ``3.33e-16``. Eight to eleven rounds tie at exactly that value,
    and ``argmax`` returns whichever comes first. So without this guard the
    field is an index into a set of indistinguishable ulps: it reproduces
    nothing, it moves whenever anything anywhere in the model shifts a last
    bit, and read as a round number it says the damage arrives late when in
    fact it never arrives at all.

    Measured 2026-08-26 against the committed record: fifty-one fields across
    the grid disagreed, every one of them this one, and every one of them on a
    cell whose largest change was that single ulp.
    """
    d = np.abs(np.diff(np.asarray(path, dtype=float)))
    if d.size == 0 or d.max() <= tol:
        return -1, 0.0
    i = int(np.argmax(d))
    return i + 1, float(d[i])


def one_run(label: str, mode: str, wspec: WriteOffSpec, auth: str,
            need_mult: float, seed: int) -> dict:
    net = Network(config_for(mode, wspec, auth, need_mult, seed))
    h = net.run()
    row = {
        "policy": label,
        "mode": mode,
        "writeoff_rate": float(wspec.rate),
        "refill": bool(wspec.refill),
        "authority": auth,
        "need_multiple": float(need_mult),
        "seed": int(seed),
    }
    for name in SERIES:
        path = np.asarray(getattr(h, name), dtype=float)
        jr, jsize = _largest_jump(path)
        row["%s_open" % name] = r(float(path[0]))
        row["%s_close" % name] = r(float(path[-1]))
        row["%s_first_move" % name] = _first_move(path)
        row["%s_jump_round" % name] = jr
        row["%s_jump_size" % name] = r(jsize)
        row["%s_at" % name] = [r(float(path[q])) for q in QUANTILE_ROUNDS]
        # Whether the series only ever goes one way. The gate reads this.
        d = np.diff(path)
        row["%s_monotone" % name] = bool((d >= -1e-12).all() or (d <= 1e-12).all())
    return row


def plan() -> dict:
    return {
        "policies": len(policies()),
        "need_multiples": list(NEED_MULTIPLES),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "series_recorded": list(SERIES),
        "sampled_at": list(QUANTILE_ROUNDS),
        "runs_total": len(policies()) * len(NEED_MULTIPLES) * len(SEEDS),
        "mechanism_changes": "none. Every switch already exists; what changes "
                             "is what gets recorded",
    }


def run_grid(needs=NEED_MULTIPLES, seeds=SEEDS) -> list:
    return [one_run(label, mode, wspec, auth, need, seed)
            for (label, mode, wspec, auth) in policies()
            for need in needs for seed in seeds]


CONTROL = "exit/none/endogenous"


def criterion_a18_1(rows: list) -> Criterion:
    """Discipline 19 on the harness, against A12's floor arm.

    This stage adds no mechanism, so what needs checking is that its own
    config-building agrees with the one that produced the records it will be
    read beside. The control policy at a floor multiple of 0.20 is A12's
    ``floor`` arm.
    """
    path = RESULTS / "a12_mechanisms.json"
    if not path.exists():
        return Criterion("A18-1  the control policy is A12's floor arm", False,
                         "a12_mechanisms.json is not on disk")
    ref = [x for x in json.loads(path.read_text(encoding="utf-8"))["runs"]
           if x["arm"] == "floor" and x["f2i"] == F2I
           and x["elasticity"] == ELASTICITY]
    mine = [x for x in rows if x["policy"] == CONTROL
            and x["need_multiple"] == 0.20 and x["seed"] == 0]
    if not ref or not mine:
        return Criterion("A18-1  the control policy is A12's floor arm", False,
                         "no comparable cell: %d reference, %d here"
                         % (len(ref), len(mine)))
    a, b = mine[0], ref[0]
    # A12 records ratios over the opening; this stage records levels, so the
    # comparison is built rather than looked up, and that is the point of the
    # check: two files that disagree about how to build it would show here.
    got = r(a["total_ratio_close"] / a["total_ratio_open"])
    bad = [] if got == b["mr_ratio"] else [("mr_ratio", got, b["mr_ratio"])]
    got_s = a["starved_close"]
    if got_s != b["starved"]:
        bad.append(("starved", got_s, b["starved"]))
    return Criterion("A18-1  the control policy is A12's floor arm", not bad,
                     "M/R over its opening %s against a12's %s, closing count "
                     "below the line %s against %s%s"
                     % (got, b["mr_ratio"], got_s, b["starved"],
                        "" if not bad else "; differing: %s" % bad))


def criterion_a18_2(rows: list) -> Criterion:
    """The gate: the count below the line is not one object across the two modes.

    Under ``exit`` it is a running total that never falls. Under ``drawdown`` it
    is re-read every round and can fall. **A comparison between them would be a
    comparison between a cumulative and an instantaneous reading**, which is why
    the main question is asked of ``M/R`` and total flow instead.

    Structural, and it fires on the property rather than on a magnitude:
    monotone under one mode and not under the other.
    """
    parts = []
    ok = True
    for mode in ("exit", "drawdown"):
        cells = [x for x in rows if x["mode"] == mode]
        if not cells:
            continue
        mono = sum(1 for x in cells if x["starved_monotone"])
        parts.append("%s: the count below the line is monotone in %d of %d cells"
                     % (mode, mono, len(cells)))
        if mode == "exit" and mono != len(cells):
            ok = False
            parts.append("exit should be monotone everywhere and is not")
    for name in ("total_ratio", "total_volume"):
        both = {}
        for mode in ("exit", "drawdown"):
            cells = [x for x in rows if x["mode"] == mode]
            both[mode] = sum(1 for x in cells if x["%s_monotone" % name])
        parts.append("%s monotone counts by mode: %s" % (name, both))
    return Criterion("A18-2  the count below the line is not one object",
                     ok, " | ".join(parts))


def criterion_a18_6(rows: list) -> Criterion:
    """Does not recognising a loss actually accumulate anything here.

    The prediction this stage was opened to test runs through an accumulation:
    losses are not recognised, so something builds, so a larger release follows.
    **The middle step has to exist before the last one can be asked about**, and
    in this model the candidate is the claim-to-resource ratio: with the
    write-off off, nothing destroys claims, so the ratio should climb.

    Printed, not thresholded: the ratio's opening and closing on each policy,
    and whether it rose at all.
    """
    parts = []
    for need in sorted({x["need_multiple"] for x in rows}):
        for wr, label in ((0.0, "not recognised"), (WRITEOFF.rate, "recognised")):
            cells = [x for x in rows if x["need_multiple"] == need
                     and x["writeoff_rate"] == wr and not x["refill"]]
            if not cells:
                continue
            ratios = sorted(r(x["total_ratio_close"] / x["total_ratio_open"])
                            for x in cells)
            destroyed = sorted(x["written_off_close"] for x in cells)
            parts.append(
                "floor %.2f, losses %s: M/R over its opening %s | claims "
                "destroyed in the closing round %s"
                % (need, label, ratios, destroyed))
    return Criterion("A18-6  does not recognising a loss accumulate anything",
                     True, " | ".join(parts))


def criterion_a18_3(rows: list) -> Criterion:
    """The main question, on the two series that mean the same in both modes.

    Three states, fixed before the run.

      **Quiet then release.** The forbearance arm's first move is later than the
      control's **and** its largest single-round jump is larger. Both, not
      either: a late start with no larger release is a different thing.

      **A slow grind.** The first move is not later and no larger jump appears.
      Forbearance spreads the damage instead of deferring it.

      **No worse than the control.** Neither reading is worse. Forbearance
      creates no deferred risk on this carrier, reported as it stands.

    **Nothing is thresholded.** The rounds and the jump sizes are printed
    against the control at the same floor and seed.
    """
    parts = []
    for need in sorted({x["need_multiple"] for x in rows}):
        ctl = {x["seed"]: x for x in rows if x["policy"] == CONTROL
               and x["need_multiple"] == need}
        if not ctl:
            continue
        for label in sorted({x["policy"] for x in rows}):
            cells = [x for x in rows if x["policy"] == label
                     and x["need_multiple"] == need and x["seed"] in ctl]
            if not cells:
                continue
            for name in ("total_ratio", "total_volume"):
                later = sorted(x["%s_first_move" % name]
                               - ctl[x["seed"]]["%s_first_move" % name]
                               for x in cells)
                bigger = sorted(r(x["%s_jump_size" % name]
                                  - ctl[x["seed"]]["%s_jump_size" % name])
                                for x in cells)
                jr = sorted(x["%s_jump_round" % name] for x in cells)
                parts.append(
                    "floor %.2f %s %s: first move minus the control's %s | "
                    "largest jump minus the control's %s | jump rounds %s"
                    % (need, label, name, later, bigger, jr))
    return Criterion("A18-3  quiet then release, a slow grind, or neither",
                     True, " | ".join(parts))


def criterion_a18_4(rows: list) -> Criterion:
    """The paths themselves, sampled, rather than any summary of them."""
    parts = ["sampled at rounds %s" % (QUANTILE_ROUNDS,)]
    for need in sorted({x["need_multiple"] for x in rows}):
        for label in sorted({x["policy"] for x in rows}):
            cells = [x for x in rows if x["policy"] == label
                     and x["need_multiple"] == need]
            if not cells:
                continue
            for name in ("total_ratio", "total_volume"):
                parts.append("floor %.2f %s %s: %s"
                             % (need, label, name,
                                [x["%s_at" % name] for x in cells[:2]]))
    return Criterion("A18-4  the paths, sampled", True, " | ".join(parts))


def criterion_a18_5(rows: list) -> Criterion:
    """Every cell counted, and the three most extreme named."""
    ctl = {(x["need_multiple"], x["seed"]): x for x in rows
           if x["policy"] == CONTROL}
    scored = []
    for x in rows:
        k = (x["need_multiple"], x["seed"])
        if k not in ctl or x["policy"] == CONTROL:
            continue
        base = ctl[k]["total_ratio_close"] / ctl[k]["total_ratio_open"]
        mine = x["total_ratio_close"] / x["total_ratio_open"]
        scored.append((r(abs(mine - base)), x["policy"], x["need_multiple"],
                       x["seed"], r(mine), r(base)))
    scored.sort(reverse=True)
    return Criterion(
        "A18-5  every cell, and the three most extreme", True,
        "%d cells against a control at the same floor and seed | the three "
        "furthest from it on M/R over its opening: %s | the three closest: %s"
        % (len(scored), scored[:3], scored[-3:]))


# ---------------------------------------------------------------------------
# A18_B: forbearance with somebody paying for it.
# ---------------------------------------------------------------------------

#: The rescue, as a multiple of the subsistence need topped up each round for a
#: node below the floor. Zero is the A arm. The grid starts at one rather than
#: at a fraction because below a rate of one the target sits under what a node
#: below the floor is already holding, so the shortfall is zero and the switch
#: is inert. That is a fact about the arithmetic, measured before this grid was
#: written, and a grid whose lower half cannot move is a grid with a dead
#: branch in it.
RESUPPLY_RATES = (0.0, 1.0, 2.0, 4.0)

#: Three floor depths rather than the A arm's two. ``0.50`` is added because the
#: rescue needs somewhere to act: at ``0.05`` the nodes below the floor still
#: hold more than any rate on this grid would top them up to, so every cell
#: there reads the control. Keeping it in is the point, it is the third state.
RESUPPLY_NEEDS = (0.05, 0.20, 0.50)

#: Where the rescue's money comes from. All three, because "where does the
#: money come from" is the question and these are its three answers, not three
#: settings of one dial. See ``RESUPPLY_FUNDING`` in the model.
#:
#: The three are run only where a rescue happens. At rate zero they are the
#: same run three times, and a grid that spends three times to record one thing
#: once is a grid with two dead cells in it.
FUNDING_ARMS: tuple[str, ...] = RESUPPLY_FUNDING

#: What a recapitalised node withdraws from circulation. Scanned only on
#: ``issuance`` under ``drawdown``, because the other two routes create no
#: recapitalised set for it to act on and ``exit`` carries no criterion.
#:
#: **The levels are where the probe found something, not a round grid.**
#: Measured before this was written: the count below the line is flat from
#: `0.00` all the way to `0.95` and only moves at total withdrawal, while
#: `M/R` climbs the whole way, from about 5 to about 32 over the same span and
#: roughly doubling per `0.1` past `0.7`. So the levels bracket a flat stretch,
#: the steep part of the price, and the one point where the count turns.
RETAIN_LEVELS: tuple[float, ...] = (0.0, 0.5, 0.9, 1.0)

#: The relative perturbation A18_B6 applies to the opening holdings.
#:
#: **Measured before it was chosen, on the cell that forced it.** Two of the
#: hundred and twenty cells came back different when the record was re-run on a
#: second machine, both of them at floor `0.50` and rate `1.0`. A ladder on
#: that cell put the boundary between `1e-12` and `1e-10` for one seed and
#: between `1e-10` and `1e-8` for another, while three seeds held to `1e-6`.
#: A single unit in the last place moved nothing at all.
#:
#: So this number is the smallest one that reaches the boundary that was
#: actually found. It is not a tolerance and nothing passes or fails on it: the
#: criterion prints which cells move.
BOUNDARY_EPSILON = 1e-10

#: Judged on ``drawdown`` only, and ``exit`` is run and printed beside it.
#: Under ``exit`` a node below the floor is out of the market: it receives and
#: does not spend, so claims sent to it are frozen by construction and the arm
#: can only report its own plumbing. That is worth printing and is not a
#: reading, so no criterion rests on it.
RESUPPLY_MODES = ("drawdown", "exit")


def _below_set(net, mode: str) -> np.ndarray:
    """Who is below the line, read off whichever object this exit rule fills."""
    return net._below.copy() if mode == "drawdown" else ~net._alive


def resupply_run(mode: str, need_mult: float, rate: float, seed: int,
                 control: dict | None, funding: str = "creditors",
                 epsilon: float = 0.0, retain: float = 0.0) -> dict:
    """One cell of the B arm.

    ``control`` is the same cell at rate zero, and it is passed in rather than
    recomputed because the two quantities this arm exists for are both
    differences against it: who is below the line who was not, and what the
    payers are holding at the end.

    **The payer set is defined on the control**, as the nodes with an edge into
    somebody who was below the line there, minus those who were below it
    themselves. Defining it on the treated run instead would let the rescue
    choose its own comparison group.
    """
    cfg = config_for(mode, WriteOffSpec(), "endogenous", need_mult, seed,
                     resupply_rate=rate)
    cfg = dataclasses.replace(
        cfg, resupply=ResupplySpec(rate=rate, funding=funding, retain=retain))
    net = Network(cfg)
    if epsilon:
        # A18_B6 only. Scaling every opening holding by the same factor is the
        # smallest change that is not a change of design: no node is singled
        # out, the shares are untouched, and only the last bits move.
        net.holdings = net.holdings * (1.0 + epsilon)
    h = net.run()
    below = _below_set(net, mode)
    hold = np.asarray(h.holdings, dtype=float)[-1]

    volume = float(np.asarray(h.total_volume, dtype=float).sum())
    row = {
        "mode": mode,
        "need_multiple": float(need_mult),
        "rate": float(rate),
        "funding": funding,
        "retain": float(retain),
        "seed": int(seed),
        "recapitalised": r(float(net._recapitalised)),
        "recap_recipients": int(net._recap_recipients.sum()),
        # What the rescue was asked for against what it could fund. The model
        # computed the first either way; recording only the second hid the
        # quantity this whole arm turns on.
        "resupply_asked": r(float(net._resupply_asked)),
        "funded_share": (r(float(net._resupplied / net._resupply_asked))
                         if net._resupply_asked > 0 else 0.0),
        "levied": r(float(net._levied)),
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "claims_close": r(float(hold.sum())),
        "below_close": int(below.sum()),
        "resupplied": r(float(net._resupplied)),
        # **The rescue travels an edge, so it is inflow.** That is the same
        # rule `_fiscal_flow` documents for a transfer routed through the flow,
        # and it has a consequence worth printing rather than discovering:
        # `effective_support` is one over the HHI of inflow, so part of any
        # movement in it is the rescue's own edges rather than the rescued
        # nodes returning to trade. This share is what that part is bounded by.
        # `below_close` is not a flow quantity and carries none of it.
        "resupply_share_of_volume": (r(float(net._resupplied) / volume)
                                     if volume > 0 else 0.0),
        "support_close": r(float(h.effective_support[-1])),
        "volume_total": r(volume),
        "frozen_close": r(float(h.frozen_holdings[-1])),
        "written_off_total": r(float(np.asarray(h.written_off,
                                                dtype=float).sum())),
        "gini_close": r(_gini(hold)),
        "claims_conserved": bool(np.isfinite(hold).all()),
    }
    if control is None:
        row |= {
            "payers": 0, "payers_poorer": 0, "payer_holdings_delta": 0.0,
            "newly_below": 0, "newly_below_lends_to_below": 0,
            "below_delta": 0,
        }
        return row

    base_below = np.asarray(control["_below"], dtype=bool)
    base_hold = np.asarray(control["_holdings"], dtype=float)
    adjacency = np.asarray(control["_adjacency"], dtype=float)

    payers = np.zeros(base_below.size, dtype=bool)
    for j in np.flatnonzero(base_below):
        payers |= adjacency[:, j] > 0
    payers &= ~base_below

    delta = hold[payers] - base_hold[payers]
    new = below & ~base_below
    lends = 0
    for i in np.flatnonzero(new):
        if (adjacency[i] > 0)[base_below].any():
            lends += 1

    row |= {
        "payers": int(payers.sum()),
        "payers_poorer": int((delta < -1e-9).sum()),
        "payer_holdings_delta": r(float(delta.sum())),
        "newly_below": int(new.sum()),
        "newly_below_lends_to_below": int(lends),
        "below_delta": int(below.sum()) - int(base_below.sum()),
    }
    return row


def _gini(v: np.ndarray) -> float:
    g = np.sort(np.asarray(v, dtype=float))
    n = g.size
    total = g.sum()
    if n == 0 or total <= 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(g) / (n * total))


def _control_for(mode: str, need: float, seed: int) -> dict:
    """The rate-zero run, whose below-the-floor set defines the payer set."""
    net = Network(config_for(mode, WriteOffSpec(), "endogenous", need, seed))
    h = net.run()
    return {
        "_below": _below_set(net, mode),
        "_holdings": np.asarray(h.holdings, dtype=float)[-1],
        "_adjacency": net.adjacency,
    }


def resupply_grid(needs=RESUPPLY_NEEDS, seeds=SEEDS,
                  modes=RESUPPLY_MODES, fundings=FUNDING_ARMS) -> list:
    rows = []
    for mode in modes:
        for need in needs:
            for seed in seeds:
                control = _control_for(mode, need, seed)
                for rate in RESUPPLY_RATES:
                    # At rate zero there is no rescue, so the three funding
                    # routes are one run. Recording it once under the default
                    # name keeps the control a single object rather than three
                    # identical rows a later reader has to notice are identical.
                    arms = fundings if rate > 0.0 else ("creditors",)
                    for funding in arms:
                        rows.append(resupply_run(mode, need, rate, seed,
                                                 control, funding))
                        # The retention scan rides on one route and one exit
                        # rule. The other routes create no recapitalised set
                        # for it to act on, and `exit` carries no criterion, so
                        # running it there would buy a number nothing reads.
                        if funding != "issuance" or mode != "drawdown":
                            continue
                        for retain in RETAIN_LEVELS:
                            if retain == 0.0:
                                continue  # already recorded, one line above
                            rows.append(resupply_run(mode, need, rate, seed,
                                                     control, funding,
                                                     retain=retain))
    return rows


def boundary_scan(needs=RESUPPLY_NEEDS, seeds=SEEDS,
                  fundings=FUNDING_ARMS) -> list:
    """A18_B6. Every judged cell, re-run with the opening holdings nudged.

    ``drawdown`` only, because that is the arm anything is judged on.
    """
    out = []
    for need in needs:
        for seed in seeds:
            control = _control_for("drawdown", need, seed)
            for rate in RESUPPLY_RATES:
                arms = fundings if rate > 0.0 else ("creditors",)
                for funding in arms:
                    a = resupply_run("drawdown", need, rate, seed, control,
                                     funding)
                    b = resupply_run("drawdown", need, rate, seed, control,
                                     funding, epsilon=BOUNDARY_EPSILON)
                    # Both halves of the portability question, from one pair of
                    # runs. The discrete half asks whether the count moves at
                    # all. The continuous half asks how far the other readings
                    # move, because a run whose count holds can still carry
                    # every other number to only three or four figures: the
                    # threshold feeds back into the flow, so a last-bit
                    # difference is rounded through a boolean every round and
                    # compounds over three hundred of them.
                    moves = {}
                    for k, va in a.items():
                        vb = b.get(k)
                        if not isinstance(va, float) or not isinstance(vb, float):
                            continue
                        if va == 0.0:
                            continue
                        moves[k] = r(abs(va - vb) / abs(va))
                    worst_field = max(moves, key=lambda k: moves[k]) if moves else None
                    worst = moves.get(worst_field, 0.0)
                    out.append({
                        "need_multiple": float(need), "rate": float(rate),
                        "funding": funding, "seed": int(seed),
                        "below_close": a["below_close"],
                        "below_close_nudged": b["below_close"],
                        "moved": a["below_close"] != b["below_close"],
                        "support_close": a["support_close"],
                        "support_close_nudged": b["support_close"],
                        "worst_relative_move": r(worst),
                        "worst_field": worst_field,
                        # Per field, so that the record answers "which of my
                        # own readings are portable, and to how many figures"
                        # rather than one number dominated by whichever field
                        # happens to be closest to zero.
                        "relative_moves": moves,
                    })
    return out


def resupply_plan() -> dict:
    return {
        "modes": list(RESUPPLY_MODES),
        "judged_on": "drawdown. exit is printed and carries no criterion",
        "need_multiples": list(RESUPPLY_NEEDS),
        "rates": list(RESUPPLY_RATES),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        # Two numbers rather than one, because they are not the same number
        # and a plan that gives only the smaller one understates the cost.
        # The control at rate zero is run twice: once to fix the payer set and
        # the below-the-floor set every other rate is compared against, and
        # once as the rate-zero row itself. The second is not wasted, it is
        # what makes A18_B1 a check rather than an identity.
        "funding_routes": list(FUNDING_ARMS),
        "retain_levels": list(RETAIN_LEVELS),
        "retain_scanned_on": "issuance under drawdown only. The other routes "
                             "create no recapitalised set and exit carries no "
                             "criterion",
        "boundary_epsilon": BOUNDARY_EPSILON,
        "rows_recorded": (len(RESUPPLY_MODES) * len(RESUPPLY_NEEDS)
                          * len(SEEDS)
                          * (1 + (len(RESUPPLY_RATES) - 1) * len(FUNDING_ARMS))
                          + len(RESUPPLY_NEEDS) * len(SEEDS)
                          * (len(RESUPPLY_RATES) - 1)
                          * (len(RETAIN_LEVELS) - 1)),
        # Rows plus the controls the payer set is defined against, plus the
        # boundary scan, which runs the judged part of the grid twice.
        "runs_executed": "see rows_recorded; the grid also runs one control "
                         "per (mode, floor, seed) and the boundary scan runs "
                         "the drawdown rows a second time nudged",
        "mechanism_added": "resupply.rate, whoever already lends to a node "
                           "below the floor tops it up along the edges already "
                           "there, and resupply.funding, which says whose "
                           "money that is: the lender's own book, new claims "
                           "from outside the graph, or a levy on everybody, "
                           "and resupply.retain, which withdraws a "
                           "recapitalised node from circulation without "
                           "excusing it from the rescue",
    }


def _moved(row: dict) -> bool:
    """Did the rescue actually move anything in this cell.

    A cell where it did not is not a failure of anything, it is the state in
    which the switch had no purchase, and every criterion below reads it as the
    third state rather than as a negative.
    """
    return row["rate"] > 0.0 and row["resupplied"] > 0.0


def criterion_a18_b1(_rows: list) -> Criterion:
    """Rule 19 for this file: the A arm's record comes back out unchanged.

    ``config_for`` grew a parameter, so every row of ``a18_policy_paths.json``
    was produced by a function that no longer exists in the form that produced
    it. The check is a re-run against the committed record, field for field,
    and not an argument about a default value.

    **It reads the record rather than recomputing a control**, because a
    control computed here would be produced by the same edited code and would
    agree with itself whatever the edit did.
    """
    if not RECORD.exists():
        return Criterion("A18_B1  the A arm reproduces its record", False,
                         "%s is not on disk, so there is nothing to "
                         "reproduce" % RECORD.name)
    recorded = json.loads(RECORD.read_text(encoding="utf-8"))["runs"]
    index = {(x["policy"], x["need_multiple"], x["seed"]): x for x in recorded}
    specs = {label: (mode, wspec, auth)
             for (label, mode, wspec, auth) in policies()}
    bad = []
    for key, was in sorted(index.items()):
        label, need, seed = key
        mode, wspec, auth = specs[label]
        now = one_run(label, mode, wspec, auth, need, seed)
        for field in sorted(was):
            if was[field] != now.get(field):
                bad.append((key, field, was[field], now.get(field)))
    return Criterion(
        "A18_B1  the A arm reproduces its record", not bad,
        "%d recorded rows re-run through the edited code, %d field(s) differ%s"
        % (len(index), len(bad),
           "" if not bad else ": %s" % (bad[:6],)))


def criterion_a18_b2(rows: list) -> Criterion:
    """Three states on what the rescue does to the count below the line.

    Read on the sign of a difference and on nothing else. No threshold, and the
    cells where the switch had no purchase are named rather than counted
    against it.
    """
    live = [x for x in rows if x["mode"] == "drawdown" and _moved(x)
            and x["retain"] == 0.0]
    inert = [x for x in rows if x["mode"] == "drawdown" and x["rate"] > 0.0
             and not _moved(x) and x["retain"] == 0.0]
    down = [x for x in live if x["below_delta"] < 0]
    up = [x for x in live if x["below_delta"] > 0]
    flat = [x for x in live if x["below_delta"] == 0]
    if not live:
        state = "third: the switch moved nothing anywhere, undecided here"
    elif up and down:
        state = "second: it cuts the count in some cells and raises it in others"
    elif down and not up:
        state = "first: where it moved money it never raised the count"
    else:
        state = "third: it moved money and never cut the count"
    by_arm = []
    for f in FUNDING_ARMS:
        cells = [x for x in live if x["funding"] == f]
        by_arm.append((f, len(cells),
                       sum(1 for x in cells if x["below_delta"] < 0),
                       sum(1 for x in cells if x["below_delta"] > 0)))
    return Criterion(
        "A18_B2  what the rescue does to the count below the line", True,
        "%s | of %d cells where money moved: %d down, %d level, %d up | %d "
        "further cells the switch could not reach, at floor depths %s | "
        "by funding route (route, cells, down, up): %s"
        % (state, len(live), len(down), len(flat), len(up), len(inert),
           sorted({x["need_multiple"] for x in inert}), by_arm))


def criterion_a18_b3(rows: list) -> Criterion:
    """What it costs the ones paying, gross against net.

    **Read on the ``creditors`` route only, and that is a scope statement not a
    convenience.** Under the other two the lenders are handed the money back,
    by an authority or by everybody, so their net position answers a question
    about the refund rather than about the rescue. A18_B7 is where the three
    routes are compared.

    **The reading declared before the run**: the payers hand over
    ``resupplied`` and end holding ``payer_holdings_delta`` less than they would
    have. Those two are the same quantity only if what they pay leaves the
    system. It does not: the rescued node spends it, and the graph carries it
    back. So the ratio is what this cell reports, and the criterion is that it
    is recorded for every cell, not that it lands anywhere in particular.
    """
    live = [x for x in rows if x["mode"] == "drawdown" and _moved(x)
            and x["funding"] == "creditors"]
    worse = [x for x in live if x["payer_holdings_delta"] > 0]
    ratios = [(r(abs(x["payer_holdings_delta"]) / x["resupplied"]),
               x["need_multiple"], x["rate"], x["seed"])
              for x in live if x["resupplied"] > 0]
    ratios.sort()
    shares = sorted(r(x["resupply_share_of_volume"]) for x in live)
    return Criterion(
        "A18_B3  gross paid against net cost to the payers", True,
        "net cost over gross paid, %d cells: smallest %s, largest %s | %d "
        "cells in which the payers end better off than in the control | "
        "payers per cell %s | the rescue as a share of total flow, so that "
        "any movement in support can be read against it: %s to %s"
        % (len(ratios), ratios[:3], ratios[-3:], len(worse),
           sorted({x["payers"] for x in live}),
           shares[0] if shares else None, shares[-1] if shares else None))


def criterion_a18_b4(rows: list) -> Criterion:
    """Is more rescue always less distress. Three states, read per cell."""
    keys = sorted({(x["need_multiple"], x["seed"], x["funding"])
                   for x in rows
                   if x["mode"] == "drawdown" and x["rate"] > 0.0
                   and x["retain"] == 0.0})
    monotone, broken = [], []
    for need, seed, funding in keys:
        series = [x for x in rows if x["mode"] == "drawdown"
                  and x["need_multiple"] == need and x["seed"] == seed
                  and x["retain"] == 0.0
                  and (x["funding"] == funding or x["rate"] == 0.0)]
        series.sort(key=lambda x: x["rate"])
        counts = [x["below_close"] for x in series]
        if all(b <= a for a, b in zip(counts, counts[1:])):
            monotone.append((need, seed, funding, counts))
        else:
            broken.append((need, seed, funding, counts))
    if not broken:
        state = "first: more rescue never raised the count in any cell"
    elif not monotone:
        state = "third: no cell was monotone"
    else:
        state = "second: monotone in some cells and not in others"
    return Criterion(
        "A18_B4  is more rescue always less distress", True,
        "%s | %d of %d cells monotone | the counts against rate %s, "
        "non-monotone cells: %s"
        % (state, len(monotone), len(keys), list(RESUPPLY_RATES), broken[:6]))


def criterion_a18_b6(scan: list) -> Criterion:
    """Which readings sit on a boundary, and which do not.

    **This exists because two cells disagreed across two machines.** The code
    reproduces itself to the bit on either one; what differs between them is
    summation order, at the level of `1e-10` or smaller, and at floor `0.50`
    with rate `1.0` that is enough to move twenty-one nodes across the line.

    So the honest object is not an exemption list, it is a measurement: every
    judged cell is re-run with the opening holdings scaled by
    ``BOUNDARY_EPSILON`` and the criterion prints which ones move. A record
    that says which of its own readings are portable is worth more than one
    that quietly assumes all of them are.

    Three states, and no threshold anywhere: nothing moves, some cells move
    and are named, everything moves.
    """
    moved = [x for x in scan if x["moved"]]
    if not moved:
        state = "first: no judged cell moved, every reading here is portable"
    elif len(moved) == len(scan):
        state = "third: every cell moved, no reading here is portable"
    else:
        state = ("second: %d of %d cells sit on a boundary and the rest do not"
                 % (len(moved), len(scan)))
    named = sorted((x["need_multiple"], x["rate"], x["funding"], x["seed"],
                    x["below_close"], x["below_close_nudged"]) for x in moved)
    # The continuous half, reported beside the discrete one and separately from
    # it, because a cell whose count holds can still carry every other number
    # to only a few figures. Printed per route, since the routes differ.
    # Per field rather than per cell. A single worst number is dominated by
    # whichever field is nearest zero, which here is `frozen_close` at the
    # deepest floor: it reads `0.30`, so a movement of `0.42` in relative terms
    # is a ratio of two small numbers and not a statement about a reading.
    # A17-8 hit the same shape and refused the same kind of number.
    READ = ("below_close", "resupplied", "resupply_asked", "funded_share",
            "support_close", "volume_total", "mr_close", "gini_close",
            "payer_holdings_delta", "recapitalised")
    per_field = []
    for k in READ:
        vals = [x["relative_moves"][k] for x in scan
                if k in x.get("relative_moves", {})]
        if vals:
            per_field.append((k, r(max(vals))))
    per_field.sort(key=lambda kv: -kv[1])
    return Criterion(
        "A18_B6  which readings sit on a boundary", True,
        "perturbation %g applied to every opening holding | %s | the cells "
        "that moved, as (floor, rate, route, seed, count, count nudged): %s | "
        "**the count is the portable reading and the continuous ones are not**"
        " -- largest relative movement of each recorded quantity across the "
        "scan, worst first: %s"
        % (BOUNDARY_EPSILON, state, named[:12], per_field))


def criterion_a18_b7(rows: list) -> Criterion:
    """The three funding routes against each other, on the same cells.

    **The question is where a rescue's money comes from**, and these are its
    three answers: the lender's own book, outside the graph, or everybody.
    Read on two quantities, both printed, neither thresholded: how many nodes
    end below the line, and what the claim stock did.

    **The second is not a side effect to be mentioned in passing.** A route
    that saves nodes by creating claims has bought them, and `M/R` is the
    price. A route that is conservative has not.
    """
    cells = sorted({(x["need_multiple"], x["rate"], x["seed"])
                    for x in rows if x["mode"] == "drawdown" and x["rate"] > 0
                    and x["retain"] == 0.0})
    table, wins = [], {f: 0 for f in FUNDING_ARMS}
    for need, rate, seed in cells:
        got = {}
        for f in FUNDING_ARMS:
            m = [x for x in rows if x["mode"] == "drawdown"
                 and x["need_multiple"] == need and x["rate"] == rate
                 and x["seed"] == seed and x["funding"] == f
                 and x["retain"] == 0.0]
            if m:
                got[f] = m[0]
        if len(got) != len(FUNDING_ARMS):
            continue
        best = min(got, key=lambda f: got[f]["below_close"])
        if len({got[f]["below_close"] for f in got}) > 1:
            wins[best] += 1
        table.append((need, rate, seed,
                      {f: (got[f]["below_close"], got[f]["mr_close"])
                       for f in FUNDING_ARMS}))
    agree = sum(1 for _n, _r, _s, d in table
                if len({v[0] for v in d.values()}) == 1)
    if agree == len(table):
        state = "third: the three routes give the same count in every cell"
    elif max(wins.values(), default=0) == sum(wins.values()) and wins:
        state = ("first: one route holds the fewest below the line wherever "
                 "they differ, and it is %s"
                 % max(wins, key=lambda f: wins[f]))
    else:
        state = "second: which route holds the fewest below the line varies"
    mr = {f: sorted({x["mr_close"] for x in rows
                     if x["mode"] == "drawdown" and x["funding"] == f
                     and x["rate"] > 0 and x["retain"] == 0.0})
          for f in FUNDING_ARMS}
    return Criterion(
        "A18_B7  where the rescue's money comes from", True,
        "%d cells with all three routes | %s | cells in which they agree on "
        "the count: %d | wins on the count: %s | the claim stock each route "
        "ends at, smallest and largest over the grid: %s | first three cells "
        "as (floor, rate, seed, {route: (count, M/R)}): %s"
        % (len(table), state, agree, wins,
           {f: (v[0], v[-1]) if v else None for f, v in mr.items()},
           table[:3]))


def criterion_a18_b8(rows: list) -> Criterion:
    """What survives when the recapitalised nodes stop passing it on.

    **Two quantities, read separately and on purpose.** How many nodes end
    below the line is what the injection was for; what the claim stock does is
    what it cost. A single verdict over both would average a benefit against a
    price, and those are not the same kind of number.

    The reading declared before the run: the count is flat across most of the
    retention range and turns, if it turns at all, only near total withdrawal,
    while `M/R` climbs throughout. Three states on the count and no threshold
    anywhere; the price is printed as the ratio between its ends.
    """
    scan = [x for x in rows if x["mode"] == "drawdown"
            and x["funding"] == "issuance" and x["rate"] > 0.0]
    if not scan:
        return Criterion("A18_B8  what survives when the money is retained",
                         False, "no cells on this route")
    keys = sorted({(x["need_multiple"], x["rate"], x["seed"]) for x in scan})
    turned, flat, table = [], [], []
    for need, rate, seed in keys:
        series = sorted((x for x in scan if x["need_multiple"] == need
                         and x["rate"] == rate and x["seed"] == seed),
                        key=lambda x: x["retain"])
        if len(series) < 2:
            continue
        counts = [x["below_close"] for x in series]
        mrs = [x["mr_close"] for x in series]
        # Where, walking up the retention levels, the count first leaves the
        # value it opened at. A level and not a size: no threshold is applied
        # to how far it moved.
        first = next((series[i]["retain"] for i in range(1, len(counts))
                      if counts[i] != counts[0]), None)
        (flat if first is None else turned).append(
            (need, rate, seed, first, counts))
        table.append((need, rate, seed, counts, [r(m) for m in mrs],
                      r(mrs[-1] / mrs[0]) if mrs[0] else None))
    if not turned:
        state = ("first: the count never left its no-retention value at any "
                 "level tested, on any cell")
    elif not flat:
        state = "third: the count moved on every cell"
    else:
        levels = sorted({x[3] for x in turned})
        state = ("second: the count turns on %d of %d cells and the level it "
                 "first turns at is one of %s" % (len(turned), len(keys), levels))
    prices = sorted(x[5] for x in table if x[5] is not None)
    return Criterion(
        "A18_B8  what survives when the money is retained", True,
        "retention levels %s | %s | the claim stock at full retention over "
        "its value at none, smallest and largest: %s and %s | first three "
        "cells as (floor, rate, seed, counts, M/R, price): %s"
        % (list(RETAIN_LEVELS), state,
           prices[0] if prices else None, prices[-1] if prices else None,
           table[:3]))


def criterion_a18_b5(rows: list) -> Criterion:
    """The exit arm, printed and not judged: where the rescue money ends up."""
    out = []
    for need in sorted({x["need_multiple"] for x in rows}):
        for rate in RESUPPLY_RATES:
            cells = [x for x in rows if x["mode"] == "exit"
                     and x["need_multiple"] == need and x["rate"] == rate]
            if not cells:
                continue
            out.append((need, rate,
                        r(float(np.mean([x["frozen_close"] for x in cells]))),
                        r(float(np.mean([x["resupplied"] for x in cells]))),
                        r(float(np.mean([x["below_close"] for x in cells]))),
                        r(float(np.mean([x["support_close"] for x in cells])))))
    return Criterion(
        "A18_B5  under exit, where the rescue money ends up", True,
        "printed and not judged, because a node out of the market receives and "
        "does not spend, so this arm reports its own construction | "
        "(floor, rate, mean frozen at close, mean paid, mean below, mean "
        "support): %s" % (out,))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="one seed, writing to results/subset")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--resupply", action="store_true",
                    help="the B arm: forbearance with somebody paying for it")
    ap.add_argument("--landing", action="store_true",
                    help="the C arm: where the created claims land")
    ap.add_argument("--repay", action="store_true",
                    help="the D arm: the rescue as a loan rather than a gift")
    ap.add_argument("--park", action="store_true",
                    help="the E arm: claims that exist and do not circulate")
    ap.add_argument("--carry", action="store_true",
                    help="the F arm: who carries a forbearance programme")
    args = ap.parse_args()

    if args.plan:
        chosen = (carry_plan() if args.carry
                  else park_plan() if args.park
                  else repay_plan() if args.repay
                  else landing_plan() if args.landing
                  else resupply_plan() if args.resupply else plan())
        for k, v in chosen.items():
            print("  %-20s %s" % (k, v))
        return 0

    if args.carry:
        return _main_carry(args)
    if args.park:
        return _main_park(args)
    if args.repay:
        return _main_repay(args)
    if args.landing:
        return _main_landing(args)
    if args.resupply:
        return _main_resupply(args)

    rows = run_grid(seeds=(0,) if args.smoke else SEEDS)
    crits = [criterion_a18_1(rows), criterion_a18_2(rows), criterion_a18_6(rows),
             criterion_a18_3(rows), criterion_a18_4(rows), criterion_a18_5(rows)]
    print("stage A18: what the policy switches do to the time path\n")
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RECORD
    if args.smoke:
        out = RESULTS / "subset" / RECORD.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, two floor depths, no mechanism added",
        "f2i": F2I, "rounds": ROUNDS, "elasticity": ELASTICITY,
        "plan": plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["need_multiple"], x["policy"],
                                            x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


# ---------------------------------------------------------------------------
# A18_C: where the new claims land.
# ---------------------------------------------------------------------------

#: The two landing points, from the model rather than restated here.
LANDING = RECAP_TARGETS

#: The wage channel's strength, swept because it is the other way a created
#: claim can reach somebody who spends it. A12 sweeps this axis already; A18's
#: A and B arms hold it at one value, so the interaction has never been run.
ELASTICITIES_C: tuple[float, ...] = (0.0, 0.5, 1.0)

#: Rates. Zero is dropped because with no rescue there is nothing to land.
RATES_C: tuple[float, ...] = (1.0, 2.0, 4.0)


def landing_run(need_mult: float, rate: float, seed: int, target: str,
                elasticity: float, retain: float = 0.0) -> dict:
    """One cell. ``drawdown`` and ``issuance`` throughout, since a landing point
    only exists where claims are created.

    **The two targets differ in nothing but where the same amount arrives**, so
    a difference in any reading is attributable to that and to nothing else.
    """
    cfg = config_for("drawdown", WriteOffSpec(), "endogenous", need_mult, seed,
                     resupply_rate=rate, elasticity=elasticity)
    cfg = dataclasses.replace(cfg, resupply=ResupplySpec(
        rate=rate, funding="issuance", retain=retain, recap_target=target))
    net = Network(cfg)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)[-1]
    volume = float(np.asarray(h.total_volume, dtype=float).sum())
    return {
        "need_multiple": float(need_mult), "rate": float(rate),
        "target": target, "elasticity": float(elasticity),
        "retain": float(retain), "seed": int(seed),
        "below_close": int(net._below.sum()),
        "recap_recipients": int(net._recap_recipients.sum()),
        "recapitalised": r(float(net._recapitalised)),
        "resupplied": r(float(net._resupplied)),
        "resupply_asked": r(float(net._resupply_asked)),
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "volume_total": r(volume),
        "support_close": r(float(h.effective_support[-1])),
        "gini_close": r(_gini(hold)),
        "claims_close": r(float(hold.sum())),
    }


def landing_grid(needs=RESUPPLY_NEEDS, seeds=SEEDS) -> list:
    rows = []
    for need in needs:
        for rate in RATES_C:
            for e in ELASTICITIES_C:
                for target in LANDING:
                    for seed in seeds:
                        rows.append(landing_run(need, rate, seed, target, e))
    # Printed and not judged. Under `uniform` every live node is a recipient,
    # so `retain` there is the whole economy withdrawing rather than the
    # recapitalised set withdrawing, and the two are not the same experiment.
    for need in needs:
        for rate in RATES_C:
            for target in LANDING:
                for seed in seeds:
                    rows.append(landing_run(need, rate, seed, target, 0.5,
                                            retain=1.0))
    return rows


def landing_plan() -> dict:
    return {
        "arm": "C",
        "question": "does it matter where created claims land",
        "landing_points": list(LANDING),
        "elasticities": list(ELASTICITIES_C),
        "need_multiples": list(RESUPPLY_NEEDS),
        "rates": list(RATES_C),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "funding": "issuance throughout, drawdown throughout",
        "judged_at": "retain 0. The retain 1 rows are printed and not judged, "
                     "because under uniform every live node is a recipient",
        "rows_recorded": (len(RESUPPLY_NEEDS) * len(RATES_C)
                          * (len(ELASTICITIES_C) + 1)
                          * len(LANDING) * len(SEEDS)),
    }


def _pairs(rows: list, retain: float = 0.0) -> list:
    """(key, lenders row, uniform row) for every cell that has both."""
    out = []
    keys = sorted({(x["need_multiple"], x["rate"], x["elasticity"], x["seed"])
                   for x in rows if x["retain"] == retain})
    for k in keys:
        got = {}
        for x in rows:
            if (x["need_multiple"], x["rate"], x["elasticity"], x["seed"]) == k \
                    and x["retain"] == retain:
                got[x["target"]] = x
        if len(got) == len(LANDING):
            out.append((k, got["lenders"], got["uniform"]))
    return out


def criterion_a18_c1(rows: list) -> Criterion:
    """The control is a control: same claims created, different recipients.

    **Structural, and it is the load-bearing check of this arm.** Everything
    below reads a difference between two arms and attributes it to the landing
    point, which is only allowed if the landing point is the only thing that
    differs. So: both arms create claims, `uniform` credits every node still
    trading, `lenders` credits fewer than that.
    """
    # **The check applies where claims were created and nowhere else.** At the
    # shallow floor the nodes below the line already hold more than any rate on
    # this grid tops them up to, so the rescue never fires and nothing is
    # created; that is the inert cell A18_B2 already reports, and it is a third
    # state rather than a failure. An earlier shape of this criterion failed
    # the whole arm on it, which is what rule 23 is about.
    bad, inert = [], []
    for (k, a, b) in _pairs(rows):
        if a["recapitalised"] <= 0.0 and b["recapitalised"] <= 0.0:
            inert.append(k)
            continue
        if b["recap_recipients"] <= a["recap_recipients"]:
            bad.append(("uniform did not reach more nodes", k,
                        a["recap_recipients"], b["recap_recipients"]))
    live = [x for x in rows if x["recapitalised"] > 0.0]
    lend = sorted({x["recap_recipients"] for x in live
                   if x["target"] == "lenders"})
    uni = sorted({x["recap_recipients"] for x in live
                  if x["target"] == "uniform"})
    return Criterion(
        "A18_C1  the two arms differ in the landing point and nothing else",
        not bad,
        "on the pairs where claims were created, recipients under lenders %s "
        "and under uniform %s | %d pairs inert because the rescue never fired, "
        "at floor depths %s | %s"
        % (lend[:6] + (["..."] if len(lend) > 6 else []), uni, len(inert),
           sorted({k[0] for k in inert}),
           "all clear" if not bad else "PROBLEMS: %s" % (bad[:5],)))


def criterion_a18_c2(rows: list) -> Criterion:
    """Does the landing point change the count below the line.

    **Read on the count, which is an integer, so there is no line to draw.**
    The continuous readings are printed by C3 rather than judged, because
    telling a real difference from this model's own numerical resolution needs
    that resolution, and A18_B6 is where it is measured.

    Three states, declared before the run: the landing point changes the count
    in every pair, in some, or in none. **The third is a real branch**, and if
    it is where this lands then a reading of the form "the claims stopped where
    they landed" is not about the landing point.
    """
    pairs = _pairs(rows)
    diff = [(k, a["below_close"], b["below_close"]) for k, a, b in pairs
            if a["below_close"] != b["below_close"]]
    if not pairs:
        return Criterion("A18_C2  does the landing point change the count",
                         False, "no complete pairs")
    if len(diff) == len(pairs):
        state = "first: it changes the count in every pair"
    elif not diff:
        state = ("third: it changes the count in no pair, so where the claims "
                 "land is not what decides whether they circulate")
    else:
        state = ("second: it changes the count in %d of %d pairs"
                 % (len(diff), len(pairs)))
    return Criterion(
        "A18_C2  does the landing point change the count", True,
        "%s | %d pairs | the pairs that differ, as ((floor, rate, elasticity, "
        "seed), lenders, uniform): %s"
        % (state, len(pairs), sorted(diff)[:8]))


def criterion_a18_c3(rows: list) -> Criterion:
    """The continuous readings across the pair, printed and not judged.

    Judging these needs a resolution, and this model's resolution on these
    fields is measured in A18_B6 rather than assumed here. What is printed is
    the relative gap between the two arms, field by field, so it can be read
    against those figures.
    """
    pairs = _pairs(rows)
    fields = ("volume_total", "mr_close", "support_close", "gini_close",
              "resupplied", "recapitalised")
    out = []
    for f in fields:
        gaps = []
        for k, a, b in pairs:
            if a[f]:
                gaps.append(r(abs(a[f] - b[f]) / abs(a[f])))
        if gaps:
            gaps.sort()
            out.append((f, gaps[0], gaps[len(gaps) // 2], gaps[-1]))
    return Criterion(
        "A18_C3  the continuous readings across the pair", True,
        "relative gap between landing on the lenders and landing on everyone, "
        "as (field, smallest, median, largest) over %d pairs, to be read "
        "against A18_B6's resolution figures for the same fields: %s"
        % (len(pairs), out))


def criterion_a18_c4(rows: list) -> Criterion:
    """Does the wage channel's strength change whether the injection lands
    somewhere that spends it.

    The other route by which a created claim reaches somebody who spends it,
    and the one A18's other arms hold fixed. Three states on the count.
    """
    keys = sorted({(x["need_multiple"], x["rate"], x["target"], x["seed"])
                   for x in rows if x["retain"] == 0.0})
    moved, flat = [], []
    for need, rate, target, seed in keys:
        series = sorted((x for x in rows if x["retain"] == 0.0
                         and x["need_multiple"] == need and x["rate"] == rate
                         and x["target"] == target and x["seed"] == seed),
                        key=lambda x: x["elasticity"])
        if len(series) < 2:
            continue
        counts = [x["below_close"] for x in series]
        (flat if len(set(counts)) == 1 else moved).append(
            (need, rate, target, seed, counts))
    if not moved:
        state = "third: the count is the same at every elasticity, everywhere"
    elif not flat:
        state = "first: the count moves with elasticity in every cell"
    else:
        state = ("second: it moves in %d of %d cells"
                 % (len(moved), len(moved) + len(flat)))
    return Criterion(
        "A18_C4  does the wage channel's strength change the count", True,
        "elasticities %s | %s | cells where it moves, as (floor, rate, target, "
        "seed, counts): %s" % (list(ELASTICITIES_C), state, sorted(moved)[:8]))


def criterion_a18_c5(rows: list) -> Criterion:
    """The full-retention rows, printed and not judged, and why not judged."""
    out = []
    for k, a, b in _pairs(rows, retain=1.0):
        out.append((k, (a["below_close"], a["mr_close"], a["volume_total"]),
                    (b["below_close"], b["mr_close"], b["volume_total"])))
    return Criterion(
        "A18_C5  full retention under each landing point", True,
        "printed and not judged: under `uniform` every node still trading is a "
        "recipient, so retention there is the whole economy withdrawing rather "
        "than the recapitalised set withdrawing, and the two are not the same "
        "experiment | (floor, rate, elasticity, seed), then (count, M/R, "
        "volume) for lenders and for uniform: %s" % (out[:6],))


# ---------------------------------------------------------------------------
# A18_D: the rescue as a loan rather than a gift.
# ---------------------------------------------------------------------------

#: Share of the outstanding balance repaid each round. Zero is the gift, which
#: is what every earlier arm ran.
#:
#: **The levels bracket what a probe found before this was written.** The
#: recycling effect is already most of the way in at `0.05`, and the count
#: below the line is worse at `1.00` than at `0.20`, so the interesting region
#: is the middle and the endpoints are there to show it is a middle.
REPAY_LEVELS: tuple[float, ...] = (0.0, 0.05, 0.20, 0.50, 1.00)

#: Rates for the judged arm. The shallow floor is inert at the low rate and
#: that cell is kept rather than dropped: it is the third state.
RATES_D: tuple[float, ...] = (1.0, 2.0, 4.0)

#: The `exit` cells exist for one reason: to reach the branch where a debtor
#: owes and every one of its creditors has left circulation.
#:
#: **Under `drawdown` that branch cannot fire at all**, and not because of
#: anything about this carrier: `_alive` is set false only in the exit rule, so
#: under `drawdown` every node is a live counterparty forever. A probe that ran
#: only `drawdown` reported the branch as never triggered, which was a
#: statement about the mode and was read as a statement about the graph.
RATES_D_EXIT: tuple[float, ...] = (2.0, 4.0)
REPAY_LEVELS_EXIT: tuple[float, ...] = (0.0, 0.20, 1.00)


def repay_run(mode: str, need_mult: float, rate: float, seed: int,
              repay: float, funding: str = "creditors",
              retain: float = 0.0) -> dict:
    """One cell of the loan arm."""
    cfg = config_for(mode, WriteOffSpec(), "endogenous", need_mult, seed,
                     resupply_rate=rate)
    cfg = dataclasses.replace(cfg, resupply=ResupplySpec(
        rate=rate, funding=funding, repay=repay, retain=retain))
    net = Network(cfg)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)[-1]
    below = _below_set(net, mode)
    lent = float(net._resupplied)
    back = float(net._repaid)
    arrears = float(net._resupply_ledger.sum())
    return {
        "mode": mode, "need_multiple": float(need_mult), "rate": float(rate),
        "repay": float(repay), "funding": funding, "retain": float(retain),
        "seed": int(seed),
        "below_close": int(below.sum()),
        "lent": r(lent), "repaid": r(back), "arrears": r(arrears),
        # The identity the ledger has to satisfy, carried as a number rather
        # than asserted away, so D1 can read it instead of trusting it.
        "ledger_residual": r(lent - back - arrears),
        "repay_blocked": int(net._repay_blocked),
        "resupply_asked": r(float(net._resupply_asked)),
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "volume_total": r(float(np.asarray(h.total_volume, dtype=float).sum())),
        "support_close": r(float(h.effective_support[-1])),
        "gini_close": r(_gini(hold)),
    }


def repay_grid(needs=RESUPPLY_NEEDS, seeds=SEEDS) -> list:
    rows = []
    for need in needs:
        for rate in RATES_D:
            for rp in REPAY_LEVELS:
                for seed in seeds:
                    rows.append(repay_run("drawdown", need, rate, seed, rp))
    # Printed and not judged. Their reason for existing is the blocked branch.
    for need in needs:
        for rate in RATES_D_EXIT:
            for rp in REPAY_LEVELS_EXIT:
                for seed in seeds:
                    rows.append(repay_run("exit", need, rate, seed, rp))
    # The cell A18_B named as the closest to a real episode, now with the
    # rescue repayable. Printed beside the rest.
    for rp in (0.0, 0.20, 1.00):
        for seed in seeds:
            rows.append(repay_run("drawdown", 0.50, 2.0, seed, rp,
                                  funding="issuance", retain=1.0))
    return rows


def repay_plan() -> dict:
    return {
        "arm": "D",
        "question": "what changes when the rescue has to be paid back",
        "repay_levels": list(REPAY_LEVELS),
        "need_multiples": list(RESUPPLY_NEEDS),
        "rates": list(RATES_D),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "judged_on": "drawdown with creditors funding. The exit cells and the "
                     "retained-issuance cells are printed and carry no "
                     "criterion",
        "exit_cells_exist_for": "the branch where a debtor owes and every one "
                                "of its creditors has left circulation, which "
                                "drawdown cannot reach because `_alive` is "
                                "only set false by the exit rule",
        "rows_recorded": (len(RESUPPLY_NEEDS) * len(RATES_D)
                          * len(REPAY_LEVELS) * len(SEEDS)
                          + len(RESUPPLY_NEEDS) * len(RATES_D_EXIT)
                          * len(REPAY_LEVELS_EXIT) * len(SEEDS)
                          + 3 * len(SEEDS)),
    }


def _judged_d(rows: list) -> list:
    return [x for x in rows if x["mode"] == "drawdown"
            and x["funding"] == "creditors"]


def criterion_a18_d1(rows: list) -> Criterion:
    """The ledger closes: what was lent, less what came back, is what is owed.

    **An identity read off a printed number rather than asserted away.** If it
    does not hold, the repayment arithmetic is losing or inventing claims
    somewhere the round's conservation guard cannot see, because that guard
    watches the holdings total and this watches the book.
    """
    worst = max(rows, key=lambda x: abs(x["ledger_residual"]))
    bad = [x for x in rows if abs(x["ledger_residual"]) > 1e-6]
    return Criterion(
        "A18_D1  the ledger closes", not bad,
        "lent minus repaid minus outstanding, over %d rows: largest absolute "
        "residual %g at (%s, floor %s, rate %s, repay %s, seed %s) | %s"
        % (len(rows), abs(worst["ledger_residual"]), worst["mode"],
           worst["need_multiple"], worst["rate"], worst["repay"],
           worst["seed"],
           "all clear" if not bad else "%d row(s) over 1e-6" % len(bad)))


def criterion_a18_d2(rows: list) -> Criterion:
    """A loan against a gift, on the count and on how much rescue got done.

    Three states on the count, read against the same cell at ``repay = 0``.
    **The second quantity is the one that explains the first if it moves**: the
    same lenders' stock can fund more rescue when it comes back, so the rescue
    delivered is not held fixed between the arms and that is the mechanism
    rather than a confound.
    """
    judged = _judged_d(rows)
    gift = {(x["need_multiple"], x["rate"], x["seed"]): x
            for x in judged if x["repay"] == 0.0}
    down, up, flat, lent_up = [], [], [], 0
    for x in judged:
        if x["repay"] == 0.0:
            continue
        g = gift.get((x["need_multiple"], x["rate"], x["seed"]))
        if g is None:
            continue
        d = x["below_close"] - g["below_close"]
        (down if d < 0 else up if d > 0 else flat).append(
            (x["need_multiple"], x["rate"], x["repay"], x["seed"], d))
        if x["lent"] > g["lent"]:
            lent_up += 1
    n = len(down) + len(up) + len(flat)
    if down and not up:
        state = "first: repayable never leaves more below the line than a gift"
    elif up and not down:
        state = "third: repayable never leaves fewer"
    else:
        state = ("second: repayable leaves fewer below the line in %d cells "
                 "and more in %d" % (len(down), len(up)))
    ratios = sorted(r(x["lent"] / gift[(x["need_multiple"], x["rate"],
                                        x["seed"])]["lent"])
                    for x in judged if x["repay"] > 0.0
                    and gift.get((x["need_multiple"], x["rate"], x["seed"]))
                    and gift[(x["need_multiple"], x["rate"], x["seed"])]["lent"] > 0)
    return Criterion(
        "A18_D2  a loan against a gift", True,
        "%s | %d comparisons, %d down, %d level, %d up | rescue delivered in "
        "%d of them exceeds the gift arm's, and the ratio runs %s to %s with "
        "median %s"
        % (state, n, len(down), len(flat), len(up), lent_up,
           ratios[0] if ratios else None, ratios[-1] if ratios else None,
           ratios[len(ratios) // 2] if ratios else None))


def criterion_a18_d3(rows: list) -> Criterion:
    """Is the best repayment rate one of the ends, or inside.

    **Read as a position on the grid, not as a size.** For each cell the rate
    with the fewest below the line is named; the criterion is which of the
    three states the collection of those positions falls into, and no
    difference is measured against any threshold.
    """
    judged = _judged_d(rows)
    keys = sorted({(x["need_multiple"], x["rate"], x["seed"]) for x in judged})
    at_zero, at_one, inside = [], [], []
    for k in keys:
        series = sorted((x for x in judged
                         if (x["need_multiple"], x["rate"], x["seed"]) == k),
                        key=lambda x: x["repay"])
        if len(series) < 3:
            continue
        best = min(series, key=lambda x: x["below_close"])["repay"]
        row = (k, best, [x["below_close"] for x in series])
        (at_zero if best == series[0]["repay"]
         else at_one if best == series[-1]["repay"] else inside).append(row)
    total = len(at_zero) + len(at_one) + len(inside)
    if inside and not at_one:
        state = ("first: the best repayment rate is never the largest one on "
                 "the grid, and it is strictly inside in %d cells" % len(inside))
    elif not inside:
        state = "third: the best rate is always an endpoint"
    else:
        state = ("second: strictly inside in %d cells, at zero in %d, at the "
                 "largest in %d" % (len(inside), len(at_zero), len(at_one)))
    return Criterion(
        "A18_D3  where the best repayment rate sits", True,
        "levels %s | %s | %d cells | inside cells, as ((floor, rate, seed), "
        "best, counts): %s"
        % (list(REPAY_LEVELS), state, total, inside[:8]))


def criterion_a18_d4(rows: list) -> Criterion:
    """Does the outstanding balance clear, and does that depend on the floor."""
    judged = [x for x in _judged_d(rows) if x["repay"] > 0.0]
    out = []
    for need in sorted({x["need_multiple"] for x in judged}):
        g = [x for x in judged if x["need_multiple"] == need]
        lent = [x["lent"] for x in g if x["lent"] > 0]
        left = [r(x["arrears"] / x["lent"]) for x in g if x["lent"] > 0]
        if left:
            left.sort()
            out.append((need, left[0], left[len(left) // 2], left[-1]))
    shares = [o[2] for o in out]
    if shares and max(shares) < min(shares) * 2:
        state = "third: the share left outstanding does not separate by floor"
    else:
        state = ("first: the share left outstanding separates by floor depth"
                 if out else "no cells")
    return Criterion(
        "A18_D4  does the balance clear", True,
        "%s | outstanding over lent, as (floor, smallest, median, largest): %s"
        % (state, out))


def criterion_a18_d5(rows: list) -> Criterion:
    """The exit cells, printed and not judged, and the branch they exist for."""
    ex = [x for x in rows if x["mode"] == "exit"]
    fired = [x for x in ex if x["repay_blocked"] > 0]
    dr = [x for x in rows if x["mode"] == "drawdown"]
    dr_fired = [x for x in dr if x["repay_blocked"] > 0]
    summary = []
    for need in sorted({x["need_multiple"] for x in ex}):
        for rp in sorted({x["repay"] for x in ex}):
            g = [x for x in ex if x["need_multiple"] == need and x["repay"] == rp]
            if g:
                summary.append((need, rp,
                                r(float(np.mean([x["below_close"] for x in g]))),
                                r(float(np.mean([x["arrears"] for x in g]))),
                                int(np.sum([x["repay_blocked"] for x in g]))))
    return Criterion(
        "A18_D5  a debtor whose creditors have left", True,
        "printed and not judged | the branch fired in %d of %d exit rows and "
        "in %d of %d drawdown rows | **two different reasons, and only the "
        "first is about the mode**: under drawdown `_alive` is never set false "
        "at all, so every creditor is live forever and the branch cannot fire; "
        "under exit it can, and does not, because the creditors are by "
        "construction the solvent in-neighbours of whoever was below the line, "
        "so they are the last nodes to leave. A count of zero here is a "
        "statement about who lends, not about how many rows were run | "
        "(floor, repay, mean count, mean outstanding, blocked): %s"
        % (len(fired), len(ex), len(dr_fired), len(dr), summary))


def criterion_a18_d6(rows: list) -> Criterion:
    """The retained-issuance cell with the rescue repayable. Printed."""
    g = [x for x in rows if x["funding"] == "issuance"]
    out = []
    for rp in sorted({x["repay"] for x in g}):
        cells = [x for x in g if x["repay"] == rp]
        if cells:
            out.append((rp,
                        r(float(np.mean([x["below_close"] for x in cells]))),
                        r(float(np.mean([x["mr_close"] for x in cells]))),
                        r(float(np.mean([x["lent"] for x in cells]))),
                        r(float(np.mean([x["arrears"] for x in cells])))))
    return Criterion(
        "A18_D6  the retained-issuance cell, with the rescue repayable", True,
        "printed and not judged | floor 0.50, rate 2.0, issuance funding, full "
        "retention | (repay, mean count, mean M/R, mean lent, mean "
        "outstanding): %s" % (out,))


# ---------------------------------------------------------------------------
# A18_E: claims that exist and do not circulate.
# ---------------------------------------------------------------------------

#: Share of a node's holdings moved out of reach each round.
#:
#: **The levels bracket a measured span rather than a round grid.** At `0.05`
#: most of the stock is already parked by the end of the run and the circulating
#: aggregate is down to a quarter of its opening; by `0.50` it is down to a
#: sixteenth. Zero is the arm every earlier station ran.
PARK_LEVELS: tuple[float, ...] = (0.0, 0.05, 0.20, 0.50)

#: Parking rates E5 measures the repayment multiplier at. Three, because the
#: probe that motivated the criterion found the sign is not monotone in this
#: rate: it is positive with no parking, negative at `0.20`, and positive again
#: at `0.50` on the shallower floor, where so little circulates that the
#: repayment flow is itself a large share of what is left.
PARK_MULTIPLIER_LEVELS: tuple[float, ...] = (0.0, 0.20, 0.50)

#: Retention levels this arm is read against. **The comparison is the point**:
#: retention was the closest thing the model had to this and the question is
#: whether it is the same thing.
RETAIN_AGAINST: tuple[float, ...] = (0.0, 0.5, 1.0)


def park_run(need_mult: float, rate: float, seed: int, park: float,
             retain: float = 0.0, target: str = "financial",
             repay: float = 0.0, funding: str = "issuance") -> dict:
    """One cell. ``issuance`` funding, because a stock has to be created before
    a question about where it sits means anything."""
    cfg = config_for("drawdown", WriteOffSpec(), "endogenous", need_mult, seed,
                     resupply_rate=rate)
    cfg = dataclasses.replace(
        cfg,
        resupply=ResupplySpec(rate=rate, funding=funding, retain=retain,
                              repay=repay),
        park=ParkSpec(rate=park, target=target))
    net = Network(cfg)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)[-1]
    circulating = float(np.asarray(h.total_claims, dtype=float)[-1])
    parked = float(np.asarray(h.parked, dtype=float)[-1])
    return {
        "need_multiple": float(need_mult), "rate": float(rate),
        "park": float(park), "retain": float(retain), "target": target,
        "repay": float(repay), "funding": funding, "seed": int(seed),
        "repaid": r(float(net._repaid)),
        "below_close": int(net._below.sum()),
        # The three that carry this arm: what exists, what of it circulates,
        # and what of it does not. Recorded separately rather than as a ratio,
        # because a ratio of two of them hides which one moved.
        "circulating_close": r(circulating),
        "parked_close": r(parked),
        "stock_close": r(circulating + parked),
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "volume_total": r(float(np.asarray(h.total_volume, dtype=float).sum())),
        "support_close": r(float(h.effective_support[-1])),
        "gini_close": r(_gini(hold)),
        "lent": r(float(net._resupplied)),
        "resupply_asked": r(float(net._resupply_asked)),
    }


def park_grid(needs=RESUPPLY_NEEDS, seeds=SEEDS) -> list:
    rows = []
    for need in needs:
        for rate in (1.0, 2.0, 4.0):
            for pk in PARK_LEVELS:
                for seed in seeds:
                    rows.append(park_run(need, rate, seed, pk))
    # The comparison arm. Retention at three strengths with no parking, so the
    # two mechanisms are read on the same cells.
    for need in needs:
        for rate in (1.0, 2.0, 4.0):
            for rt in RETAIN_AGAINST:
                if rt == 0.0:
                    continue  # already there as park 0
                for seed in seeds:
                    rows.append(park_run(need, rate, seed, 0.0, retain=rt))
    # Who parks. Printed beside the financial-layer default.
    for target in PARK_TARGETS:
        if target == "financial":
            continue
        for seed in seeds:
            rows.append(park_run(0.50, 2.0, seed, 0.20, target=target))
    # E5's sub-grid: repayment crossed with parking. **This is what the switch
    # was built for.** A18_D measured the output response to repayment and got
    # a positive number, because the creditor received it and lent it again;
    # the episode that measurement was pointed at has the payments leaving the
    # economy. Parking is what lets them leave.
    for need in (0.20, 0.50):
        for pk in PARK_MULTIPLIER_LEVELS:
            for rp in REPAY_LEVELS:
                for seed in seeds:
                    # **`creditors` funding, not `issuance`.** The quantity is
                    # the output response to repayment, and under `issuance`
                    # the recapitalisation creates claims in the same rounds,
                    # so the two channels are tangled and the number measures
                    # neither. The first version of this sub-grid made that
                    # mistake and read multipliers of minus twenty.
                    rows.append(park_run(need, 2.0, seed, pk, repay=rp,
                                         funding="creditors"))
    return rows


def park_plan() -> dict:
    return {
        "arm": "E",
        "question": "can a claim exist, be owned, and not be in the money that "
                    "circulates",
        "park_levels": list(PARK_LEVELS),
        "retain_compared_at": list(RETAIN_AGAINST),
        "park_targets": list(PARK_TARGETS),
        "need_multiples": list(RESUPPLY_NEEDS),
        "rates": [1.0, 2.0, 4.0],
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "funding": "issuance throughout, drawdown throughout",
        "why_it_exists": "two separate correspondences ended on the same limit: "
                         "retaining and holding something outside the trading "
                         "system are one state when there is no outside",
        "rows_recorded": (len(RESUPPLY_NEEDS) * 3 * len(PARK_LEVELS) * len(SEEDS)
                          + len(RESUPPLY_NEEDS) * 3 * 2 * len(SEEDS)
                          + 2 * len(SEEDS)
                          + 2 * len(PARK_MULTIPLIER_LEVELS) * len(REPAY_LEVELS)
                          * len(SEEDS)),
    }


def criterion_a18_e1(rows: list) -> Criterion:
    """Does the mechanism produce a stock that exists and does not circulate.

    **The discriminating check, and it is structural.** Retention was the
    nearest thing the model had, so the question is whether parking is a second
    name for it. Under retention the parked stock is zero by construction and
    the whole stock circulates; under parking the two separate. If they did not,
    this switch would be a synonym and should not exist.
    """
    parked_arm = [x for x in rows if x["park"] > 0.0]
    retain_arm = [x for x in rows if x["park"] == 0.0 and x["retain"] > 0.0]
    bad = [x for x in retain_arm if x["parked_close"] != 0.0]
    split = [x for x in parked_arm if x["parked_close"] > 0.0]
    if not parked_arm:
        return Criterion("A18_E1  a stock that does not circulate", False,
                         "no parking cells")
    return Criterion(
        "A18_E1  a stock that does not circulate", not bad,
        "under retention the parked stock is zero in %d of %d cells, which is "
        "by construction and is the point | under parking it is above zero in "
        "%d of %d | %s"
        % (len(retain_arm) - len(bad), len(retain_arm), len(split),
           len(parked_arm),
           "all clear" if not bad else "RETENTION PARKED SOMETHING: %s"
           % (bad[:4],)))


def criterion_a18_e2(rows: list) -> Criterion:
    """What each mechanism does to the two halves of the stock, side by side.

    **Two quantities and no threshold on either.** Retention and parking are
    compared on the same cells at the strengths each has; the reading declared
    before the run is that they move the stock similarly and the circulating
    half in opposite directions, and if they do not then parking adds nothing.
    """
    out = []
    keys = sorted({(x["need_multiple"], x["rate"]) for x in rows})
    for need, rate in keys:
        g = [x for x in rows if x["need_multiple"] == need and x["rate"] == rate]
        def mean(sel, k):
            v = [x[k] for x in sel]
            return r(float(np.mean(v))) if v else None
        base = [x for x in g if x["park"] == 0.0 and x["retain"] == 0.0]
        ret = [x for x in g if x["park"] == 0.0 and x["retain"] == 1.0]
        pk = [x for x in g if x["park"] == max(PARK_LEVELS)]
        out.append((need, rate,
                    (mean(base, "stock_close"), mean(base, "circulating_close")),
                    (mean(ret, "stock_close"), mean(ret, "circulating_close")),
                    (mean(pk, "stock_close"), mean(pk, "circulating_close"))))
    opposite = sum(1 for (_n, _r, b, rt, pkv) in out
                   if None not in (b[1], rt[1], pkv[1])
                   and (rt[1] - b[1]) * (pkv[1] - b[1]) < 0)
    if opposite == len(out):
        state = ("first: in every cell retention and parking move the "
                 "circulating half in opposite directions")
    elif opposite == 0:
        state = "third: they never move it in opposite directions"
    else:
        state = ("second: opposite in %d of %d cells" % (opposite, len(out)))
    return Criterion(
        "A18_E2  the two halves under each mechanism", True,
        "%s | (floor, rate) then (stock, circulating) for off, retention 1.0, "
        "and parking at %.2f: %s"
        % (state, max(PARK_LEVELS), out[:6]))


def criterion_a18_e3(rows: list) -> Criterion:
    """How far the circulating half can be pushed, printed against the stock."""
    out = []
    for pk in PARK_LEVELS:
        g = [x for x in rows if x["park"] == pk and x["retain"] == 0.0
             and x["target"] == "financial"]
        if g:
            out.append((pk,
                        r(float(np.mean([x["stock_close"] for x in g]))),
                        r(float(np.mean([x["circulating_close"] for x in g]))),
                        r(float(np.mean([x["parked_close"] for x in g]))),
                        r(float(np.mean([x["below_close"] for x in g]))),
                        r(float(np.mean([x["volume_total"] for x in g])))))
    return Criterion(
        "A18_E3  how far the circulating half moves", True,
        "(park, mean stock, mean circulating, mean parked, mean count below, "
        "mean flow), averaged over every floor, rate and seed: %s" % (out,))


def criterion_a18_e4(rows: list) -> Criterion:
    """Who parks. Printed and not judged: the sets are different sizes."""
    out = []
    for target in PARK_TARGETS:
        # **Every axis of the cell, not the three that name it.** The E5
        # sub-grid also sits at floor 0.50, rate 2.0, park 0.20 and the default
        # target, and differs only in `repay` and `funding`; without those two
        # clauses twenty-five of its rows land in this bucket and the
        # `financial` figure becomes a blend of two arms. Measured before the
        # fix: `financial` read a stock of 2044.7 against the 3688.5 it reads
        # when the bucket contains what it says it contains.
        g = [x for x in rows if x["target"] == target and x["park"] == 0.20
             and x["need_multiple"] == 0.50 and x["rate"] == 2.0
             and x["repay"] == 0.0 and x["funding"] == "issuance"]
        if g:
            out.append((target,
                        r(float(np.mean([x["stock_close"] for x in g]))),
                        r(float(np.mean([x["circulating_close"] for x in g]))),
                        r(float(np.mean([x["below_close"] for x in g]))),
                        r(float(np.mean([x["volume_total"] for x in g])))))
    return Criterion(
        "A18_E4  who parks", True,
        "printed and not judged, because the three sets are different sizes and "
        "a difference between them is partly that | floor 0.50, rate 2.0, park "
        "0.20 | (target, stock, circulating, count below, flow): %s" % (out,))


def criterion_a18_e5(rows: list) -> Criterion:
    """Output per unit repaid, at each parking rate.

    **The quantity is a multiplier and it is in the units the argument is
    conducted in**: change in total flow per unit of repayment. A18_D measured
    it at **+0.56 to +1.50** and that number is not wrong, it is the answer for
    a creditor who lends the money out again. Parking is what lets the payment
    leave the trading system, which is the case the argument is about.

    **The reading declared before the run is the sign and only the sign.** No
    threshold is applied to the size, and the size is printed.
    """
    grid = [x for x in rows if x.get("funding") == "creditors"]
    out, signs = [], set()
    for need in (0.20, 0.50):
        for pk in PARK_MULTIPLIER_LEVELS:
            base = [x for x in grid if x["need_multiple"] == need
                    and x["park"] == pk and x["repay"] == 0.0]
            if not base:
                continue
            v0 = float(np.mean([x["volume_total"] for x in base]))
            r0 = float(np.mean([x["repaid"] for x in base]))
            for rp in REPAY_LEVELS:
                if rp == 0.0:
                    continue
                g = [x for x in grid if x["need_multiple"] == need
                     and x["park"] == pk and x["repay"] == rp]
                if not g:
                    continue
                v = float(np.mean([x["volume_total"] for x in g]))
                rr = float(np.mean([x["repaid"] for x in g]))
                if rr <= r0:
                    continue
                m = r((v - v0) / (rr - r0))
                out.append((need, pk, rp, m))
                signs.add((pk, m > 0))
    by_park = {}
    for need, pk, rp, m in out:
        by_park.setdefault(pk, []).append(m)
    pos = sorted(pk for pk, v in by_park.items() if all(x > 0 for x in v))
    neg = sorted(pk for pk, v in by_park.items() if all(x < 0 for x in v))
    mixed = sorted(pk for pk, v in by_park.items()
                   if pk not in pos and pk not in neg)
    if neg and pos:
        state = ("first: the sign depends on the parking rate, positive "
                 "throughout at %s and negative throughout at %s%s"
                 % (pos, neg, ", mixed at %s" % mixed if mixed else ""))
    elif not neg and not mixed:
        state = ("third: positive at every parking rate, so letting the "
                 "payment leave the trading system changed nothing")
    elif not pos and not mixed:
        state = "second: negative at every parking rate"
    else:
        state = ("second: no parking rate has one sign throughout; positive "
                 "at %s, negative at %s, mixed at %s" % (pos, neg, mixed))
    ranges = {pk: (r(min(v)), r(max(v))) for pk, v in sorted(by_park.items())}
    return Criterion(
        "A18_E5  output per unit repaid, at each parking rate", True,
        "%s | ranges by parking rate: %s | every cell as (floor, park, repay, "
        "multiplier): %s" % (state, ranges, out[:12]))


# ---------------------------------------------------------------------------
# A18_F: who carries the forbearance, at a parking rate that is not extreme.
# ---------------------------------------------------------------------------

#: Parking rates for this arm, **three orders below A18_E's**.
#:
#: **Measured before it was chosen, and the measurement changed the design.**
#: A18_E's grid starts at `0.05`, and at `0.05` the parked stock is already
#: ninety-two per cent of everything outstanding. Any external share worth
#: comparing against sits far below that: the parked share passes a third at
#: about `0.002`. A grid whose lowest rung is past the region of interest is a
#: grid that can only report saturation, so this arm has its own.
PARK_FINE: tuple[float, ...] = (0.0, 0.001, 0.002, 0.005, 0.010, 0.020)

#: The axis this arm exists for: who carries a forbearance programme.
#:
#: ``creditors``   the lenders fund it from their own book
#: ``issuance``    an authority creates claims and hands them to the lenders
#:
#: Both with the same parking behaviour, so the comparison is the funding route
#: and nothing else.
FUNDING_F: tuple[str, ...] = ("creditors", "issuance")


#: Rounds the parked share is read at, so the published table is indexed by
#: rate and horizon rather than by rate alone. The last is the run's own end.
PARK_HORIZONS: tuple[int, ...] = (50, 100, 150, 200, 250, 299)


def _share_at(h, t_round: int) -> float:
    """Parked stock over total stock at one round."""
    circ = float(np.asarray(h.total_claims, dtype=float)[t_round])
    pk = float(np.asarray(h.parked, dtype=float)[t_round])
    return pk / (circ + pk) if circ + pk > 0 else 0.0


def carry_run(need_mult: float, rate: float, seed: int, park: float,
              funding: str) -> dict:
    cfg = config_for("drawdown", WriteOffSpec(), "endogenous", need_mult, seed,
                     resupply_rate=rate)
    cfg = dataclasses.replace(
        cfg, resupply=ResupplySpec(rate=rate, funding=funding),
        park=ParkSpec(rate=park, target="financial"))
    net = Network(cfg)
    h = net.run()
    hold = np.asarray(h.holdings, dtype=float)[-1]
    circ = float(np.asarray(h.total_claims, dtype=float)[-1])
    pk = float(np.asarray(h.parked, dtype=float)[-1])
    return {
        "need_multiple": float(need_mult), "rate": float(rate),
        "park": float(park), "funding": funding, "seed": int(seed),
        "below_close": int(net._below.sum()),
        "circulating_close": r(circ), "parked_close": r(pk),
        "stock_close": r(circ + pk),
        # The translation table this arm publishes: where a given external
        # share of assets sitting outside the trading system lands on the dial.
        #
        # **Read at several horizons off the same run, and that is not a
        # refinement, it is a correction.** Parking is one way, so the parked
        # stock only accumulates and its share climbs towards one without
        # settling. There is no steady state to quote. A share is therefore a
        # property of the rate and the horizon together, and a table indexed by
        # the rate alone would invite a reader to land an external figure on it
        # without matching the second. Measured: the same rate reads 0.18 at a
        # hundred and fifty rounds and 0.47 at six hundred.
        "parked_share": r(pk / (circ + pk)) if circ + pk > 0 else 0.0,
        "parked_share_at": {
            str(q): r(_share_at(h, q)) for q in PARK_HORIZONS
        },
        "mr_close": r(float(np.asarray(h.total_ratio, dtype=float)[-1])),
        "volume_total": r(float(np.asarray(h.total_volume, dtype=float).sum())),
        "support_close": r(float(h.effective_support[-1])),
        "gini_close": r(_gini(hold)),
        "lent": r(float(net._resupplied)),
    }


def carry_grid(needs=(0.20, 0.50), seeds=SEEDS) -> list:
    return [carry_run(need, 2.0, seed, pk, f)
            for need in needs for pk in PARK_FINE
            for f in FUNDING_F for seed in seeds]


def carry_plan() -> dict:
    return {
        "arm": "F",
        "question": "who carries a forbearance programme, at a parking rate "
                    "that is not saturated",
        "funding_routes": list(FUNDING_F),
        "park_rates": list(PARK_FINE),
        "need_multiples": [0.20, 0.50],
        "rate": 2.0,
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "why_the_fine_grid": "A18_E's lowest parking rate already leaves "
                             "ninety-two per cent of the stock parked, so it "
                             "can only report saturation. The parked share "
                             "passes a third at about 0.002",
        "rows_recorded": (2 * len(PARK_FINE) * len(FUNDING_F) * len(SEEDS)),
    }


def _carry_pairs(rows: list) -> list:
    out = []
    keys = sorted({(x["need_multiple"], x["park"], x["seed"]) for x in rows})
    for k in keys:
        got = {x["funding"]: x for x in rows
               if (x["need_multiple"], x["park"], x["seed"]) == k}
        if len(got) == len(FUNDING_F):
            out.append((k, got["creditors"], got["issuance"]))
    return out


def criterion_a18_f1(rows: list) -> Criterion:
    """The dial is monotone and the grid brackets the region of interest.

    **A calibration check that calibrates nothing.** It asks whether the parked
    share rises with the parking rate and whether the grid spans a share of one
    third, so that an external figure has somewhere to land. No external figure
    is used to set any parameter here.
    """
    bad, spans = [], []
    for need in sorted({x["need_multiple"] for x in rows}):
        for f in FUNDING_F:
            series = sorted((x for x in rows if x["need_multiple"] == need
                             and x["funding"] == f),
                            key=lambda x: (x["park"], x["seed"]))
            by_rate = {}
            for x in series:
                by_rate.setdefault(x["park"], []).append(x["parked_share"])
            means = [(pk, r(float(np.mean(v)))) for pk, v in sorted(by_rate.items())]
            vals = [m for _pk, m in means]
            if any(b < a for a, b in zip(vals, vals[1:])):
                bad.append((need, f, means))
            spans.append((need, f, vals[0], vals[-1]))
    brackets = [s for s in spans if s[2] <= 1 / 3 <= s[3]]
    # The table itself, indexed by rate and horizon. Averaged over floor,
    # route and seed, because the measurement that motivated this criterion
    # found those three move the share by under a tenth while the horizon
    # moves it by a factor of two and a half.
    table = []
    for pk in sorted({x["park"] for x in rows}):
        g = [x for x in rows if x["park"] == pk]
        row = [pk]
        for q in PARK_HORIZONS:
            vals = [x["parked_share_at"][str(q)] for x in g
                    if str(q) in x.get("parked_share_at", {})]
            row.append(r(float(np.mean(vals))) if vals else None)
        table.append(tuple(row))
    return Criterion(
        "A18_F1  the dial is monotone and spans the region", not bad,
        "parked share from lowest to highest parking rate, as (floor, route, "
        "smallest, largest): %s | %d of %d series bracket one third | %s | "
        "**the share has no steady state**, because parking is one way and the "
        "stock only accumulates, so the table is indexed by rate and horizon "
        "together: (parking rate, then share at rounds %s): %s"
        % (spans, len(brackets), len(spans),
           "monotone everywhere" if not bad
           else "NOT MONOTONE: %s" % (bad[:3],),
           list(PARK_HORIZONS), table))


def criterion_a18_f2(rows: list) -> Criterion:
    """Does who carries it change the readings, and where on the dial.

    Three states on the count, which is an integer, and the flow printed
    beside it against A18_B6's resolution figures rather than thresholded.
    """
    pairs = _carry_pairs(rows)
    diff = [(k, a["below_close"], b["below_close"]) for k, a, b in pairs
            if a["below_close"] != b["below_close"]]
    if not pairs:
        return Criterion("A18_F2  does who carries it change the count", False,
                         "no complete pairs")
    if len(diff) == len(pairs):
        state = "first: the funding route changes the count in every pair"
    elif not diff:
        state = ("third: the funding route changes the count in no pair, so "
                 "who carries it does not decide who ends below the line")
    else:
        state = ("second: it changes the count in %d of %d pairs"
                 % (len(diff), len(pairs)))
    # **Per floor, not pooled.** The two floor depths sit at different levels
    # of everything, so a mean over both is dominated by the deeper one and
    # reports its ratio as if it were the grid's. This repository has made that
    # mistake before and named it: a median over a grid hides what is sparse.
    flows = []
    for need in sorted({k[0] for k, _a, _b in pairs}):
        for pk in PARK_FINE:
            sel = [(a, b) for k, a, b in pairs if k[0] == need and k[1] == pk]
            if not sel:
                continue
            ratio = float(np.mean([b["volume_total"] / a["volume_total"]
                                   for a, b in sel if a["volume_total"] > 0]))
            share = float(np.mean([a["parked_share"] for a, _b in sel]))
            flows.append((need, pk, r(share), r(ratio)))
    return Criterion(
        "A18_F2  does who carries it change the count", True,
        "%s | %d pairs | flow under issuance over flow under creditors, as "
        "(floor, parking rate, parked share, ratio): %s | pairs whose count "
        "differs: %s" % (state, len(pairs), flows, sorted(diff)[:6]))


def criterion_a18_f3(rows: list) -> Criterion:
    """Is the count monotone in the parking rate, per route."""
    out, broken = [], []
    for need in sorted({x["need_multiple"] for x in rows}):
        for f in FUNDING_F:
            for seed in sorted({x["seed"] for x in rows}):
                series = sorted((x for x in rows if x["need_multiple"] == need
                                 and x["funding"] == f and x["seed"] == seed),
                                key=lambda x: x["park"])
                counts = [x["below_close"] for x in series]
                if len(counts) < 3:
                    continue
                mono = all(b >= a for a, b in zip(counts, counts[1:]))
                out.append((need, f, seed, mono))
                if not mono:
                    broken.append((need, f, seed, counts))
    by_route = {f: sum(1 for o in out if o[1] == f and not o[3])
                for f in FUNDING_F}
    total = {f: sum(1 for o in out if o[1] == f) for f in FUNDING_F}
    if not broken:
        state = "first: more parking never lowers the count, on either route"
    elif all(by_route[f] == total[f] for f in FUNDING_F):
        state = "third: it is non-monotone on every cell of both routes"
    else:
        state = ("second: non-monotone in %s of %s cells by route"
                 % (by_route, total))
    return Criterion(
        "A18_F3  is the count monotone in the parking rate", True,
        "%s | non-monotone cells, as (floor, route, seed, counts against "
        "parking rate %s): %s" % (state, list(PARK_FINE), broken[:6]))


def _main_resupply(args) -> int:
    seeds = (0,) if args.smoke else SEEDS
    rows = resupply_grid(seeds=seeds)
    scan = boundary_scan(seeds=seeds)
    crits = [criterion_a18_b1(rows), criterion_a18_b2(rows),
             criterion_a18_b3(rows), criterion_a18_b4(rows),
             criterion_a18_b7(rows), criterion_a18_b8(rows),
             criterion_a18_b6(scan), criterion_a18_b5(rows)]
    print("stage A18_B: forbearance with somebody paying for it\n")
    print("%9s %5s %5s %10s %6s %4s | %6s %10s %6s %9s %8s"
          % ("mode", "floor", "rate", "funding", "retain", "seed", "below",
             "paid", "funded", "M/R", "support"))
    for x in sorted(rows, key=lambda x: (x["mode"], x["need_multiple"],
                                         x["seed"], x["rate"], x["funding"],
                                         x["retain"])):
        print("%9s %5.2f %5.2f %10s %6.2f %4d | %6d %10.1f %6.3f %9.4f %8.3f"
              % (x["mode"], x["need_multiple"], x["rate"], x["funding"],
                 x["retain"], x["seed"], x["below_close"], x["resupplied"],
                 x["funded_share"], x["mr_close"], x["support_close"]))
    print()
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RECORD_B
    if args.smoke:
        out = RESULTS / "subset" / RECORD_B.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18",
        "arm": "B",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, three floor depths, one mechanism "
                   "added: resupply along the edges already there",
        "f2i": F2I, "rounds": ROUNDS, "elasticity": ELASTICITY,
        "plan": resupply_plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["mode"], x["need_multiple"],
                                            x["rate"], x["funding"],
                                            x["retain"], x["seed"])),
        # Recorded in full beside the runs rather than summarised into the
        # criterion, because which cells sit on a boundary is a property of
        # this carrier that the next reader needs and cannot recompute cheaply.
        "boundary_scan": sorted(scan, key=lambda x: (x["need_multiple"],
                                                     x["rate"], x["funding"],
                                                     x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


def _main_landing(args) -> int:
    rows = landing_grid(seeds=(0,) if args.smoke else SEEDS)
    crits = [criterion_a18_c1(rows), criterion_a18_c2(rows),
             criterion_a18_c3(rows), criterion_a18_c4(rows),
             criterion_a18_c5(rows)]
    print("stage A18_C: where the new claims land\n")
    print("%5s %5s %6s %9s %5s %4s | %6s %8s %9s %8s %6s"
          % ("floor", "rate", "elast", "target", "ret", "seed", "below",
             "M/R", "volume", "support", "recip"))
    for x in sorted(rows, key=lambda x: (x["retain"], x["need_multiple"],
                                         x["rate"], x["elasticity"],
                                         x["seed"], x["target"])):
        print("%5.2f %5.1f %6.2f %9s %5.1f %4d | %6d %8.3f %9.0f %8.2f %6d"
              % (x["need_multiple"], x["rate"], x["elasticity"], x["target"],
                 x["retain"], x["seed"], x["below_close"], x["mr_close"],
                 x["volume_total"], x["support_close"],
                 x["recap_recipients"]))
    print()
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RESULTS / "a18_landing.json"
    if args.smoke:
        out = RESULTS / "subset" / out.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18",
        "arm": "C",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, issuance funding throughout, two "
                   "landing points, the wage elasticity swept",
        "f2i": F2I, "rounds": ROUNDS,
        "plan": landing_plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["retain"], x["need_multiple"],
                                            x["rate"], x["elasticity"],
                                            x["target"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


def _main_repay(args) -> int:
    rows = repay_grid(seeds=(0,) if args.smoke else SEEDS)
    crits = [criterion_a18_d1(rows), criterion_a18_d2(rows),
             criterion_a18_d3(rows), criterion_a18_d4(rows),
             criterion_a18_d5(rows), criterion_a18_d6(rows)]
    print("stage A18_D: the rescue as a loan rather than a gift\n")
    print("%9s %5s %5s %6s %10s %4s | %6s %9s %9s %9s %4s %8s"
          % ("mode", "floor", "rate", "repay", "funding", "seed", "below",
             "lent", "repaid", "arrears", "blk", "M/R"))
    for x in sorted(rows, key=lambda x: (x["mode"], x["funding"],
                                         x["need_multiple"], x["rate"],
                                         x["seed"], x["repay"])):
        print("%9s %5.2f %5.1f %6.2f %10s %4d | %6d %9.1f %9.1f %9.1f %4d %8.3f"
              % (x["mode"], x["need_multiple"], x["rate"], x["repay"],
                 x["funding"], x["seed"], x["below_close"], x["lent"],
                 x["repaid"], x["arrears"], x["repay_blocked"], x["mr_close"]))
    print()
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RESULTS / "a18_repay.json"
    if args.smoke:
        out = RESULTS / "subset" / out.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18", "arm": "D",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, the rescue carrying a repayment "
                   "obligation senior to the borrower's own spending",
        "f2i": F2I, "rounds": ROUNDS,
        "plan": repay_plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["mode"], x["funding"],
                                            x["need_multiple"], x["rate"],
                                            x["repay"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


def _main_park(args) -> int:
    rows = park_grid(seeds=(0,) if args.smoke else SEEDS)
    crits = [criterion_a18_e1(rows), criterion_a18_e2(rows),
             criterion_a18_e3(rows), criterion_a18_e5(rows),
             criterion_a18_e4(rows)]
    print("stage A18_E: claims that exist and do not circulate\n")
    print("%5s %5s %6s %6s %13s %4s | %6s %11s %9s %9s %8s %9s"
          % ("floor", "rate", "park", "retain", "target", "seed", "below",
             "circulating", "parked", "stock", "M/R", "volume"))
    for x in sorted(rows, key=lambda x: (x["target"], x["need_multiple"],
                                         x["rate"], x["retain"], x["park"],
                                         x["seed"])):
        print("%5.2f %5.1f %6.2f %6.2f %13s %4d | %6d %11.1f %9.1f %9.1f %8.3f %9.0f"
              % (x["need_multiple"], x["rate"], x["park"], x["retain"],
                 x["target"], x["seed"], x["below_close"],
                 x["circulating_close"], x["parked_close"], x["stock_close"],
                 x["mr_close"], x["volume_total"]))
    print()
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RESULTS / "a18_park.json"
    if args.smoke:
        out = RESULTS / "subset" / out.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18", "arm": "E",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, issuance funding, claims moved out "
                   "of the trading accounts without being destroyed",
        "f2i": F2I, "rounds": ROUNDS,
        "plan": park_plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["target"], x["need_multiple"],
                                            x["rate"], x["retain"], x["park"],
                                            x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


def _main_carry(args) -> int:
    rows = carry_grid(seeds=(0,) if args.smoke else SEEDS)
    crits = [criterion_a18_f1(rows), criterion_a18_f2(rows),
             criterion_a18_f3(rows)]
    print("stage A18_F: who carries a forbearance programme\n")
    print("%5s %7s %10s %4s | %6s %12s %11s %9s %8s"
          % ("floor", "park", "funding", "seed", "below", "parked share",
             "circulating", "volume", "M/R"))
    for x in sorted(rows, key=lambda x: (x["need_multiple"], x["park"],
                                         x["funding"], x["seed"])):
        print("%5.2f %7.3f %10s %4d | %6d %12.4f %11.1f %9.0f %8.3f"
              % (x["need_multiple"], x["park"], x["funding"], x["seed"],
                 x["below_close"], x["parked_share"], x["circulating_close"],
                 x["volume_total"], x["mr_close"]))
    print()
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RESULTS / "a18_carry.json"
    if args.smoke:
        out = RESULTS / "subset" / out.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A18", "arm": "F",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, two funding routes for the same "
                   "forbearance, at parking rates below saturation",
        "f2i": F2I, "rounds": ROUNDS,
        "plan": carry_plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["need_multiple"], x["park"],
                                            x["funding"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
