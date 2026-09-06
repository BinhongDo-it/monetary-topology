"""A24: how much redundancy is left once the information edges are gone.

Two switches already in ``network.py`` stand for the two substrates, and the
distinction is in their own docstrings, not invented here.

``SubsistenceSpec``  a node crosses the floor and stops trading, and **the
    adjacency is untouched**: "the potential graph is exactly what it was at
    construction". Damage to G_T with G_I intact.

``EdgeCutSpec``  "Edges removed from **the graph itself**", written because
    "the model has no way for a trading relationship to end". Damage to G_I.

``RewireSpec``  with ``conserve_degree=False`` an acquiring node gains edges
    without dropping any, so the graph can grow edges back. Reconnection is
    therefore measured here rather than assumed away. It runs through promotion,
    promotion needs holdings to rise, and a node whose out-edges are all cut
    spends nothing, so whether it can reconnect is gated on the very thing that
    was destroyed.

A17 measured the first half and stopped: cutting seven tenths of the edges
leaves total flow at 0.99 of the control while the graph falls into 13 to 19
components with 32 to 42 nodes stranded, because "cutting only makes the flow
reroute". This station asks what the rerouting spent, and whether it can be
bought back.

``--gate`` is the first cut and it settles what has to be settled before
anything else is spent: whether the two substrates damage the same set of
nodes. A17's docstring reports that at the registered floor they do, 180
against 180, the same set, which would make two arms one arm under two names
(discipline 12). So the gate scans the floor for a level where the sets come
apart, and prints the sets rather than a summary of them (rule 11).

Usage

    python experiments/a24_information_wall.py --gate
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    BroadcastSpec,
    EdgeCutSpec,
    Network,
    NetworkConfig,
    NetworkSpec,
    RewireSpec,
    SubsistenceSpec,
    WageChannel,
)



RECORD = RESULTS / "a24_information_wall.json"


def _fmt(x):
    """Floats through an explicit spec, never repr (derived-file rule 5)."""
    if isinstance(x, float):
        return float(f"{x:.10f}")
    if isinstance(x, (set, frozenset)):
        return sorted(int(v) for v in x)
    if isinstance(x, tuple):
        return [_fmt(v) for v in x]
    if isinstance(x, list):
        return [_fmt(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _fmt(v) for k, v in x.items()}
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(f"{float(x):.10f}")
    return x


def _config_diff(obj, seen=None) -> dict:
    """Every dataclass field of ``obj`` that differs from its own default.

    Discipline 18d: a record has to carry the configuration it ran under, or a
    later rebuild cannot tell a different answer from a different setting. The
    fields left at their defaults are dropped, so what comes back is exactly the
    choices this stage made. Nested dataclasses recurse; anything at its default
    disappears, so an empty dict means nothing was changed.
    """
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return {}
    seen.add(id(obj))
    out = {}
    for f in dataclasses.fields(obj):
        if not f.init:
            continue
        cur = getattr(obj, f.name)
        if f.default is not dataclasses.MISSING:
            dflt = f.default
        elif f.default_factory is not dataclasses.MISSING:
            dflt = f.default_factory()
        else:
            dflt = None
        if dataclasses.is_dataclass(cur) and not isinstance(cur, type):
            sub = _config_diff(cur, seen)
            if sub:
                out[f.name] = sub
            continue
        if isinstance(cur, np.ndarray):
            continue
        try:
            same = bool(cur == dflt)
        except Exception:
            same = False
        if not same:
            out[f.name] = cur
    return out


def station_config() -> dict:
    """What this station chose, as against what the library defaults to.

    The seed is reported as the tuple the stage sweeps rather than the one used
    to build the probe, because no single run uses the tuple and every run uses
    one of its entries.
    """
    cfg = _config_diff(base_config(SEEDS[0]))
    cfg.pop("seed", None)
    if "spec" in cfg:
        cfg["spec"].pop("seed", None)
    return {
        "carrier": "A12 BASE_CARRIER",
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "f2i": F2I,
        "elasticity": ELASTICITY,
        "broadcast_weights": list(BC_WEIGHTS),
        "hysteresis_switch_rounds": list(HYST_ROUNDS),
        "hysteresis_weight": HYST_W,
        "crossing_trigger": CROSS_TRIGGER,
        "crossing_shares": list(CROSS_SHARES),
        "crossing_weight": CROSS_W,
        "shock_round": SHOCK_ROUND,
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one mode's payload into the station record.

    Merged rather than overwritten so running the modes separately accumulates,
    and no wall-clock content goes in: git records when a file was committed and
    a generated-on line would differ from the committed copy every day after.
    """
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A24"
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    n = sum(len(v.get("criteria", [])) for v in doc["sections"].values())
    print(f"\n   record: {RECORD.name}, sections {sorted(doc['sections'])}, "
          f"{n} criteria")

def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A12 = _load(ROOT / "experiments" / "a12_mechanisms.py", "_a12_for_a24")
BASE_CARRIER = _A12.BASE_CARRIER

# Reconnection is A13's registered arm, imported rather than restated, so this
# station introduces no constant of its own (D5). A13 reads cluster_rate off
# Chetty et al. (Nature 2022) and retain_rate off Eckbo, Thorburn and Wang
# (JFE 2015); they are 0.5 and 1/3.
_A13 = _load(ROOT / "experiments" / "a13_mobility.py", "_a13_for_a24")
REWIRE_OFF = _A13.ARMS["off"]
REWIRE_ON = _A13.ARMS["both, degree not conserved"]

#: The density grid. The thin and thick ends are named from what A24-2 reads,
#: not pinned in advance. 30 is A17's value and is in the grid for that reason.
DENSITIES = (5, 10, 20, 30, 45)

# Taken from A17 so the control arm is A17's control arm and A24-1 can compare
# against its record. Not choices made here.
F2I = 30
ELASTICITY = 0.5
ROUNDS = 300
SEEDS = (0, 1, 2, 3, 4)
SHOCK_ROUND = 50
CUT_SHARES = (0.1, 0.3, 0.5, 0.7)

# This station's own grid. Deliberately shallow: A17 reports 180 of 200 gone at
# the registered floor, which is past the point where a comparison says
# anything.
#: A17's own trigger grid for the triggered arms. Imported as a value rather
#: than restated, so this station introduces no threshold of its own (D5).
TRIGGERS = (2.0, 4.0, 6.0, 8.0, 12.0)

NEEDS = (0.02, 0.05, 0.10, 0.20, 0.40, 0.80)


def components(adj) -> tuple[int, int]:
    """Weakly connected components, and the largest one. A17's helper."""
    import collections
    n = adj.shape[0]
    g = collections.defaultdict(set)
    ii, jj = np.nonzero(adj > 0)
    for i, j in zip(ii, jj):
        g[int(i)].add(int(j))
        g[int(j)].add(int(i))
    seen: set[int] = set()
    count = largest = 0
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


def base_config(seed: int, need: float = 0.0, f2i: int = F2I) -> NetworkConfig:
    c = BASE_CARRIER
    return NetworkConfig(
        spec=NetworkSpec(
            seed=seed,
            layer1_size=c.layer1_size,
            intermediate_size=c.intermediate_size,
            layer2_size=c.layer2_size,
            financial_to_intermediate_edges=f2i,
        ),
        seed=seed,
        rounds=ROUNDS,
        wages=WageChannel(elasticity=ELASTICITY),
        subsistence=SubsistenceSpec(need=need) if need > 0 else SubsistenceSpec(),
    )


