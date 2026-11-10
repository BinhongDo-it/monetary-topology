"""A17: edges cut out of the graph, rather than a node ceasing to trade.

The question is whether a phase transition in the graph itself produces a
cascade, without an income threshold doing the work.

It is not a repeat of A16. Every rule in this model reads the node's own state,
and the exit branch does not touch the adjacency at all: it flips a membership
flag, the routes that pointed at the node are masked for that round, and the
potential graph is exactly what it was at construction. So a trading
relationship ending is not something the model can currently express, and that
is the shape a run has: the depositor cuts the edge before the bank has failed
anything.

Three arms, and the three thresholds sit in three different places.

  shock       a share of every edge is cut once, at a named round. **No trigger
              and no propagation rule at all.** This arm asks what the graph
              does on its own. It can still produce a discrete event, because a
              node whose out-edges are gone has no route to spend along.
  self_cut    a node whose inflow falls below a threshold cuts its own
              out-edges. The threshold lives on the edges rather than on the
              trading.
  run         the edges pointing at a node whose inflow has fallen below the
              threshold are cut by whoever holds them. **The trigger is read on
              one node and the action taken on another**, which no other rule
              here does.

What a cut removes, and what it leaves running. A cut deletes entries of the
adjacency and rebuilds the discretionary routes from what is left. Two channels
do not read the adjacency and carry on through every arm:

  payroll     the fixed roster pays its fixed receivers each round
              (``_rebuild_route`` leaves the wage mask alone, ``_wage_flow``
              never looks at the adjacency). On the hub-ranked shock arm at
              share 0.7, 73 to 75 per cent of all wages paid over the run go
              along relations the cut has deleted.
  issuance    the authority's rule is endogenous, and it issues each round
              what the non-financial inflow has fallen below its opening level.

So "the graph on its own" here is the discretionary graph with payroll and the
authority still working. And ``run`` removes relations only: a cut moves no
cash at the instant it happens, and no deposit is redeemed.

The floor is off on every arm, and two probe measurements are why.

  With the cut trigger set at the floor, the nodes whose edges get cut are
  exactly the nodes that have already left: 180 stranded against 180 departed,
  the same set, and the total flow identical to the control's. A run happens
  before the failure, not after it.

  Raising the trigger above the floor does not fix it either, because at the
  registered floor the cascade already takes 180 of 200 and nearly everyone is
  under any threshold. So the floor comes off and the cut threshold becomes the
  only one in the model, which is what makes the three arms comparable.

Usage

    python experiments/a17_edge_cut.py --plan
    python experiments/a17_edge_cut.py --smoke
    python experiments/a17_edge_cut.py
"""

from __future__ import annotations

import argparse
import collections
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
    EDGE_CUT_MODES,
    EDGE_CUT_TARGETING,
    EdgeCutSpec,
    Network,
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
    WageChannel,
)

RECORD = RESULTS / "a17_edge_cut.json"
DIGITS = 6
TAIL = 25


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A12 = _load(ROOT / "experiments" / "a12_mechanisms.py", "_a12")
BASE_CARRIER = _A12.BASE_CARRIER
r = _A12.r

F2I = 30
ELASTICITY = 0.5
ROUNDS = 300
SEEDS = (0, 1, 2, 3, 4)

#: The shock arm's share grid, and it is dense on purpose. A probe at three
#: points read 397,047 at 0.30, **406,660 at 0.40**, and 52,585 at 0.50: the
#: curve is not monotone, so a coarse grid would have reported a threshold in
#: the wrong place or missed it.
SHOCK_SHARES = (0.10, 0.20, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70)

#: One shock round. The arm asks what a cut does, not when it does it, and a
#: second value would double the grid to answer a question nothing has asked.
SHOCK_ROUND = 50

#: The triggered arms. The trigger is in the units inflow is measured in, and
#: with no floor the median per-node inflow on this carrier is about 6.6, so the
#: grid straddles it rather than sitting on one side.
TRIGGERS = (2.0, 4.0, 6.0, 8.0, 12.0)
CUT_SHARES = (0.10, 0.30, 0.50, 0.70)

