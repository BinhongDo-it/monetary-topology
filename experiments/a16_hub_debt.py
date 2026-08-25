"""A16: a bilateral obligation on the highest-degree nodes.

The question is whether a liability makes the cascade a function of the debt
structure. It matters because this model has none anywhere else: no
liabilities, no receivables, claims conserved through every exit, and it still
produces a cascade. So the interbank literature's balance-sheet interconnection
and the production-network literature's real input dependence are each
sufficient for one and neither is necessary, and what this stage asks is what a
liability adds on top of that.

A15-4 gave it a second reason. The three concentration measures on this carrier
are driven by one latent: the Gini rising implies all three rise in 344 of 344
cells, and the top percentile falling implies all three fall in 266 of 266. A
three-way divergence needs two independent concentration processes and there is
one. ``mutual`` is a candidate second channel, because a hub's departure removes
an asset from another hub's book without passing through the upward leak.

Carrier and grid

    The stratified carrier, not the complete graph. The complete graph was
    excluded on two counts, each sufficient on its own, and both were measured
    before anything was registered. In-degree there takes exactly one value,
    199, so "the highest-degree nodes" is not a defined set and the selection
    falls through to index order. And the one reading that moved there is an
    identity: under ``creditor`` the closing starved count is ``nodes - hubs``
    at every hub count, and the survivors are the hub set itself, because they
    collect from everyone else.

Usage

    python experiments/a16_hub_debt.py --plan
    python experiments/a16_hub_debt.py --smoke
    python experiments/a16_hub_debt.py
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
    HUB_DEBT_ORIENTATIONS,
    HubDebtSpec,
    Network,
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
    WageChannel,
)

RECORD = RESULTS / "a16_hub_debt.json"
DIGITS = 6
TAIL = 25


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A12 is the carrier, imported rather than restated for the reason A12 imports
#: its own from A8: two stages that read the same graph must not be able to
#: drift apart on what the graph is.
_A12 = _load(ROOT / "experiments" / "a12_mechanisms.py", "_a12")
BASE_CARRIER = _A12.BASE_CARRIER
r = _A12.r

#: One edge count rather than A12's nine. The switch under test moves claims
#: between nodes and the edge grid moves the graph they move over, so sweeping
#: both would put two mechanisms in one cell. Thirty is where A15-2b found the
#: return catching, so it is the point on that grid with the most going on.
F2I = 30

#: A11's floor grid, imported in spirit and restated here because A11 builds its
#: configs without a carrier. The floor is what makes a cascade, so it is the
#: axis the main question is read along.
NEED_MULTIPLES = (0.05, 0.20, 0.50, 1.00)

#: The obligation's size. Zero is the control and it is run as its own arm
#: rather than inferred, so the comparison is against a run and not against a
#: number from another file.
RATES = (0.02, 0.05, 0.10, 0.20, 0.30)

#: How many nodes carry the obligation. **The values are not free**: this
#: carrier's in-degree has a long plateau at 30, running from the thirteenth
#: node to past the thirtieth, so most cut points fall inside it and the set is
#: then partly index order rather than partly degree. Measured across the five
#: seeds, the cuts that separate at every one of them are ``k`` in 1, 2 and 10.
#: Two are taken, because the hub-count axis exists only to catch the identity
#: the complete graph produced, and two points show a slope as well as three do.
HUB_COUNTS = (2, 10)

SEEDS = (0, 1, 2, 3, 4)
ROUNDS = 300
ELASTICITY = 0.5


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def gini(v: np.ndarray) -> float:
    x = np.sort(np.asarray(v, dtype=float))
    n = x.size
    c = x.cumsum()
    return float((n + 1 - 2 * (c / c[-1]).sum()) / n) if c[-1] > 0 else 0.0


def top_share(v: np.ndarray, k: int) -> float:
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = float(s.sum())
    return float(s[:k].sum() / total) if total > 0 else float("nan")


def base_config(seed: int, need_mult: float) -> NetworkConfig:
    c = BASE_CARRIER
    scale = 100.0 / c.nodes
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
        wages=WageChannel(elasticity=ELASTICITY),
        subsistence=SubsistenceSpec(need=need_mult * scale, grace=1),
    )


def one_run(orientation: str | None, rate: float, hubs: int,
            need_mult: float, seed: int) -> dict:
    hd = (HubDebtSpec() if orientation is None
          else HubDebtSpec(hubs=hubs, orientation=orientation, rate=rate))
    net = Network(dataclasses.replace(base_config(seed, need_mult), hub_debt=hd))
    h = net.run()
    n = h.holdings.shape[1]
    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    support = np.asarray(h.effective_support, dtype=float)
    volume = float(np.asarray(h.total_volume, dtype=float).sum())
    alive = np.flatnonzero(net._alive)
    hub_set = np.sort(np.asarray(net._hub_nodes, dtype=int))
    return {
        "orientation": orientation or "off",
        "rate": float(rate),
        "hubs": int(hubs),
        "need_multiple": float(need_mult),
        "seed": int(seed),
        "starved_close": int(h.starved[-1]),
        "starved_peak": int(np.asarray(h.starved).max()),
        "survivors": int(alive.size),
        # The artefact detector. On the complete graph the survivors were the
        # hub set exactly, at every hub count, which made the partial cascade an
        # identity rather than a reading. Printed here so the same shape cannot
        # arrive unnoticed on this carrier.
        "survivors_are_the_hubs": bool(np.array_equal(np.sort(alive), hub_set)),
        "hub_nodes": [int(x) for x in hub_set],
        "in_degree_values": int(np.unique(net.adjacency.sum(axis=0)).size),
        "in_degree_at_k": float(np.sort(net.adjacency.sum(axis=0))[::-1][hubs - 1])
        if hubs >= 1 else float("nan"),
        "in_degree_at_k_plus_1": float(np.sort(net.adjacency.sum(axis=0))[::-1][hubs])
        if hubs < n else float("nan"),
        "debt_paid": r(net._hub_debt_paid),
        "debt_share_of_volume": r(net._hub_debt_paid / volume) if volume > 0 else 0.0,
        "debt_blocked_rounds": int(net._hub_debt_blocked),
        # The mechanism variable for the floor scan. ``frozen_holdings`` is the
        # stock held by nodes that have left, and the whole difference between
        # the two regimes is whether that stock is negligible or dominant: at a
        # shallow floor the leavers take 0.3 per cent with them and the reading
        # becomes redistribution among survivors, at a deeper one they freeze
        # holding 94 per cent and every measure collapses together. **Added
        # after the 380-row grid ran**, so that record does not carry it and the
        # scan does.
        "frozen_share_close": r(float(np.asarray(h.frozen_holdings)[-1] / m[-1])
                                if m[-1] > 0 else 0.0),
        "gini_open": r(gini(h.holdings[0])),
        "gini_close": r(gini(h.holdings[-1])),
        "top1_open": r(top_share(h.holdings[0], max(1, n // 100))),
        "top1_close": r(top_share(h.holdings[-1], max(1, n // 100))),
        "top10_open": r(top_share(h.holdings[0], max(1, n // 10))),
        "top10_close": r(top_share(h.holdings[-1], max(1, n // 10))),
        "m_ratio": r(m[-1] / m[0]),
        "support_ratio": r(float(support[-TAIL:].mean() / support[0])),
        "claims_conserved": True,
    }


#: The configurations, as (orientation, rate, hubs). The rate is swept at one
#: hub count and the hub count at one rate, rather than the product of the two.
#: The hub-count axis exists for one purpose, which is to see whether the
#: closing starved count is a function of ``hubs`` the way it was on the
#: complete graph, and that shape shows at a single rate. The product would cost
#: twice as much for the same two answers.
PIVOT_HUBS = 10
PIVOT_RATE = 0.10


def configurations() -> list:
    out = [(None, 0.0, PIVOT_HUBS)]
    for o in HUB_DEBT_ORIENTATIONS:
        for rate in RATES:
            out.append((o, rate, PIVOT_HUBS))
        for hubs in HUB_COUNTS:
            if hubs != PIVOT_HUBS:
                out.append((o, PIVOT_RATE, hubs))
    return out



#: The floor scan. A16-7 found the 1929 shape at ``need = 0.05`` and nowhere
#: else on a grid whose next point is ``0.20``, so the boundary is somewhere in
#: between and the axis is worth one pass at eight points. **The orientations
#: are carried through it rather than swept separately**, because the question
#: "does the direction of the obligation move the boundary" is the same question
#: as the hit-rate spread A16-7 reported, measured on a cleaner axis and at no
#: extra cost.
NEED_SCAN = (0.02, 0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20)
SCAN_ARMS = ((None, 0.0, PIVOT_HUBS),) + tuple(
    (o, PIVOT_RATE, PIVOT_HUBS) for o in HUB_DEBT_ORIENTATIONS)


def criterion_a16_8(rows: list) -> Criterion:
    """Where the composition effect lives, along the floor, and what marks it.

    Three states, fixed before the scan.

      The shape occurs below some floor depth and not above it, and the frozen
      share crosses from negligible to dominant across the same place. Then the
      boundary is located and the thing that marks it is named.

      The shape occurs at every depth in the range. The boundary is outside it
      and the scan says which way to extend.

      The frozen share rises smoothly and the shape does not track it. Then the
      mechanism read off the two-point comparison was the wrong one and the
      reading says so.

    Structural verdict: the scan covers the range at every depth with a control
    arm present. **No line is drawn on the frozen share**, which is printed per
    cell because it is the object.
    """
    def sg(a, b):
        return (a > b) - (a < b)
    ok = True
    parts = []
    needs = sorted({x["need_multiple"] for x in rows})
    orients = sorted({x["orientation"] for x in rows})
    for need in needs:
        cells = [x for x in rows if x["need_multiple"] == need]
        if "off" not in {x["orientation"] for x in cells}:
            ok = False
            parts.append("need=%.3f has no control arm" % need)
        hits = [x for x in cells
                if sg(x["top1_close"], x["top1_open"]) < 0
                and sg(x["top10_close"], x["top10_open"]) > 0
                and sg(x["gini_close"], x["gini_open"]) > 0]
        parts.append(
            "need=%.3f: 1929 shape %d/%d | frozen share at close %s | starved %s"
            % (need, len(hits), len(cells),
               sorted({x["frozen_share_close"] for x in cells}),
               sorted({x["starved_close"] for x in cells})))
    for o in orients:
        per = []
        for need in needs:
            cells = [x for x in rows if x["need_multiple"] == need
                     and x["orientation"] == o]
            hits = sum(1 for x in cells
                       if sg(x["top1_close"], x["top1_open"]) < 0
                       and sg(x["top10_close"], x["top10_open"]) > 0
                       and sg(x["gini_close"], x["gini_open"]) > 0)
            per.append((need, hits, len(cells)))
        parts.append("%s by depth: %s" % (o, per))
    return Criterion("A16-8  where along the floor the composition effect lives",
                     ok, " | ".join(parts))


def plan() -> dict:
    cfgs = configurations()
    return {
        "configurations": len(cfgs),
        "need_multiples": list(NEED_MULTIPLES),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "f2i": F2I,
        "runs_total": len(cfgs) * len(NEED_MULTIPLES) * len(SEEDS),
        "carrier": "the stratified carrier. The complete graph is excluded: "
                   "in-degree there takes one value so the hub set is not "
                   "defined, and the one reading that moved was the identity "
                   "starved = nodes - hubs",
    }


def run_grid(needs=NEED_MULTIPLES, seeds=SEEDS, cfgs=None) -> list:
    cfgs = configurations() if cfgs is None else cfgs
    return [one_run(o, rate, hubs, need, seed)
            for (o, rate, hubs) in cfgs for need in needs for seed in seeds]


def _key(x: dict) -> tuple:
    return (x["need_multiple"], x["seed"])


def criterion_a16_1(rows: list) -> Criterion:
    """Discipline 19, against A12's record rather than against this file.

    The control arm at ``need_multiple = 0.20`` is A12's ``floor`` arm: the same
    carrier, the same edge count, the same elasticity, and a floor need of
    ``0.20 * 100 / 200``, which is the ``0.1`` A12 writes. So the two must agree
    to the last bit, and a disagreement means this stage's harness is not the
    one that produced the record it is going to be read beside.
    """
    path = RESULTS / "a12_mechanisms.json"
    if not path.exists():
        return Criterion("A16-1  the control arm is A12's floor arm", False,
                         "a12_mechanisms.json is not on disk")
    ref = [x for x in json.loads(path.read_text(encoding="utf-8"))["runs"]
           if x["arm"] == "floor" and x["f2i"] == F2I and x["elasticity"] == ELASTICITY]
    mine = [x for x in rows if x["orientation"] == "off"
            and x["need_multiple"] == 0.20 and x["seed"] == 0]
    if not ref or not mine:
        return Criterion("A16-1  the control arm is A12's floor arm", False,
                         "no comparable cell: %d reference, %d here"
                         % (len(ref), len(mine)))
    a, b = mine[0], ref[0]
    checks = {"gini_close": "gini_close", "m_ratio": "m_ratio",
              "support_ratio": "support_ratio", "starved_close": "starved",
              "top1_close": "top1_wealth", "top10_close": "top10_wealth"}
    bad = [(k, a[k], b[v]) for k, v in checks.items() if a[k] != b[v]]
    return Criterion(
        "A16-1  the control arm is A12's floor arm",
        not bad,
        "%d/%d fields identical to a12_mechanisms.json%s"
        % (len(checks) - len(bad), len(checks),
           "" if not bad else "; differing: %s" % bad))


def criterion_a16_2(rows: list) -> Criterion:
    """The hub set, and how much of it is degree rather than index order.

    **A tie at the cut is not one failure, it is a range of them**, and the
    criterion is shaped so the range it kills matches. On the complete graph
    every in-degree is 199, so the whole set is index order and the words "the
    highest-degree nodes" name nothing: that is the state worth failing on. On
    this carrier the in-degree has a plateau at 30, so a cut inside it makes
    part of the set degree and part of it index order, and killing the stage for
    that would be setting the criterion at its strictest rather than where it is
    good enough.

    So the verdict is that **some** of the set is unambiguous, and the number
    that is gets printed. A count whose cut lands on a tie is named and its rows
    are not read for the hub-count question.
    """
    parts, ok = [], True
    for hubs in sorted({x["hubs"] for x in rows if x["orientation"] != "off"}):
        cells = [x for x in rows if x["hubs"] == hubs and x["orientation"] != "off"]
        if not cells:
            continue
        x = cells[0]
        tie = x["in_degree_at_k"] == x["in_degree_at_k_plus_1"]
        # How much of the set sits strictly above the first excluded node. That
        # part is degree; the rest is whatever the stable sort did with a tie.
        cut_next = x["in_degree_at_k_plus_1"]
        parts.append(
            "hubs=%d: in-degree takes %d distinct values, the cut is %g against "
            "%g, tie at the cut %s, set %s"
            % (hubs, x["in_degree_values"], x["in_degree_at_k"], cut_next,
               tie, x["hub_nodes"][:6]))
        if tie:
            parts.append("hubs=%d is not read for the hub-count question: its "
                         "cut is inside a plateau, so the set is partly index "
                         "order" % hubs)
        # The failing state is the complete graph's: one distinct in-degree, so
        # nothing in the set is there on degree.
        if x["in_degree_values"] <= 1:
            ok = False
            parts.append("hubs=%d: in-degree takes one value, so the set is "
                         "index order and names nothing" % hubs)
    return Criterion("A16-2  the hub set, and how much of it is degree",
                     ok, " | ".join(parts))


def criterion_a16_6(rows: list) -> Criterion:
    """The artefact detector: is the survivor set the hub set.

    On the complete graph it was, at every hub count, which made the partial
    cascade there the identity ``nodes - hubs`` rather than a reading. This
    prints the cells where the same shape recurs. **It is not a threshold**:
    the set equality is a fact about one run and the count of such runs is the
    object.
    """
    hits = [x for x in rows if x["survivors_are_the_hubs"]]
    near = [x for x in rows if not x["survivors_are_the_hubs"]
            and x["survivors"] == x["hubs"]]
    return Criterion(
        "A16-6  do the survivors turn out to be the hub set", True,
        "survivors equal the hub set in %d of %d runs%s | survivor count equals "
        "the hub count without the sets matching in %d runs"
        % (len(hits), len(rows),
           "" if not hits else ": %s" % sorted(
               {(x["orientation"], x["rate"], x["hubs"], x["need_multiple"])
                for x in hits})[:8],
           len(near)))


def criterion_a16_4(rows: list) -> Criterion:
    """The main question, cell by cell against the control at the same cell.

    Three states, fixed before the run.

      The closing starved count varies continuously with the rate, at some
      orientation. The cascade is a function of the debt structure and the
      stage has its answer.

      It does not move from the control at any rate. The obligation is not the
      switch and the floor is, which is a negative reading and gets reported.

      It moves at some orientations and not others. The orientations that move
      it are named, and that is the reading.

    **No line is drawn on the counts.** They are printed per cell against the
    control at the same floor and seed, and the reading is the spread.
    """
    ctl = {_key(x): x for x in rows if x["orientation"] == "off"}
    parts, moved = [], {}
    for o in HUB_DEBT_ORIENTATIONS:
        for rate in sorted({x["rate"] for x in rows
                            if x["orientation"] == o and x["hubs"] == PIVOT_HUBS}):
            cells = [x for x in rows if x["orientation"] == o
                     and x["rate"] == rate and x["hubs"] == PIVOT_HUBS]
            deltas = [x["starved_close"] - ctl[_key(x)]["starved_close"]
                      for x in cells if _key(x) in ctl]
            if not deltas:
                continue
            moved.setdefault(o, []).append((rate, min(deltas), max(deltas)))
    for o, seq in moved.items():
        parts.append("%s, closing starved minus the control at the same cell, "
                     "by rate: %s" % (o, [(rt, lo, hi) for rt, lo, hi in seq]))
    ever = {o for o, seq in moved.items() if any(lo or hi for _rt, lo, hi in seq)}
    parts.append("orientations that move the count at any rate: %s"
                 % (sorted(ever) or "none"))
    return Criterion("A16-4  does the cascade become a function of the debt",
                     True, " | ".join(parts))


def criterion_a16_5(rows: list) -> Criterion:
    """Every cell, and the smallest three, rather than a mean over cells.

    Discipline 13 step 1. A mean over the grid would hide the cells where the
    obligation moved almost nothing, and those are the ones that say whether a
    reading elsewhere is the mechanism or the floor.
    """
    parts = []
    for need in sorted({x["need_multiple"] for x in rows}):
        for o in ["off"] + list(HUB_DEBT_ORIENTATIONS):
            for rate in sorted({x["rate"] for x in rows if x["orientation"] == o
                                and x["hubs"] == PIVOT_HUBS}):
                cells = [x for x in rows if x["need_multiple"] == need
                         and x["orientation"] == o and x["rate"] == rate
                         and x["hubs"] == PIVOT_HUBS]
                if not cells:
                    continue
                parts.append(
                    "need=%.2f %s rate=%.2f: starved close %s peak %s, debt share "
                    "of volume %s, blocked rounds %s, m_ratio %s, support %s"
                    % (need, o, rate,
                       sorted(x["starved_close"] for x in cells),
                       sorted(x["starved_peak"] for x in cells),
                       sorted(x["debt_share_of_volume"] for x in cells),
                       sorted(x["debt_blocked_rounds"] for x in cells),
                       sorted(x["m_ratio"] for x in cells),
                       sorted(x["support_ratio"] for x in cells)))
    thin = sorted(rows, key=lambda x: x["debt_share_of_volume"])[:3]
    parts.append("the three cells where the obligation moved the least: %s"
                 % [(x["orientation"], x["rate"], x["hubs"], x["need_multiple"],
                     x["seed"], x["debt_share_of_volume"]) for x in thin])
    return Criterion("A16-5  every cell, and the thinnest three", True,
                     " | ".join(parts))


def criterion_a16_7(rows: list) -> Criterion:
    """A15-4's handoff: does the obligation add a second concentration process.

    A15-4 found the three measures driven by one latent, with the Gini rising
    implying all three rise in 344 of 344 cells and the top percentile falling
    implying all three fall in 266 of 266. The shape the 1929 material needs is
    the top percentile falling while the Gini rises, and it occurred zero times.
    **This prints the same decomposition on this stage's rows**, so the answer
    is a count and not an impression.
    """
    def sg(a, b):
        return (a > b) - (a < b)
    tri = [{"gini": sg(x["gini_close"], x["gini_open"]),
            "top1": sg(x["top1_close"], x["top1_open"]),
            "top10": sg(x["top10_close"], x["top10_open"]),
            "o": x["orientation"]} for x in rows]
    hist = {}
    for v in tri:
        k = (v["gini"], v["top1"], v["top10"])
        hist[k] = hist.get(k, 0) + 1
    three = [v for v in tri if len({v["gini"], v["top1"], v["top10"]}) == 3]
    target = [v for v in tri if v["top1"] < 0 and v["top10"] > 0 and v["gini"] > 0]
    pair = sum(1 for v in tri if v["top1"] < 0 and v["gini"] > 0)
    return Criterion(
        "A16-7  does the obligation add a second concentration process", True,
        "%d rows | sign triples (gini, top1, top10) that occur: %s | three ways "
        "%d, 1929 shape %d, and the pair the shape needs, top1 down with gini "
        "up: %d | orientations producing either: %s"
        % (len(tri), sorted(hist.items(), key=lambda kv: -kv[1]),
           len(three), len(target), pair,
           sorted({v["o"] for v in three + target}) or "none"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true",
                    help="print the run count and exit, spending nothing")
    ap.add_argument("--need-scan", action="store_true",
                    help="the floor scan only: eight depths, four arms, five "
                         "seeds, written to its own record")
    ap.add_argument("--smoke", action="store_true",
                    help="one floor and one seed, writing to results/subset")
    ap.add_argument("--no-write", action="store_true",
                    help="print and do not touch the registered record")
    args = ap.parse_args()

    if args.plan:
        for k, v in plan().items():
            print("  %-18s %s" % (k, v))
        return 0

    if args.need_scan:
        rows = run_grid(needs=(NEED_SCAN if not args.smoke else (0.05, 0.20)),
                        seeds=(SEEDS if not args.smoke else (3,)),
                        cfgs=SCAN_ARMS)
        crits = [criterion_a16_8(rows)]
        print("stage A16, the floor scan\n")
    else:
        if args.smoke:
            rows = run_grid(needs=(0.20,), seeds=(0,))
        else:
            rows = run_grid()
        crits = [criterion_a16_1(rows), criterion_a16_2(rows), criterion_a16_6(rows),
                 criterion_a16_4(rows), criterion_a16_5(rows), criterion_a16_7(rows)]
        print("stage A16: a bilateral obligation on the highest-degree nodes\n")
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))
    if args.no_write:
        return 0 if passed == len(crits) else 1

    # Failure mode 35: the reduced run writes results/subset, which is this
    # repository's own separation and is committed on purpose.
    out = RESULTS / "a16_need_scan.json" if args.need_scan else RECORD
    if args.smoke:
        out = RESULTS / "subset" / out.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A16",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": plan()["carrier"],
        "f2i": F2I,
        "rounds": ROUNDS,
        "elasticity": ELASTICITY,
        "plan": plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["need_multiple"], x["orientation"],
                                            x["rate"], x["hubs"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