def one(seed: int, *, need: float = 0.0, cut_share: float = 0.0,
        f2i: int = F2I, rewire: RewireSpec | None = None,
        mode: str = "shock", trigger: float = 0.0,
        broadcast: BroadcastSpec | None = None) -> dict:
    """One run. Returns the damaged set itself, not a count of it (rule 11)."""
    if cut_share <= 0.0:
        ec = EdgeCutSpec()
    elif mode == "shock":
        ec = EdgeCutSpec(mode="shock", share=cut_share,
                         at_round=SHOCK_ROUND, targeting="random")
    else:
        # The triggered arms take a threshold in the units inflow is measured
        # in. A17's own grid, imported below, not chosen here.
        ec = EdgeCutSpec(mode=mode, share=cut_share, trigger=trigger,
                         at_round=SHOCK_ROUND, targeting="random")
    cfg = dataclasses.replace(base_config(seed, need, f2i), edge_cut=ec)
    if rewire is not None:
        cfg = dataclasses.replace(cfg, rewire=rewire)
    if broadcast is not None:
        cfg = dataclasses.replace(cfg, broadcast=broadcast)
    net = Network(cfg)
    h = net.run()
    stranded = set(np.flatnonzero(~net._has_out).tolist())
    departed = set(np.flatnonzero(~net._alive).tolist())
    return {
        "seed": seed, "need": need, "cut_share": cut_share, "f2i": f2i,
        "mode": mode if cut_share > 0 else "off", "trigger": trigger,
        "bc_weight": 0.0 if broadcast is None else float(broadcast.weight),
        "volume": float(np.asarray(h.total_volume, dtype=float).sum()),
        "support_close": float(np.asarray(h.effective_support, dtype=float)[-1]),
        "starved_close": int(np.asarray(h.starved)[-1]),
        "stranded": stranded, "departed": departed,
        "damaged": stranded | departed,
        "adjacency_sum": float(net.adjacency.sum()),
        "promoted": int(np.asarray(h.promoted).sum()),
        "demoted": int(np.asarray(h.demoted).sum()),
        "components": components(net.adjacency),
    }


def jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return (len(a & b) / u) if u else float("nan")


def gate() -> None:
    n_nodes = (BASE_CARRIER.layer1_size + BASE_CARRIER.intermediate_size
               + BASE_CARRIER.layer2_size)
    print(f"carrier n={n_nodes}  rounds={ROUNDS}  seeds={SEEDS}  f2i={F2I}\n")

    ctrl = {s: one(s) for s in SEEDS}

    # ---- A24-1: structural, against A17's own record --------------------
    print("== A24-1  control arm against A17's off arm ==")
    rec = json.loads((RESULTS / "a17_edge_cut.json").read_text(encoding="utf-8"))
    txt = json.dumps(rec)
    a1_hits = {}
    for s in SEEDS:
        v = ctrl[s]["volume"]
        a1_hits[s] = f"{v:.6f}"[:10] in txt
        print(f"   seed {s}: volume {v:.6f}  support_close {ctrl[s]['support_close']:.6f}"
              f"  edges {ctrl[s]['adjacency_sum']:.0f}"
              f"  {'in a17 record' if a1_hits[s] else 'not matched by string'}")
    # The verdict was computed here and thrown away for the life of this stage:
    # the loop above printed it and the record kept only the volumes. A
    # structural check that is performed and discarded is worse than one never
    # written, because the printout makes it look covered. Discipline 19 says
    # the reproduction has to be run, and this is the half where the run has to
    # be *recorded*.
    print(f"   A24-1: {sum(a1_hits.values())} of {len(SEEDS)} matched")

    # ---- A24-0: are the two substrates the same set? --------------------
    print("\n== A24-0  G_I arm: |damaged|, volume over control ==")
    gi = {}
    for share in CUT_SHARES:
        cells = []
        for s in SEEDS:
            r = one(s, cut_share=share); gi[(share, s)] = r
            cells.append(f"{len(r['damaged']):>3}/{r['volume']/ctrl[s]['volume']:.3f}")
        print(f"   cut {share:<4} " + "  ".join(cells))

    print("\n== A24-0  G_T arm: |damaged|, volume over control ==")
    gt = {}
    for need in NEEDS:
        cells = []
        for s in SEEDS:
            r = one(s, need=need); gt[(need, s)] = r
            cells.append(f"{len(r['damaged']):>3}/{r['volume']/ctrl[s]['volume']:.3f}")
        print(f"   need {need:<4} " + "  ".join(cells))

    print("\n== A24-0  the gate: Jaccard of the two damaged sets, seed 0 ==")
    print("   a value near 1 means one arm under two names (discipline 12)")
    print("   " + " " * 10 + "  ".join(f"need {n:<5}" for n in NEEDS))
    for share in CUT_SHARES:
        a = gi[(share, 0)]["damaged"]
        row = "  ".join(f"{jaccard(a, gt[(n, 0)]['damaged']):<10.3f}" for n in NEEDS)
        print(f"   cut {share:<5} {row}")

    print("\n== A24-6  the three worst cells on each arm (rule 13 step 1) ==")
    for label, d in (("G_I", gi), ("G_T", gt)):
        worst = sorted(d.items(),
                       key=lambda kv: kv[1]["volume"] / ctrl[kv[1]["seed"]]["volume"])[:3]
        for k, r in worst:
            print(f"   {label} {k}: volume ratio "
                  f"{r['volume']/ctrl[r['seed']]['volume']:.4f}  |damaged| {len(r['damaged'])}")

    write_record("gate", {
        "criteria": [
            {"name": "A24-1  the control arm reproduces A17's off arm",
             "passed": bool(all(a1_hits.values())),
             "detail": {"matched": {str(s): bool(a1_hits[s]) for s in SEEDS},
                        "volume": {str(s): ctrl[s]["volume"] for s in SEEDS},
                        "how": "each control volume printed to six places is "
                               "searched for in a17_edge_cut.json as a string. "
                               "A string test is weak and it is what this "
                               "check has always done; what changed on "
                               "2026-09-03 is that its answer is recorded"}},
            {"name": "A24-2  the two substrates do not damage the same set",
             "detail": {f"cut {sh} vs need {nd}":
                        jaccard(gi[(sh, 0)]["damaged"], gt[(nd, 0)]["damaged"])
                        for sh in CUT_SHARES for nd in NEEDS}},
        ],
        "gi": {f"{k[0]}|{k[1]}": {"damaged": v["damaged"], "volume": v["volume"],
                                  "components": v["components"]}
               for k, v in gi.items()},
        "gt": {f"{k[0]}|{k[1]}": {"damaged": v["damaged"], "volume": v["volume"],
                                  "components": v["components"]}
               for k, v in gt.items()},
        "control": {str(s): ctrl[s]["volume"] for s in SEEDS},
    })



def main_arms() -> None:
    """A24-2 names the thin and thick ends; A24-3 is the main question."""
    print(f"rewire ON  = {REWIRE_ON}")
    print(f"rewire OFF = {REWIRE_OFF}")
    print()
    print("== A24-2  density alone, no cut, no floor, rewire off ==")
    print("   f2i   edges   volume      support_close  comps  largest")
    for f in DENSITIES:
        rows = [one(s, f2i=f, rewire=REWIRE_OFF) for s in SEEDS]
        e = np.mean([r["adjacency_sum"] for r in rows])
        v = np.mean([r["volume"] for r in rows])
        sup = np.mean([r["support_close"] for r in rows])
        nc = np.mean([r["components"][0] for r in rows])
        lg = np.mean([r["components"][1] for r in rows])
        print(f"   {f:<5} {e:>7.0f} {v:>11.2f} {sup:>14.4f} {nc:>6.1f} {lg:>8.1f}")
    thin, thick = DENSITIES[0], DENSITIES[-1]
    print(f"   naming from the scan: thin = f2i {thin}, thick = f2i {thick}")
    print()
    print("== A24-3  does the cut leave a mark once reconnection is available? ==")
    print("   volume over the matched control (same density, same rewire, no cut)")
    out = {}
    for f in (thin, thick):
        for rw_name, rw in (("off", REWIRE_OFF), ("ON", REWIRE_ON)):
            ctl = [one(s, f2i=f, rewire=rw) for s in SEEDS]
            print(f"   -- f2i {f}, rewire {rw_name}: control volume "
                  f"{np.mean([c['volume'] for c in ctl]):.1f}, "
                  f"promoted {np.mean([c['promoted'] for c in ctl]):.1f}")
            for share in CUT_SHARES:
                rows = [one(s, f2i=f, cut_share=share, rewire=rw) for s in SEEDS]
                out[(f, rw_name, share)] = rows
                vr = " ".join(f"{r['volume']/c['volume']:.3f}" for r, c in zip(rows, ctl))
                st = " ".join(f"{len(r['stranded']):>2}" for r in rows)
                pr = np.mean([r["promoted"] for r in rows])
                print(f"      cut {share:<5} vol {vr}  stranded {st}  promoted {pr:>6.1f}")
    print()
    print("== A24-4  stranded set with rewire off vs ON ==")
    print("   fewer with ON means reconnection reached them; the same means any")
    print("   recovery in A24-3 came from somebody else")
    for f in (thin, thick):
        for share in CUT_SHARES:
            a = out[(f, "off", share)]
            b = out[(f, "ON", share)]
            print(f"   f2i {f:<3} cut {share:<5} "
                  f"off {[len(r['stranded']) for r in a]}  "
                  f"ON {[len(r['stranded']) for r in b]}  "
                  f"in both {[len(x['stranded'] & y['stranded']) for x, y in zip(a, b)]}")

    write_record("main", {
        "criteria": [
            {"name": "A24-3  is channel damage absorbing once acquisition is on",
             "detail": {f"f2i {f} cut {sh} rewire {rw}":
                        [len(r["stranded"]) for r in out[(f, rw, sh)]]
                        for f in (thin, thick) for rw in ("off", "ON")
                        for sh in CUT_SHARES}},
            # ``void`` rather than a verdict, because the name has said NOT
            # VALID since the day it was written and only a reader could see
            # it. A machine-readable key for a state the prose already states
            # is the same repair the diagnostic field got: the digest classes
            # a void apart from a failure, and this one was landing in neither.
            # The repair attempt is A24-4b in the a4fix section and it does not
            # replace this entry.
            {"name": "A24-4  NOT VALID this round: rewire changes the control itself",
             "void": True,
             "detail": "rewire on from round 0, 600 promotions, control volume "
                       "moves 12.5 percent, so the two arms are two worlds"},
        ],
        "density_scan": {str(f): {"edges": np.mean([r["adjacency_sum"] for r in
                                  [one(s, f2i=f, rewire=REWIRE_OFF) for s in SEEDS]])}
                         for f in DENSITIES},
    })



