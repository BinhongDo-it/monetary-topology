"""A38: how wide the withdrawal spreads, made a knob instead of an outcome.

A37 measured how deep a withdrawal goes and found that how wide it spreads is
not something that station could set: the count that withdraws runs to the
whole population two grid steps before the graph goes down, so past the first
depth there is no group left that did not withdraw and the two-group comparison
has nothing to compare. A37 registered the switch and did not build it.

``EdgeCutSpec.cutter_share`` is that switch. ``share`` is a share of edges and
this is a share of nodes: one says how deep, the other how wide.

Three steps, one at a time and in this order:

    python experiments/a38_breadth.py --gate      # rule 19, then nothing else runs
    python experiments/a38_breadth.py --time      # seconds per cell, measured
    python experiments/a38_breadth.py --run       # the grid

``--selftest`` seeds a fault and requires the gate to report it: a gate that has
never failed is not a gate. This file's gate has three halves rather than one,
because the thing added is a knob and not a recorded field, so reproducing the
old path is necessary and nowhere near sufficient.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "monetary_topology"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from monetary_topology.network import EdgeCutSpec, Network  # noqa: E402

#: The module as it stood before the knob, under the repository's backup
#: convention. The gate compares against this file and not against a remembered
#: number, because a number written into a script checks the script's memory.
PRE_MODULE = SRC / "network.py.expired_20260914_pre_A38"

#: A37's grid, used as the knob's own control column: at ``cutter_share = 1.0``
#: this station is that station, so its record is the thing to reproduce.
A37_RECORD = RESULTS / "a37_lying_flat.json"

#: How far a float in that record may sit from the one recomputed here. Six
#: orders above the worst this check has seen and nine below anything a changed
#: mechanism would produce, so it is a band on machine noise and not a line
#: drawn on a reading.
IDENTITY_BAND = 1e-9


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def gate_configs(mod) -> list[tuple[str, object]]:
    """Configurations the default has to reproduce bit for bit.

    Off and on both, for A37's reason: the lines this change adds sit inside
    ``_cut_edges`` and in the constructor, so a run with the switch on is where
    a perturbed draw order would show.
    """
    C, S, EC = mod.NetworkConfig, mod.NetworkSpec, mod.EdgeCutSpec
    out: list[tuple[str, object]] = []
    out.append(("default", C(rounds=60)))
    out.append(("seed 7", C(spec=S(seed=7), seed=7, rounds=60)))
    out.append(("small", C(spec=S(layer1_size=8, layer2_size=40), rounds=60)))
    out.append(("rounds 120", C(rounds=120)))
    for mode, extra in (("shock", {"at_round": 10}),
                        ("self_cut", {"trigger": 2.0}),
                        ("run", {"trigger": 2.0})):
        for share in (0.30, 0.70):
            out.append((f"{mode} {share:.2f}",
                        C(edge_cut=EC(mode=mode, share=share, **extra), rounds=60)))
    return out


def compare(a, b) -> tuple[list[str], list[str]]:
    """Every field the two histories share, bitwise. Returns differences and the
    names only one of them has.

    **Only the shared fields, and the rest named rather than skipped quietly.**
    A gate written against a frozen backup goes stale the moment any later
    stage adds a field: the old module has no such attribute and the comparison
    raises, so the gate stops being a runnable regression exactly when the
    module it guards is changing. Comparing the intersection keeps it alive,
    and printing what fell outside it keeps the reader from thinking the
    intersection was the whole history.
    """
    bad, only = [], []
    names_a = {f.name for f in dataclasses.fields(a)}
    names_b = {f.name for f in dataclasses.fields(b)}
    only = sorted(names_a ^ names_b)
    for name in sorted(names_a & names_b):
        x, y = getattr(a, name), getattr(b, name)
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            if x is None or y is None:
                if x is not y:
                    bad.append(name)
            elif not np.array_equal(x, y):
                bad.append(name)
        elif isinstance(x, dict):
            if set(x) != set(y) or any(not np.array_equal(x[k], y[k]) for k in x):
                bad.append(name)
        elif x != y:
            bad.append(name)
    return bad, only


# --------------------------------------------------------------------------
# the three halves


def half_one(perturb: str | None) -> tuple[bool, list[str]]:
    """Rule 19: the default reproduces the module before the knob, bitwise."""
    lines = []
    if not PRE_MODULE.exists():
        return False, [f"no backup at {PRE_MODULE.name}"]
    old = _load(PRE_MODULE, "monetary_topology._network_pre_a38")
    import monetary_topology.network as new

    with _fault(new, perturb):
        ok = True
        shown_only = False
        for (name, cfg_new), (_, cfg_old) in zip(gate_configs(new), gate_configs(old)):
            bad, only = compare(new.Network(cfg_new).run(),
                                old.Network(cfg_old).run())
            ok = ok and not bad
            lines.append(f"  {'ok  ' if not bad else 'FAIL'} {name:18s} "
                         f"differing fields: {len(bad)}"
                         + (f"   {'; '.join(bad[:4])}" if bad else ""))
            if only and not shown_only:
                shown_only = True
                lines.append(f"       compared the fields both modules have; "
                             f"only one side carries {only}")
    return ok, lines


def half_two(perturb: str | None) -> tuple[bool, list[str]]:
    """A37's recorded cells come back on this module.

    Cross-station rather than in-process: A37 wrote the numbers this arm
    produced at ``cutter_share = 1.0``, so its record is what the default has to
    return. A comparison against a rerun in the same process would only say the
    two runs agree with each other.

    **Two shapes, because the record crosses machines.** The counts are exact
    and compared exactly: they are the mechanism, and a mechanism that moved
    would move them. The floats are compared to an identity band, because that
    record was written on one build and this check runs on another, and the last
    digit of a three-hundred-round accumulation belongs to the linear algebra
    rather than to the model. That is the derived-file discipline's fifth item,
    read here as a criterion instead of a formatting rule, and an exact match on
    a float across two builds is the banned shape in rule 11.

    **The worst difference is printed**, so the margin is in the record and not
    just the verdict.
    """
    import monetary_topology.network as new
    from a37_lying_flat import one_cell

    if not A37_RECORD.exists():
        return False, [f"  FAIL no record at {A37_RECORD.name}"]
    rows = json.loads(A37_RECORD.read_text(encoding="utf-8"))["runs"]
    want = [r for r in rows if r["seed"] in (0, 1) and r["share"] in (0.10, 0.30)]
    exact = ("n_flat", "n_not")
    within = ("share_flat", "share_not", "support_ratio", "m_ratio",
              "volume_ratio", "trade_t", "edges_cut")
    lines, ok, cache, worst, where = [], True, {}, 0.0, None
    with _fault(new, perturb):
        for r in want:
            got = one_cell(r["need"], r["trigger"], r["share"], r["seed"], cache)
            bad = [k for k in exact if got[k] != r[k]]
            for k in within:
                a, b = float(got[k]), float(r[k])
                if a != a and b != b:
                    continue
                d = abs(a - b) / max(abs(b), 1.0)
                if d > worst:
                    worst, where = d, (k, r["need"], r["trigger"], r["share"],
                                       r["seed"])
                if d > IDENTITY_BAND:
                    bad.append(f"{k} {a!r} vs {b!r}")
            ok = ok and not bad
            if bad:
                lines.append(f"  FAIL need {r['need']} trigger {r['trigger']} "
                             f"share {r['share']} seed {r['seed']}   {bad[:3]}")
    lines.append(f"  {'ok  ' if ok else 'FAIL'} {len(want)} cells: every count "
                 f"exact, every float within {IDENTITY_BAND:g}")
    lines.append(f"       worst relative difference {worst:.3e}"
                 + (f" at {where}" if where else
                    " (every float identical: this is the machine that wrote "
                    "the record)"))
    return ok, lines


def half_three(perturb: str | None) -> tuple[bool, list[str]]:
    """D28: the knob carries something, and it carries the right thing.

    Two grids that differ in one entry, and the count of nodes that cut printed
    for each. **The reading is the count against what the knob asked for**, not
    a claim about where the population sits: A37's own second round bought that
    distinction, and the mechanical effect is what answers it.
    """
    import monetary_topology.network as new
    from a17_edge_cut import base_config

    lines, ok = [], True
    with _fault(new, perturb):
        base = base_config(0, need=0.20)
        full = dataclasses.replace(
            base, edge_cut=new.EdgeCutSpec(mode="self_cut", share=0.30, trigger=2.0))
        n_full = int((new.Network(full).run().cut_out.sum(axis=0) > 0).sum())
        lines.append(f"  cutters at cutter_share 1.00: {n_full}")
        prev = None
        for cs in (0.80, 0.60, 0.40, 0.20):
            cfg = dataclasses.replace(
                base, edge_cut=new.EdgeCutSpec(mode="self_cut", share=0.30,
                                               trigger=2.0, cutter_share=cs))
            h = new.Network(cfg).run()
            n = int((h.cut_out.sum(axis=0) > 0).sum())
            # The ceiling is exact and known before the run: willingness is
            # drawn over every node, so at most that many can ever cut. A count
            # above it means the mask is not being applied, or is being redrawn.
            ceiling = int(round(cs * len(h.holdings[0])))
            bad = []
            if n > ceiling:
                bad.append(f"above the ceiling {ceiling}")
            if prev is not None and n > prev:
                bad.append(f"rose as the knob fell ({prev} -> {n})")
            if n == n_full and cs < 1.0:
                bad.append("unchanged from the full grid: the knob is inert")
            ok = ok and not bad
            prev = n
            lines.append(f"  {'ok  ' if not bad else 'FAIL'} cutter_share {cs:.2f}: "
                         f"cutters {n:3d}  ceiling {ceiling:3d}"
                         + (f"   {'; '.join(bad)}" if bad else ""))
    return ok, lines


def half_four() -> tuple[bool, list[str]]:
    """The knob is rejected where it has no meaning, rather than ignored."""
    lines, ok = [], True
    try:
        EdgeCutSpec(mode="run", share=0.3, trigger=2.0, cutter_share=0.5)
        ok = False
        lines.append("  FAIL a partial cutter_share was accepted on mode 'run'")
    except ValueError:
        lines.append("  ok   mode 'run' rejects a partial cutter_share")
    try:
        EdgeCutSpec(mode="self_cut", share=0.3, trigger=2.0, cutter_share=1.4)
        ok = False
        lines.append("  FAIL a cutter_share above one was accepted")
    except ValueError:
        lines.append("  ok   a cutter_share outside [0, 1] is rejected")
    return ok, lines


# --------------------------------------------------------------------------
# faults (11f)


class _fault:
    """Seed a fault into the module for the duration of a block.

    Each one is a way the knob could be wrong while every other number in the
    run looks right, which is the only kind worth planting.
    """

    def __init__(self, mod, name: str | None):
        self.mod, self.name, self.saved = mod, name, None

    def __enter__(self):
        if self.name is None:
            return self
        self.saved = self.mod.Network._draw_cutters
        if self.name == "inert":
            # The mask is never built, so the knob does nothing at all and
            # every count comes back the full grid's.
            def patched(self):
                return None
        elif self.name == "leak":
            # The draw is taken even at the default and off the cut stream, so
            # every later cut moves by one draw and the default stops
            # reproducing.
            def patched(self):
                ec = self.config.edge_cut
                k = int(round(min(ec.cutter_share, 1.0) * self._n))
                mask = np.zeros(self._n, dtype=bool)
                if k > 0:
                    mask[self._cut_rng.choice(self._n, size=k, replace=False)] = True
                return mask
        elif self.name == "redraw":
            # Willingness becomes a coin flipped each round rather than a
            # disposition, so the set of withdrawers accumulates past the
            # ceiling the knob is supposed to impose.
            def patched(self):
                ec = self.config.edge_cut
                if ec.cutter_share >= 1.0:
                    return None
                n = self._n
                rng = self._cut_rng

                class _Rolling:
                    def __array__(self, dtype=None):
                        m = np.zeros(n, dtype=bool)
                        k = int(round(ec.cutter_share * n))
                        if k > 0:
                            m[rng.choice(n, size=k, replace=False)] = True
                        return m.astype(dtype) if dtype else m

                    def __and__(self, other):
                        return np.asarray(self) & other

                    def __rand__(self, other):
                        return other & np.asarray(self)

                return _Rolling()
        else:
            raise ValueError(f"unknown fault {self.name!r}")
        self.mod.Network._draw_cutters = patched
        return self

    def __exit__(self, *exc):
        if self.saved is not None:
            self.mod.Network._draw_cutters = self.saved
        return False


def run_gate(perturb: str | None = None) -> bool:
    blocks = [("rule 19: the default reproduces the module before the knob",
               half_one(perturb)),
              ("A37's recorded cells come back on this module", half_two(perturb)),
              ("D28: the knob carries something", half_three(perturb)),
              ("the knob is rejected where it has no meaning", half_four())]
    ok = True
    for title, (good, lines) in blocks:
        print(f"\n{title}")
        for ln in lines:
            print(ln)
        ok = ok and good
    print("\ngate:", "PASS" if ok else "FAIL")
    return ok


def selftest() -> bool:
    print("selftest: the gate must fail on each seeded fault")
    results = []
    for fault in ("inert", "leak", "redraw"):
        print(f"\n{'='*60}\n--- fault: {fault}")
        caught = not run_gate(perturb=fault)
        print(f"--- caught: {caught}")
        results.append(caught)
    print("\nselftest:", "PASS" if all(results) else "FAIL")
    return all(results)


# --------------------------------------------------------------------------
# the grid

from a17_edge_cut import ELASTICITY, F2I, ROUNDS, base_config  # noqa: E402

#: Two carriers, as A37: the floor off reads what withdrawal does with no
#: absorbing wall anywhere, the floor on reads who crosses it.
NEEDS = (0.0, 0.20)

#: Three depths. A37 measured the graph going down between 0.50 and 0.55, so
#: past 0.50 there is no trading economy left to read and a fourth column would
#: buy nothing (rule 12).
DEPTHS = (0.10, 0.30, 0.50)

#: Five widths. One is A37's own column and is what A38-4 checks against its
#: record; the rest are the interval that station could not reach, because the
#: width it produced on its own ran to the whole population.
BREADTHS = (0.20, 0.40, 0.60, 0.80, 1.00)

SEEDS = (0, 1, 2, 3, 4)

#: One trigger. A37 read 88 to 98 nodes caught at all three of its triggers on
#: the first depth, near enough the same number that the axis buys nothing.
TRIGGER = 2.0

TIMING = RESULTS / "a38_timing.json"
RECORD = RESULTS / "a38_breadth.json"


def _med(x: np.ndarray) -> float:
    return float(np.median(x)) if x.size else float("nan")


def one_cell(need: float, depth: float, breadth: float, seed: int,
             ctrl_cache: dict) -> dict:
    """One treated run against its own twin, and the nodes split three ways.

    **Three groups, not two, and this is what the knob changed.** A37 split on
    whether a node cut, because at full width every node that did not cut was
    one the trigger never caught, four of two hundred. Once width is a knob the
    same complement holds two mechanically different kinds: nodes that would
    have withdrawn and were never stressed, and nodes that would not withdraw at
    all. **The question is the first group against the third**, and putting the
    second in with the third answers a different one.
    """
    key = (need, seed)
    if key not in ctrl_cache:
        ctrl_cache[key] = Network(base_config(seed, need=need)).run()
    ctrl = ctrl_cache[key]

    cfg = dataclasses.replace(
        base_config(seed, need=need),
        edge_cut=EdgeCutSpec(mode="self_cut", share=depth, trigger=TRIGGER,
                             cutter_share=breadth))
    net = Network(cfg)
    hist = net.run()

    n = len(hist.holdings[0])
    cut = hist.cut_out.sum(axis=0) > 0
    # Read off the module, never recomputed here from the knob: a second
    # definition of the same set is the twelfth category error, and A16-2 was
    # written against exactly that.
    will = net._will_cut
    will = np.ones(n, dtype=bool) if will is None else will
    idle = will & ~cut          # willing, never caught by the trigger
    unwilling = ~will           # would not withdraw at all

    h_t, h_c = hist.holdings[-1], ctrl.holdings[-1]

    def _norm(v):
        s = float(v.sum())
        return v / s if s > 0 else v

    s_t, s_c = _norm(h_t), _norm(h_c)

    def rel(mask):
        if not mask.any():
            return float("nan")
        base = _med(s_c[mask])
        return float(_med(s_t[mask]) / base) if base > 0 else float("nan")

    tail = max(1, hist.effective_support.size // 10)
    sup_t = float(np.median(hist.effective_support[-tail:]))
    sup_c = float(np.median(ctrl.effective_support[-tail:]))
    trade_t = float(hist.total_volume[-tail:].sum() - hist.wage_paid[-tail:].sum())
    trade_c = float(ctrl.total_volume[-tail:].sum() - ctrl.wage_paid[-tail:].sum())
    vol_t, vol_c = float(hist.total_volume.sum()), float(ctrl.total_volume.sum())

    return {
        "need": need, "depth": depth, "breadth": breadth, "seed": seed, "n": n,
        "n_cut": int(cut.sum()), "n_idle": int(idle.sum()),
        "n_unwilling": int(unwilling.sum()),
        "share_cut": rel(cut), "share_idle": rel(idle),
        "share_unwilling": rel(unwilling),
        # A37's split, kept so the two ways of cutting the same population can
        # be read side by side rather than argued about.
        "share_not_mixed": rel(~cut),
        "support_ratio": sup_t / sup_c if sup_c > 0 else float("nan"),
        "m_ratio": (float(h_t.sum()) / float(h_c.sum())
                    if float(h_c.sum()) > 0 else float("nan")),
        "volume_ratio": vol_t / vol_c if vol_c > 0 else float("nan"),
        "trade_t": trade_t, "trade_c": trade_c,
        "thin": bool(vol_c > 0 and vol_t / vol_c < 0.05),
    }


def grid(smoke: bool = False):
    needs = NEEDS[:1] if smoke else NEEDS
    depths = DEPTHS[:1] if smoke else DEPTHS
    breadths = (0.20, 1.00) if smoke else BREADTHS
    seeds = SEEDS[:1] if smoke else SEEDS
    return [(a, b, c, d) for a in needs for b in depths
            for c in breadths for d in seeds]


def run_grid(smoke: bool = False) -> list[dict]:
    cells = grid(smoke)
    cache: dict = {}
    rows = []
    for i, (nd, dp, br, sd) in enumerate(cells, 1):
        rows.append(one_cell(nd, dp, br, sd, cache))
        if i % 25 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}", flush=True)
    return rows


def _by(rows, need, depth, key):
    """Median of ``key`` at each width, with the count behind it."""
    out = []
    for br in sorted({r["breadth"] for r in rows}):
        vals = [r[key] for r in rows
                if r["need"] == need and r["depth"] == depth
                and r["breadth"] == br and not np.isnan(r[key])]
        out.append((br, float(np.median(vals)) if vals else float("nan"), len(vals)))
    return out


# --------------------------------------------------------------------------
# criteria


def criteria(rows: list[dict]) -> list[dict]:
    c: list[dict] = []

    # A38-1: the three groups are a partition and the third is the size the
    # knob asked for. Construction, so it should hold, and it has to be able to
    # fail or the split below rests on nothing.
    bad = []
    for r in rows:
        if r["n_cut"] + r["n_idle"] + r["n_unwilling"] != r["n"]:
            bad.append(f"not a partition at {r['need']}/{r['depth']}/"
                       f"{r['breadth']}/{r['seed']}")
        want = r["n"] - int(round(r["breadth"] * r["n"]))
        if r["n_unwilling"] != want:
            bad.append(f"unwilling {r['n_unwilling']} wanted {want} at "
                       f"{r['need']}/{r['depth']}/{r['breadth']}/{r['seed']}")
    full = [r for r in rows if r["breadth"] >= 1.0]
    if full and any(r["n_unwilling"] != 0 for r in full):
        bad.append("a node is unwilling at full width")
    idle = sorted({r["n_idle"] for r in rows})
    c.append(dict(name="A38-1  the three groups partition the nodes and the "
                       "third is the size the knob asked for",
                  kind="instrument", passed=not bad,
                  detail=(f"{len(rows)} cells: every one partitions, every "
                          f"unwilling count is n minus round(breadth*n), and "
                          f"none at full width. Nodes willing but never caught "
                          f"by the trigger: {idle[:8]}"
                          if not bad else "  |  ".join(bad[:5]))[:900]))

    # A38-2: the reading. Does withdrawing pay, and does it need company?
    # Group one against group three, in shares, against width.
    #
    # **The ratio is taken in each cell and then the cells are counted.** A
    # median of one group over seeds divided by a median of the other is a
    # ratio of medians, which is not the median of the ratio and can cross one
    # where no cell does. The first version did that and reported a crossing on
    # the carrier where the seeds do not agree on a direction at all.
    #
    # **Nothing here is compared against a threshold.** A cell is above one or
    # below it, the seeds at a width either agree or they do not, and what is
    # printed is those counts. The registered three states are read off the
    # agreement and not off any magnitude: a width where the seeds split
    # carries no direction, and that is the state that maps to no verdict
    # (11c), not to a pass.
    verdicts, shown = [], []
    for need in sorted({r["need"] for r in rows}):
        for dp in sorted({r["depth"] for r in rows}):
            widths = []
            for br in sorted({r["breadth"] for r in rows}):
                cells = [r["share_cut"] / r["share_unwilling"] for r in rows
                         if r["need"] == need and r["depth"] == dp
                         and r["breadth"] == br
                         and not np.isnan(r["share_cut"])
                         and not np.isnan(r["share_unwilling"])
                         and r["share_unwilling"] > 0]
                if not cells:
                    continue
                up = sum(1 for x in cells if x > 1.0)
                dn = len(cells) - up
                side = "up" if dn == 0 else ("down" if up == 0 else "split")
                widths.append((br, side, up, dn, float(np.median(cells))))
            if not widths:
                verdicts.append((need, dp, "no object: the third group is empty "
                                           "at every width")); continue
            agreed = [(b, s) for b, s, _, _, _ in widths if s != "split"]
            split = [b for b, s, _, _, _ in widths if s == "split"]
            if not agreed:
                v = (f"Void: the seeds agree on no width, {len(split)} of "
                     f"{len(widths)} split")
            elif len({s for _, s in agreed}) == 1:
                s = agreed[0][1]
                v = (f"every width the seeds agree on is {s}, "
                     f"{len(agreed)} of {len(widths)}"
                     + (f"; {len(split)} split at {split}" if split else
                        "; none split"))
            else:
                turns = [agreed[k][0] for k in range(1, len(agreed))
                         if agreed[k][1] != agreed[k - 1][1]]
                v = f"the side the seeds agree on turns at widths {turns}"
            verdicts.append((need, dp, v))
            # **Both groups' own figures, not only their ratio.** A ratio that
            # moves says nothing about which side moved, and the two answers
            # are different findings: the withdrawers losing an advantage is
            # not the stayers catching up.
            apart = []
            for br in sorted({r["breadth"] for r in rows}):
                g = [r for r in rows if r["need"] == need and r["depth"] == dp
                     and r["breadth"] == br]
                def _m(k):
                    v = [r[k] for r in g if not np.isnan(r[k])]
                    return float(np.median(v)) if v else float("nan")
                apart.append(f"{br:.2f}:cut{_m('share_cut'):.3f}/"
                             f"stay{_m('share_unwilling'):.3f}")
            shown.append(f"need {need} depth {dp}: "
                         + " ".join(f"{b:.2f}:{u}up/{d}dn(med {m:.2f})"
                                    for b, _, u, d, m in widths)
                         + "  [each group: " + " ".join(apart) + "]")
    c.append(dict(name="A38-2  the withdrawing group against the group that "
                       "would not withdraw, against width",
                  kind="own_reading", passed=bool(verdicts),
                  detail=("; ".join(f"need {n} depth {d}: {v}"
                                    for n, d, v in verdicts)
                          + "  |  " + "; ".join(shown))[:3000]))

    # A38-3: what width does to the economy the two groups are standing in.
    shown = []
    for need in sorted({r["need"] for r in rows}):
        for dp in sorted({r["depth"] for r in rows}):
            vol = _by(rows, need, dp, "volume_ratio")
            sup = dict((b, v) for b, v, _ in _by(rows, need, dp, "support_ratio"))
            shown.append(f"need {need} depth {dp}: "
                         + " ".join(f"{b:.2f}:vol{v:.3f}/sup{sup.get(b, float('nan')):.3f}"
                                    for b, v, k in vol if k))
    thin = sum(1 for r in rows if r["thin"])
    c.append(dict(name="A38-3  what width does to flow and to the receiving set",
                  kind="own_reading", passed=True,
                  detail=(f"{thin}/{len(rows)} cells below a twentieth of their "
                          f"twin's flow.  " + "; ".join(shown))[:1500]))

    # A38-4: the two ways of splitting the same population, side by side.
    # **The point is not that one is wrong in general**: at full width they are
    # the same split, which is why A37 could use either. It is that they come
    # apart as soon as width is set, and by how much is a reading.
    gaps = []
    for r in rows:
        a, b = r["share_unwilling"], r["share_not_mixed"]
        if np.isnan(a) or np.isnan(b) or b == 0:
            continue
        gaps.append((abs(a - b) / max(abs(b), 1e-12), r["breadth"]))
    below = [g for g, br in gaps if br < 1.0]
    empty = sum(1 for r in rows if r["breadth"] >= 1.0)
    med = float(np.median(below)) if below else float("nan")
    c.append(dict(name="A38-4  the two ways of splitting the same population",
                  kind="own_reading", passed=True,
                  detail=(f"At full width there is nothing to compare: the "
                          f"group that would not withdraw is empty in all "
                          f"{empty} of those cells, which is why one station "
                          f"could use either split. Below full width the two "
                          f"come apart as sets, and the relative gap between "
                          f"their figures over {len(below)} cells has median "
                          f"{med:.4f} and largest "
                          f"{max(below) if below else float('nan'):.4f}. "
                          f"**How far apart the sets are does not settle how "
                          f"far apart the numbers are, and this line reports "
                          f"the numbers.**")[:900]))
    return c


def selftest_criteria() -> bool:
    """11f: seed a fault into the rows and require each criterion to report it."""
    base = []
    for br in BREADTHS:
        for sd in SEEDS[:2]:
            n = 200
            unw = n - int(round(br * n))
            base.append(dict(need=0.0, depth=0.10, breadth=br, seed=sd, n=n,
                             n_cut=int(round(br * n)) - 4, n_idle=4,
                             n_unwilling=unw, share_cut=1.0, share_idle=1.0,
                             share_unwilling=1.0, share_not_mixed=1.0,
                             support_ratio=0.5, m_ratio=2.0, volume_ratio=1.0,
                             trade_t=10.0, trade_c=20.0, thin=False))

    def pick(rows, nm):
        return [x for x in criteria(rows) if x["name"].startswith(nm)][0]

    ok = []
    rows = [dict(r) for r in base]
    rows[0]["n_unwilling"] += 1
    got = pick(rows, "A38-1")
    ok.append(not got["passed"] and "not a partition" in got["detail"])
    print(f"  broken partition -> A38-1 passed={got['passed']} (want False)")

    rows = [dict(r, n_unwilling=0, n_cut=r["n"] - r["n_idle"]) for r in base]
    got = pick(rows, "A38-1")
    ok.append(not got["passed"] and "wanted" in got["detail"])
    print(f"  knob not applied -> A38-1 passed={got['passed']} (want False)")

    # the side turns as width rises, and every seed agrees at every width:
    # A38-2 has to name where it turns
    rows = [dict(r, share_cut=(0.5 if r["breadth"] < 0.6 else 2.0)) for r in base]
    got = pick(rows, "A38-2")
    ok.append("turns at widths" in got["detail"])
    print(f"  side turns       -> A38-2 says {got['detail'][:52]!r}")

    # one side at every width: A38-2 has to say so rather than find a line
    rows = [dict(r, share_cut=2.0) for r in base]
    got = pick(rows, "A38-2")
    ok.append("agree on is up" in got["detail"] and "none split" in got["detail"])
    print(f"  one side         -> A38-2 says {got['detail'][:52]!r}")

    # the seeds disagree at every width: no verdict, and it has to say Void
    rows = [dict(r, share_cut=(0.5 if r["seed"] % 2 else 2.0)) for r in base]
    got = pick(rows, "A38-2")
    ok.append("Void" in got["detail"])
    print(f"  seeds disagree   -> A38-2 says {got['detail'][:52]!r}")

    # the third group is empty everywhere: no object, and no verdict either way
    rows = [dict(r, share_unwilling=float("nan")) for r in base]
    got = pick(rows, "A38-2")
    ok.append("no object" in got["detail"])
    print(f"  third group gone -> A38-2 says {got['detail'][:52]!r}")
    return all(ok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        a = selftest()
        print("\ncriteria selftest:")
        b = selftest_criteria()
        print("criteria selftest:", "PASS" if b else "FAIL")
        return 0 if (a and b) else 1
    if args.gate:
        return 0 if run_gate() else 1

    if args.time:
        import time
        cache: dict = {}
        t0 = time.time(); one_cell(0.0, 0.30, 0.60, 0, cache); t1 = time.time()
        one_cell(0.20, 0.30, 0.60, 0, cache); t2 = time.time()
        per = {"floor_off_seconds": round(t1 - t0, 4),
               "floor_on_seconds": round(t2 - t1, 4),
               "cells_total": len(grid()),
               "note": "measured, not assumed (D38). A run reads this file; "
                       "without it no hour figure may be quoted."}
        per["estimate_seconds"] = round(
            len(grid()) * (per["floor_off_seconds"] + per["floor_on_seconds"]) / 2, 1)
        print(json.dumps(per, indent=2))
        if not args.no_write:
            TIMING.write_text(json.dumps(per, indent=2) + "\n", encoding="utf-8")
        return 0

    if args.run:
        if not args.smoke and not TIMING.exists():
            print("refusing: run --time first (D38)"); return 1
        rows = run_grid(smoke=args.smoke)
        crit = criteria(rows)
        for x in crit:
            print(f"  {'PASS' if x['passed'] else 'FAIL'}[{x['kind']}] {x['name']}")
            print(f"        {x['detail'][:420]}")
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
            return 0
        rec = {"stage": "A38",
               "diagnostic_only": True,
               "diagnostic_reason": (
                   "Station not closed. The width of a withdrawal is a knob "
                   "here for the first time; the debt this carrier does not "
                   "have is the next station, and it is what would give the "
                   "per-head burden claim an object."),
               "config": {"needs": list(NEEDS), "depths": list(DEPTHS),
                          "breadths": list(BREADTHS), "seeds": list(SEEDS),
                          "trigger": TRIGGER, "mode": "self_cut",
                          "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
                          "hub_debt": False, "sovereign": False,
                          "write_off": False},
               "criteria": crit, "runs": rows}
        RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"\nwrote {RECORD}")
        return 0 if all(x["passed"] for x in crit) else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