#: A17-2's gate. The same threshold, delivered two ways: as a floor the node
#: trades under, and as a rule about its edges. If the two read the same
#: numbers then the edge rule is the floor under another name.
GATE_TRIGGER = 6.0


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def r_sig(x: float) -> float:
    """Six significant figures. The tail fields run down to 1e-24 and ``r``
    rounds to six decimals, which would write every one of them as zero."""
    return float("%.6e" % float(x))


def gini(v: np.ndarray) -> float:
    x = np.sort(np.asarray(v, dtype=float))
    n = x.size
    c = x.cumsum()
    return float((n + 1 - 2 * (c / c[-1]).sum()) / n) if c[-1] > 0 else 0.0


def top_share(v: np.ndarray, k: int) -> float:
    s = np.sort(np.asarray(v, dtype=float))[::-1]
    total = float(s.sum())
    return float(s[:k].sum() / total) if total > 0 else float("nan")


def components(adj: np.ndarray) -> tuple[int, int]:
    """Number of weakly connected components, and the largest one's size."""
    n = adj.shape[0]
    g = collections.defaultdict(set)
    ii, jj = np.nonzero(adj > 0)
    for i, j in zip(ii, jj):
        g[int(i)].add(int(j))
        g[int(j)].add(int(i))
    seen: set[int] = set()
    count = 0
    largest = 0
    for s in range(n):
        if s in seen:
            continue
        count += 1
        stack = [s]
        seen.add(s)
        size = 0
        while stack:
            u = stack.pop()
            size += 1
            for v in g[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        largest = max(largest, size)
    return count, largest


def base_config(seed: int, need: float = 0.0) -> NetworkConfig:
    c = BASE_CARRIER
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
        subsistence=SubsistenceSpec(need=need) if need > 0 else SubsistenceSpec(),
    )