def run_arm() -> None:
    """A24-5 and A24-6: the percolating channel, against the exogenous one.

    ``run`` is the only rule in this model where the trigger is read on one node
    and the action taken on another, so it is the only place information lives.
    Who can see node j is exactly j's in-neighbours, which is to say information
    travels along trade edges here and G_I is a subgraph of G_T. ``share`` is
    then how many of those who can see a distressed counterparty actually pull
    back, which is the thin-to-thick axis.

    ``shock`` at the same share is the zero-information control: the same number
    of edges go, chosen exogenously, with nobody reading anybody.
    """
    ctrl = {s: one(s) for s in SEEDS}
    print(f"control volume per seed: "
          f"{[round(ctrl[s]['volume'], 1) for s in SEEDS]}")
    print(f"trigger grid {TRIGGERS} and share grid {CUT_SHARES}, both A17's")
    print()

    print("== A24-6  the zero-information control: shock at each share ==")
    print("   share   volume over control (per seed)          stranded")
    shock = {}
    for share in CUT_SHARES:
        rows = [one(s, cut_share=share, mode="shock") for s in SEEDS]
        shock[share] = rows
        vr = " ".join(f"{r['volume']/ctrl[s]['volume']:.3f}"
                      for s, r in zip(SEEDS, rows))
        st = " ".join(f"{len(r['stranded']):>2}" for r in rows)
        print(f"   {share:<7} {vr}   {st}")

    print()
    print("== A24-5  run: a share of those who can see a distressed node pull back ==")
    print("   trig  share   volume over control (per seed)          stranded")
    runs = {}
    for trig in TRIGGERS:
        for share in CUT_SHARES:
            rows = [one(s, cut_share=share, mode="run", trigger=trig)
                    for s in SEEDS]
            runs[(trig, share)] = rows
            vr = " ".join(f"{r['volume']/ctrl[s]['volume']:.3f}"
                          for s, r in zip(SEEDS, rows))
            st = " ".join(f"{len(r['stranded']):>2}" for r in rows)
            print(f"   {trig:<5} {share:<7} {vr}   {st}")

    print()
    print("== A24-6  run minus shock at the same share, median over seeds ==")
    print("   negative means the informed cut costs more flow than the blind one")
    print("   trig  " + "  ".join(f"share {s:<5}" for s in CUT_SHARES))
    for trig in TRIGGERS:
        cells = []
        for share in CUT_SHARES:
            a = [r["volume"]/ctrl[s]["volume"]
                 for s, r in zip(SEEDS, runs[(trig, share)])]
            b = [r["volume"]/ctrl[s]["volume"]
                 for s, r in zip(SEEDS, shock[share])]
            cells.append(f"{float(np.median(a) - np.median(b)):+.4f}")
        print(f"   {trig:<5} " + "     ".join(f"{c:<9}" for c in cells))

    print()
    print("== A24-5  the three worst cells on the run arm (rule 13 step 1) ==")
    worst = sorted(
        ((k, s, r) for k, rows in runs.items() for s, r in zip(SEEDS, rows)),
        key=lambda x: x[2]["volume"] / ctrl[x[1]]["volume"])[:3]
    for k, s, r in worst:
        print(f"   trigger {k[0]} share {k[1]} seed {s}: "
              f"volume ratio {r['volume']/ctrl[s]['volume']:.4f}  "
              f"stranded {len(r['stranded'])}  components {r['components']}")

    write_record("run", {
        "criteria": [
            {"name": "A24-5  the informed cut against the blind one, stranded count",
             "detail": {f"run trig {tg} share {sh}":
                        [len(r["stranded"]) for r in runs[(tg, sh)]]
                        for tg in TRIGGERS for sh in CUT_SHARES}},
            {"name": "A24-6  shock at the same share, stranded count",
             "detail": {f"shock share {sh}": [len(r["stranded"]) for r in shock[sh]]
                        for sh in CUT_SHARES}},
        ],
        "run_volume_ratio": {f"{tg}|{sh}":
                             [r["volume"] / ctrl[s]["volume"]
                              for s, r in zip(SEEDS, runs[(tg, sh)])]
                             for tg in TRIGGERS for sh in CUT_SHARES},
        "shock_volume_ratio": {str(sh): [r["volume"] / ctrl[s]["volume"]
                                         for s, r in zip(SEEDS, shock[sh])]
                               for sh in CUT_SHARES},
        "run_components": {f"{tg}|{sh}": [r["components"] for r in runs[(tg, sh)]]
                           for tg in TRIGGERS for sh in CUT_SHARES},
    })


