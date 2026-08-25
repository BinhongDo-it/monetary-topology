"""A15: which of these phenomena are transcribed, and which fall out.

Three things look like three questions and share one discriminant:

    remove the absorbing wall and see whether the phenomenon is still there.

The instrument is already on the shelf. ``SubsistenceSpec.mode`` carries two
exit rules. ``exit`` has the wall, ``drawdown`` does not, and nothing else
differs between them.

Two of the three have readings that are known before this stage runs, and that
is exactly what makes them useful here. They are the rulers the third gets
measured against.

  Ruler one, transcribed and inert.
      Flipping ``reversible`` on its own moves the closing Gini by 0.0005 on
      A12's carrier, against 0.32 for ``cut_payroll``. A switch that quotes the
      manuscript and does no work reads near zero on this scale.

  Ruler two, written by nobody.
      On the complete graph at need = 1.0, ``exit`` puts 200 of 200 below the
      line and ``drawdown`` puts 0 of 200. No line anywhere states that one
      departure causes another. It falls out of the graph.

  The open question.
      Whether any subset of mechanisms sends the three inequality measures in
      three directions at once. Nothing on record answers it. The floor on its
      own does not: under ``drawdown`` A11 moves the closing Gini from 0.9367 to
      0.9370. And no criterion in this repository has ever read ``top10``.

There is a fourth reading that belongs with the rulers rather than with the
open question, and it was added after the first three were written down.

  The wage level.
      Scarring in the wage sense is a different object from the two booleans.
      The distribution cannot scar here: wages are split evenly, so no single
      node has a wage that could fall. The level can, and its mechanism is
      already in the code. ``WageChannel.elasticity`` makes the bill a function
      of last round's production-layer spending, so a contraction cuts the bill
      and the cut feeds back. A8 measured that channel at 10.6 per cent on the
      payment rate and 0.0 per cent on the closing Gini, which is why this one
      is read on the bill and not on the Gini.

Every quantity this stage varies is imported from A12 at run time rather than
restated, for the reason A12 imports its carrier from A8: two stages that read
the same curve must not be able to drift apart on what the curve is drawn over.

This file is stage one of the script. It carries the two structural criteria
and the run plan, and it deliberately does not carry the measuring criteria
yet, so that the imports and the plan can be read before anything is spent.

Usage

    python experiments/a15_transcribed_vs_implied.py --plan
    python experiments/a15_transcribed_vs_implied.py --selftest
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

RECORD = RESULTS / "a15_transcribed_vs_implied.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: A12 is the carrier and the arm table. Loading the module rather than copying
#: any of it is what makes A15-1 a check on this stage instead of a check on
#: whoever last edited a literal.
_A12 = _load(ROOT / "experiments" / "a12_mechanisms.py", "_a12")

EDGES = _A12.EDGES
ELASTICITIES = _A12.ELASTICITIES
BASE_CARRIER = _A12.BASE_CARRIER
carrier_at = _A12.carrier_at
arms_for = _A12.arms_for
need_for = _A12.need_for
one_run = _A12.one_run
FLOOR_NEED = _A12.FLOOR_NEED
r = _A12.r

#: The two node counts. A14-5 measured that at two hundred nodes the top one
#: per cent is two nodes, so a top-share reading there rests on two numbers.
#: The larger carrier is run for that reason and for no other.
NODE_COUNTS = (200, 1000)

#: A12 runs one seed and sweeps elasticity, so its grid is
#: arms * edges * elasticities = 14 * 9 * 5 = 630 cells, all at seed 0. The
#: main grid here is that grid at two node counts, on the same seed, which is
#: what makes the control arm reproduce A12's cells to the last bit rather than
#: to within a seed.
#:
#: **Seeds are not spent up front, and that is a cost decision with a rule
#: behind it.** The open question is whether any subset of mechanisms sends the
#: three measures in three directions. If no subset does, seeds bought in
#: advance would have bought nothing. If one does, that subset alone gets the
#: repetitions, which is a handful of cells rather than fourteen arms.
MAIN_SEED = 0
FOLLOW_UP_SEEDS = 5
ROUNDS = 300

#: A11's floor grid, reused rather than restated for the same reason A12's
#: carrier is. The wage sweep runs on the complete graph, which is where the
#: cascade is all-or-nothing and therefore where a wage level has the furthest
#: to fall.
NEED_MULTIPLES = (0.05, 0.20, 0.50, 1.00)
GRACES = (1, 5)

#: The wage sweep's second axis. Zero is ``WageChannel``'s own no-feedback
#: control, and a positive value is needed because at zero the bill is
#: disconnected from spending and this criterion reads zero by construction.
WAGE_ELASTICITIES = (0.0, 1.0)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def criterion_a15_1() -> Criterion:
    """Structural: the grid, the carrier and the arm table are A12's own.

    Two halves. The first is that this file holds no literal copy of any of
    them, which is checked by identity against the loaded module. The second is
    that A12's record on disk was written on the same grid, which catches the
    case where A12 has been edited since it last ran and this stage would
    otherwise be comparing against a record that no longer describes the code.
    """
    ok = True
    parts = []

    same = (
        EDGES is _A12.EDGES
        and ELASTICITIES is _A12.ELASTICITIES
        and BASE_CARRIER is _A12.BASE_CARRIER
    )
    ok = ok and same
    parts.append(
        "grid and carrier taken from the loaded module by identity: %s" % same
    )

    path = RESULTS / "a12_mechanisms.json"
    if not path.exists():
        ok = False
        parts.append("a12_mechanisms.json is not on disk, so the grid cannot be checked against it")
        return Criterion("A15-1  one grid, imported not restated", ok, "; ".join(parts))

    rec = json.loads(path.read_text(encoding="utf-8"))
    rec_edges = sorted({int(row["f2i"]) for row in rec["runs"]})
    rec_elast = sorted({float(row["elasticity"]) for row in rec["runs"]})
    rec_arms = sorted({row["arm"] for row in rec["runs"]})
    here_arms = sorted(arms_for(need_for(BASE_CARRIER)))

    edges_ok = rec_edges == sorted(int(e) for e in EDGES)
    elast_ok = rec_elast == sorted(float(x) for x in ELASTICITIES)
    arms_ok = rec_arms == here_arms
    ok = ok and edges_ok and elast_ok and arms_ok
    parts.append("edge grid matches the record: %s (%s)" % (edges_ok, rec_edges))
    parts.append("elasticities match: %s (%s)" % (elast_ok, rec_elast))
    parts.append("arm table matches: %s (%d arms)" % (arms_ok, len(rec_arms)))

    return Criterion("A15-1  one grid, imported not restated", ok, "; ".join(parts))


def criterion_a15_6() -> Criterion:
    """Structural: how many nodes a top share is actually averaging over.

    Printed rather than judged against a threshold. A14-5 already established
    that the count at the registered carrier is two, and the point of printing
    it here is that A15's open question reads three inequality measures at once
    and one of them rests on that count.
    """
    rows = []
    for n in NODE_COUNTS:
        c = carrier_at(n)
        rows.append(
            "n=%d (carrier %d): top 1%% is %d node(s), top 10%% is %d node(s)"
            % (n, c.nodes, max(1, c.nodes // 100), max(1, c.nodes // 10))
        )
    return Criterion(
        "A15-6  how many nodes each top share averages over", True, "; ".join(rows)
    )


#: The two arms that isolate one boolean each, against the same base arm.
#: ``floor`` is the plain floor: cut_payroll False, reversible False, mode exit.
#: ``floor payroll kept`` differs from it in ``reversible`` alone and
#: ``floor payroll severed`` in ``cut_payroll`` alone, so the two differences
#: are one switch each and not a bundle.
RULER_BASE = "floor"
RULER_PAIRS = (
    ("reversible", "floor payroll kept"),
    ("cut_payroll", "floor payroll severed"),
)


def _cells(runs: list[dict], arm: str) -> dict:
    return {(int(x["f2i"]), float(x["elasticity"])): x for x in runs if x["arm"] == arm}


def criterion_a15_2() -> Criterion:
    """Ruler one, read off A12's record. Nothing is run.

    A12-6 already ran both corners. What this adds is the per-cell spread: A12
    reported one closing Gini per arm, and a ruler wants to know whether the
    near-zero holds on every cell or only on the one that got printed.

    The verdict is structural, that the two arms cover the same cells as the
    base arm. **The magnitudes are printed and no line is drawn on them**, which
    is what a ruler is for.
    """
    path = RESULTS / "a12_mechanisms.json"
    if not path.exists():
        return Criterion("A15-2  ruler one: a transcribed switch that does no work",
                         False, "a12_mechanisms.json is not on disk")

    runs = json.loads(path.read_text(encoding="utf-8"))["runs"]
    base = _cells(runs, RULER_BASE)
    ok = bool(base)
    parts = ["base arm %r on %d cells" % (RULER_BASE, len(base))]

    for switch, arm in RULER_PAIRS:
        other = _cells(runs, arm)
        same = set(other) == set(base)
        ok = ok and same
        diffs = sorted(
            ((abs(other[k]["gini_close"] - base[k]["gini_close"]), k) for k in base),
            reverse=True,
        )
        worst = "; ".join(
            "f2i=%d e=%g -> %.6f" % (k[0], k[1], d) for d, k in diffs[:3]
        )
        parts.append(
            "%s alone (%r vs %r), same cells: %s. Closing-Gini gap over %d cells: "
            "max %.6f, median %.6f, min %.6f. Three widest cells: %s"
            % (switch, arm, RULER_BASE, same, len(diffs),
               diffs[0][0], diffs[len(diffs) // 2][0], diffs[-1][0], worst)
        )

    return Criterion("A15-2  ruler one: a transcribed switch that does no work",
                     ok, " | ".join(parts))


def criterion_a15_3() -> Criterion:
    """Ruler two, read off A11's two records. Nothing is run.

    The complete graph under both exit rules, across the same floor grid. Both
    out-of-market counts are printed for both rules rather than one each,
    because the two rules do not populate the same field: ``exit`` moves a
    membership flag and ``drawdown`` re-reads a spending rule every round, so a
    single column would be empty on one side and look like a reading.
    """
    names = ("a11_subsistence.json", "a11_subsistence_drawdown.json")
    recs = {}
    for n in names:
        path = RESULTS / n
        if not path.exists():
            return Criterion("A15-3  ruler two: a cascade nobody wrote", False,
                             "%s is not on disk" % n)
        recs[n] = json.loads(path.read_text(encoding="utf-8"))

    ok = True
    parts = []
    grids = {n: tuple(recs[n]["need_multiples"]) for n in names}
    same_grid = len(set(grids.values())) == 1
    ok = ok and same_grid
    parts.append("both records on one floor grid: %s %s" % (same_grid, grids[names[0]]))

    rows = []
    for n in names:
        rule = recs[n]["exit_rule"]
        comp = [x for x in recs[n]["runs"] if x["graph"] == "complete"]
        if not comp:
            ok = False
            parts.append("%s has no complete-graph rows" % n)
            continue
        n_nodes = comp[0]["financial_nodes"] + comp[0]["production_nodes"]
        for mult in sorted({x["need_multiple"] for x in comp}):
            for grace in sorted({x["grace"] for x in comp if x["need_multiple"] == mult}):
                cell = [x for x in comp
                        if x["need_multiple"] == mult and x["grace"] == grace]
                rows.append(
                    "%s need=%.2f grace=%d n=%d: starved %s, below-floor at close %s, "
                    "below-floor at peak %s"
                    % (rule, mult, grace, n_nodes,
                       sorted(x["starved"] for x in cell),
                       sorted(x["below_floor_close"] for x in cell),
                       sorted(x["below_floor_peak"] for x in cell))
                )
    parts.extend(rows)
    return Criterion("A15-3  ruler two: a cascade nobody wrote", ok, " | ".join(parts))


# -- the pinpoint repetition -------------------------------------------------
#
# A15-2 found the reversible switch reading full scale on exactly one cell of
# forty-five, at one seed. One cell at one seed does not carry a sentence, and
# the sentence it would carry is the most valuable thing this stage has, so the
# repetitions are spent here and nowhere else. That ordering is the design's
# own: buy seeds for the subset that produced something, not for the grid.
#
# The neighbourhood is one step wider than the cell in both directions, so a
# reading confined to the corner is distinguishable from one with a gradient.
# ``f2i = 20`` is the grid point below 30 and ``e = 0.5`` the wage elasticity
# above 0.
PIN_F2I = (20, 30)
PIN_ELASTICITIES = (0.0, 0.5)
PIN_SEEDS = (0, 1, 2, 3, 4)

#: Four arms rather than the two that make the contrast. ``off`` and
#: ``floor drawdown`` cost the same as the other two and they are what makes
#: the contrast readable: the question is not only how far ``reversible`` moves
#: the number, it is whether moving it lands back on the no-wall arm.
PIN_ARMS = ("off", "floor", "floor payroll kept", "floor drawdown")


def run_pinpoint(seeds: tuple = PIN_SEEDS, f2is: tuple = PIN_F2I,
                 elasticities: tuple = PIN_ELASTICITIES) -> list:
    rows = []
    for seed in seeds:
        for f2i in f2is:
            for e in elasticities:
                for arm in PIN_ARMS:
                    row = one_run(arm, f2i, e, ROUNDS, seed)
                    row["seed"] = int(seed)
                    # **The batch label is load-bearing and it was missing.**
                    # This batch and the shallow one below share arm names,
                    # ``f2i`` and ``elasticity``, and they differ only in the
                    # floor need, which no field carried. Twenty rows in the
                    # first written record had a duplicate key and nothing in
                    # the file said which floor each belonged to.
                    row["batch"] = "pinpoint"
                    row["floor_need"] = r(FLOOR_NEED)
                    rows.append(row)
    return rows


def criterion_a15_2b(rows: list) -> Criterion:
    """Does the one cell survive four more seeds.

    Three states, fixed before the run.

      The gap holds at every seed. The cell is a property of the carrier at
      that point and the sentence stands.

      The gap appears at some seeds and not others. It is a property of the
      draw. The rate gets reported and the general sentence does not get
      written.

      The gap does not reproduce at seed zero. Then this harness disagrees with
      A12's record on A12's own cell, and nothing here is readable until that is
      resolved. That is discipline 19 and it costs nothing extra.

    The verdict is the reproduction at seed zero, which is structural. **The
    gaps themselves are printed with no line drawn on them.**
    """
    by = {(x["seed"], x["f2i"], x["elasticity"], x["arm"]): x for x in rows}
    parts = []
    ok = True

    a12 = {(x["f2i"], x["elasticity"], x["arm"]): x
           for x in json.loads(
               (RESULTS / "a12_mechanisms.json").read_text(encoding="utf-8"))["runs"]}
    checked = repro = 0
    worst = ("", 0.0)
    for (seed, f2i, e, arm), row in by.items():
        if seed != MAIN_SEED or (f2i, e, arm) not in a12:
            continue
        ref = a12[(f2i, e, arm)]
        checked += 1
        same = all(row[k] == ref[k] for k in
                   ("gini_close", "m_ratio", "starved", "support_ratio", "wage_funding"))
        repro += bool(same)
        if not same:
            ok = False
            d = abs(row["gini_close"] - ref["gini_close"])
            if d > worst[1]:
                worst = ("f2i=%d e=%g %s" % (f2i, e, arm), d)
    parts.append("seed %d reproduces A12's record on %d/%d shared cells%s"
                 % (MAIN_SEED, repro, checked,
                    "" if ok else "; widest disagreement %s %.6f" % worst))

    # The hit rate per (f2i, e), and then the shape of the hits. The rate is
    # what the design's second state asks for. The shape is what turned out to
    # be the harder fact: the catches do not sit on a continuum with the
    # misses, they sit in a second cluster with nothing in between, so the
    # gap between the two clusters is printed as an object rather than
    # summarised.
    kept_starved, kept_m, hits = [], [], {}
    for (seed, f2i, e, arm), row in by.items():
        if arm != "floor payroll kept":
            continue
        kept_starved.append((row["starved"], f2i, e, seed))
        kept_m.append((row["m_ratio"], f2i, e, seed))
        base = by[(seed, f2i, e, RULER_BASE)]
        caught = row["starved"] < base["starved"] * 0.75
        hits.setdefault((f2i, e), [0, 0])
        hits[(f2i, e)][1] += 1
        hits[(f2i, e)][0] += int(caught)
    if hits:
        parts.append("catch rate per cell: " + ", ".join(
            "f2i=%d e=%g %d/%d" % (f2i, e, a, b)
            for (f2i, e), (a, b) in sorted(hits.items())))
        lo = sorted(x for x in kept_m if x[0] < 5.0)
        hi = sorted(x for x in kept_m if x[0] >= 5.0)
        if lo and hi:
            parts.append(
                "kept m_ratio splits in two with nothing between: caught %s "
                "(n=%d, max %.3f), missed n=%d (min %.3f), ratio across the "
                "empty band %.1fx"
                % ([round(x[0], 3) for x in lo], len(lo), lo[-1][0], len(hi),
                   hi[0][0], hi[0][0] / max(lo[-1][0], 1e-9)))
        parts.append("kept starved, caught %s | missed %s"
                     % (sorted(x[0] for x in kept_starved if x[0] < 100),
                        sorted(x[0] for x in kept_starved if x[0] >= 100)))

    seen_f2i = sorted({k[1] for k in by})
    seen_e = sorted({k[2] for k in by})
    seen_seed = sorted({k[0] for k in by})
    for f2i in seen_f2i:
        for e in seen_e:
            for seed in seen_seed:
                if (seed, f2i, e, PIN_ARMS[0]) not in by:
                    continue
                g = {a: by[(seed, f2i, e, a)]["gini_close"] for a in PIN_ARMS}
                s = {a: by[(seed, f2i, e, a)]["starved"] for a in PIN_ARMS}
                m = {a: by[(seed, f2i, e, a)]["m_ratio"] for a in PIN_ARMS}
                parts.append(
                    "f2i=%d e=%g seed=%d: gap(reversible) %.6f, kept-vs-drawdown %.6f "
                    "| gini off %.4f floor %.4f kept %.4f drawdown %.4f "
                    "| starved %d/%d/%d/%d | m_ratio %.3f/%.3f/%.3f/%.3f"
                    % (f2i, e, seed,
                       abs(g["floor payroll kept"] - g["floor"]),
                       abs(g["floor payroll kept"] - g["floor drawdown"]),
                       g["off"], g["floor"], g["floor payroll kept"], g["floor drawdown"],
                       s["off"], s["floor"], s["floor payroll kept"], s["floor drawdown"],
                       m["off"], m["floor"], m["floor payroll kept"], m["floor drawdown"]))

    return Criterion("A15-2b  does the one cell survive four more seeds", ok,
                     " | ".join(parts))


# -- the main question -------------------------------------------------------
#
# **The main grid needs no runs.** A12's two records are it: 630 rows each, one
# per arm per cell, at seed 0, and they carry the four top-share fields because
# those fields were added to A12 for this stage. So A15-4 and A15-5 read two
# files.
#
# The measures are compared against the control arm cell by cell, and the sign
# is taken on the recorded six-decimal values with no threshold anywhere: a
# sign is three-valued because an exact tie is a third thing and not a small
# move. That is also what makes the design's three states land: three pairwise
# distinct signs, all three equal, or two against one.
CONTROL_ARM = "off"
MEASURES = ("gini_close", "top1_wealth", "top10_wealth")

#: The shape the manuscript's 1929 material describes, in this stage's measures:
#: the top percentile falls while the top decile and the Gini rise. Named here
#: so that its frequency is a printed number rather than something read off a
#: histogram afterwards.
TARGET = {"top1_wealth": -1, "top10_wealth": +1, "gini_close": +1}

MAIN_RECORDS = (("n=200", "a12_mechanisms.json"),
                ("n=1000", "a12_mechanisms_n1000.json"))


def _sign(a: float, b: float) -> int:
    return (a > b) - (a < b)


def _mechanisms(arm: str, arms: dict) -> frozenset:
    """The switches an arm turns on, as labels, from the arm table itself."""
    floor, write, transfer = arms[arm]
    out = set()
    if floor is None:
        out |= {"floor", "floor:exit"}
    elif floor.need > 0.0:
        out.add("floor")
        out.add("floor:%s" % floor.mode)
        if floor.cut_payroll:
            out.add("cut_payroll")
        if floor.reversible:
            out.add("reversible")
    if write is not None and getattr(write, "rate", 0.0) > 0.0:
        out.add("writeoff")
        if getattr(write, "refill", False):
            out.add("writeoff:refill")
    if transfer > 0.0:
        out.add("transfer")
    return frozenset(out)


#: The opening counterpart of each measure, so the same three quantities can be
#: read over the run rather than across arms.
OPEN_OF = {"gini_close": "gini_open",
           "top1_wealth": "top1_open",
           "top10_wealth": "top10_open"}


def _triples_over_time(runs: list) -> dict:
    """(arm, f2i, elasticity) -> the three signs from opening to close.

    **This is the operationalisation the historical statement has.** The 1929
    material is a divergence in time: between 1929 and 1933 the top percentile
    fell while the top decile and urban inequality rose. Reading the same thing
    across arms answers a different question, which is what a mechanism adds
    relative to its absence, so both are reported and this one is first.
    """
    return {(x["arm"], x["f2i"], x["elasticity"]):
            {m: _sign(x[m], x[OPEN_OF[m]]) for m in MEASURES}
            for x in runs}


def _triples(runs: list) -> dict:
    """(arm, f2i, elasticity) -> the three signs against the control cell."""
    ctl = {(x["f2i"], x["elasticity"]): x for x in runs if x["arm"] == CONTROL_ARM}
    out = {}
    for x in runs:
        if x["arm"] == CONTROL_ARM:
            continue
        key = (x["f2i"], x["elasticity"])
        if key not in ctl:
            continue
        out[(x["arm"], key[0], key[1])] = {
            m: _sign(x[m], ctl[key][m]) for m in MEASURES
        }
    return out


def criterion_a15_4() -> Criterion:
    """The open question, read off A12's two records. Nothing is run.

    Three states, from the design.

      The three signs are pairwise distinct on some cell. That subset sends the
      three measures three ways and the stage has its answer.

      All three signs agree everywhere. The measures co-move on this carrier and
      nothing here produces the pattern.

      Two against one. Partial, and the split is reported by which measure is
      the odd one out.

    **A fourth state was missing and the run found it.** A zero in the first
    three is only a reading if the target could have been hit, and on this
    carrier it could not: ``top1`` falling and ``gini`` rising co-occur in zero
    of 1,260 arm-cells across both node counts, so the shape was out of reach
    before anything ran. The pairwise decomposition below is what makes that
    visible instead of letting an unreachable zero arrive as a verdict.
    """
    parts, ok = [], True
    for label, name in MAIN_RECORDS:
        path = RESULTS / name
        if not path.exists():
            return Criterion("A15-4  do the three measures ever go three ways",
                             False, "%s is not on disk" % name)
        runs = json.loads(path.read_text(encoding="utf-8"))["runs"]

        # First, over the run, which is what the historical statement is about.
        tt = _triples_over_time(runs)
        t_distinct = {k: v for k, v in tt.items() if len(set(v.values())) == 3}
        t_target = {k: v for k, v in tt.items()
                    if all(v[m] == s for m, s in TARGET.items())}
        parts.append(
            "%s over the run, %d arm-cells: three ways %d, 1929 shape %d"
            % (label, len(tt), len(t_distinct), len(t_target)))

        # A zero is only a reading if the thing that read zero could have been
        # non-zero. The whole histogram is printed, and then the target is
        # decomposed into its three pairwise conditions, so that a zero which
        # was unreachable is visible as a zero on one of the pairs rather than
        # arriving as a verdict about the framework.
        hist = {}
        for v in tt.values():
            hist[tuple(v[m] for m in MEASURES)] = hist.get(
                tuple(v[m] for m in MEASURES), 0) + 1
        parts.append("%s sign triples that occur, order %s: %s (of 27 possible)"
                     % (label, MEASURES,
                        sorted(hist.items(), key=lambda kv: -kv[1])))
        pairs = [
            ("top1 down and gini up", lambda v: v["top1_wealth"] < 0 and v["gini_close"] > 0),
            ("top10 up and gini up", lambda v: v["top10_wealth"] > 0 and v["gini_close"] > 0),
            ("top1 down and top10 up", lambda v: v["top1_wealth"] < 0 and v["top10_wealth"] > 0),
        ]
        parts.append("%s the target decomposed into pairs: %s"
                     % (label, [(n, sum(1 for v in tt.values() if f(v)))
                                for n, f in pairs]))
        for tag, d in (("over the run, three ways", t_distinct),
                       ("over the run, 1929 shape", t_target)):
            if d:
                parts.append("%s %s produced by %s"
                             % (label, tag, sorted({k[0] for k in d})))

        tri = _triples(runs)
        if not tri:
            ok = False
            parts.append("%s: no control cells to compare against" % label)
            continue
        distinct = {k: v for k, v in tri.items() if len(set(v.values())) == 3}
        agree = {k: v for k, v in tri.items() if len(set(v.values())) == 1}
        split = {k: v for k, v in tri.items() if len(set(v.values())) == 2}
        target = {k: v for k, v in tri.items()
                  if all(v[m] == s for m, s in TARGET.items())}
        parts.append(
            "%s over %d arm-cells: three ways %d, all one way %d, two-against-one %d, "
            "and the 1929 shape (top1 down, top10 up, gini up) %d"
            % (label, len(tri), len(distinct), len(agree), len(split), len(target)))
        for tag, d in (("three ways", distinct), ("1929 shape", target)):
            if d:
                arms_hit = sorted({k[0] for k in d})
                parts.append("%s %s produced by %d arm(s): %s"
                             % (label, tag, len(arms_hit), arms_hit))
        odd = {}
        for v in split.values():
            vals = list(v.values())
            for m in MEASURES:
                if vals.count(v[m]) == 1:
                    odd[m] = odd.get(m, 0) + 1
        if odd:
            parts.append("%s odd measure out, when two against one: %s"
                         % (label, sorted(odd.items(), key=lambda kv: -kv[1])))
    return Criterion("A15-4  do the three measures ever go three ways", ok,
                     " | ".join(parts))


def criterion_a15_5() -> Criterion:
    """Which switches are in every subset that produced something.

    Prints the intersection and the union. **No line is drawn on either**: a
    mechanism appearing in every producing arm is necessary on this grid and
    that is a statement about this grid, so the sets are the reading.
    """
    arms = arms_for(need_for(BASE_CARRIER))
    parts, ok = [], True
    for label, name in MAIN_RECORDS:
        path = RESULTS / name
        if not path.exists():
            return Criterion("A15-5  which switches every producing subset shares",
                             False, "%s is not on disk" % name)
        runs = json.loads(path.read_text(encoding="utf-8"))["runs"]
        tri = _triples(runs)
        tt = _triples_over_time(runs)
        producing = sorted(
            {k[0] for k, v in tri.items()
             if len(set(v.values())) == 3 or all(v[m] == s for m, s in TARGET.items())}
            | {k[0] for k, v in tt.items()
               if len(set(v.values())) == 3 or all(v[m] == s for m, s in TARGET.items())}
        )
        if not producing:
            parts.append("%s: no arm produced either shape, so there is no "
                         "intersection to take" % label)
            continue
        sets = [_mechanisms(a, arms) for a in producing if a in arms]
        inter = set.intersection(*[set(s) for s in sets]) if sets else set()
        union = set.union(*[set(s) for s in sets]) if sets else set()
        parts.append("%s producing arms %s | in every one: %s | in at least one: %s"
                     % (label, producing, sorted(inter) or "nothing",
                        sorted(union) or "nothing"))
    return Criterion("A15-5  which switches every producing subset shares", ok,
                     " | ".join(parts))


def criterion_a15_7(rows: list) -> Criterion:
    """The wage level, on the rows the pinpoint repetition already produced.

    **The carrier in the design was wrong and three probe runs said so.** It
    named the complete graph, on the reasoning that a wage level has the
    furthest to fall where the cascade is all-or-nothing. On that graph the
    answer is forced: at a floor of 0.20 nobody leaves at all, at 1.00 everyone
    does, and ``reversible`` on and off return the same numbers to the last
    digit at both. Nothing can be read there.

    The stratified carrier has all three states, and it has them on rows that
    are already on disk, because ``wage_owed_ratio`` is the mean of the last
    twenty-five rounds' bill over the opening bill, which is exactly the
    closing level this criterion wants.

    The verdict is structural: at ``e = 0`` the bill is disconnected from
    spending by ``WageChannel``'s own definition, so every arm must read exactly
    1.0000. **A control that does not read its forced value is a broken
    control**, and the levels at ``e > 0`` are printed with no line on them.
    """
    if not rows:
        return Criterion("A15-7  does the wage level come back", False, "no rows")
    by = {(x["seed"], x["f2i"], x["elasticity"], x["arm"]): x for x in rows}
    parts, ok = [], True

    flat = [v["wage_owed_ratio"] for k, v in by.items() if k[2] == 0.0]
    if flat:
        exact = all(v == 1.0 for v in flat)
        ok = ok and exact
        parts.append("control: at e=0 the bill is constant by definition, and "
                     "%d/%d rows read exactly 1.0000" % (sum(1 for v in flat if v == 1.0),
                                                         len(flat)))

    for f2i in sorted({k[1] for k in by}):
        for e in sorted({k[2] for k in by}):
            if e == 0.0:
                continue
            for seed in sorted({k[0] for k in by}):
                if (seed, f2i, e, RULER_BASE) not in by:
                    continue
                a = by[(seed, f2i, e, RULER_BASE)]
                b = by[(seed, f2i, e, "floor payroll kept")]
                loss_a, loss_b = 1.0 - a["wage_owed_ratio"], 1.0 - b["wage_owed_ratio"]
                recovered = (loss_a - loss_b) / loss_a if loss_a > 0 else float("nan")
                parts.append(
                    "f2i=%d e=%g seed=%d: closing bill floor %.4f kept %.4f "
                    "(loss %.4f vs %.4f, share of the loss the return takes back "
                    "%.3f), starved %d vs %d"
                    % (f2i, e, seed, a["wage_owed_ratio"], b["wage_owed_ratio"],
                       loss_a, loss_b, recovered, a["starved"], b["starved"]))

    parts.append("horizon caveat: wage_owed_ratio is the last twenty-five rounds' "
                 "mean over the opening bill, and on the one cell where the return "
                 "catches the bill is still climbing at the end, so the residual "
                 "gap is a reading at 300 rounds and not a limit")
    return Criterion("A15-7  does the wage level come back", ok, " | ".join(parts))



# -- the main question, re-asked at the depth where the shape lives -----------
#
# A15-4 read A12's grid and found the target unreachable. A16 then measured why:
# that grid holds the floor at 0.20, and at 0.20 the nodes that leave freeze
# holding 94 per cent of the closing stock, so every concentration measure moves
# with that accumulation and none of them can separate. At 0.05 the leavers hold
# 0.3 per cent and the same three measures do separate. **The carrier was never
# the problem; the grid was missing the axis.**
#
# A16 could not answer A15-4's actual question, because A16's arms carry the
# floor and the obligation and nothing else, while A15-4 asks which subset of
# {floor, write-off, rewiring} produces the shape. So the question comes back
# here, on A12's fourteen arms, moved to the shallow floor.
#
# **The floor arm has to be built explicitly.** ``arms_for`` returns ``None``
# for it and ``one_run`` then fills in ``FLOOR_MULTIPLE`` regardless of the need
# it was handed, so passing a shallow arm table alone would move thirteen arms
# and leave that one at 0.20.
SHALLOW_MULTIPLE = 0.05
SHALLOW_F2I = 30
SHALLOW_ELASTICITY = 0.5


def shallow_arms() -> dict:
    from monetary_topology.network import SubsistenceSpec
    need = SHALLOW_MULTIPLE * 100.0 / BASE_CARRIER.nodes
    arms = dict(arms_for(need))
    floor, write, transfer = arms["floor"]
    if floor is None:
        arms["floor"] = (SubsistenceSpec(need=need), write, transfer)
    return arms


def run_shallow(seeds: tuple = PIN_SEEDS) -> list:
    arms = shallow_arms()
    rows = []
    for seed in seeds:
        for arm in arms:
            row = one_run(arm, SHALLOW_F2I, SHALLOW_ELASTICITY, ROUNDS, seed, arms)
            row["seed"] = int(seed)
            row["batch"] = "shallow"
            row["floor_need"] = r(SHALLOW_MULTIPLE * 100.0 / BASE_CARRIER.nodes)
            rows.append(row)
    return rows


def criterion_a15_4b(rows: list) -> Criterion:
    """The open question, at the depth where the shape exists.

    Four states now, and the fourth is the one A16 added.

      A subset produces it, no single mechanism in it does, and it does not
      contain the exit. The pattern is an interaction and a change in the
      sample is not necessary for it.

      Only exit-bearing subsets produce it. The sample change is necessary and
      the orthodox reading wins on this carrier, reported as it stands.

      No subset produces it. Reported, and no mechanism is added to reach it.

      **Every subset produces it, on the same seeds.** Then it is the graph
      draw and not the mechanism, which is what A16-8 found along the floor:
      four hits in twenty at every depth in the shallow regime, the same four
      cells each time.

    Verdict structural: the fourteen arms ran at every seed. **The counts are
    printed with no line on them.**
    """
    def sg(a, b):
        return (a > b) - (a < b)
    if not rows:
        return Criterion("A15-4b  the question at the depth where the shape is",
                         False, "no rows")
    arms = sorted({x["arm"] for x in rows})
    seeds = sorted({x["seed"] for x in rows})
    ok = all(len([x for x in rows if x["arm"] == a]) == len(seeds) for a in arms)
    per, hit_seeds = {}, {}
    for a in arms:
        cells = [x for x in rows if x["arm"] == a]
        hits = [x for x in cells
                if sg(x["top1_wealth"], x["top1_open"]) < 0
                and sg(x["top10_wealth"], x["top10_open"]) > 0
                and sg(x["gini_close"], x["gini_open"]) > 0]
        per[a] = (len(hits), len(cells))
        hit_seeds[a] = sorted({x["seed"] for x in hits})
    producing = [a for a in arms if per[a][0] > 0]
    all_hit_seeds = sorted({s for a in producing for s in hit_seeds[a]})
    parts = [
        "%d arms x %d seeds at floor %.2f, f2i=%d, e=%g"
        % (len(arms), len(seeds), SHALLOW_MULTIPLE, SHALLOW_F2I, SHALLOW_ELASTICITY),
        "1929 shape by arm: %s" % sorted(per.items(), key=lambda kv: -kv[1][0]),
        "arms producing it: %d of %d" % (len(producing), len(arms)),
        "the seeds it lands on, over every producing arm: %s" % all_hit_seeds,
        "arms producing nothing: %s" % [a for a in arms if per[a][0] == 0],
    ]
    return Criterion("A15-4b  the question at the depth where the shape is",
                     ok, " | ".join(parts))


def criterion_a15_5b(rows: list) -> Criterion:
    """Which switches every producing arm shares, at the shallow floor.

    Prints the intersection and the union. **A mechanism in every producing arm
    is necessary on this grid and that is a statement about this grid**, so the
    sets are the reading and no line is drawn on them.
    """
    def sg(a, b):
        return (a > b) - (a < b)
    arms = shallow_arms()

    def switches(name: str) -> set:
        floor, write, transfer = arms[name]
        out = set()
        if floor is not None and floor.need > 0.0:
            out.add("floor")
            out.add("floor:%s" % floor.mode)
            if floor.cut_payroll:
                out.add("cut_payroll")
            if floor.reversible:
                out.add("reversible")
        if write is not None and getattr(write, "rate", 0.0) > 0.0:
            out.add("writeoff")
            if getattr(write, "refill", False):
                out.add("writeoff:refill")
        if transfer > 0.0:
            out.add("transfer")
        return out

    producing = sorted({x["arm"] for x in rows
                        if sg(x["top1_wealth"], x["top1_open"]) < 0
                        and sg(x["top10_wealth"], x["top10_open"]) > 0
                        and sg(x["gini_close"], x["gini_open"]) > 0})
    if not producing:
        return Criterion("A15-5b  which switches every producing arm shares",
                         True, "no arm produced the shape, so there is no "
                               "intersection to take")
    sets = [switches(a) for a in producing]
    inter = set.intersection(*sets)
    union = set.union(*sets)
    quiet = sorted(set(arms) - set(producing))
    return Criterion(
        "A15-5b  which switches every producing arm shares", True,
        "producing arms %s | in every one: %s | in at least one: %s | arms that "
        "produced nothing: %s"
        % (producing, sorted(inter) or "nothing", sorted(union) or "nothing", quiet))


def plan() -> dict:
    """The product, before anything is spent. Discipline 13 step 4.

    Two of the six measuring criteria turn out to cost nothing, and that was
    found by writing this function rather than by running anything.

      A15-2, the inert switch, is already in A12's record. A12-6 ran both
      corners and printed both closing Ginis.

      A15-3, the cascade, is already in A11's two records. That stage ran the
      complete graph under both exit rules across the same floor grid.

    So the spend is the main grid plus the wage sweep, and the two rulers are
    read off disk.
    """
    pin = len(PIN_ARMS) * len(PIN_F2I) * len(PIN_ELASTICITIES) * len(PIN_SEEDS)
    return {
        "rounds": ROUNDS,
        "main_seed": MAIN_SEED,
        "pinpoint_runs": pin,
        "runs_total": pin,
        "read_and_not_run": {
            "A15-2": "a12_mechanisms.json",
            "A15-3": "a11_subsistence.json and a11_subsistence_drawdown.json",
            "A15-4": "a12_mechanisms.json and a12_mechanisms_n1000.json, which "
                     "are the main grid: 630 rows each, 14 arms, seed 0, and "
                     "they carry the four top-share fields because those were "
                     "added to A12 for this stage",
            "A15-5": "the same two records",
            "A15-7": "the pinpoint rows, whose wage_owed_ratio is the closing "
                     "bill over the opening bill",
        },
        "runs_this_stage_does_not_make": {
            "main grid": len(arms_for(need_for(BASE_CARRIER))) * len(EDGES)
                         * len(ELASTICITIES) * len(NODE_COUNTS),
            "wage sweep on the complete graph":
                2 * len(WAGE_ELASTICITIES) * len(NEED_MULTIPLES) * FOLLOW_UP_SEEDS,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true",
                    help="print the run count and exit, spending nothing")
    ap.add_argument("--selftest", action="store_true",
                    help="the structural criteria only, touching no other record")
    ap.add_argument("--smoke", action="store_true",
                    help="the pinpoint cell at seed 0 only, four runs, to check the "
                         "harness reproduces A12 before the rest is spent")
    ap.add_argument("--no-write", action="store_true",
                    help="print and do not touch the registered record")
    args = ap.parse_args()

    if args.plan:
        p = plan()
        print("A15 run plan, nothing spent")
        for k, v in p.items():
            print("  %-22s %s" % (k, v))
        print("\n  A12's 630 runs measured in the ten-minute range, so this is the")
        print("  same order of magnitude and buys no data.")
        return 0

    crits = [criterion_a15_1(), criterion_a15_6()]
    rows: list = []
    if not args.selftest:
        crits += [criterion_a15_2(), criterion_a15_3()]
        if args.smoke:
            rows = run_pinpoint(seeds=(MAIN_SEED,), f2is=(30,), elasticities=(0.0,))
        else:
            rows = run_pinpoint()
        crits.append(criterion_a15_2b(rows))
        crits += [criterion_a15_4(), criterion_a15_5(), criterion_a15_7(rows)]
        shallow = run_shallow(seeds=(MAIN_SEED,) if args.smoke else PIN_SEEDS)
        crits += [criterion_a15_4b(shallow), criterion_a15_5b(shallow)]
        rows = rows + shallow
    print("A15 stages one to three. The main grid and the wage sweep are not in this file yet.\n")
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))

    if args.selftest or args.no_write:
        return 0 if passed == len(crits) else 1

    record = {
        "stage": "A15",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "the station is not closed. This record carries the two rulers read "
            "off A11's and A12's records and the pinpoint repetition, and it does "
            "not carry the main grid or the wage sweep, which are not written yet"
        ),
        "carrier": "A12's carrier and arm table, imported at run time",
        "rounds": ROUNDS,
        "main_seed": MAIN_SEED,
        "pinpoint": {"f2i": list(PIN_F2I), "elasticities": list(PIN_ELASTICITIES),
                     "seeds": list(PIN_SEEDS), "arms": list(PIN_ARMS)},
        "plan": plan(),
        "criteria": [c.as_dict() for c in crits],
        "runs": sorted(rows, key=lambda x: (x.get("batch", ""), x["seed"], x["f2i"],
                                            x["elasticity"], x["arm"])),
    }
    # Failure mode 35: a smoke run and a registered run must not write the same
    # path. The smoke run exists to check the harness before the rest is spent,
    # so it carries four rows, and four rows at the registered path is a record
    # that looks like a reading and is not one.
    # ``results/subset`` is this repository's own answer to that, and the reason
    # written beside it in ``.gitignore`` is better than a suffix would be: the
    # directory is the separation, and reduced runs are committed there on
    # purpose, because a smoke run that disagrees with the full one belongs in
    # the history rather than outside it.
    out = RECORD
    if args.smoke:
        out = RESULTS / "subset" / RECORD.name
        out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows)%s" % (out.name, len(rows),
          "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