def one_run(mode: str | None, share: float, trigger: float, seed: int,
            need: float = 0.0, targeting: str = "random") -> dict:
    ec = (EdgeCutSpec() if mode is None
          else EdgeCutSpec(mode=mode, share=share, trigger=trigger,
                           at_round=SHOCK_ROUND, targeting=targeting))
    net = Network(dataclasses.replace(base_config(seed, need), edge_cut=ec))
    h = net.run()
    n = h.holdings.shape[1]
    m = np.asarray(h.holdings, dtype=float).sum(axis=1)
    support = np.asarray(h.effective_support, dtype=float)
    flow = np.asarray(h.total_volume, dtype=float)
    volume = float(flow.sum())
    opening_degree = np.asarray(
        Network(base_config(seed, need)).adjacency, dtype=float).sum(axis=1)
    stranded = ~net._has_out
    ncomp, largest = components(net.adjacency)
    return {
        "mode": mode or "off",
        "targeting": targeting,
        "share": float(share),
        "trigger": float(trigger),
        "need": float(need),
        "seed": int(seed),
        "edges_cut": int(net._edges_cut),
        "edges_open": int((np.asarray(
            Network(base_config(seed, need)).adjacency) > 0).sum()),
        "stranded": int(stranded.sum()),
        "components": int(ncomp),
        "largest_component": int(largest),
        "starved_close": int(h.starved[-1]),
        "volume": r(volume),
        "support_ratio": r(float(support[-TAIL:].mean() / support[0])),
        "support_open": r(float(support[0])),
        "support_close": r(float(support[-TAIL:].mean())),
        # A17-8's raw material. Support is read on the last TAIL rounds, so the
        # flow it is read beside is the flow of those rounds, and the wages in
        # it say whether anything but the fixed roster is still trading. The
        # two shares of the control are filled in by ``attach_shares``.
        "volume_tail": r_sig(float(flow[-TAIL:].sum())),
        "wages_tail": r_sig(float(
            np.asarray(h.wage_paid, dtype=float)[-TAIL:].sum())),
        "volume_share_of_control": None,
        "volume_tail_share_of_control": None,
        "gini_open": r(gini(h.holdings[0])),
        "gini_close": r(gini(h.holdings[-1])),
        "top1_close": r(top_share(h.holdings[-1], max(1, n // 100))),
        "top10_close": r(top_share(h.holdings[-1], max(1, n // 10))),
        "m_ratio": r(m[-1] / m[0]),
        # Whether the stranded set is just the low-degree tail, which would make
        # a reading about the graph a reading about the degree distribution.
        "stranded_mean_degree": r(float(opening_degree[stranded].mean()))
        if stranded.any() else None,
        "kept_mean_degree": r(float(opening_degree[~stranded].mean()))
        if (~stranded).any() else None,
    }


def configurations() -> list:
    """(mode, share, trigger, need, targeting). ``None`` for mode is control.

    The shock arm runs twice, once uniformly over the edges and once ranked by
    hub incidence. **One of those is half of a known result**: graphs of this
    kind are reported robust to random link removal and fragile to targeted
    removal, and an arm that only cuts at random would report the robust half
    as if it were the whole finding.
    """
    out = [(None, 0.0, 0.0, 0.0, "random")]
    for tg in EDGE_CUT_TARGETING:
        out += [("shock", s, 0.0, 0.0, tg) for s in SHOCK_SHARES]
    for mode in ("self_cut", "run"):
        out += [(mode, s, tr, 0.0, "random")
                for tr in TRIGGERS for s in CUT_SHARES]
    return out


#: A17-2's configurations: one threshold, two responses, at two settings.
#:
#: **Two settings rather than one, because a smoke run showed why.** At the
#: severe setting both responses take the whole graph, 200 stranded against 200
#: departed, and the two volumes that separate them are 228 and 94 against a
#: control of 20,325. They do differ, but a gate that only ever fires where
#: everything has died is a gate on a degenerate pair. The mild setting is where
#: the difference has room to be a difference.
GATE_TRIGGER_MILD = 2.0
GATE_CONFIGS = (("self_cut", 0.70, GATE_TRIGGER, 0.0, "random"),
                (None, 0.0, 0.0, GATE_TRIGGER, "random"),
                ("self_cut", 0.30, GATE_TRIGGER_MILD, 0.0, "random"),
                (None, 0.0, 0.0, GATE_TRIGGER_MILD, "random"))


def plan() -> dict:
    cfgs = configurations()
    return {
        "configurations": len(cfgs),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "f2i": F2I,
        "shock_round": SHOCK_ROUND,
        "shock_shares": list(SHOCK_SHARES),
        "targeting": list(EDGE_CUT_TARGETING),
        "triggers": list(TRIGGERS),
        "cut_shares": list(CUT_SHARES),
        "gate_runs": len(GATE_CONFIGS) * len(SEEDS),
        "runs_total": len(cfgs) * len(SEEDS) + len(GATE_CONFIGS) * len(SEEDS),
        "floor": "off on every arm. See the module docstring: with the cut "
                 "trigger at the floor the cut lands on nodes that have already "
                 "left, and above it nearly everyone is under any threshold",
    }


def run_grid(seeds=SEEDS, cfgs=None) -> list:
    cfgs = configurations() if cfgs is None else cfgs
    return [one_run(mode, share, trig, seed, need, tg)
            for (mode, share, trig, need, tg) in cfgs for seed in seeds]


def attach_shares(rows: list) -> list:
    """Each row's flow over the floor-off control at the same seed, both windows.

    The cumulative share is what A17-8 first named cells on; the tail share is
    the window the support statistic is actually read in.
    """
    ctl = {x["seed"]: x for x in rows if x["mode"] == "off" and x["need"] == 0.0}
    for x in rows:
        c = ctl.get(x["seed"])
        if c is None:
            continue
        x["volume_share_of_control"] = (
            r_sig(x["volume"] / c["volume"]) if c["volume"] > 0 else None)
        x["volume_tail_share_of_control"] = (
            r_sig(x["volume_tail"] / c["volume_tail"])
            if c["volume_tail"] > 0 else None)
    return rows


def criterion_a17_1(rows: list) -> Criterion:
    """Discipline 19, against A12's record rather than against this file.

    The control arm here is A12's ``off`` arm: same carrier, same edge count,
    same elasticity, and no floor on either. A disagreement means this stage's
    harness is not the one that produced the records it will be read beside.
    """
    path = RESULTS / "a12_mechanisms.json"
    if not path.exists():
        return Criterion("A17-1  the control arm is A12's off arm", False,
                         "a12_mechanisms.json is not on disk")
    ref = [x for x in json.loads(path.read_text(encoding="utf-8"))["runs"]
           if x["arm"] == "off" and x["f2i"] == F2I and x["elasticity"] == ELASTICITY]
    mine = [x for x in rows if x["mode"] == "off" and x["need"] == 0.0
            and x["seed"] == 0]
    if not ref or not mine:
        return Criterion("A17-1  the control arm is A12's off arm", False,
                         "no comparable cell: %d reference, %d here"
                         % (len(ref), len(mine)))
    a, b = mine[0], ref[0]
    checks = {"gini_close": "gini_close", "m_ratio": "m_ratio",
              "support_ratio": "support_ratio", "top1_close": "top1_wealth",
              "top10_close": "top10_wealth"}
    bad = [(k, a[k], b[v]) for k, v in checks.items() if a[k] != b[v]]
    return Criterion("A17-1  the control arm is A12's off arm", not bad,
                     "%d/%d fields identical to a12_mechanisms.json%s"
                     % (len(checks) - len(bad), len(checks),
                        "" if not bad else "; differing: %s" % bad))


def criterion_a17_2(rows: list) -> Criterion:
    """The gate: one threshold delivered two ways has to read differently.

    If cutting a stressed node's edges and putting a floor under it at the same
    threshold return the same numbers, then the edge rule is the floor renamed
    and the arm is not worth its runs. **This is the executable form of the
    reachability check**: an arm whose answer is forced by construction is not
    an arm.

    The verdict is that they differ. **No line is drawn on how much**; the
    quantities are printed.
    """
    fields = ("volume", "gini_close", "support_ratio", "m_ratio")
    # The pairs have to be the control's seeds, all of them. ``not any([])`` is
    # true, so without this a gate whose two sides share no seed would pass.
    expected = sorted({x["seed"] for x in rows
                       if x["mode"] == "off" and x["need"] == 0.0})
    ok = bool(expected)
    parts = []
    for trig, share in ((GATE_TRIGGER, 0.70), (GATE_TRIGGER_MILD, 0.30)):
        cut = [x for x in rows if x["mode"] == "self_cut"
               and x["trigger"] == trig and x["share"] == share
               and x["need"] == 0.0]
        floor = [x for x in rows if x["mode"] == "off" and x["need"] == trig]
        if not cut or not floor:
            ok = False
            parts.append("threshold %g: gate cells missing, %d cut and %d floor"
                         % (trig, len(cut), len(floor)))
            continue
        bc = {x["seed"]: x for x in cut}
        bf = {x["seed"]: x for x in floor}
        seeds = sorted(set(bc) & set(bf))
        same = [all(bc[s][k] == bf[s][k] for k in fields) for s in seeds]
        complete = bool(seeds) and seeds == expected
        ok = ok and complete and not any(same)
        parts.append("threshold %g, share %.2f: identical on %d of %d seeds%s"
                     % (trig, share, sum(same), len(seeds),
                        "" if complete else "; paired seeds %s against the "
                        "control's %s" % (seeds, expected)))
        for s in seeds:
            c, f = bc[s], bf[s]
            parts.append(
                "  seed %d: cut volume %s against floor %s, gini %s against %s, "
                "stranded %d against departed %d"
                % (s, c["volume"], f["volume"], c["gini_close"],
                   f["gini_close"], c["stranded"], f["starved_close"]))
    return Criterion("A17-2  one threshold, two responses, two readings",
                     ok, " | ".join(parts))


def criterion_a17_4(rows: list) -> Criterion:
    """The shock arm: what the graph does with no trigger anywhere.

    Three states, fixed before the run.

      A discrete collapse appears at some share. **The graph on its own carries
      a cascade** and the income threshold is not necessary for one.

      Only a continuous decline appears. The graph degrades and does not
      collapse, which is a different object and gets reported as one.

      Nothing moves at any share. The cut is not large enough and the grid says
      which way to extend.

    **No line is drawn on the volume.** It is printed per share against the
    control at the same seed, and the reading is the shape of that sequence.
    """
    ctl = {x["seed"]: x for x in rows if x["mode"] == "off" and x["need"] == 0.0}
    parts = []
    for tg in EDGE_CUT_TARGETING:
        for share in sorted({x["share"] for x in rows if x["mode"] == "shock"
                             and x["targeting"] == tg}):
            cells = [x for x in rows if x["mode"] == "shock"
                     and x["share"] == share and x["targeting"] == tg]
            ratios = sorted(r(x["volume"] / ctl[x["seed"]]["volume"])
                            for x in cells if x["seed"] in ctl)
            parts.append(
                "%s share %.2f: volume over the control at the same seed %s | "
                "stranded %s | components %s | largest %s"
                % (tg, share, ratios,
                   sorted(x["stranded"] for x in cells),
                   sorted(x["components"] for x in cells),
                   sorted(x["largest_component"] for x in cells)))
    return Criterion("A17-4  what the graph does with no trigger anywhere",
                     True, " | ".join(parts))


def criterion_a17_5(rows: list) -> Criterion:
    """The two triggered arms, against each other and against the control.

    Three states, fixed before the run.

      The two arms move the same quantities the same way. Then cutting is one
      mechanism and who does the cutting does not matter.

      They move them in opposite directions. Then the direction of the cut is
      the mechanism, and a run and a withdrawal are different objects.

      Only one of them moves anything. That one is named and the other is
      reported as inert.

    **The quantities are printed per cell against the control at the same
    seed.** Nothing is thresholded.
    """
    ctl = {x["seed"]: x for x in rows if x["mode"] == "off" and x["need"] == 0.0}
    parts = []
    for mode in ("self_cut", "run"):
        for trig in sorted({x["trigger"] for x in rows if x["mode"] == mode}):
            row = []
            for share in sorted({x["share"] for x in rows
                                 if x["mode"] == mode and x["trigger"] == trig}):
                cells = [x for x in rows if x["mode"] == mode
                         and x["trigger"] == trig and x["share"] == share]
                vr = sorted(r(x["volume"] / ctl[x["seed"]]["volume"])
                            for x in cells if x["seed"] in ctl)
                gd = sorted(r(x["gini_close"] - ctl[x["seed"]]["gini_close"])
                            for x in cells if x["seed"] in ctl)
                row.append((share, vr[len(vr) // 2] if vr else None,
                            gd[len(gd) // 2] if gd else None))
            parts.append("%s trigger %g, (share, median volume over control, "
                         "median gini minus control): %s" % (mode, trig, row))
    return Criterion("A17-5  the two triggered arms against each other",
                     True, " | ".join(parts))


def criterion_a17_7(rows: list) -> Criterion:
    """Is the stranded set just the low-degree tail.

    A reading about the graph that turns out to be a reading about the degree
    distribution is the shape A16-6 was written for. This prints the mean
    opening out-degree of the stranded nodes against the rest, per cell that
    stranded anybody, and takes no ratio and draws no line.
    """
    with_stranded = [x for x in rows if x["stranded"] > 0]
    if not with_stranded:
        return Criterion("A17-7  is the stranded set the low-degree tail", True,
                         "no cell stranded anybody, so there is no set to check")
    pairs = sorted({(x["mode"], x["share"], x["trigger"],
                     x["stranded_mean_degree"], x["kept_mean_degree"],
                     x["stranded"]) for x in with_stranded})
    return Criterion(
        "A17-7  is the stranded set the low-degree tail", True,
        "%d of %d cells stranded somebody | (mode, share, trigger, stranded "
        "mean opening out-degree, kept mean, count): %s"
        % (len(with_stranded), len(rows), pairs[:20]))


#: A17-8's cut. A twentieth of the control's flow, unchanged from the guard's
#: first version.
THIN = 0.05

#: Discretionary flow at or below this share of the control's tail is the
#: residue of a trade that has ended. A37-7's line for "no trade left".
ENDED = 1e-9


def tail_state(x: dict, ctl_tail: float) -> str:
    """What the last TAIL rounds of one row carry, from its own accounting.

      no flow        nothing moved. E reads 0, the convention for an empty vector
      payroll only   the fixed roster is the whole flow, so E reads the roster
      residue        everything left is under ENDED of the control's tail
      thin trade     discretionary flow is left, at a low level of activity
    """
    vt, wt = x["volume_tail"], x["wages_tail"]
    if vt == 0.0:
        return "no flow"
    if abs(vt - wt) <= 1e-5 * vt:
        return "payroll only"
    if vt <= ENDED * ctl_tail:
        return "residue"
    return "thin trade"


def criterion_a17_8(rows: list) -> Criterion:
    """Cells on thin flow, named on both windows, and what their support reads.

    The support statistic is E = (sum F)^2 / sum F^2. **It does not move when
    every inflow is scaled by the same factor**, so a small flow does not make
    it a ratio of two small numbers: scaling a thin cell's last 25 rounds by
    1e-6 moves E by under 3e-14. What a thin cell's E reads is how the flow
    that is left is spread, and the thing to say about it is what that flow is.

    Two windows. E is read on the last TAIL rounds, so a cell is named when its
    cumulative flow **or** its last-TAIL flow is under THIN of the control's at
    the same seed. Naming on the cumulative flow alone passes a cell that traded
    for most of the run and stopped near the end.

    Each named cell is given one of ``tail_state``'s four states. **The flag
    reads the object**: it fails when a no-flow cell's E is anything but 0, a
    payroll-only cell's E is not a whole number, or a cell with flow in its tail
    reads E = 0. Each of those would mean the field does not hold what its code
    says it holds.
    """
    ctl = {x["seed"]: x for x in rows if x["mode"] == "off" and x["need"] == 0.0}
    named, bad = [], []
    for x in rows:
        if x["seed"] not in ctl or (x["mode"] == "off" and x["need"] == 0.0):
            continue
        c = ctl[x["seed"]]
        if c["volume"] <= 0 or c["volume_tail"] <= 0:
            bad.append("seed %d control has no flow" % x["seed"])
            continue
        cum = x["volume"] / c["volume"]
        tail = x["volume_tail"] / c["volume_tail"]
        if cum >= THIN and tail >= THIN:
            continue
        state = tail_state(x, c["volume_tail"])
        e = x["support_close"]
        key = (x["mode"], x["targeting"], x["share"], x["trigger"], x["need"],
               x["seed"])
        if state == "no flow" and e != 0.0:
            bad.append("%s no flow but E %r" % (key, e))
        if state == "payroll only" and abs(e - round(e)) > 1e-6:
            bad.append("%s payroll only but E %r" % (key, e))
        if state != "no flow" and e == 0.0:
            bad.append("%s flow in the tail but E 0" % (key,))
        named.append((state, "cumulative" if cum < THIN else "tail only",
                      key, r_sig(cum), r_sig(tail), e))
    counts = collections.Counter(n[0] for n in named)
    window = collections.Counter(n[1] for n in named)
    unique = len({n[2] for n in named})
    roster = sorted({n[5] for n in named if n[0] == "payroll only"})
    by_state = {s: sorted({n[5] for n in named if n[0] == s})
                for s in ("residue", "thin trade")}
    detail = (
        "%d rows (%d distinct cells) run under %g of the control's flow on the "
        "cumulative window or the last %d rounds: %d named on the cumulative "
        "window, %d on the tail only | tail state: %s | E on them reads 0 where "
        "nothing moved, the roster %s where payroll is the whole flow, %s on a "
        "residue under %g of the control's tail, and %s on thin trade | "
        "control E over its opening %s | tail-only cells: %s"
        % (len(named), unique, THIN, TAIL, window["cumulative"],
           window["tail only"], dict(sorted(counts.items())), roster,
           by_state["residue"], ENDED, by_state["thin trade"],
           sorted({ctl[s]["support_ratio"] for s in ctl}),
           sorted({(n[2], n[3], n[4]) for n in named
                   if n[1] == "tail only"}) or "none"))
    return Criterion(
        "A17-8  what support reads on thin flow", not bad,
        detail if not bad else " | ".join(bad[:8]))


def selftest() -> int:
    """Plant a wrong input under A17-2 and A17-8 and check each flag falls.

    Reads the record on disk and runs no model.
    """
    rows = json.loads(RECORD.read_text(encoding="utf-8"))["runs"]
    if any("volume_tail" not in x for x in rows):
        print("  the record predates volume_tail: run the grid first")
        return 1
    failures = []

    def expect(label, crit, want):
        got = crit.passed
        print("  [%s] %s: %s" % ("ok" if got == want else "WRONG", label,
                                 "PASS" if got else "FAIL"))
        if got != want:
            failures.append(label)

    expect("A17-2 on the record", criterion_a17_2(rows), True)
    drop4 = [x for x in rows if not (x["mode"] == "off" and x["need"] > 0
                                     and x["seed"] == 4)]
    expect("A17-2 with seed 4 gone from the floor arm", criterion_a17_2(drop4),
           False)
    apart = [x for x in rows
             if not (x["mode"] == "off" and x["need"] > 0 and x["seed"] < 3)
             and not (x["mode"] == "self_cut" and x["seed"] >= 3)]
    expect("A17-2 with the two sides sharing no seed", criterion_a17_2(apart),
           False)

    expect("A17-8 on the record", criterion_a17_8(rows), True)
    ctl = {x["seed"]: x for x in rows if x["mode"] == "off" and x["need"] == 0.0}
    for state, plant in (("no flow", 1.0), ("thin trade", 0.0),
                         ("payroll only", 74.5)):
        hit = next((i for i, x in enumerate(rows)
                    if x["seed"] in ctl and x["mode"] != "off"
                    and min(x["volume"] / ctl[x["seed"]]["volume"],
                            x["volume_tail"] / ctl[x["seed"]]["volume_tail"])
                    < THIN
                    and tail_state(x, ctl[x["seed"]]["volume_tail"]) == state),
                   None)
        if hit is None:
            print("  [--] no %s cell on the record to plant in" % state)
            continue
        bent = [dict(x) for x in rows]
        bent[hit]["support_close"] = plant
        expect("A17-8 with a %s cell's E set to %g" % (state, plant),
               criterion_a17_8(bent), False)
    print("\n  selftest %s" % ("failed: %s" % failures if failures else "ok"))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="one seed, writing to results/subset")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="plant wrong inputs under A17-2 and A17-8, no model run")
    args = ap.parse_args()

    if args.plan:
        for k, v in plan().items():
            print("  %-18s %s" % (k, v))
        return 0
    if args.selftest:
        return selftest()

    seeds = (0,) if args.smoke else SEEDS
    rows = attach_shares(run_grid(seeds=seeds)
                         + run_grid(seeds=seeds, cfgs=GATE_CONFIGS))

    crits = [criterion_a17_1(rows), criterion_a17_2(rows), criterion_a17_4(rows),
             criterion_a17_5(rows), criterion_a17_7(rows), criterion_a17_8(rows)]
    print("stage A17: edges cut out of the graph\n")
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
        "stage": "A17",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "the stratified carrier, floor off on every arm",
        "f2i": F2I, "rounds": ROUNDS, "elasticity": ELASTICITY,
        "plan": plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x["mode"], x["targeting"],
                                            x["trigger"], x["share"],
                                            x["need"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