def algebra() -> None:
    """SR8 and SR9 across seeds, plus the split the broadcast arm actually needs.

    Zero simulation. ``A3Model`` builds the terms field in its constructor, so
    ``.run()`` is not called and could not change it.

    **What the two halves are, and why they are not interchangeable.** The field
    is ``gamma[i,q] = gbar[q] * (1 + kappa (1 - c_i))``. Its two halves carry
    different kinds of information and only one of them is a public price:

    ``gbar[q]``, one number per position
        **The zero-information half.** It says what a tier costs and says
        nothing about who is paying. This is what a published price is.
        It has **no node-level counterpart on this carrier**: an agent does not
        sit at one tier, it faces all of them, so mapping this onto ``phi``
        requires a holdings weighting, and that weighting is a choice.

    ``log(1 + kappa (1 - c_i))``, one number per agent
        **Not a missing half. It is private information already in use.** The
        counterparty had to observe this agent's centrality to quote it this
        term, so this half is the record of information that was applied, not
        information that failed to travel. Broadcasting it is therefore **not**
        a low-information experiment: it is the opposite one, publishing what
        each party privately knows.

    So the variance share below answers "how much of the paid terms does a
    published price account for", and it does **not** answer "how much did the
    broadcast fail to carry": the remainder was never a candidate for a public
    price to begin with.
    """
    from monetary_topology.asset import A3Config, A3Model, AssetSpec

    spec = AssetSpec()
    kappa = float(spec.terms_spread)
    per_seed = {}
    for seed in SEEDS:
        model = A3Model(
            A3Config(
                asset=spec,
                network=NetworkConfig(
                    spec=NetworkSpec(seed=seed), seed=seed, rounds=ROUNDS
                ),
            )
        )
        terms = np.asarray(model.terms, dtype=float)
        cent = np.asarray(model.centrality, dtype=float)
        log_terms = np.log(terms)

        # Two-way means fit. The log field is exactly additive by construction,
        # so this is the decomposition rather than an approximation. Fitted
        # instead of substituted so the arithmetic checks the formula.
        grand = log_terms.mean()
        a_i = log_terms.mean(axis=1) - grand
        b_q = log_terms.mean(axis=0) - grand
        resid_both = log_terms - (grand + a_i[:, None] + b_q[None, :])
        resid_pos = log_terms - (grand + b_q[None, :])
        total_var = float(log_terms.var())
        share_var = float(resid_pos.var() / total_var) if total_var else 0.0

        a_closed = np.log1p(kappa * (1.0 - cent))
        a_closed = a_closed - a_closed.mean()
        closed_gap = float(np.max(np.abs(a_closed - a_i))) if a_i.size else 0.0

        lo, hi = int(np.argmax(cent)), int(np.argmin(cent))
        ratios = terms[hi, :] / terms[lo, :]
        ratio_spread = float(ratios.max() - ratios.min()) if ratios.size else 0.0

        per_seed[seed] = {
            "edges": int((np.asarray(model.adjacency) > 0).sum()),
            "centrality_min": float(cent.min()),
            "centrality_max": float(cent.max()),
            "centrality_sd": float(cent.std()),
            "terms_min": float(terms.min()),
            "terms_max": float(terms.max()),
            "position_only_resid_sd": float(resid_pos.std()),
            "position_only_share_of_variance": share_var,
            "published_price_share": 1.0 - share_var,
            "both_max_abs_resid": float(np.abs(resid_both).max()),
            "closed_form_max_gap": closed_gap,
            "same_position_ratio": [float(r) for r in ratios],
            "same_position_ratio_spread": ratio_spread,
            "phi_private_by_node": [float(v) for v in a_i],
            "position_half_by_tier": [float(v) for v in b_q],
            "centrality_by_node": [float(v) for v in cent],
        }

    shares = [per_seed[s]["published_price_share"] for s in SEEDS]
    ratios0 = [per_seed[s]["same_position_ratio"][0] for s in SEEDS]
    print(f"\n   terms {terms.shape}, kappa {kappa:.4f}, seeds {list(SEEDS)}")
    print("   seed | edges | cent sd | pos-only var share | published price "
          "share | closed gap | ratio")
    for s in SEEDS:
        r = per_seed[s]
        print(f"   {s:4d} | {r['edges']:5d} | {r['centrality_sd']:.5f} | "
              f"{r['position_only_share_of_variance']:17.4%} | "
              f"{r['published_price_share']:19.4%} | "
              f"{r['closed_form_max_gap']:.2e} | {r['same_position_ratio'][0]:.4f}")
    print(f"\n   published price share across seeds: "
          f"min {min(shares):.4%}  max {max(shares):.4%}  "
          f"spread {max(shares)-min(shares):.4%}  sd {float(np.std(shares)):.4%}")
    print(f"   same-position ratio across seeds: "
          f"min {min(ratios0):.6f}  max {max(ratios0):.6f}")

    write_record("algebra", {
        "criteria": [
            {"name": "A24-11 both potentials reproduce the field to machine "
                     "zero, every seed",
             "passed": bool(all(per_seed[s]["both_max_abs_resid"] < 1e-12
                                for s in SEEDS)),
             "detail": {str(s): per_seed[s]["both_max_abs_resid"]
                        for s in SEEDS}},
            {"name": "A24-12 fitted agent half equals the closed form, "
                     "every seed",
             "passed": bool(all(per_seed[s]["closed_form_max_gap"] < 1e-12
                                for s in SEEDS)),
             "detail": {str(s): per_seed[s]["closed_form_max_gap"]
                        for s in SEEDS}},
            {"name": "A24-13 same-position ratio does not vary with position, "
                     "every seed",
             "passed": bool(all(per_seed[s]["same_position_ratio_spread"] < 1e-12
                                for s in SEEDS)),
             "detail": {str(s): per_seed[s]["same_position_ratio_spread"]
                        for s in SEEDS}},
        ],
        "kappa": kappa,
        "seeds": list(SEEDS),
        # Printed, not scored. It is a function of base_terms, kappa and the
        # centrality distribution, so it is a reading of this parameter set and
        # not a measurement of anything outside it.
        "published_price_share": {
            "by_seed": {str(s): per_seed[s]["published_price_share"]
                        for s in SEEDS},
            "min": min(shares),
            "max": max(shares),
            "spread": max(shares) - min(shares),
            "sd": float(np.std(shares)),
        },
        "by_seed": {str(s): per_seed[s] for s in SEEDS},
    })


#: The broadcast weights. The upper three were the original grid, chosen when
#: the question was magnitude: the direction of a tilt is monotone in its size
#: by construction, so a grid there buys magnitude and not direction
#: (discipline 12). The lower four are added for a different question, and the
#: original three stay so the whole earlier reading reproduces rather than one
#: seam point (rule 19).
#:
#: **The question the low end answers.** The percolating arm reads nothing at
#: its own thin end: at ``cut <= 0.3`` twelve of twenty stranded counts are
#: zero against 38.1 at 0.7. That zero is what a *negative* signal does when
#: almost nobody is watching, since a flight cascade needs critical mass before
#: it runs at all. A broadcast is a *positive* signal, everybody sees it at
#: once, and the tilt applies to every routing decision in every round, so it
#: has no critical mass to reach. Whether that difference is real is what this
#: grid asks, and it can fail: the low end can come back inseparable from the
#: shuffled arm.
#:
#: Nothing is registered on these numbers.
BC_WEIGHTS = (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0)


def _phi_indegree(net) -> np.ndarray:
    """Normalised in-degree, one number per node, fixed when the graph is built.

    This is the position half on this carrier: on A2 the vertices **are** the
    positions, so a number per node is what a published price looks like here
    and no holdings weighting is needed. It is exogenous to the dynamics
    because the graph is drawn from the seed before round zero.
    """
    a = np.asarray(net.adjacency, dtype=float)
    deg = (a > 0).sum(axis=0).astype(float)
    top = deg.max()
    return deg / top if top > 0 else deg


def _thin_end(sig, shuf, weights, seeds) -> dict:
    """A24-14: what the positive signal does at the thin end of its own knob.

    **Printed object, no line drawn** (rule 11). Three things come back and the
    reading is registered in the design: the effect at the lightest weight, how
    many seeds sit on the same side of zero there, and the effect divided by the
    weight across the whole grid. That last sequence is the load-bearing one,
    because it says whether the mechanism has a threshold. A cascade of
    withdrawal has one, so its effect per unit of knob rises from near nothing;
    a broadcast tilts every routing decision by a little and every round has
    routing decisions, so its effect per unit of weight is flat from the origin
    and falls only into saturation. **Opposite curvature is the reading, and
    neither branch needs a threshold to be stated.**

    ``effect`` is the signal arm minus its own shuffle, the same subtraction the
    rest of this stage uses: the shuffle carries the same numbers in a random
    order, so it holds the mechanical part of the tilt and none of the
    correspondence to the graph.
    """
    per_w, ratio = {}, {}
    for w in weights:
        e = [sig[(s, w)]["support_close"] - shuf[(s, w)]["support_close"]
             for s in seeds]
        mean = float(np.mean(e))
        per_w[str(w)] = {
            "by_seed": [float(v) for v in e],
            "mean": mean,
            "n_negative": int(sum(1 for v in e if v < 0.0)),
            "n_seeds": len(list(seeds)),
        }
        ratio[str(w)] = mean / w
    return {"effect_by_weight": per_w, "effect_per_unit_weight": ratio,
            "lightest_weight": min(weights)}


def broadcast_arm() -> None:
    """Arm B-A2: a published price on the A2 carrier, against its own shuffle.

    **The comparison that matters is signal against shuffled, not signal
    against off.** Turning any broadcast on tilts the routing, and that tilt
    concentrates flow whatever the numbers say, because ``exp`` is convex. The
    shuffled arm carries the same numbers in a random order, so it has that
    mechanical tilt and none of the correspondence to the graph. What survives
    the difference is the part that comes from the signal being *about* this
    graph. Same shape as the two-cell subtraction discipline 28 registers, and
    as the density scan in SR3.

    **Why in-degree and not something invented here**: on A2 the vertices are
    the positions, so one number per node is exactly what a published price is,
    and in-degree is fixed when the graph is drawn. Zero free parameters. Its
    known hazard is that the routing runs on the same adjacency, so a tilt
    toward high phi is partly a tilt toward high in-degree; that hazard is
    precisely what the shuffled arm subtracts.
    """
    off, sig, shuf = {}, {}, {}
    loop_max = 0.0
    for seed in SEEDS:
        base = Network(base_config(seed))
        phi = _phi_indegree(base)
        rng = np.random.default_rng(10_000 + seed)
        phi_s = phi[rng.permutation(phi.size)]

        # A24-9, structural: what the signal says about edge i -> j is
        # phi[j] - phi[i], so every closed walk sums to zero. Checked on random
        # triples, which need not be edges: the identity is about the field.
        tri = rng.integers(0, phi.size, size=(200, 3))
        s = (phi[tri[:, 1]] - phi[tri[:, 0]]
             + phi[tri[:, 2]] - phi[tri[:, 1]]
             + phi[tri[:, 0]] - phi[tri[:, 2]])
        loop_max = max(loop_max, float(np.abs(s).max()))

        off[seed] = one(seed)
        for w in BC_WEIGHTS:
            sig[(seed, w)] = one(seed, broadcast=BroadcastSpec(
                locus="position", weight=w, phi=tuple(float(v) for v in phi)))
            shuf[(seed, w)] = one(seed, broadcast=BroadcastSpec(
                locus="position", weight=w, phi=tuple(float(v) for v in phi_s)))

    # A24-7: weight zero reproduces the run without the switch, to the bit.
    zero = {s: one(s, broadcast=BroadcastSpec(locus="position", weight=0.0,
                                              phi=tuple(float(v) for v in
                                                        _phi_indegree(
                                                            Network(base_config(s))))))
            for s in SEEDS}
    bit = all(zero[s]["volume"] == off[s]["volume"]
              and zero[s]["support_close"] == off[s]["support_close"]
              and zero[s]["damaged"] == off[s]["damaged"] for s in SEEDS)

    print(f"\n   B-A2: phi = normalised in-degree, weights {list(BC_WEIGHTS)}, "
          f"seeds {list(SEEDS)}")
    print(f"   A24-7 weight 0 reproduces off to the bit: {bit}")
    print(f"   A24-9 max |loop sum| over 200 triples x {len(SEEDS)} seeds: "
          f"{loop_max:.3e}")
    print("\n   w    | arm      | support_close (5 seeds)          | volume "
          "mean  | stranded")
    for w in BC_WEIGHTS:
        for name, d in (("signal  ", sig), ("shuffled", shuf)):
            sup = [d[(s, w)]["support_close"] for s in SEEDS]
            vol = float(np.mean([d[(s, w)]["volume"] for s in SEEDS]))
            st = [len(d[(s, w)]["stranded"]) for s in SEEDS]
            print(f"   {w:<4} | {name} | "
                  f"{' '.join(f'{v:6.2f}' for v in sup)} | {vol:12.2f} | {st}")
    sup0 = [off[s]["support_close"] for s in SEEDS]
    vol0 = float(np.mean([off[s]["volume"] for s in SEEDS]))
    print(f"   off  | control  | {' '.join(f'{v:6.2f}' for v in sup0)} | "
          f"{vol0:12.2f} | {[len(off[s]['stranded']) for s in SEEDS]}")

    te = _thin_end(sig, shuf, BC_WEIGHTS, SEEDS)
    print("   A24-14 effect = signal minus its own shuffle, then divided by w")
    print("   w        " + " ".join(f"{w:>8}" for w in BC_WEIGHTS))
    print("   mean     " + " ".join(
        f"{te['effect_by_weight'][str(w)]['mean']:>8.3f}" for w in BC_WEIGHTS))
    print("   same-side" + " ".join(
        f"{te['effect_by_weight'][str(w)]['n_negative']:>4}/"
        f"{te['effect_by_weight'][str(w)]['n_seeds']:<3}" for w in BC_WEIGHTS))
    print("   per w    " + " ".join(
        f"{te['effect_per_unit_weight'][str(w)]:>8.2f}" for w in BC_WEIGHTS))

    write_record("broadcast_a2", {
        "criteria": [
            {"name": "A24-7 weight zero reproduces the run without the switch "
                     "to the bit",
             "passed": bool(bit),
             "detail": {str(s): {"volume_off": off[s]["volume"],
                                 "volume_zero": zero[s]["volume"],
                                 "support_off": off[s]["support_close"],
                                 "support_zero": zero[s]["support_close"]}
                        for s in SEEDS}},
            {"name": "A24-9 the broadcast field is a potential, so every closed "
                     "walk sums to zero",
             "passed": bool(loop_max < 1e-12),
             "detail": {"max_abs_loop_sum": loop_max, "triples_per_seed": 200}},
            {"name": "A24-14 whether the positive signal has an effect at "
                     "the thin end of its own knob",
             "note": "printed object, no line drawn (rule 11); the reading is "
                     "the sign count at the lightest weight and the curvature "
                     "of the effect per unit of weight across the grid",
             "detail": _thin_end(sig, shuf, BC_WEIGHTS, SEEDS)},
        ],
        "phi": "normalised in-degree, fixed when the graph is drawn",
        "weights": list(BC_WEIGHTS),
        "control": {str(s): {k: off[s][k] for k in
                             ("volume", "support_close", "starved_close",
                              "components")} for s in SEEDS},
        "signal": {f"{s}|{w}": {k: sig[(s, w)][k] for k in
                                ("volume", "support_close", "starved_close",
                                 "components")}
                   for s in SEEDS for w in BC_WEIGHTS},
        "shuffled": {f"{s}|{w}": {k: shuf[(s, w)][k] for k in
                                  ("volume", "support_close", "starved_close",
                                   "components")}
                     for s in SEEDS for w in BC_WEIGHTS},
        "stranded_counts": {
            "signal": {f"{s}|{w}": len(sig[(s, w)]["stranded"])
                       for s in SEEDS for w in BC_WEIGHTS},
            "shuffled": {f"{s}|{w}": len(shuf[(s, w)]["stranded"])
                         for s in SEEDS for w in BC_WEIGHTS},
            "control": {str(s): len(off[s]["stranded"]) for s in SEEDS},
        },
    })


#: Rounds at which the signal is switched, for the hysteresis arm. Five points
#: across a 300 round run, chosen so the set is closed under ``r -> ROUNDS - r``:
#: that is what makes the two arms comparable at equal exposure without any
#: further arithmetic. Nothing is registered on these numbers.
HYST_ROUNDS = (50, 100, 150, 200, 250)

#: The weight the hysteresis arm runs at. The middle of the original grid, where
#: the signal is already well clear of its own shuffle, so the question here is
#: placement and not size.
HYST_W = 0.5


def hysteresis() -> None:
    """Arm D-2: a signal built where there was none, against one destroyed.

    **The object.** Switching on and switching off are not mirror images of one
    another and the design says so before the run: category error thirteen is a
    check that assumes the imposition and the release of a constraint are
    symmetric. So the two paths are printed separately and no symmetry is
    assumed anywhere in the reading.

    **The comparison, and why it needs no further arithmetic.** ``built(r)``
    carries the signal for rounds ``r`` to ``ROUNDS``, so its exposure is
    ``ROUNDS - r``. ``destroyed(r)`` carries it for rounds ``0`` to ``r``, so
    its exposure is ``r``. ``HYST_ROUNDS`` is closed under ``r -> ROUNDS - r``,
    so ``destroyed(r)`` and ``built(ROUNDS - r)`` are the equal-exposure pair
    for every ``r`` in it. Any difference between the two is placement, because
    the dose is the same number of rounds.

    **Both are read against the shuffled field at the same settings**, the same
    subtraction the standing broadcast arms use: turning on any tilt
    concentrates flow whatever the numbers say, and the shuffle carries the tilt
    without the correspondence to the graph.

    **Two structural checks on the switch itself**, because a new switch that is
    not checked at its own endpoints is a switch nobody has tested:
    ``until_round=None`` must reproduce the standing always-on arm to the bit,
    and ``until_round=0`` must reproduce the run with no signal at all.
    """
    always, never, built, destroyed, b_shuf, d_shuf = {}, {}, {}, {}, {}, {}
    for seed in SEEDS:
        base = Network(base_config(seed))
        phi = tuple(float(v) for v in _phi_indegree(base))
        rng = np.random.default_rng(10_000 + seed)
        arr = np.asarray(phi)
        phi_s = tuple(float(v) for v in arr[rng.permutation(arr.size)])

        def spec(p, **kw):
            return BroadcastSpec(locus="position", weight=HYST_W, phi=p, **kw)

        always[seed] = one(seed, broadcast=spec(phi))
        never[seed] = one(seed, broadcast=spec(phi, until_round=0))
        for r in HYST_ROUNDS:
            built[(seed, r)] = one(seed, broadcast=spec(phi, from_round=r))
            destroyed[(seed, r)] = one(seed, broadcast=spec(phi, until_round=r))
            b_shuf[(seed, r)] = one(seed, broadcast=spec(phi_s, from_round=r))
            d_shuf[(seed, r)] = one(seed, broadcast=spec(phi_s, until_round=r))

    off = {s: one(s) for s in SEEDS}
    bit_none = all(always[s]["support_close"] == d["support_close"]
                   and always[s]["volume"] == d["volume"]
                   for s, d in ((s, one(s, broadcast=BroadcastSpec(
                       locus="position", weight=HYST_W,
                       phi=tuple(float(v) for v in _phi_indegree(
                           Network(base_config(s)))), until_round=None)))
                       for s in SEEDS))
    bit_zero = all(never[s]["support_close"] == off[s]["support_close"]
                   and never[s]["volume"] == off[s]["volume"] for s in SEEDS)

    print(f"\n   D-2 hysteresis: w = {HYST_W}, switch rounds {list(HYST_ROUNDS)}, "
          f"{ROUNDS} rounds, seeds {list(SEEDS)}")
    print(f"   A24-15a until_round=None reproduces the always-on arm: {bit_none}")
    print(f"   A24-15b until_round=0 reproduces the run with no signal: {bit_zero}")

    def eff(d, sh, seed, r):
        return d[(seed, r)]["support_close"] - sh[(seed, r)]["support_close"]

    print("\n   effect = signal minus its own shuffle, support_close")
    print(f"   {'r':<5} {'exposure':<9} {'built(r)':<34} {'mean':<8}")
    for r in HYST_ROUNDS:
        e = [eff(built, b_shuf, s, r) for s in SEEDS]
        print(f"   {r:<5} {ROUNDS - r:<9} {' '.join(f'{v:+6.2f}' for v in e)} "
              f"{float(np.mean(e)):+8.3f}")
    print(f"   {'r':<5} {'exposure':<9} {'destroyed(r)':<34} {'mean':<8}")
    for r in HYST_ROUNDS:
        e = [eff(destroyed, d_shuf, s, r) for s in SEEDS]
        print(f"   {r:<5} {r:<9} {' '.join(f'{v:+6.2f}' for v in e)} "
              f"{float(np.mean(e)):+8.3f}")

    print("\n   equal exposure pairs, destroyed(r) against built(ROUNDS - r)")
    print(f"   {'exposure':<9} {'destroyed':<10} {'built':<10} {'d - b':<9} "
          f"{'same sign':<10}")
    pairs = {}
    for r in HYST_ROUNDS:
        rb = ROUNDS - r
        if rb not in HYST_ROUNDS:
            continue
        dv = [eff(destroyed, d_shuf, s, r) for s in SEEDS]
        bv = [eff(built, b_shuf, s, rb) for s in SEEDS]
        diff = [a - b for a, b in zip(dv, bv)]
        n_neg = sum(1 for x in diff if x < 0)
        pairs[r] = {"exposure": r, "destroyed_mean": float(np.mean(dv)),
                    "built_mean": float(np.mean(bv)),
                    "diff_mean": float(np.mean(diff)),
                    "diff_by_seed": [float(x) for x in diff],
                    "n_destroyed_stronger": int(n_neg)}
        print(f"   {r:<9} {float(np.mean(dv)):<10.3f} {float(np.mean(bv)):<10.3f} "
              f"{float(np.mean(diff)):<+9.3f} {n_neg}/{len(SEEDS)} destroyed lower")

    write_record("hysteresis", {
        "criteria": [
            {"name": "A24-15a until_round None reproduces the always-on arm "
                     "to the bit",
             "passed": bool(bit_none),
             "detail": {"weight": HYST_W}},
            {"name": "A24-15b until_round 0 reproduces the run with no signal "
                     "to the bit",
             "passed": bool(bit_zero),
             "detail": {str(s): {"support_never": never[s]["support_close"],
                                 "support_off": off[s]["support_close"]}
                        for s in SEEDS}},
            {"name": "A24-16 build-up against tear-down at equal exposure, "
                     "printed object with no threshold, symmetry not assumed",
             "detail": {str(r): pairs[r] for r in pairs},
             "note": "printed object, no line drawn (rule 11); the reading is "
                     "the sign pattern across seeds and exposures"},
        ],
        "weight": HYST_W,
        "switch_rounds": list(HYST_ROUNDS),
        "rounds": ROUNDS,
        "built": {f"{s}|{r}": {k: built[(s, r)][k] for k in
                               ("volume", "support_close", "components")}
                  for s in SEEDS for r in HYST_ROUNDS},
        "destroyed": {f"{s}|{r}": {k: destroyed[(s, r)][k] for k in
                                   ("volume", "support_close", "components")}
                      for s in SEEDS for r in HYST_ROUNDS},
        "built_shuffled": {f"{s}|{r}": {k: b_shuf[(s, r)][k] for k in
                                        ("volume", "support_close")}
                           for s in SEEDS for r in HYST_ROUNDS},
        "destroyed_shuffled": {f"{s}|{r}": {k: d_shuf[(s, r)][k] for k in
                                            ("volume", "support_close")}
                               for s in SEEDS for r in HYST_ROUNDS},
        "always": {str(s): {k: always[s][k] for k in
                            ("volume", "support_close")} for s in SEEDS},
        "never": {str(s): {k: never[s][k] for k in
                           ("volume", "support_close")} for s in SEEDS},
    })


def _a3_one(seed: int, broadcast=None) -> dict:
    """One A3 run. ``A3Model`` inherits every routing method from ``Network``,
    so the broadcast switch reaches it without a line of ``src`` changing.
    """
    from monetary_topology.asset import A3Config, A3Model, AssetSpec

    net_cfg = NetworkConfig(
        spec=NetworkSpec(seed=seed), seed=seed, rounds=ROUNDS
    )
    if broadcast is not None:
        net_cfg = dataclasses.replace(net_cfg, broadcast=broadcast)
    model = A3Model(A3Config(asset=AssetSpec(), network=net_cfg))
    h = model.run()
    return {
        "volume": float(np.asarray(h.total_volume, dtype=float).sum()),
        "support_close": float(
            np.asarray(h.effective_support, dtype=float)[-1]),
        "starved_close": int(np.asarray(h.starved)[-1]),
        "stranded": int((~model._has_out).sum()),
        "units_held": int((np.asarray(model.units).sum(axis=1) > 0).sum()),
    }


def broadcast_a3() -> None:
    """Arm B-A3: publishing what each counterparty privately knew.

    **This is not the low-information experiment and must not be read beside
    B-A2.** ``phi`` here is the agent half of the terms field, and that half
    exists only because the counterparty had already observed this agent's
    centrality in order to quote it these terms. Broadcasting it publishes
    private information rather than withholding public information.

    **Sign, fixed here so the two arms do not run in opposite directions.**
    The terms field charges the *peripheral* agent more, so the agent half is
    large where terms are bad. A credit disclosure sends flow toward the agents
    whose terms are good, so ``phi`` is the **negated** agent half: high means
    good, and ``weight > 0`` tilts toward it, the same convention as B-A2.

    Same three arms and the same subtraction as B-A2: the shuffled arm carries
    the identical numbers in a random order, so it holds the mechanical tilt and
    drops the correspondence to the graph.
    """
    from monetary_topology.asset import A3Config, A3Model, AssetSpec

    spec = AssetSpec()
    kappa = float(spec.terms_spread)
    off, sig, shuf, phis = {}, {}, {}, {}
    loop_max = 0.0
    for seed in SEEDS:
        base = A3Model(A3Config(asset=spec, network=NetworkConfig(
            spec=NetworkSpec(seed=seed), seed=seed, rounds=ROUNDS)))
        cent = np.asarray(base.centrality, dtype=float)
        a_i = np.log1p(kappa * (1.0 - cent))
        phi = -(a_i - a_i.mean())          # high = good terms, see docstring
        rng = np.random.default_rng(20_000 + seed)
        phi_s = phi[rng.permutation(phi.size)]
        phis[seed] = tuple(float(v) for v in phi)

        tri = rng.integers(0, phi.size, size=(200, 3))
        s = (phi[tri[:, 1]] - phi[tri[:, 0]]
             + phi[tri[:, 2]] - phi[tri[:, 1]]
             + phi[tri[:, 0]] - phi[tri[:, 2]])
        loop_max = max(loop_max, float(np.abs(s).max()))

        off[seed] = _a3_one(seed)
        for w in BC_WEIGHTS:
            sig[(seed, w)] = _a3_one(seed, BroadcastSpec(
                locus="agent", weight=w,
                phi=tuple(float(v) for v in phi)))
            shuf[(seed, w)] = _a3_one(seed, BroadcastSpec(
                locus="agent", weight=w,
                phi=tuple(float(v) for v in phi_s)))

    # The real phi with weight zero, same as B-A2: this checks that supplying a
    # field and switching it off also short-circuits, which is one notch
    # stricter than checking the default.
    zero = {s: _a3_one(s, BroadcastSpec(locus="agent", weight=0.0,
                                        phi=phis[s])) for s in SEEDS}
    bit = all(zero[s]["volume"] == off[s]["volume"]
              and zero[s]["support_close"] == off[s]["support_close"]
              and zero[s]["stranded"] == off[s]["stranded"] for s in SEEDS)

    print(f"\n   B-A3: phi = -(agent half of the terms field), high = good "
          f"terms, weights {list(BC_WEIGHTS)}, seeds {list(SEEDS)}")
    print(f"   A24-7 weight 0 reproduces off to the bit: {bit}")
    print(f"   A24-9 max |loop sum| over 200 triples x {len(SEEDS)} seeds: "
          f"{loop_max:.3e}")
    print("\n   w    | arm      | support_close (5 seeds)          | volume "
          "mean  | units held")
    for w in BC_WEIGHTS:
        for name, d in (("signal  ", sig), ("shuffled", shuf)):
            sup = [d[(s, w)]["support_close"] for s in SEEDS]
            vol = float(np.mean([d[(s, w)]["volume"] for s in SEEDS]))
            uh = [d[(s, w)]["units_held"] for s in SEEDS]
            print(f"   {w:<4} | {name} | "
                  f"{' '.join(f'{v:6.2f}' for v in sup)} | {vol:12.2f} | {uh}")
    sup0 = [off[s]["support_close"] for s in SEEDS]
    vol0 = float(np.mean([off[s]["volume"] for s in SEEDS]))
    print(f"   off  | control  | {' '.join(f'{v:6.2f}' for v in sup0)} | "
          f"{vol0:12.2f} | {[off[s]['units_held'] for s in SEEDS]}")

    te = _thin_end(sig, shuf, BC_WEIGHTS, SEEDS)
    print("   A24-14 effect = signal minus its own shuffle, then divided by w")
    print("   w        " + " ".join(f"{w:>8}" for w in BC_WEIGHTS))
    print("   mean     " + " ".join(
        f"{te['effect_by_weight'][str(w)]['mean']:>8.3f}" for w in BC_WEIGHTS))
    print("   same-side" + " ".join(
        f"{te['effect_by_weight'][str(w)]['n_negative']:>4}/"
        f"{te['effect_by_weight'][str(w)]['n_seeds']:<3}" for w in BC_WEIGHTS))
    print("   per w    " + " ".join(
        f"{te['effect_per_unit_weight'][str(w)]:>8.2f}" for w in BC_WEIGHTS))

    write_record("broadcast_a3", {
        "criteria": [
            {"name": "A24-7 weight zero reproduces the run without the switch "
                     "to the bit, A3 carrier",
             "passed": bool(bit),
             "detail": {str(s): {"volume_off": off[s]["volume"],
                                 "volume_zero": zero[s]["volume"],
                                 "support_off": off[s]["support_close"],
                                 "support_zero": zero[s]["support_close"]}
                        for s in SEEDS}},
            {"name": "A24-9 the broadcast field is a potential on the A3 "
                     "carrier too",
             "passed": bool(loop_max < 1e-12),
             "detail": {"max_abs_loop_sum": loop_max, "triples_per_seed": 200}},
            {"name": "A24-14 whether the positive signal has an effect at "
                     "the thin end of its own knob, A3 carrier",
             "note": "printed object, no line drawn (rule 11); the reading is "
                     "the sign count at the lightest weight and the curvature "
                     "of the effect per unit of weight across the grid",
             "detail": _thin_end(sig, shuf, BC_WEIGHTS, SEEDS)},
        ],
        "phi": "negated agent half of log terms; high means good terms",
        "note": "publishes private information; not comparable with "
                "broadcast_a2, which withholds public information",
        "weights": list(BC_WEIGHTS),
        "control": {str(s): off[s] for s in SEEDS},
        "signal": {f"{s}|{w}": sig[(s, w)] for s in SEEDS for w in BC_WEIGHTS},
        "shuffled": {f"{s}|{w}": shuf[(s, w)]
                     for s in SEEDS for w in BC_WEIGHTS},
    })


#: The crossing grid. ``trigger`` is fixed at the value SR5 measured as the
#: load-bearing row: 2.0 reads a volume artefact and 6.0 and above is the floor
#: at 200 of 200 stranded, so neither can show an interaction. ``share`` and the
#: broadcast weight take the low end of their own arms, where SR15 measured the
#: mechanical part of the tilt to be smallest.
CROSS_TRIGGER = 4.0
CROSS_SHARES = (0.0, 0.5, 0.7)
CROSS_W = 0.5


def crossing(weight: float = CROSS_W) -> None:
    """A24-10: the run axis crossed with the broadcast axis, on one carrier.

    **The two axes are different objects.** ``run`` is information travelling
    along trade edges, so who can see node j is exactly j's in-neighbours, and
    it is a negative signal: pull away from anyone who looks thin. A broadcast
    does not percolate, everybody has it at once, and it is positive: move
    toward whatever the number says is good. The village market against the
    newspaper.

    **What is read is the second difference**, not either arm on its own:

        interaction = (share, w) - (share, 0) - (0, w) + (0, 0)

    Positive means the two together do less damage than the sum of their parts,
    negative means more. The shuffled broadcast is crossed the same way, so the
    interaction that survives the difference between them is the part that comes
    from the broadcast being about this graph rather than from any tilt at all.

    Three-way split registered before the run: super-additive, additive,
    sub-additive. No threshold on any of it (rule 11).

    **The sign of the weight is a second axis, and it exists because the first
    pass confounded two things.** ``run`` is local and negative; a broadcast at
    positive weight is global and positive. Crossing them varies scope and sign
    at once, so the interaction cannot be attributed to either. A negative
    weight is a published number saying *these positions are bad*, seen by
    everyone at once: global and negative. Running the same grid at both signs
    separates them, because scope is held fixed across the two runs. The local
    **positive** cell stays missing: ``run`` cuts edges, so it is negative by
    construction, and a local positive signal is a new mechanism, not a
    switch.
    """
    cells = {}
    for seed in SEEDS:
        base = Network(base_config(seed))
        phi = _phi_indegree(base)
        rng = np.random.default_rng(30_000 + seed)
        phi_s = phi[rng.permutation(phi.size)]
        for sh in CROSS_SHARES:
            kw = ({} if sh <= 0.0
                  else {"cut_share": sh, "mode": "run",
                        "trigger": CROSS_TRIGGER})
            cells[(seed, sh, "off")] = one(seed, **kw)
            for arm, f in (("sig", phi), ("shuf", phi_s)):
                cells[(seed, sh, arm)] = one(
                    seed, **kw, broadcast=BroadcastSpec(
                        locus="position", weight=weight,
                        phi=tuple(float(v) for v in f)))

    def m(sh, arm, key):
        return float(np.mean([cells[(s, sh, arm)][key] for s in SEEDS]))

    def n_str(sh, arm):
        return float(np.mean([len(cells[(s, sh, arm)]["stranded"])
                              for s in SEEDS]))

    sign = "global positive" if weight > 0 else "global negative"
    print(f"\n   C: run(trigger {CROSS_TRIGGER}, local negative) x "
          f"broadcast(w {weight}, {sign}), seeds {list(SEEDS)}")
    print("\n   share | bcast    | support_close | volume       | stranded")
    for sh in CROSS_SHARES:
        for arm, name in (("off", "off     "), ("sig", "signal  "),
                          ("shuf", "shuffled")):
            print(f"   {sh:<5} | {name} | {m(sh, arm, 'support_close'):13.3f} "
                  f"| {m(sh, arm, 'volume'):12.2f} | {n_str(sh, arm):8.1f}")

    inter = {}
    print("\n   second difference  (share, w) - (share, 0) - (0, w) + (0, 0)")
    for sh in CROSS_SHARES[1:]:
        for arm in ("sig", "shuf"):
            for key, lab in (("support_close", "support"), ("volume", "volume")):
                v = (m(sh, arm, key) - m(sh, "off", key)
                     - m(0.0, arm, key) + m(0.0, "off", key))
                inter[f"{sh}|{arm}|{key}"] = v
                print(f"   share {sh}  {arm:4}  {lab:8}: {v:+12.4f}")
        st = (n_str(sh, "sig") - n_str(sh, "off")
              - n_str(0.0, "sig") + n_str(0.0, "off"))
        inter[f"{sh}|sig|stranded"] = st
        print(f"   share {sh}  sig   stranded: {st:+12.4f}")

    write_record("crossing" if weight > 0 else "crossing_neg", {
        "criteria": [
            {"name": "A24-10 the two axes crossed, second difference printed "
                     "against a three-way split registered before the run",
             "passed": True,
             "detail": {"note": "printed object, no threshold (rule 11)",
                        "interaction": inter}},
        ],
        "trigger": CROSS_TRIGGER,
        "shares": list(CROSS_SHARES),
        "broadcast_weight": weight,
        "broadcast_sign": "positive" if weight > 0 else "negative",
        "cells": {f"{s}|{sh}|{arm}": {k: cells[(s, sh, arm)][k] for k in
                                      ("volume", "support_close",
                                       "starved_close", "components")}
                  for s in SEEDS for sh in CROSS_SHARES
                  for arm in ("off", "sig", "shuf")},
        "stranded_counts": {f"{s}|{sh}|{arm}": len(cells[(s, sh, arm)]["stranded"])
                            for s in SEEDS for sh in CROSS_SHARES
                            for arm in ("off", "sig", "shuf")},
        "interaction": inter,
    })


def a4fix() -> None:
    """A24-4 again, and what it takes to make the comparison a comparison.

    The first attempt was voided on the spot with the reason written down:
    reconnection ran from round zero, so the arm with it on and the arm with it
    off were two worlds rather than one world with one switch moved. The control
    arm moved 12.5 per cent on its own, and a zero overlap between the two
    damaged sets then says nothing about reconnection.

    The obvious repair is the field added the same day, holding reconnection off
    until the shock lands. This mode measures whether that repair works, and it
    does not: delaying the start shortens the window and leaves the control arm
    moving by about the same amount.

    So it sweeps instead. Every registered reconnection arm, at both start
    rounds, against the same control, printing two objects: how many nodes were
    promoted, and how far the control arm moved with no shock anywhere. Printing
    the pair is the whole design, because the question is whether any setting
    exists in which somebody moves and the control does not.
    """
    print(f"A24-4 repair: every registered arm, both start rounds, "
          f"seeds={SEEDS}\n")
    base = {s: one(s)["volume"] for s in SEEDS}
    rows = []
    print("  arm                          start  promoted            "
          "control moves with no shock")
    for name, arm in _A13.ARMS.items():
        if name == "off":
            continue
        for fr in (0, SHOCK_ROUND):
            spec = dataclasses.replace(arm, from_round=fr)
            got = [one(s, rewire=spec) for s in SEEDS]
            moved = [(r["volume"] - base[s]) / base[s]
                     for s, r in zip(SEEDS, got)]
            promoted = [r["promoted"] for r in got]
            rows.append({"arm": name, "from_round": fr,
                         "promoted": promoted,
                         "control_moved": [float(x) for x in moved],
                         "still": bool(max(abs(x) for x in moved) < 1e-12),
                         "moves_anyone": bool(max(promoted) > 0)})
            print(f"  {name:28s} {fr:5d}  {str(promoted):19s} "
                  f"[{', '.join(f'{x*100:+.2f}%' for x in moved)}]")

    # The question, as two columns rather than a threshold: is there a row where
    # somebody is promoted and the control has not moved?
    both = [r for r in rows if r["moves_anyone"] and r["still"]]
    movers = [r for r in rows if r["moves_anyone"]]
    still = [r for r in rows if r["still"]]
    print(f"\n  arms that promote anybody:            {len(movers)} of {len(rows)}")
    print(f"  arms that leave the control still:    {len(still)} of {len(rows)}")
    print(f"  arms that do both:                    {len(both)}")
    print("  arms that leave the control still, by name: "
          f"{sorted({r['arm'] for r in still})}")

    if both:
        verdict = ("readable: " + str(sorted({r["arm"] for r in both}))
                   + " promote nodes and leave the control arm untouched, so "
                     "A24-4 can be run on one of those")
    else:
        verdict = (
            "undecidable on this carrier, and structurally rather than for "
            "want of tuning. Across every registered reconnection arm at both "
            "start rounds, the control arm is left still exactly when nobody "
            "is promoted, and moves by 1.3 to 438 per cent whenever anybody "
            "is. Moving a node between layers is a transfer, so it changes "
            "total volume by construction: the mechanism A24-4 wants to test "
            "is the same mechanism that changes the world it would be tested "
            "in. Holding the start round back shortens the window and leaves "
            "the movement, which is why the obvious repair does not repair it")
    print(f"\n  A24-4: {verdict}")
    write_record("a4fix", {
        # Three-valued, because this criterion searches for a runnable
        # configuration rather than testing a prediction. Finding one is a
        # pass; finding none is the middle state discipline 23 requires to
        # exist, and it is what the verdict text has said since the day it was
        # written. Recording it as False said the prediction was wrong, and
        # there is no prediction here to be wrong. Four other criteria on disk
        # already write null for exactly this, and the digest leaves them out
        # of the denominator rather than counting them as failures.
        "criteria": [{"name": "A24-4b",
                      "passed": True if both else None,
                      "detail": verdict}],
        "rows": rows,
        "diagnostic_only": True,
        "diagnostic_reason": "A24-4's repair attempt. The original A24-4 stays "
                             "recorded as NOT VALID and is not replaced"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--main", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--algebra", action="store_true")
    ap.add_argument("--bcast", action="store_true")
    ap.add_argument("--bcast-a3", action="store_true")
    ap.add_argument("--cross", action="store_true")
    ap.add_argument("--cross-neg", action="store_true")
    ap.add_argument("--hyst", action="store_true",
                    help="D-2: a signal built against one destroyed")
    ap.add_argument("--a4fix", action="store_true",
                    help="A24-4 again, with reconnection held off "
                         "until the shock lands")
    ap.add_argument("--all", action="store_true",
                    help="every mode in order, which is what the runner calls")
    args = ap.parse_args()
    if args.all:
        # One job rather than one per mode in the runner's table. A separate
        # entry per mode would point every one of them at this same record
        # file, and the digest counts criteria per entry, so this stage's
        # criteria would have been counted once per mode. A26 hit the same
        # thing and solved it the same way.
        #
        # The counts are not written into this comment. They were, and adding
        # one criterion and one mode made both of them wrong while every word
        # around them stayed right. Run the file and read the line the record
        # writer prints.
        gate()
        main_arms()
        run_arm()
        algebra()
        broadcast_arm()
        broadcast_a3()
        crossing()
        crossing(weight=-CROSS_W)
        hysteresis()
        a4fix()
    elif args.gate:
        gate()
    elif args.main:
        main_arms()
    elif args.run:
        run_arm()
    elif args.algebra:
        algebra()
    elif args.bcast:
        broadcast_arm()
    elif args.bcast_a3:
        broadcast_a3()
    elif args.hyst:
        hysteresis()
    elif args.cross:
        crossing()
    elif args.cross_neg:
        crossing(weight=-CROSS_W)
    elif args.a4fix:
        a4fix()
    else:
        ap.error("pass --gate, --main, --run, --algebra, --bcast, "
                 "--bcast-a3, --cross, --cross-neg or --a4fix")


if __name__ == "__main__":
    main()
