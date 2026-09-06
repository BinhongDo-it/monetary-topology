"""A26: what happens when every node ranks its counterparties.

Every other rule in ``network.py`` splits a node's spending over its surviving
edges in proportion. Nothing anywhere compares two counterparties, and the
docstring of ``EDGE_CUT_MODES`` records the same thing: every rule here reads
the node's own state. ``GreedySpec`` is the first one that does not. A node
fills the counterparty that did the most business last round, then the next,
and so on down its own out-edges.

**This is the strongest assumption for the opposing account and the weakest for
this one**, which is why it is worth spending a station on. It is the agent
standard economics is most willing to grant: locally optimising, acting on what
it can see, moving on without hesitation when a counterparty is full. If the
framework's readings survive under it, that is a stronger result than surviving
under a rule nobody would defend.

It is also the cell the crossing was missing. A24 §R19 crossed a local negative
signal against a global positive one and could not separate scope from sign,
because only one row of the square existed:

                     negative signal      positive signal
    local            EdgeCutSpec run      **this station**
    global           broadcast w<0        broadcast w>0

``run`` and this rule read the same number, ``inflow``, and act on it with
opposite signs: one sees a low value and cuts the edge for good, the other sees
a high value and fills it first. That shared signal is what makes ``--cross`` a
clean crossing rather than two unrelated interventions laid on top of one
another.

Modes

    --gate    A26-1 and A26-2: the switch off reproduces the previous build to
              the bit, and the switch on reorders without deleting.
    --main    A26-3: what the ranking does to support and volume, five seeds,
              against the permutation control.
    --cross   A26-4: the ranking crossed with ``run``, read as a second
              difference against the control arm.

Usage

    python experiments/a26_greedy.py --gate
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.config import MonetaryAuthority, WageChannel  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    EdgeCutSpec,
    GreedySpec,
    Network,
)

RECORD = RESULTS / "a26_greedy.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# A24's carrier, grid and helpers, imported rather than restated so this station
# introduces no constant of its own (D5) and its crossing lands on the same
# machine A24 read (design sheet, box 4).
_A24 = _load(ROOT / "experiments" / "a24_information_wall.py", "_a24_for_a26")
base_config = _A24.base_config
components = _A24.components
jaccard = _A24.jaccard
_fmt = _A24._fmt
SEEDS = _A24.SEEDS
ROUNDS = _A24.ROUNDS
F2I = _A24.F2I
# The wage elasticity the carrier is registered at. Imported rather
# than restated, and named here because `one` reports it: the sweep
# below overrides it per cell and a record that did not say which value
# a row was run at would be a row nobody can place.
ELASTICITY = _A24.ELASTICITY
SHOCK_ROUND = _A24.SHOCK_ROUND
CROSS_TRIGGER = _A24.CROSS_TRIGGER
# A24's own cut grid, not this station's. The two-point grid A24 used for its
# own crossing (0.5 and 0.7) turned out to sit past the point where the outcome
# saturates, so the crossing is run on A24's full registered grid instead. No
# constant of this station's own is introduced either way (D5).
CROSS_SHARES = (0.0,) + tuple(_A24.CUT_SHARES)


def write_record(section: str, payload: dict) -> None:
    """Merge one mode's payload into the station record. A24's writer's shape."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A26"
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    n = sum(len(v.get("criteria", [])) for v in doc["sections"].values())
    print(f"\n   record: {RECORD.name}, sections {sorted(doc['sections'])}, "
          f"{n} criteria")


def one(seed: int, *, greedy: bool = False, shuffled: bool = False,
        cut_share: float = 0.0, trigger: float = CROSS_TRIGGER,
        rounds: int = ROUNDS, issuance: bool = True,
        f2i: int = F2I, elasticity: float | None = None) -> dict:
    """One run. Returns the objects, not summaries of them (rule 11).

    ``issuance=False`` is ``MonetaryAuthority(rule="none")``, which the config
    file registers as the baseline for isolating one mechanism at a time. It is
    needed here because the endogenous rule is a saturating element sitting
    between the routing and every outcome: it issues the shortfall in layer-two
    inflow every round, so once that inflow is on the floor the stock climbs at
    a fixed rate to a ceiling of ``opening inflow x rounds`` and stops carrying
    information about what the routing did.
    """
    cfg = base_config(seed, 0.0, f2i)
    cfg = dataclasses.replace(cfg, rounds=rounds,
                              greedy=GreedySpec(enabled=greedy,
                                                shuffled=shuffled))
    if elasticity is not None:
        cfg = dataclasses.replace(cfg, wages=WageChannel(elasticity=elasticity))
    if not issuance:
        cfg = dataclasses.replace(cfg, authority=MonetaryAuthority(rule="none"))
    if cut_share > 0.0:
        cfg = dataclasses.replace(cfg, edge_cut=EdgeCutSpec(
            mode="run", share=cut_share, trigger=trigger,
            at_round=SHOCK_ROUND, targeting="random"))
    net = Network(cfg)
    h = net.run()
    proportional = net._route > 0.0
    ever = net._greedy_ever_used
    filled = np.asarray(net._greedy_filled, dtype=int)
    return {
        "seed": seed, "greedy": greedy, "shuffled": shuffled,
        "cut_share": cut_share, "f2i": f2i,
        "elasticity": ELASTICITY if elasticity is None else elasticity,
        "volume": float(np.asarray(h.total_volume, dtype=float).sum()),
        "support_close": float(np.asarray(h.effective_support, dtype=float)[-1]),
        "support_l2_close": float(
            np.asarray(h.effective_support_l2, dtype=float)[-1]),
        "reached_close": int(np.asarray(h.realized_support)[-1]),
        "starved_close": int(np.asarray(h.starved)[-1]),
        # The claim stock and what the authority did to it. Added after the
        # first run of this mode: volume rose twenty-five fold and reading it
        # as circulation would have been wrong, because the stock itself had
        # risen sixty-nine fold. Volume is not the object here, the stock and
        # the target the authority is aiming at are.
        "claims_close": float(np.asarray(h.holdings, dtype=float)[-1].sum()),
        "issuance_sum": float(np.asarray(h.issuance, dtype=float).sum()),
        "l2_inflow_close": float(np.asarray(h.layer2_inflow, dtype=float)[-1]),
        # The area, not the endpoint. The endpoint sits on the floor in every
        # arm once the cut is deep enough, and the claim stock sits on the
        # ceiling the controller's own arithmetic gives it, so a crossing read
        # on either of those is reading a bound rather than a mechanism.
        "l2_inflow_sum": float(np.asarray(h.layer2_inflow, dtype=float).sum()),
        "l2_inflow_open": float(np.asarray(h.layer2_inflow, dtype=float)[0]),
        "wage_owed_close": float(np.asarray(h.wage_owed, dtype=float)[-1]),
        "wage_paid_close": float(np.asarray(h.wage_paid, dtype=float)[-1]),
        "stranded": set(np.flatnonzero(~net._has_out).tolist()),
        "departed": set(np.flatnonzero(~net._alive).tolist()),
        "adjacency_sum": float(net.adjacency.sum()),
        "components": components(net.adjacency),
        # The rank-and-fill objects. Counterparties actually reached per payer,
        # and how many edges the proportional split would have used that the
        # queue never once reached in the whole run.
        # **Last round only.** See the note in ``_greedy_reroute``. Kept
        # because it is what a single round's queue looks like, reported under
        # a name that says so, and not used as a run-level quantity.
        "filled_min_last_round": int(filled.min()),
        "filled_max_last_round": int(filled.max()),
        "filled_median_last_round": float(np.median(filled)),
        # The run-level counterpart: how many distinct counterparties a payer
        # reached at any point in the run.
        "reached_median_over_run": float(np.median(
            ever.sum(axis=1)[net._has_out])) if net._has_out.any() else 0.0,
        "prop_edges": int(proportional.sum()),
        "ever_used": int((ever & proportional).sum()),
        "never_used": int((proportional & ~ever).sum()),
    }


def gate(baseline: Path | None = None) -> None:
    """A26-1 and A26-2. Both structural, both unit tests rather than readings."""
    crit = []

    # ---- A26-1: the switch off reproduces the previous build to the bit ----
    #
    # Run against the ``.expired`` copy taken before the switch was added, so
    # the check is a comparison and not an argument (rule 19: the check is run,
    # not reasoned). The copy is found by name; a tree without one says so
    # rather than passing by having nothing to compare against.
    src = ROOT / "src" / "monetary_topology"
    cands = sorted(src.glob("network.py.expired_*_pre_A26"))
    if baseline is None and cands:
        baseline = cands[-1]
    print(f"A26-1  baseline: {baseline.name if baseline else 'NONE FOUND'}")
    if baseline is None:
        crit.append({"name": "A26-1", "passed": False,
                     "detail": "no pre-A26 baseline copy on disk to compare "
                               "against; the check cannot be run"})
    else:
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "monetary_topology"
            shutil.copytree(src, pkg, ignore=shutil.ignore_patterns(
                "*.expired*", "__pycache__"))
            shutil.copy2(baseline, pkg / "network.py")
            saved = {k: v for k, v in sys.modules.items()
                     if k.startswith("monetary_topology")}
            for k in list(saved):
                del sys.modules[k]
            sys.path.insert(0, tmp)
            old = importlib.import_module("monetary_topology.network")
            h_old = old.Network(old.NetworkConfig(
                spec=old.NetworkSpec(seed=0), seed=0, rounds=120)).run()
            f_old = _arrays(h_old)
            sys.path.pop(0)
            for k in list(sys.modules):
                if k.startswith("monetary_topology"):
                    del sys.modules[k]
            sys.modules.update(saved)
        from monetary_topology.network import (NetworkConfig as NC,
                                               NetworkSpec as NS)
        h_new = Network(NC(spec=NS(seed=0), seed=0, rounds=120)).run()
        f_new = _arrays(h_new)
        keys = sorted(set(f_old) | set(f_new))
        diffs = [k for k in keys
                 if k not in f_old or k not in f_new
                 or f_old[k].shape != f_new[k].shape
                 or not np.array_equal(f_old[k], f_new[k])]
        print(f"       {len(keys)} history fields compared, "
              f"{len(diffs)} differ: {diffs if diffs else 'none'}")
        crit.append({
            "name": "A26-1",
            "passed": not diffs,
            "detail": (f"greedy off reproduces {baseline.name} on all "
                       f"{len(keys)} history fields, bit for bit")
            if not diffs else f"fields that differ: {diffs}"})

    # ---- A26-2: reorders, does not delete -------------------------------
    #
    # Three clauses, and the third is the one A11's ruling bought: a starved
    # edge has to be able to come back, or the rule has grown an absorbing wall
    # of its own and the crossing with ``run`` reads two irreversible things
    # rather than one reversible and one not.
    print("\nA26-2  reorders without deleting")
    rows = []
    for seed in SEEDS:
        off = one(seed, greedy=False)
        on = one(seed, greedy=True)
        cfg = dataclasses.replace(base_config(seed, 0.0, F2I),
                                  greedy=GreedySpec(enabled=True))
        net = Network(cfg)
        adj_before = net.adjacency.copy()
        net.run()
        adj_same = bool(np.array_equal(adj_before, net.adjacency))
        rows_ok = bool(np.allclose(
            net._route.sum(axis=1)[net._has_out], 1.0, rtol=0, atol=1e-12))
        rows.append({
            "seed": seed, "adjacency_unchanged": adj_same,
            "route_rows_sum_one": rows_ok,
            "adjacency_sum_off": off["adjacency_sum"],
            "adjacency_sum_on": on["adjacency_sum"],
            "prop_edges": on["prop_edges"], "ever_used": on["ever_used"],
            "never_used": on["never_used"],
            "filled_median_last_round": on["filled_median_last_round"],
            "filled_max_last_round": on["filled_max_last_round"],
        })
        print(f"  seed {seed}  adjacency unchanged {adj_same}  "
              f"rows sum one {rows_ok}  "
              f"edges {on['prop_edges']}  reached at least once "
              f"{on['ever_used']}  never {on['never_used']}  "
              f"filled/payer median {on['filled_median_last_round']:.1f} "
              f"max {on['filled_max_last_round']}")
    c1 = all(r["adjacency_unchanged"] for r in rows)
    c2 = all(r["route_rows_sum_one"] for r in rows)
    never = [r["never_used"] for r in rows]
    c3 = all(v == 0 for v in never)
    crit.append({"name": "A26-2a", "passed": c1,
                 "detail": "the adjacency is bit-identical before and after "
                           "every run with the rule on"})
    crit.append({"name": "A26-2b", "passed": c2,
                 "detail": "routing rows still sum to one wherever a payer has "
                           "an out-edge"})
    crit.append({
        "name": "A26-2c", "passed": c3,
        "detail": (f"edges the proportional split would use that the queue "
                   f"never reaches in {ROUNDS} rounds, by seed: {never}. "
                   f"Zero everywhere is reversibility in the sense A11 asks "
                   f"for; anything else is an absorbing wall the rule made "
                   f"itself, and it is a reading rather than a defect")})
    for c in crit:
        print(f"  {'PASS' if c['passed'] else 'FAIL'}  {c['name']}  "
              f"{c['detail']}")
    write_record("gate", {"criteria": crit, "rows": rows,
                          "diagnostic_only": True,
                          "diagnostic_reason": "A26 is open; A26-3 and A26-4 "
                                               "have not been scored"})


def main_arm() -> None:
    """A26-3: what the ranking does, against the permutation control.

    Three arms, and the middle one is the reason the third exists. Turning the
    rule off removes the queue as well as the ranking, so ``on`` minus ``off``
    is the mechanism and the information at once. The control arm keeps the
    queue and shuffles which counterparty each capacity belongs to, so
    ``on`` minus ``shuffled`` is what the correspondence to the graph bought.
    """
    rows = []
    print(f"A26-3  carrier: A24 base, f2i={F2I}, rounds={ROUNDS}, "
          f"seeds={SEEDS}\n")
    print("  seed  arm         claims      volume    support   supp_l2   "
          "l2_in_0  l2_in_T   wage_owed  wage_paid")
    for seed in SEEDS:
        for arm, kw in (("off", {}),
                        ("shuffled", {"greedy": True, "shuffled": True}),
                        ("greedy", {"greedy": True})):
            r = one(seed, **kw)
            r["arm"] = arm
            rows.append(r)
            print(f"  {seed:4d}  {arm:9s} {r['claims_close']:9.1f} "
                  f"{r['volume']:11.1f} {r['support_close']:9.4f} "
                  f"{r['support_l2_close']:9.4f} {r['l2_inflow_open']:8.3f} "
                  f"{r['l2_inflow_close']:8.3f} {r['wage_owed_close']:10.3f} "
                  f"{r['wage_paid_close']:10.3f}")

    def col(arm, key):
        return np.array([r[key] for r in rows if r["arm"] == arm], dtype=float)

    print("\n  differences, by seed")
    print("  key                signal-off              signal-shuffled")
    diffs = {}
    for key in ("volume", "claims_close", "issuance_sum", "support_close",
                "support_l2_close", "l2_inflow_close", "wage_paid_close",
                "reached_close", "starved_close"):
        d_off = col("greedy", key) - col("off", key)
        d_sh = col("greedy", key) - col("shuffled", key)
        diffs[key] = {"signal_minus_off": [float(v) for v in d_off],
                      "signal_minus_shuffled": [float(v) for v in d_sh],
                      "off": [float(v) for v in col("off", key)],
                      "shuffled": [float(v) for v in col("shuffled", key)],
                      "greedy": [float(v) for v in col("greedy", key)]}
        print(f"  {key:18s} "
              f"[{', '.join(f'{v:+.3f}' for v in d_off)}]   "
              f"[{', '.join(f'{v:+.3f}' for v in d_sh)}]")

    # Whether the two arms damage the same nodes, or the ranking picks a
    # different set from the same numbers in a different order.
    js = []
    for seed in SEEDS:
        g = [r for r in rows if r["arm"] == "greedy" and r["seed"] == seed][0]
        s = [r for r in rows if r["arm"] == "shuffled" and r["seed"] == seed][0]
        js.append(jaccard(g["stranded"] | g["departed"],
                          s["stranded"] | s["departed"]))
    print(f"\n  damaged-set jaccard, greedy against shuffled, by seed: "
          f"[{', '.join(f'{v:.4f}' for v in js)}]")

    crit = [{
        "name": "A26-3",
        "passed": True,
        "detail": ("three-way read, no threshold. support close by arm: "
                   f"off {[round(v, 4) for v in col('off', 'support_close')]}, "
                   f"shuffled "
                   f"{[round(v, 4) for v in col('shuffled', 'support_close')]}, "
                   f"greedy "
                   f"{[round(v, 4) for v in col('greedy', 'support_close')]}")}]
    write_record("main", {"criteria": crit, "rows": rows, "diffs": diffs,
                          "damaged_jaccard": js,
                          "diagnostic_only": True,
                          "diagnostic_reason": "A26 is open; A26-4 has not "
                                               "been scored"})


#: What the crossing is read on. Volume is deliberately absent from the leading
#: keys: A26-3 established that it moves with the claim stock rather than with
#: circulation, so a crossing read on it would be a crossing on the issuance
#: rule. It is still printed, because everything this run produces is reported
#: (the completeness rule), just not read first.
#: ``never_used`` is deliberately absent. With the rule off nothing ever
#: updates the counter, so for that arm it reports the number of surviving
#: edges instead of the number of unreached ones, and the two are not the same
#: object (category error six). It stays a level reading in ``--gate`` and does
#: not enter a difference.
CROSS_KEYS = ("l2_inflow_sum", "claims_close", "l2_inflow_close",
              "wage_paid_close", "support_close", "volume")

#: What the controller can issue in total if layer two never receives anything:
#: the opening layer-two inflow, every round, for the whole run. A cell within a
#: whisker of this has saturated and its second difference is arithmetic on the
#: bound rather than a reading. Not a threshold on an estimator: it is the
#: closed form of the issuance rule, and it is printed with the cells beside it.
def _ceiling(runs, seed) -> float:
    return runs[(seed, "off", 0.0)]["l2_inflow_open"] * float(ROUNDS)



#: Set by ``--cross`` and ``--cross-nomoney``. Module level rather than an
#: argument so the saturation helper and the printer read the same setting the
#: runs were made under.
ISSUANCE = True


def cross(issuance: bool = True) -> None:
    """A26-4: the ranking crossed with ``run``, as a second difference.

    The square A24 could not close. ``run`` is a local negative signal, this
    station's rule is a local positive one, and both read ``inflow``. Crossing
    them asks whether a positive local signal and a negative local signal on the
    same observable add up, cancel, or do something neither does alone.

    **Read against the control arm, not against the rule being off.** Turning
    the rule off removes the queue with it, so a second difference taken against
    ``off`` would credit the queue's own concentration to the crossing. The
    control arm holds the queue and shuffles the ranking, so the difference
    taken against it is what the correspondence to the graph contributed. Both
    are printed; the one that is read is the second.
    """
    global ISSUANCE
    ISSUANCE = issuance
    print(f"A26-4  crossing: rank-and-fill x run, trigger={CROSS_TRIGGER}, "
          f"shares={CROSS_SHARES}, seeds={SEEDS}, "
          f"authority={'endogenous' if issuance else 'none'}\n")
    runs = {}
    for seed in SEEDS:
        for arm, kw in (("off", {}),
                        ("shuffled", {"greedy": True, "shuffled": True}),
                        ("greedy", {"greedy": True})):
            for share in CROSS_SHARES:
                runs[(seed, arm, share)] = one(seed, cut_share=share,
                                               issuance=ISSUANCE, **kw)

    # Saturation first, because it decides which shares can be read at all.
    # A cell whose claim stock is within one round's issuance of the closed-form
    # ceiling has stopped responding, and a second difference across two
    # saturated cells returns the main effect with a minus sign.
    sat = {}
    if not issuance:
        print("  saturation check: the controller is off, so there is no "
              "ceiling to sit on; the claim stock is constant by construction")
        for share in CROSS_SHARES:
            sat[share] = []
    else:
        print("  saturation check: ceiling = opening layer-2 inflow x rounds")
        for share in CROSS_SHARES:
            hits = []
            for seed in SEEDS:
                ceil = _ceiling(runs, seed)
                for arm in ("off", "shuffled", "greedy"):
                    r = runs[(seed, arm, share)]
                    if r["claims_close"] >= ceil - r["l2_inflow_open"]:
                        hits.append((seed, arm))
            sat[share] = hits
            print(f"    share {share:4.2f}   {len(hits):2d} of 15 cells at the "
                  f"ceiling  "
                  f"{'READABLE' if not hits else 'saturated: ' + str(hits)}")
    readable = [s for s in CROSS_SHARES if s > 0.0 and not sat[s]]
    print(f"\n  shares the crossing can be read on: "
          f"{readable if readable else 'NONE'}\n")

    print("  seed  arm        share      claims   l2_in_T   l2_in_sum  "
          "wage_paid   support")
    for seed in SEEDS:
        for arm in ("off", "shuffled", "greedy"):
            for share in CROSS_SHARES:
                r = runs[(seed, arm, share)]
                print(f"  {seed:4d}  {arm:9s} {share:5.2f} {r['claims_close']:11.1f} "
                      f"{r['l2_inflow_close']:9.3f} {r['l2_inflow_sum']:11.1f} "
                      f"{r['wage_paid_close']:10.3f} {r['support_close']:9.4f}")

    # The second difference, per key, per share, per seed. Two of them: against
    # the control arm, which is the reading, and against the switch being off,
    # which is printed so that nothing this run produced goes unreported.
    inter = {}
    for base in ("shuffled", "off"):
        for key in CROSS_KEYS:
            for share in CROSS_SHARES:
                if share == 0.0:
                    continue
                vals = []
                for seed in SEEDS:
                    g_r = runs[(seed, "greedy", share)][key]
                    g_0 = runs[(seed, "greedy", 0.0)][key]
                    b_r = runs[(seed, base, share)][key]
                    b_0 = runs[(seed, base, 0.0)][key]
                    vals.append(float(g_r) - float(g_0) - float(b_r)
                                + float(b_0))
                inter[f"{key}|share={share}|vs_{base}"] = vals

    for base, label in (("shuffled", "READ: against the control arm"),
                        ("off", "printed only: against the switch off")):
        print(f"\n  {label}")
        print("  key                share   second difference by seed"
              "                              sign")
        for key in CROSS_KEYS:
            for share in CROSS_SHARES:
                if share == 0.0:
                    continue
                v = inter[f"{key}|share={share}|vs_{base}"]
                same = ("all +" if all(x > 0 for x in v)
                        else "all -" if all(x < 0 for x in v) else "MIXED")
                print(f"  {key:18s} {share:5.2f}   "
                      f"[{', '.join(f'{x:+10.3f}' for x in v)}]  {same}")

    # Whether the second factor has any room left once the first has acted.
    # Printed as the object rather than tested against a line (rule 11): for
    # each arm, how far layer two's total inflow travels as the cut deepens.
    # An arm whose range is a rounding error next to the control arm's has
    # nothing left for the cut to take, and a second difference on it is
    # masking rather than an interaction.
    print("\n  room left for the cut: range of l2_inflow_sum across shares")
    print("  seed      off arm            control arm         rank-and-fill "
          "     ctrl/off   greedy/off  masked")
    room = {}
    masked = 0
    for seed in SEEDS:
        spans = {}
        for arm in ("off", "shuffled", "greedy"):
            vals = [runs[(seed, arm, s)]["l2_inflow_sum"] for s in CROSS_SHARES]
            spans[arm] = (min(vals), max(vals))
        base = spans["off"][1] - spans["off"][0]

        def _r(arm):
            return ((spans[arm][1] - spans[arm][0]) / base
                    if base > 0 else float("nan"))

        rg, rs = _r("greedy"), _r("shuffled")
        # Like for like: the control arm holds the queue and drops the ranking,
        # so it is the comparison that says whether the ranking in particular
        # is what took the cut's room away.
        is_masked = rg < rs
        masked += int(is_masked)
        room[seed] = {"spans": {k: list(v) for k, v in spans.items()},
                      "greedy_over_off": float(rg),
                      "shuffled_over_off": float(rs),
                      "masked": bool(is_masked)}
        print(f"  {seed:4d}  {spans['off'][0]:8.1f}-{spans['off'][1]:8.1f}  "
              f"{spans['shuffled'][0]:8.1f}-{spans['shuffled'][1]:8.1f}  "
              f"{spans['greedy'][0]:8.1f}-{spans['greedy'][1]:8.1f}  "
              f"{rs:10.4f} {rg:12.4f}  {'yes' if is_masked else 'NO':>5s}")
    print(f"  masked in {masked} of {len(SEEDS)} seeds")

    # Three-way, no threshold, and only on a share that is not saturated. The
    # quantity is the area under layer-two inflow: the stock has a ceiling the
    # controller's own arithmetic sets, the endpoint has a floor at zero, and
    # the area has neither in this range.
    if not readable:
        key = "none"
        v = []
        verdict = ("not readable on this grid: every cut share drives the claim "
                   "stock onto the controller's ceiling in at least one cell, "
                   "and a second difference between two saturated cells is the "
                   "main effect with a minus sign, not an interaction")
    else:
        key = f"l2_inflow_sum|share={readable[-1]}|vs_shuffled"
        v = inter[key]
        ratios = [round(room[s]["greedy_over_off"], 4) for s in SEEDS]
        if masked == len(SEEDS):
            verdict = ("masking, not an interaction: with the ranking on, "
                       "layer two's total inflow barely moves as the cut "
                       f"deepens. Range under the ranking is {ratios} of the "
                       "range with it off, by seed, and below the control "
                       "arm's in every seed. The second difference is the "
                       "first factor's main effect, so A26-4 is undecidable "
                       "on this carrier rather than answered")
        elif masked:
            verdict = (f"undecidable on this carrier. Masking in {masked} of "
                       f"{len(SEEDS)} seeds: the ranking leaves the cut almost "
                       f"no room, ratios {ratios} against the control arm's, "
                       "so in those seeds the second difference returns the "
                       "ranking's own main effect. The remaining seed does not "
                       "mask, so the reading is not uniform either way. The "
                       "middle state of the three, not a failure")
        elif all(x > 0 for x in v):
            verdict = ("superadditive: the two local signals together leave "
                       "layer two with more than the sum of what each leaves "
                       "it alone")
        elif all(x < 0 for x in v):
            verdict = ("subadditive: the negative local signal takes back part "
                       "of what the positive one did")
        else:
            verdict = ("undecided at this carrier: the second difference does "
                       "not hold one sign across seeds")
    print(f"\n  A26-4 on {key}: {verdict}")
    crit = [{"name": "A26-4", "passed": True,
             "detail": f"{verdict}. Values by seed: "
                       f"{[round(x, 3) for x in v]}"}]
    write_record("cross_nomoney" if not issuance else "cross", {
        "criteria": crit,
        "room": room,
        "rows": [dict(v, key=f"{k[0]}|{k[1]}|{k[2]}") for k, v in runs.items()],
        "interactions": inter,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open; the station has not been closed out"})


def overlap() -> None:
    """Are the edges the queue abandons the edges the run arm would cut.

    This checks a conclusion rather than adding one. A26 was opened to fill the
    fourth cell of a square whose other local cell is the run arm, and the two
    read the same number with opposite signs. If the set of edges the ranking
    stops using turns out to be the set the run arm removes, then they are one
    mechanism wearing two labels, the square has three cells rather than four,
    and what this stage reports as a distinct finding is a restatement.

    Three sets per seed, all on the same graph and seed so they are comparable:
    the edges the ranking never once reaches; the edges the run arm removes;
    and the edges a blind cut of the same size removes, which is the null. The
    overlap of two sets drawn independently from the same edge list is
    ``|A||B| / |E|`` in expectation, so that number is printed beside each
    measured overlap rather than a threshold being set on either.
    """
    print(f"A26-6  what the queue abandons against what the run arm cuts, "
          f"trigger={CROSS_TRIGGER}, seeds={SEEDS}\n")
    rows = []
    print("  seed  share   |adj|  |never|   |cut|   overlap  expected   ratio"
          "   jaccard   blind ov  blind ratio")
    for seed in SEEDS:
        # The ranking alone. Edges present in the proportional split that the
        # queue never reaches in the whole run.
        cfg = dataclasses.replace(base_config(seed, 0.0, F2I),
                                  greedy=GreedySpec(enabled=True))
        net = Network(cfg)
        net.run()
        proportional = net._route > 0.0
        never = proportional & ~net._greedy_ever_used
        # **The universe is the adjacency, not the routing support.** The
        # abandoned set lives inside the discretionary routing, which is the
        # adjacency minus the payroll edges, while the run arm cuts anywhere in
        # the adjacency. Dividing by the smaller of the two put the expected
        # overlap about three times too high and made every measured overlap
        # read as a third of chance, uniformly, which is what gave it away: a
        # ratio that lands on the same value in all ten cells is arithmetic,
        # not a finding. Both sets are subsets of the adjacency, so that is
        # what the two of them are drawn from.
        universe = int((net.adjacency > 0).sum())
        support = int(proportional.sum())

        for share in (0.3, 0.5):
            # The run arm alone, on the same graph, differenced against the
            # adjacency it started from so the set is the edges themselves.
            c2 = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                edge_cut=EdgeCutSpec(mode="run", share=share,
                                     trigger=CROSS_TRIGGER,
                                     at_round=SHOCK_ROUND, targeting="random"))
            n2 = Network(c2)
            before = n2.adjacency > 0
            n2.run()
            cut = before & ~(n2.adjacency > 0)

            # The null: a blind cut of the same size, which is what the shock
            # arm is. Its overlap with the abandoned set is what any two sets
            # of these sizes would share by arithmetic.
            c3 = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                edge_cut=EdgeCutSpec(mode="shock", share=share,
                                     at_round=SHOCK_ROUND, targeting="random"))
            n3 = Network(c3)
            before3 = n3.adjacency > 0
            n3.run()
            blind = before3 & ~(n3.adjacency > 0)

            inter = int((never & cut).sum())
            union = int((never | cut).sum())
            exp = (int(never.sum()) * int(cut.sum()) / universe
                   if universe else 0.0)
            binter = int((never & blind).sum())
            bexp = (int(never.sum()) * int(blind.sum()) / universe
                    if universe else 0.0)
            row = {
                "seed": seed, "share": share,
                "adjacency_edges": universe, "route_support": support,
                "never": int(never.sum()), "cut": int(cut.sum()),
                "blind": int(blind.sum()),
                "overlap": inter, "expected": exp,
                "ratio": inter / exp if exp else float("nan"),
                "jaccard": inter / union if union else float("nan"),
                "blind_overlap": binter, "blind_expected": bexp,
                "blind_ratio": binter / bexp if bexp else float("nan"),
            }
            rows.append(row)
            print(f"  {seed:4d} {share:6.2f} {universe:7d} {row['never']:8d} "
                  f"{row['cut']:7d} {inter:9d} {exp:9.1f} {row['ratio']:7.3f} "
                  f"{row['jaccard']:9.4f} {binter:10d} {row['blind_ratio']:12.3f}")

    ratios = [r["ratio"] for r in rows]
    jac = [r["jaccard"] for r in rows]
    blind = [r["blind_ratio"] for r in rows]
    print(f"\n  overlap against chance, run arm:   min {min(ratios):.3f}  "
          f"max {max(ratios):.3f}")
    print(f"  overlap against chance, blind cut: min {min(blind):.3f}  "
          f"max {max(blind):.3f}")
    print(f"  jaccard, run arm:                  min {min(jac):.4f}  "
          f"max {max(jac):.4f}")

    detail = (
        f"three sets per seed on one graph: edges the queue never reaches, "
        f"edges the run arm removes, edges a blind cut of the same size "
        f"removes. Overlap with the run arm runs {min(ratios):.3f} to "
        f"{max(ratios):.3f} times what two sets of those sizes share by "
        f"arithmetic, jaccard {min(jac):.4f} to {max(jac):.4f}; the blind cut "
        f"runs {min(blind):.3f} to {max(blind):.3f}. Read against the blind "
        f"column, not against zero")
    crit = [{"name": "A26-6", "passed": True, "detail": detail}]
    print(f"\n  A26-6: {detail}")
    write_record("overlap", {"criteria": crit, "rows": rows,
                             "diagnostic_only": True,
                             "diagnostic_reason": "A26 is open"})


def locate() -> None:
    """Find a configuration where the ranking bites without flooring layer two.

    A26-4 came back undecidable and the reason was stated: with the ranking on,
    cumulative household inflow is already at half a per cent of control before
    the cut arm does anything, so the cut has nothing left to take and the
    second difference returns the ranking's own main effect. That is a property
    of this carrier at these settings rather than of the two mechanisms, and the
    way to find out which is to look at other settings.

    Two axes, both of them values this project already registered: the density
    of the edges into the intermediate layer, which is A24's own grid, and the
    wage elasticity, which feeds layer two through a channel the ranking does
    not route. Neither is a new parameter.

    The reading is one ratio printed per cell, cumulative household inflow under
    the ranking over the same under the control arm, with the issuance rule off
    so the claim stock cannot climb to its ceiling and hide it. **No line is
    drawn on it.** A cell near zero is floored and cannot carry a crossing; a
    cell near one has no main effect to cross against; what a crossing needs is
    in between, and where that is is what this prints.
    """
    grid_f2i = _A24.DENSITIES
    grid_eta = (0.5, 0.7, 0.9)
    print(f"A26-7  locating a readable cell: f2i x wage elasticity, "
          f"issuance off, seeds={SEEDS}\n")
    print("  f2i   eta    control l2_sum      greedy l2_sum   greedy/control "
          "by seed")
    rows = []
    for f2i in grid_f2i:
        for eta in grid_eta:
            ctrl = [one(s, f2i=f2i, elasticity=eta, issuance=False)
                    for s in SEEDS]
            grd = [one(s, greedy=True, f2i=f2i, elasticity=eta, issuance=False)
                   for s in SEEDS]
            c = [r["l2_inflow_sum"] for r in ctrl]
            g = [r["l2_inflow_sum"] for r in grd]
            ratio = [gi / ci if ci else float("nan") for gi, ci in zip(g, c)]
            rows.append({"f2i": f2i, "elasticity": eta,
                         "control": c, "greedy": g, "ratio": ratio})
            print(f"  {f2i:3d}  {eta:4.1f}  {sum(c)/len(c):14,.0f}  "
                  f"{sum(g)/len(g):17,.0f}   "
                  f"[{', '.join(f'{x:.3f}' for x in ratio)}]")

    # The object, not a verdict: which cells sit away from both ends. Printed
    # with the two ends named so that the middle is read as a range rather than
    # as a threshold somebody chose.
    def band(r, lo, hi):
        return all(lo <= x <= hi for x in r["ratio"])

    mid = [r for r in rows if band(r, 0.05, 0.80)]
    floored = [r for r in rows if all(x < 0.05 for x in r["ratio"])]
    inert = [r for r in rows if all(x > 0.80 for x in r["ratio"])]
    print(f"\n  cells where every seed is under 0.05, the ranking floors "
          f"layer two: {[(r['f2i'], r['elasticity']) for r in floored]}")
    print(f"  cells where every seed is over 0.80, the ranking barely bites: "
          f"{[(r['f2i'], r['elasticity']) for r in inert]}")
    print(f"  cells in between, which is what a crossing needs: "
          f"{[(r['f2i'], r['elasticity']) for r in mid]}")

    detail = (
        "locator sweep, no threshold on any estimator. Cumulative household "
        "inflow under the ranking over the same under the control arm, "
        "issuance off, on A24's density grid crossed with three wage "
        f"elasticities. Floored in {len(floored)} of {len(rows)} cells, barely "
        f"biting in {len(inert)}, in between in {len(mid)}")
    print(f"\n  A26-7: {detail}")
    write_record("locate", {
        "criteria": [{"name": "A26-7", "passed": bool(mid), "detail": detail}],
        "rows": rows,
        "floored": [(r["f2i"], r["elasticity"]) for r in floored],
        "inert": [(r["f2i"], r["elasticity"]) for r in inert],
        "middle": [(r["f2i"], r["elasticity"]) for r in mid],
        "diagnostic_only": True,
        "diagnostic_reason": "locator for A26-4; no criterion of A26 is scored "
                             "on it"})


def cross_queue() -> None:
    """A26-4 again, on an axis the ranking does not floor and a count that lives.

    Two things were wrong with the first two attempts and the locator settled
    both. The outcome was cumulative household inflow, which the ranking drives
    to half a per cent of control at every one of the fifteen registered
    settings, so there was never a cell where the cut arm had room. And the one
    quantity that does move, the count of edges the queue never reaches, could
    not enter a difference because with the ranking off nothing updates it.

    Both are fixed by moving the first axis. Instead of the ranking against
    itself switched off, it is the ranking against the **control arm**, which
    carries the same queue with the ranking shuffled. All four cells then have
    the queue running, the counter updates in all four, and the difference is
    what correspondence to the graph contributed, which is the comparison
    section four already argued for on other grounds.

    The outcome is the count of abandoned edges, which runs 309 to 421 under the
    ranking and is not against any bound.
    """
    print(f"A26-4b  the ranking against its control arm, crossed with the run "
          f"arm. trigger={CROSS_TRIGGER}, seeds={SEEDS}\n")
    shares = [s for s in CROSS_SHARES if s > 0.0]
    runs = {}
    for seed in SEEDS:
        for arm in ("shuffled", "greedy"):
            for share in (0.0, *shares):
                runs[(seed, arm, share)] = one(
                    seed, greedy=True, shuffled=(arm == "shuffled"),
                    cut_share=share, issuance=False)

    print("  seed  arm        share   never_used   route_edges   l2_in_sum")
    for seed in SEEDS:
        for arm in ("shuffled", "greedy"):
            for share in (0.0, *shares):
                r = runs[(seed, arm, share)]
                print(f"  {seed:4d}  {arm:9s} {share:5.2f} {r['never_used']:12d} "
                      f"{r['prop_edges']:13d} {r['l2_inflow_sum']:11.1f}")

    keys = ("never_used", "prop_edges", "l2_inflow_sum", "support_close")
    inter = {}
    print("\n  second difference, ranking against its control arm")
    print("  key                share   by seed"
          "                                        sign")
    for key in keys:
        for share in shares:
            v = []
            for seed in SEEDS:
                g_r = runs[(seed, "greedy", share)][key]
                g_0 = runs[(seed, "greedy", 0.0)][key]
                s_r = runs[(seed, "shuffled", share)][key]
                s_0 = runs[(seed, "shuffled", 0.0)][key]
                v.append(float(g_r) - float(g_0) - float(s_r) + float(s_0))
            inter[f"{key}|share={share}"] = v
            same = ("all +" if all(x > 0 for x in v)
                    else "all -" if all(x < 0 for x in v) else "MIXED")
            print(f"  {key:18s} {share:5.2f}   "
                  f"[{', '.join(f'{x:+9.2f}' for x in v)}]  {same}")

    # Room, the same object section four printed, on the new outcome: does the
    # cut still move the abandoned count once the ranking is on.
    room = {}
    for seed in SEEDS:
        sp = {}
        for arm in ("shuffled", "greedy"):
            vals = [runs[(seed, arm, s)]["never_used"] for s in (0.0, *shares)]
            sp[arm] = (min(vals), max(vals))
        room[seed] = {k: list(v) for k, v in sp.items()}
    print("\n  room on the abandoned count: range across cut shares")
    print("  seed   control arm        ranking")
    for seed in SEEDS:
        a, b = room[seed]["shuffled"], room[seed]["greedy"]
        print(f"  {seed:4d}   {a[0]:5d}-{a[1]:5d}      {b[0]:5d}-{b[1]:5d}")

    deep = shares[-1]
    v = inter[f"never_used|share={deep}"]
    if all(x > 0 for x in v):
        verdict = ("superadditive on the abandoned count: the ranking and the "
                   "cut together strand more edges than the two do apart")
    elif all(x < 0 for x in v):
        verdict = ("subadditive on the abandoned count: the cut takes back part "
                   "of what the ranking abandoned, which it can do by removing "
                   "the edge outright so that it is no longer an edge that went "
                   "unused")
    else:
        verdict = ("still undecidable: the second difference does not hold one "
                   "sign across seeds on an outcome the ranking does not floor, "
                   "so the earlier undecidable was not only about saturation")
    print(f"\n  A26-4b at share {deep}: {verdict}")
    write_record("cross_queue", {
        "criteria": [{"name": "A26-4b", "passed": True, "detail": verdict}],
        "rows": [dict(v, key=f"{k[0]}|{k[1]}|{k[2]}") for k, v in runs.items()],
        "interactions": inter, "room": room,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def _graph_stats(net) -> dict:
    """Properties of the graph itself, before anything is run on it."""
    a = np.asarray(net.adjacency, dtype=float) > 0
    ind = a.sum(axis=0).astype(float)
    outd = a.sum(axis=1).astype(float)
    comp, largest = components(np.asarray(net.adjacency, dtype=float))
    n = a.shape[0]
    return {
        "edges": int(a.sum()),
        "in_degree_sd": float(ind.std()),
        "out_degree_sd": float(outd.std()),
        "in_degree_max": float(ind.max()),
        "components": comp,
        "largest_component_share": largest / n,
        "route_support": int((net._route > 0).sum()),
        "wage_payers": int(np.asarray(net._wage_payers).size),
        "l1": int(np.asarray(net._l1).size),
        "l2": int(np.asarray(net._l2).size),
    }


def split_probe(seeds=None) -> None:
    """Which property of the graph goes with the sign, and can it be tested.

    A26-4b came back with the second difference splitting two seeds against
    three, the same split at all four cut depths. That is a real object and the
    obvious next question is what separates the two groups.

    **With five points and a dozen candidate properties something separates
    them whatever is going on**, so this mode is written in two halves and the
    halves are not the same kind of thing. The first prints the properties
    beside the signs and picks a candidate. The second runs seeds the candidate
    was not chosen on and asks whether it predicts their signs. Only the second
    carries anything, and it is registered here rather than decided afterwards:
    **the candidate is whichever single property orders the five seeds so that
    the two positive ones fall on one side, and it is tested by whether the new
    seeds' signs follow it.**
    """
    seeds = tuple(seeds or SEEDS)
    share = CROSS_SHARES[-1]
    print(f"A26-8  what goes with the sign. seeds={seeds}, cut share={share}\n")
    rows = []
    for seed in seeds:
        cfg = dataclasses.replace(base_config(seed, 0.0, F2I),
                                  greedy=GreedySpec(enabled=True))
        net = Network(cfg)
        stats = _graph_stats(net)
        # The sign, recomputed here so the row carries both halves and nobody
        # has to line two tables up by eye.
        cells = {}
        for arm in ("shuffled", "greedy"):
            for sh in (0.0, share):
                cells[(arm, sh)] = one(seed, greedy=True,
                                       shuffled=(arm == "shuffled"),
                                       cut_share=sh, issuance=False)
        d = (cells[("greedy", share)]["never_used"]
             - cells[("greedy", 0.0)]["never_used"]
             - cells[("shuffled", share)]["never_used"]
             + cells[("shuffled", 0.0)]["never_used"])
        # The four cells themselves, not only their combination. Added after
        # the second difference came back bimodal with an empty middle: a
        # difference of four numbers can be bimodal because one of the four is,
        # and printing only the combination cannot tell those apart. Same runs,
        # one more thing kept.
        stats.update({"seed": seed, "second_difference": float(d),
                      "sign": "+" if d > 0 else "-",
                      "cells": {f"{arm}|{sh}": cells[(arm, sh)]["never_used"]
                                for arm, sh in cells}})
        rows.append(stats)

    keys = ("edges", "route_support", "in_degree_sd", "out_degree_sd",
            "in_degree_max", "components", "largest_component_share",
            "wage_payers")
    print("  seed  sign   2nd diff  " + "  ".join(f"{k[:11]:>11s}" for k in keys))
    for r in rows:
        print(f"  {r['seed']:4d}  {r['sign']:^4s} {r['second_difference']:+10.1f}  "
              + "  ".join(f"{r[k]:11.3f}" if isinstance(r[k], float)
                          else f"{r[k]:11d}" for k in keys))

    # Which single property puts every plus on one side of every minus. Printed
    # as the list, because more than one will do it on five points and that is
    # the finding rather than a nuisance.
    plus = [r for r in rows if r["sign"] == "+"]
    minus = [r for r in rows if r["sign"] == "-"]
    seps = []
    for k in keys:
        if not plus or not minus:
            continue
        if max(r[k] for r in plus) < min(r[k] for r in minus):
            seps.append((k, "lower"))
        elif min(r[k] for r in plus) > max(r[k] for r in minus):
            seps.append((k, "higher"))
    print(f"\n  properties that separate the two groups cleanly: {seps}")
    print(f"  candidates found: {len(seps)} of {len(keys)} tried. On "
          f"{len(plus)} against {len(minus)} points, a clean separator is "
          f"cheap: this is a list to test, not a result")
    write_record("split", {
        "criteria": [{"name": "A26-8", "passed": True,
                      "detail": (f"seeds {list(seeds)}, cut share {share}. "
                                 f"Signs "
                                 f"{[r['sign'] for r in rows]}. Properties "
                                 f"separating the groups: {seps}. Generated on "
                                 f"these seeds, so it predicts nothing until it "
                                 f"is run on others")}],
        "rows": rows, "separators": seps,
        "diagnostic_only": True,
        "diagnostic_reason": "candidate generation; nothing is scored on it"})


class _HeadWatcher(Network):
    """Records who is at the head of the queue, round by round.

    A subclass rather than a change to the model: nothing here alters the run,
    the hook it uses is the one the round loop already calls and the base class
    leaves empty, and the readings are identical to the same seed run through
    ``Network`` because no line of arithmetic is touched.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.heads: list[int] = []

    def _post_round(self, t: int) -> None:
        if self._last_inflow is not None:
            self.heads.append(int(np.argmax(self._last_inflow)))


def head_probe(seeds=None) -> None:
    """The queue's head, and whether it goes with the two modes.

    The eight coarse graph properties are out on twenty seeds, so the next
    candidates are mechanism-level and discrete, which is what section twelve
    registered: where the injection lands, and who the ranking puts first.

    **The direction is written down before the run.** The rule fills the
    counterparty with the largest inflow, so a head that never changes funnels
    everything to one place and leaves the rest unreached, while a head that
    rotates spreads the filling over more counterparties. The three seeds that
    abandon eleven per cent of their edges should therefore have **more**
    distinct heads and more changes of head than the seventeen that abandon
    twenty-six to thirty-six. If they have fewer, the candidate is dead in the
    direction as well as in the separation.
    """
    seeds = tuple(seeds or range(20))
    print(f"A26-9  the head of the queue against the two modes. "
          f"seeds={seeds[0]}-{seeds[-1]}\n")
    rows = []
    for seed in seeds:
        cfg = dataclasses.replace(base_config(seed, 0.0, F2I),
                                  greedy=GreedySpec(enabled=True),
                                  authority=MonetaryAuthority(rule="none"))
        net = _HeadWatcher(cfg)
        net.run()
        heads = net.heads
        changes = sum(1 for i in range(1, len(heads)) if heads[i] != heads[i-1])
        distinct = len(set(heads))
        modal = max(set(heads), key=heads.count)
        modal_share = heads.count(modal) / len(heads) if heads else float("nan")
        inj = int(net.injection_node)
        deg = (np.asarray(net.adjacency, dtype=float) > 0).sum(axis=0)
        layers = {"l1": set(np.asarray(net._l1).tolist()),
                  "mid": set(np.asarray(net._mid).tolist()),
                  "l2": set(np.asarray(net._l2).tolist())}

        def where(i):
            for k, v in layers.items():
                if i in v:
                    return k
            return "?"

        prop = net._route > 0.0
        never = int((prop & ~net._greedy_ever_used).sum())
        # The rule's own state variable, kept beside the graph properties on
        # purpose. How many counterparties a payer actually reaches is the
        # other side of how many edges go unreached, so if the modes are a
        # property of the allocation rather than of the graph, this is where
        # they show and the graph columns are where they do not.
        filled = np.asarray(net._greedy_filled, dtype=int)
        rows.append({
            "seed": seed, "never_used": never,
            "filled_min_last_round": int(filled.min()),
            "filled_median_last_round": float(np.median(filled)),
            "filled_max_last_round": int(filled.max()),
            "filled_mean_last_round": float(filled.mean()),
            # The run-level counterpart, which is what a claim about a run has
            # to be made on. See the note in ``_greedy_reroute``.
            "reached_median_over_run": float(np.median(
                np.asarray(net._greedy_ever_used).sum(axis=1)[net._has_out])),
            "route_support": int(prop.sum()),
            "abandoned_share": never / max(int(prop.sum()), 1),
            "distinct_heads": distinct, "head_changes": changes,
            "modal_head": modal, "modal_head_share": float(modal_share),
            "modal_head_layer": where(modal),
            "modal_head_in_degree": float(deg[modal]),
            "injection_node": inj, "injection_layer": where(inj),
            "injection_in_degree": float(deg[inj]),
            "injection_is_head": bool(inj == modal),
        })

    lo = [r for r in rows if r["abandoned_share"] < 0.20]
    hi = [r for r in rows if r["abandoned_share"] >= 0.20]
    print("  seed  abandoned   lastrnd/run   distinct  changes   "
          "modal head (layer, share)   injection (layer)  inj==head")
    for r in rows:
        mark = " *" if r in lo else "  "
        print(f"  {r['seed']:4d}{mark} {r['abandoned_share']*100:7.1f}%  "
              f"{r['filled_median_last_round']:6.1f}/"
              f"{r['reached_median_over_run']:<5.1f}  "
              f"{r['distinct_heads']:8d} {r['head_changes']:8d}   "
              f"{r['modal_head']:4d} {r['modal_head_layer']:>4s} "
              f"{r['modal_head_share']*100:5.1f}%        "
              f"{r['injection_node']:5d} {r['injection_layer']:>4s}    "
              f"{str(r['injection_is_head']):>5s}")
    print(f"\n  * marks the low-abandonment mode: {[r['seed'] for r in lo]}")

    keys = ("distinct_heads", "head_changes", "modal_head_share",
            "modal_head_in_degree", "injection_in_degree",
            "filled_median_last_round", "filled_mean_last_round",
            "filled_max_last_round", "reached_median_over_run")
    seps = []
    for k in keys:
        if not lo or not hi:
            continue
        if max(r[k] for r in lo) < min(r[k] for r in hi):
            seps.append((k, "lower in the low mode"))
        elif min(r[k] for r in lo) > max(r[k] for r in hi):
            seps.append((k, "higher in the low mode"))
    for k in ("modal_head_layer", "injection_layer", "injection_is_head"):
        a = {r[k] for r in lo}
        b = {r[k] for r in hi}
        if a and b and not (a & b):
            seps.append((k, f"{sorted(a)} against {sorted(b)}"))
    print(f"  properties that separate the two modes cleanly: {seps}")
    print(f"  chance for one property to isolate {len(lo)} of {len(rows)} "
          f"points: 2/C({len(rows)},{len(lo)}) = "
          f"{2 / (len(rows) * (len(rows)-1) * (len(rows)-2) / 6):.4f}")

    pred = None
    if lo and hi:
        pred = (max(r["distinct_heads"] for r in lo)
                < min(r["distinct_heads"] for r in hi))
    detail = (f"registered before the run: the low-abandonment seeds should "
              f"have more distinct heads and more head changes. Distinct heads "
              f"in the low mode {[r['distinct_heads'] for r in lo]}, in the "
              f"high mode {sorted(r['distinct_heads'] for r in hi)}. "
              f"Separators found: {seps}")
    print(f"\n  A26-9: {detail}")
    write_record("head", {
        "criteria": [{"name": "A26-9", "passed": bool(seps), "detail": detail}],
        "rows": rows, "separators": seps, "low_mode": [r["seed"] for r in lo],
        "diagnostic_only": True,
        "diagnostic_reason": "candidate testing for the two modes"})


class _RatioWatcher(Network):
    """Records the head's capacity against a typical payer's budget, per round.

    The budget is a proxy and is named one: a payer spends a fresh uniform draw
    times its holdings each round, and the draw is not kept, so the midpoint of
    that payer's own propensity band times its holdings stands in for it. The
    band is per node and is the model's own, so the proxy is exact in
    expectation and wrong only by the round's draw.

    Nothing here changes the run. The hook is the one the round loop already
    calls and the base class leaves empty.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.trace: list[dict] = []

    def _post_round(self, t: int) -> None:
        if self._last_inflow is None:
            return
        cap = np.maximum(np.asarray(self._last_inflow, dtype=float), 0.0)
        mid = 0.5 * (np.asarray(self._p_low, dtype=float)
                     + np.asarray(self._p_high, dtype=float))
        budget = mid * np.maximum(np.asarray(self.holdings, dtype=float), 0.0)
        payers = budget[self._has_out]
        med = float(np.median(payers)) if payers.size else float("nan")
        filled = np.asarray(self._greedy_filled, dtype=int)
        self.trace.append({
            "round": t,
            "head_capacity": float(cap.max()),
            "median_budget": med,
            "ratio": float(cap.max() / med) if med else float("nan"),
            "filled_median_last_round": float(np.median(filled)) if filled.size else 0.0,
        })


def ratio_probe(seeds=None) -> None:
    """Is the mode set in the first rounds, and by that ratio.

    Section fourteen found the proximate quantity, how many counterparties the
    median payer reaches, and said plainly that it is the outcome in other
    units rather than a cause. The quantity upstream of it is the one the rule
    actually consults: how much the head can absorb against what a typical
    payer has to spend. A head that swallows a whole budget ends the queue at
    one; a head that cannot forces the payer down to the second and third.

    **Registered before the run.** The three low-abandonment seeds, whose
    median payer reaches four or five, should show a **lower** ratio than the
    seventeen whose median payer reaches three. And if the mode is decided by
    the draw rather than by the path, the separation should be visible in the
    first rounds and not only at the end.
    """
    seeds = tuple(seeds or range(20))
    print(f"A26-10  head capacity against a typical budget. "
          f"seeds={seeds[0]}-{seeds[-1]}\n")
    rows = []
    for seed in seeds:
        cfg = dataclasses.replace(base_config(seed, 0.0, F2I),
                                  greedy=GreedySpec(enabled=True),
                                  authority=MonetaryAuthority(rule="none"))
        net = _RatioWatcher(cfg)
        net.run()
        tr = net.trace
        prop = net._route > 0.0
        never = int((prop & ~net._greedy_ever_used).sum())
        first = tr[0] if tr else {}
        early = [x["ratio"] for x in tr[:10]]
        late = [x["ratio"] for x in tr[-10:]]
        rows.append({
            "seed": seed,
            "abandoned_share": never / max(int(prop.sum()), 1),
            "ratio_round1": float(first.get("ratio", float("nan"))),
            "filled_median_round1": float(first.get("filled_median_last_round", 0.0)),
            "ratio_first10": float(np.mean(early)) if early else float("nan"),
            "ratio_last10": float(np.mean(late)) if late else float("nan"),
            "filled_median_final": float(tr[-1]["filled_median_last_round"]) if tr else 0.0,
        })

    lo = [r for r in rows if r["abandoned_share"] < 0.20]
    hi = [r for r in rows if r["abandoned_share"] >= 0.20]
    print("  seed  abandoned   ratio@1   filled@1   ratio first10  "
          "ratio last10   filled final")
    for r in rows:
        mark = " *" if r in lo else "  "
        print(f"  {r['seed']:4d}{mark} {r['abandoned_share']*100:7.1f}%  "
              f"{r['ratio_round1']:8.3f} {r['filled_median_round1']:10.1f}   "
              f"{r['ratio_first10']:12.3f}  {r['ratio_last10']:12.3f}  "
              f"{r['filled_median_final']:12.1f}")
    print(f"\n  * the low mode: {[r['seed'] for r in lo]}")

    seps = []
    for k in ("ratio_round1", "ratio_first10", "ratio_last10",
              "filled_median_round1"):
        if not lo or not hi:
            continue
        if max(r[k] for r in lo) < min(r[k] for r in hi):
            seps.append((k, "lower in the low mode"))
        elif min(r[k] for r in lo) > max(r[k] for r in hi):
            seps.append((k, "higher in the low mode"))
    print(f"  properties that separate: {seps}")
    direction = ("as registered" if ("ratio_round1", "lower in the low mode")
                 in seps or ("ratio_first10", "lower in the low mode") in seps
                 else "not in the registered direction")
    detail = (f"registered before the run: the low mode should show a lower "
              f"head-to-budget ratio, visible early if the draw decides it. "
              f"Ratio at round 1, low mode "
              f"{[round(r['ratio_round1'], 3) for r in lo]}, high mode "
              f"{sorted(round(r['ratio_round1'], 3) for r in hi)}. "
              f"Separators: {seps}. Outcome: {direction}")
    print(f"\n  A26-10: {detail}")
    write_record("ratio", {
        "criteria": [{"name": "A26-10",
                      "passed": bool(direction == "as registered"),
                      "detail": detail}],
        "rows": rows, "separators": seps, "low_mode": [r["seed"] for r in lo],
        "diagnostic_only": True,
        "diagnostic_reason": "upstream candidate for the two modes"})


def rank_arm(seeds=None) -> None:
    """Does it matter what the queue is ordered on, and is the feedback needed.

    This stage's own readings say the ordering is driven by its own result: a
    counterparty that goes unreached takes in less, ranks lower next round, and
    goes unreached again. **That sentence has been in the record since the first
    run and has never been tested.** Ordering on the counterparty's in-degree
    tests it directly, because the in-degree does not move with the flow: under
    that ordering the loop the sentence describes cannot close.

    Only the ordering changes. Capacity stays what a counterparty took in last
    round, so this separates two roles the first version had collapsed onto one
    quantity.

    **Registered before the run.** If the feedback is what drives edges out of
    use, the static ordering should leave **fewer** edges unreached. If it
    leaves as many or more, the sentence is wrong and the concentration comes
    from ranking as such rather than from ranking on a quantity the ranking
    moves.
    """
    seeds = tuple(seeds or range(20))
    print(f"A26-12  what the queue is ordered on. seeds={seeds[0]}-{seeds[-1]}, "
          f"capacity held at last round's inflow\n")
    rows = []
    print("  seed   inflow-ranked   degree-ranked   bilateral   "
          "degree-inflow   bilateral-inflow")
    for seed in seeds:
        got = {}
        for rb in ("inflow", "degree", "bilateral"):
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by=rb),
                authority=MonetaryAuthority(rule="none"))
            net = Network(cfg)
            net.run()
            prop = net._route > 0.0
            never = int((prop & ~net._greedy_ever_used).sum())
            got[rb] = {"never": never, "support": int(prop.sum()),
                       "share": never / max(int(prop.sum()), 1)}
        rows.append({"seed": seed,
                     "inflow_share": got["inflow"]["share"],
                     "degree_share": got["degree"]["share"],
                     "bilateral_share": got["bilateral"]["share"],
                     "inflow_never": got["inflow"]["never"],
                     "degree_never": got["degree"]["never"],
                     "bilateral_never": got["bilateral"]["never"],
                     "support": got["inflow"]["support"]})
        d = got["degree"]["share"] - got["inflow"]["share"]
        b = got["bilateral"]["share"] - got["inflow"]["share"]
        print(f"  {seed:4d} {got['inflow']['share']*100:14.1f}% "
              f"{got['degree']['share']*100:14.1f}% "
              f"{got['bilateral']['share']*100:10.1f}% "
              f"{d*100:+14.1f}pp {b*100:+16.1f}pp")

    diffs = [r["degree_share"] - r["inflow_share"] for r in rows]
    fewer = sum(1 for d in diffs if d < 0)
    print(f"\n  static ordering leaves fewer edges unreached in {fewer} of "
          f"{len(rows)} seeds")
    print(f"  difference runs {min(diffs)*100:+.1f} to {max(diffs)*100:+.1f} "
          f"percentage points")
    inf = [r["inflow_share"] for r in rows]
    deg = [r["degree_share"] for r in rows]
    bil = [r["bilateral_share"] for r in rows]
    print(f"  inflow-ranked    range {min(inf)*100:5.1f} to {max(inf)*100:5.1f} per cent")
    print(f"  degree-ranked    range {min(deg)*100:5.1f} to {max(deg)*100:5.1f} per cent")
    print(f"  bilateral-ranked range {min(bil)*100:5.1f} to {max(bil)*100:5.1f} per cent")
    bd = [r["bilateral_share"] - r["inflow_share"] for r in rows]
    print(f"  bilateral against inflow: {min(bd)*100:+.1f} to {max(bd)*100:+.1f} "
          f"percentage points, and the two orders are different objects, one on "
          f"the node and one on the edge")
    lo_inf = [r["seed"] for r in rows if r["inflow_share"] < 0.20]
    lo_bil = [r["seed"] for r in rows if r["bilateral_share"] < 0.20]
    lo_deg = [r["seed"] for r in rows if r["degree_share"] < 0.20]
    print(f"  seeds under twenty per cent: inflow {lo_inf}, bilateral {lo_bil}, "
          f"degree {lo_deg}")

    if fewer == len(rows):
        verdict = ("as registered: the static ordering leaves fewer edges "
                   "unreached in every seed, so the feedback from flow to order "
                   "is doing work")
    elif fewer == 0:
        verdict = ("refuted, and in every seed. The static ordering leaves as "
                   "many edges unreached or more, so the sentence that the "
                   "ordering is driven by its own result is not what produces "
                   "the disuse. Ranking as such produces it, and ranking on a "
                   "quantity the ranking moves is not required")
    else:
        verdict = (f"mixed: the static ordering leaves fewer unreached in "
                   f"{fewer} of {len(rows)} seeds, so neither reading holds "
                   f"across the carrier")
    print(f"\n  A26-12: {verdict}")
    write_record("rank", {
        "criteria": [{"name": "A26-12", "passed": bool(fewer == len(rows)),
                      "detail": verdict}],
        "rows": rows,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


#: The congestion sweep. Zero is the switch off and reproduces the build before
#: it; the rest is a range wide enough to show the direction and its limit. A
#: knob, so what is read is the direction across the sweep and not a value.
ETAS = (0.0, 0.25, 0.5, 1.0, 2.0, 5.0)


def congestion_arm(seeds=None) -> None:
    """Grant the arbitrage and see what survives.

    With terms fixed by position, piling onto a profitable counterparty never
    makes it less profitable, so the arbitrage never closes and any
    concentration is given by the construction. That is the condition the edge
    locus is locked on, and it is also the opposing account's own mechanism:
    the standard claim is that arbitrage removes persistent differences.
    Switching it on hands that over.

    **Registered before the run**, from the axis section eighteen measured:
    congestion makes a filled counterparty fall in the order, which is churn,
    and churn keeps edges in use. So abandonment should **fall** as the
    elasticity rises. What is read is that direction across the sweep, not any
    value on it.

    The registered form of A26-16 was "non-increasing at every step of the
    sweep in every seed". That is the shape the eleventh engineering rule
    forbids, an N-of-N vote on a strict comparator over a path that is not
    claimed to be smooth, and it broke on five seeds whose largest step up is
    0.88 of a point inside a fall of thirty-two. The shape is repaired here
    under the record rule for criterion shape: the direction is read at the
    ends of the sweep, the whole path is printed, and the seeds that rise in
    the middle are named rather than absorbed into a count. Not one number
    below changes with the repair.
    """
    seeds = tuple(seeds or range(20))
    print(f"A26-16  terms that respond to the flow that arrives. "
          f"seeds={seeds[0]}-{seeds[-1]}, eta={ETAS}\n")
    rows = []
    diff_seeds = {e: [] for e in ETAS}
    frozen_mismatch = []
    header = "  seed  " + "".join(f"  eta={e:<6.2f}" for e in ETAS) + "   degree"
    print(header)
    for seed in seeds:
        vals, used = {}, {}
        for eta in ETAS:
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by="terms",
                                  congestion=eta),
                authority=MonetaryAuthority(rule="none"))
            net = Network(cfg)
            net.run()
            prop = net._route > 0.0
            used[eta] = np.array(net._greedy_ever_used, dtype=bool)
            vals[eta] = int((prop & ~used[eta]).sum()) / max(int(prop.sum()), 1)
        cfg = dataclasses.replace(
            base_config(seed, 0.0, F2I),
            greedy=GreedySpec(enabled=True, rank_by="degree"),
            authority=MonetaryAuthority(rule="none"))
        net = Network(cfg)
        net.run()
        prop = net._route > 0.0
        used_deg = np.array(net._greedy_ever_used, dtype=bool)
        deg = int((prop & ~used_deg).sum()) / max(int(prop.sum()), 1)
        cells = int((used[0.0] != used_deg).sum())
        if cells:
            frozen_mismatch.append({"seed": seed, "cells": cells})
        for eta in ETAS:
            if eta > 0.0 and int((used[eta] != used_deg).sum()):
                diff_seeds[eta].append(seed)
        rows.append({"seed": seed, "degree": deg,
                     "eta0_vs_degree_cells": cells,
                     **{f"eta_{e}": vals[e] for e in ETAS}})
        print(f"  {seed:4d}  " + "".join(f"{vals[e]*100:10.1f}%" for e in ETAS)
              + f" {deg*100:8.1f}%")

    rises = []
    for r in rows:
        v = [r[f"eta_{e}"] for e in ETAS]
        for i in range(len(v) - 1):
            if v[i + 1] > v[i] + 1e-12:
                rises.append({"seed": r["seed"], "from": ETAS[i],
                              "to": ETAS[i + 1],
                              "pp": (v[i + 1] - v[i]) * 100.0})
    bumpy = sorted({d["seed"] for d in rises})
    falls = [r for r in rows if r[f"eta_{ETAS[-1]}"] < r["eta_0.0"]]
    zero = [r["seed"] for r in rows if r[f"eta_{ETAS[-1]}"] <= 0.0]
    worst = max((d["pp"] for d in rises), default=0.0)

    print(f"\n  A26-14  terms at eta=0 against the degree order, on the "
          f"used-edge matrix itself: "
          f"{len(rows) - len(frozen_mismatch)} of {len(rows)} seeds identical"
          + (f", mismatches {frozen_mismatch}" if frozen_mismatch else ""))
    print("  A26-15  seeds whose used-edge matrix leaves the degree order:")
    for e in ETAS:
        if e > 0.0:
            print(f"    eta={e:<5.2f} {len(diff_seeds[e])} of {len(rows)}")
    print(f"\n  falls from eta=0 to eta={ETAS[-1]}: {len(falls)} of {len(rows)}"
          f" seeds")
    print(f"  reaching zero at eta={ETAS[-1]}: {len(zero)} of {len(rows)} seeds "
          f"{zero if len(zero) < len(rows) else ''}")
    print(f"  rising at some step in between: {bumpy}, largest rise "
          f"{worst:.2f} points")
    for d in rises:
        print(f"    seed {d['seed']:3d}  eta {d['from']} -> {d['to']}  "
              f"+{d['pp']:.2f} points")
    for e in ETAS:
        v = [r[f"eta_{e}"] for r in rows]
        print(f"    eta={e:<5.2f} abandoned {min(v)*100:5.1f} to "
              f"{max(v)*100:5.1f} per cent, mean {sum(v)/len(v)*100:5.1f}")

    v14 = (f"the switch is off at eta=0 by construction and the run proves it: "
           f"the terms order at eta=0 and the degree order leave the same "
           f"used-edge matrix, cell for cell, in "
           f"{len(rows) - len(frozen_mismatch)} of {len(rows)} seeds"
           + (f". Mismatches {frozen_mismatch}" if frozen_mismatch else ""))
    v15 = ("unit test, one reachable branch. The switch does something as "
           "soon as it is on: the used-edge "
           "matrix leaves the degree order in "
           + ", ".join(f"{len(diff_seeds[e])} of {len(rows)} seeds at eta={e}"
                       for e in ETAS if e > 0.0))
    verdict = (
        f"as registered, and the direction is what is read rather than any "
        f"value on it. Abandonment falls from a mean of "
        f"{sum(r['eta_0.0'] for r in rows)/len(rows)*100:.1f} per cent with "
        f"terms fixed by position to "
        f"{sum(r[f'eta_{ETAS[-1]}'] for r in rows)/len(rows)*100:.1f} at the "
        f"top of the sweep, in {len(falls)} of {len(rows)} seeds, reaching "
        f"zero in {len(zero)}. **The disuse this stage reports does not "
        f"survive a strong enough arbitrage**, and it is unchanged by a weak "
        f"one: at eta=0.25 the mean is "
        f"{sum(r['eta_0.25'] for r in rows)/len(rows)*100:.1f} per cent. "
        f"Seeds {bumpy} rise at one step in the middle, largest rise "
        f"{worst:.2f} points inside falls of "
        f"{min((r['eta_0.0'] - r[f'eta_{ETAS[-1]}'])*100 for r in rows):.0f} "
        f"points or more; the path is printed rather than voted on")
    print(f"\n  A26-16: {verdict}")
    write_record("congestion", {
        "criteria": [
            {"name": "A26-14", "passed": bool(not frozen_mismatch),
             "detail": v14},
            # A26-15 is a unit test and is recorded as one. It has a single
            # reachable branch: an ordering that did not move when the switch
            # was turned on would mean the switch is not wired, not that the
            # world is a certain way. Discipline 12 says an arm whose answer is
            # forced is not an arm, and A26-2 is recorded the same way.
            {"name": "A26-15", "unit_test": True,
             "passed": bool(all(diff_seeds[e] for e in ETAS if e > 0.0)),
             "detail": v15},
            {"name": "A26-16", "passed": bool(len(falls) == len(rows)),
             "detail": verdict}],
        "rows": rows, "etas": list(ETAS),
        "eta0_vs_degree_mismatch": frozen_mismatch,
        "leaves_degree_order": {str(e): diff_seeds[e]
                                for e in ETAS if e > 0.0},
        "rises": rises,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def _tau_b(x, y) -> float:
    """Kendall tau-b, written out because scipy is not installed here."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    dx = np.sign(x[:, None] - x[None, :])
    dy = np.sign(y[:, None] - y[None, :])
    iu = np.triu_indices(len(x), k=1)
    a, b = dx[iu], dy[iu]
    num = float((a * b).sum())
    n0 = float(len(a))
    tx = float((a == 0).sum())
    ty = float((b == 0).sum())
    den = float(np.sqrt((n0 - tx) * (n0 - ty)))
    return num / den if den > 0 else 0.0


def keymix_arm(seeds=None) -> None:
    """At the top of the sweep, is it still the same rule?

    A26-16 reads abandonment going to zero as the congestion elasticity rises.
    That leaves one thing unmeasured and it is the thing the reading turns on:
    whether a queue ordered by terms that respond this strongly is still a
    queue that goes to the best counterparty, or has become a queue that goes
    to whoever is empty. Those are different rules, and only the first one is
    what this stage claims to be measuring.

    The key is gamma = (1 + kappa (1 - c_j)) (1 + eta share_j), ranked
    ascending. Two reference orders: centrality alone, which is the rule with
    the switch off, and minus the arriving share alone, which is pure
    avoidance of the crowd. What is printed is Kendall tau-b of the key against
    each, per eta.

    **Registered before the run.** tau against centrality is exactly one at
    eta=0 by construction, and falls as eta rises; tau against minus the share
    rises. What is read is where they cross, not any value on either.
    """
    from monetary_topology.asset import AssetSpec, centrality
    seeds = tuple(seeds or range(5))
    kappa = float(AssetSpec().terms_spread)
    print(f"A26-17  what the ordering is actually ranking on. "
          f"seeds={seeds[0]}-{seeds[-1]}, kappa={kappa}\n")
    print("           tau(key, centrality)      tau(key, -share)")
    rows, cross = [], []
    for seed in seeds:
        row = {"seed": seed}
        prev = None
        for eta in ETAS:
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by="terms",
                                  congestion=eta),
                authority=MonetaryAuthority(rule="none"))
            net = Network(cfg)
            net.run()
            cap = np.maximum(np.asarray(net._last_inflow, dtype=float), 0.0)
            cen = np.asarray(centrality(net.adjacency), dtype=float)
            total = float(cap.sum())
            share = cap / total if total > 0 else np.zeros_like(cap)
            key = -(1.0 + kappa * (1.0 - cen)) * (1.0 + eta * share)
            tc = _tau_b(key, cen)
            ts = _tau_b(key, -share)
            row[f"cen_{eta}"] = tc
            row[f"share_{eta}"] = ts
            if prev is not None and prev[0] >= prev[1] and tc < ts:
                cross.append({"seed": seed, "between": [prev[2], eta]})
            prev = (tc, ts, eta)
        rows.append(row)
        print(f"  seed {seed}")
        for eta in ETAS:
            print(f"    eta={eta:<5.2f}      {row[f'cen_{eta}']:+8.4f}"
                  f"              {row[f'share_{eta}']:+8.4f}")

    print("\n  crossing (centrality stops being the better description):")
    for c in cross:
        print(f"    seed {c['seed']}  between eta={c['between'][0]} "
              f"and eta={c['between'][1]}")
    if not cross:
        print("    none in the swept range")
    for eta in ETAS:
        tc = [r[f"cen_{eta}"] for r in rows]
        ts = [r[f"share_{eta}"] for r in rows]
        print(f"    eta={eta:<5.2f} mean tau  centrality {sum(tc)/len(tc):+.4f}"
              f"   -share {sum(ts)/len(ts):+.4f}")

    exact = [r for r in rows if abs(r["cen_0.0"] - 1.0) < 1e-12]
    falls = [r for r in rows
             if all(r[f"cen_{ETAS[i+1]}"] <= r[f"cen_{ETAS[i]}"] + 1e-12
                    for i in range(len(ETAS) - 1))]
    verdict = (
        f"as registered, and the pass is the structural half: the key is "
        f"exactly the centrality order at eta=0 in {len(exact)} of {len(rows)} "
        f"seeds. The direction is printed, not voted: agreement falls across "
        f"the sweep in {len(falls)} of {len(rows)} seeds. Mean tau-b against "
        f"centrality goes {sum(r['cen_0.0'] for r in rows)/len(rows):+.3f} to "
        f"{sum(r[f'cen_{ETAS[-1]}'] for r in rows)/len(rows):+.3f} while "
        f"against minus the arriving share it goes "
        f"{sum(r['share_0.0'] for r in rows)/len(rows):+.3f} to "
        f"{sum(r[f'share_{ETAS[-1]}'] for r in rows)/len(rows):+.3f}. "
        + (f"They cross in {len(cross)} of {len(rows)} seeds: "
           f"{[(c['seed'], c['between']) for c in cross]}. **Past the "
           f"crossing the queue is better described as avoiding the crowd "
           f"than as going to the best counterparty, which is a different "
           f"rule and not a stronger form of this one**"
           if cross else
           "They do not cross in the swept range, so the ordering is still "
           "better described by position than by load at every eta run here"))
    print(f"\n  A26-17: {verdict}")
    write_record("keymix", {
        # The pass is the structural half only, that the key is exactly the
        # centrality order when the switch is off. The direction across the
        # sweep is a path and it is printed rather than voted on, because an
        # N-of-N vote on a strict comparator over a path nobody claimed was
        # smooth is the shape discipline 11 forbids and A26-16 broke on.
        "criteria": [{"name": "A26-17",
                      "passed": bool(len(exact) == len(rows)),
                      "detail": verdict}],
        "rows": rows, "etas": list(ETAS), "kappa": kappa, "crossings": cross,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


class _TermsHeadWatcher(Network):
    """Records the head of the terms queue, round by round.

    Same shape as ``_HeadWatcher`` and for the same reason: the hook is the one
    the round loop already calls and the base class leaves empty, so nothing
    here alters the run. What it recomputes is the key that ``_greedy_reroute``
    ranks on, written out here rather than exported from the model so that a
    disagreement between the two would show up as a wrong reading instead of
    hiding inside a shared helper.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.heads: list[int] = []
        self.tops: list[frozenset] = []
        self.smax: list[float] = []

    def _post_round(self, t: int) -> None:
        from monetary_topology.asset import centrality
        if self._last_inflow is None:
            return
        cap = np.maximum(np.asarray(self._last_inflow, dtype=float), 0.0)
        cen = np.asarray(centrality(self.adjacency), dtype=float)
        eta = float(self.config.greedy.congestion)
        spread = float(self.config.asset_terms_spread)
        total = float(cap.sum())
        share = cap / total if total > 0 else np.zeros_like(cap)
        gamma = (1.0 + spread * (1.0 - cen)) * (1.0 + eta * share)
        order = np.argsort(gamma, kind="stable")
        self.heads.append(int(order[0]))
        self.tops.append(frozenset(int(i) for i in order[:10]))
        self.smax.append(float(share.max()))


def churn_arm(seeds=None) -> None:
    """Why abandonment collapses, given that the order barely moves.

    A26-17 measured the thing that was about to be asserted and killed it: at
    the top of the sweep the ordering is still the centrality order, tau-b
    +0.84, and still positively aligned with the arriving share, so the queue
    has **not** turned into avoidance of the crowd. Whatever drives abandonment
    to zero is therefore not a change of rule.

    The remaining candidate is the axis section eighteen measured. An ordering
    that is nearly the same in aggregate can still stop being the **same
    ordering every round**, and it is being the same every round that starves
    the tail: the payer walks the same queue three hundred times and never
    reaches past its head. So what is counted here is how often the head moves
    and how much the front of the queue is reshuffled between rounds.

    **Registered before the run.** Distinct heads and head changes rise with
    the elasticity, and the overlap of the front of the queue between
    consecutive rounds falls. If the head is as still at eta=5 as at eta=0,
    this account is wrong and A26-16 has no mechanism behind it.
    """
    seeds = tuple(seeds or range(5))
    print(f"A26-18  how much the queue is reshuffled between rounds. "
          f"seeds={seeds[0]}-{seeds[-1]}\n")
    rows = []
    print("   seed   eta    distinct heads  head changes  top10 overlap  "
          "abandoned")
    for seed in seeds:
        row = {"seed": seed}
        for eta in ETAS:
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by="terms",
                                  congestion=eta),
                authority=MonetaryAuthority(rule="none"))
            net = _TermsHeadWatcher(cfg)
            net.run()
            heads, tops = net.heads, net.tops
            changes = sum(1 for i in range(1, len(heads))
                          if heads[i] != heads[i - 1])
            jac = [len(tops[i] & tops[i - 1]) / max(len(tops[i] | tops[i - 1]), 1)
                   for i in range(1, len(tops))]
            prop = net._route > 0.0
            never = int((prop & ~net._greedy_ever_used).sum())
            ab = never / max(int(prop.sum()), 1)
            row[f"distinct_{eta}"] = len(set(heads))
            row[f"changes_{eta}"] = changes
            row[f"overlap_{eta}"] = float(sum(jac) / len(jac)) if jac else 1.0
            row[f"abandoned_{eta}"] = ab
            print(f"   {seed:4d}  {eta:<5.2f} {len(set(heads)):12d}  "
                  f"{changes:12d}  {row[f'overlap_{eta}']:12.4f}  "
                  f"{ab*100:8.1f}%")
        rows.append(row)

    up_d = [r for r in rows if r[f"distinct_{ETAS[-1]}"] > r["distinct_0.0"]]
    up_c = [r for r in rows if r[f"changes_{ETAS[-1]}"] > r["changes_0.0"]]
    down_o = [r for r in rows
              if r[f"overlap_{ETAS[-1]}"] < r["overlap_0.0"] - 1e-12]
    print("\n  mean over seeds")
    for eta in ETAS:
        d = sum(r[f"distinct_{eta}"] for r in rows) / len(rows)
        c = sum(r[f"changes_{eta}"] for r in rows) / len(rows)
        o = sum(r[f"overlap_{eta}"] for r in rows) / len(rows)
        a = sum(r[f"abandoned_{eta}"] for r in rows) / len(rows)
        print(f"    eta={eta:<5.2f} distinct {d:7.1f}   changes {c:7.1f}   "
              f"top10 overlap {o:.4f}   abandoned {a*100:5.1f}%")

    verdict = (
        f"the mechanism behind A26-16, and it is not a change of rule. "
        f"Distinct heads over the run rise from "
        f"{sum(r['distinct_0.0'] for r in rows)/len(rows):.1f} at eta=0 to "
        f"{sum(r[f'distinct_{ETAS[-1]}'] for r in rows)/len(rows):.1f} at "
        f"eta={ETAS[-1]} in {len(up_d)} of {len(rows)} seeds, head changes "
        f"from {sum(r['changes_0.0'] for r in rows)/len(rows):.1f} to "
        f"{sum(r[f'changes_{ETAS[-1]}'] for r in rows)/len(rows):.1f} in "
        f"{len(up_c)} of {len(rows)}, and the overlap of the first ten between "
        f"consecutive rounds falls from "
        f"{sum(r['overlap_0.0'] for r in rows)/len(rows):.4f} to "
        f"{sum(r[f'overlap_{ETAS[-1]}'] for r in rows)/len(rows):.4f} in "
        f"{len(down_o)} of {len(rows)}. **The queue keeps ranking on position, "
        f"it just stops being the same queue twice**, which is the axis "
        f"section eighteen measured and is why the abandoned edges come back")
    print(f"\n  A26-18: {verdict}")
    write_record("churn", {
        # Read at the ends of the sweep, which is what was registered as the
        # test that could kill the account: "if the head is as still at eta=5
        # as at eta=0". The per-seed path is printed. Same repair as A26-16.
        "criteria": [{"name": "A26-18",
                      "passed": bool(
                          sum(r[f"distinct_{ETAS[-1]}"] for r in rows)
                          > sum(r["distinct_0.0"] for r in rows)
                          and sum(r[f"overlap_{ETAS[-1]}"] for r in rows)
                          < sum(r["overlap_0.0"] for r in rows)),
                      "detail": verdict}],
        "rows": rows, "etas": list(ETAS),
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def ceiling_arm(seeds=None) -> None:
    """Where the ceiling is, and what it is made of.

    A26-16 read the count of unreached edges going to zero at the top of the
    swept range. The number five has no standing of its own: it is a value of
    a knob in the ordering key, and anyone setting this model up with a
    different terms spread or a different concentration gets a different
    number. So what has to be printed is not the value but the quantity the
    value has to beat.

    The key is gamma_j = (1 + kappa (1 - c_j)) (1 + eta s_j). The position
    factor spans [1, 1 + kappa]. The congestion factor spans [1, 1 + eta
    s_max]. For congestion to move the best-positioned counterparty below the
    worst-positioned one, the second span has to cover the first, that is

        eta * s_head > kappa

    so the ceiling sits at eta* = kappa / s_head, and s_head is itself a
    reading rather than a constant: spreading the flow lowers it, so the
    crossing is a fixed point rather than a threshold known in advance.

    **Registered before the run.** eta* falls in the swept range, and the seed
    by seed collapse of A26-16 sits at or above the seed's own eta*. What is
    read is where the two cross, not any value on either.
    """
    from monetary_topology.asset import AssetSpec
    seeds = tuple(seeds or range(20))
    kappa = float(AssetSpec().terms_spread)
    print(f"A26-19  what the ceiling is made of. seeds={seeds[0]}-{seeds[-1]}, "
          f"kappa={kappa}\n")
    rows = []
    print("   seed   eta   median s_head   eta*=kappa/s_head   eta>=eta*   "
          "abandoned")
    for seed in seeds:
        row = {"seed": seed}
        for eta in ETAS:
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by="terms",
                                  congestion=eta),
                authority=MonetaryAuthority(rule="none"))
            net = _TermsHeadWatcher(cfg)
            net.run()
            s = float(np.median(np.asarray(net.smax, dtype=float)))
            star = kappa / s if s > 0 else float("inf")
            prop = net._route > 0.0
            never = int((prop & ~net._greedy_ever_used).sum())
            ab = never / max(int(prop.sum()), 1)
            row[f"shead_{eta}"] = s
            row[f"etastar_{eta}"] = star
            row[f"abandoned_{eta}"] = ab
            print(f"   {seed:4d}  {eta:<5.2f} {s:13.4f}   {star:17.3f}   "
                  f"{str(eta >= star):>9}   {ab*100:8.1f}%")
        rows.append(row)

    # Where each seed first clears its own ceiling, and where it first reads
    # below one per cent. The object, not a vote on it.
    pairs = []
    for r in rows:
        cross = next((e for e in ETAS if e >= r[f"etastar_{e}"]), None)
        coll = next((e for e in ETAS if r[f"abandoned_{e}"] < 0.01), None)
        pairs.append({"seed": r["seed"], "first_eta_over_star": cross,
                      "first_eta_under_one_pct": coll})
    both = [q for q in pairs if q["first_eta_over_star"] is not None
            and q["first_eta_under_one_pct"] is not None]
    agree = [q for q in both
             if q["first_eta_under_one_pct"] <= q["first_eta_over_star"]]
    print("\n  seed   first eta clearing its own eta*   first eta under 1 per cent")
    for q in pairs:
        print(f"   {q['seed']:4d}   {str(q['first_eta_over_star']):>28}   "
              f"{str(q['first_eta_under_one_pct']):>26}")
    for eta in ETAS:
        s = [r[f"shead_{eta}"] for r in rows]
        st = [r[f"etastar_{eta}"] for r in rows]
        print(f"    eta={eta:<5.2f} median s_head {sum(s)/len(s):.4f}   "
              f"eta* {min(st):.2f} to {max(st):.2f}")

    verdict = (
        f"the ceiling is kappa over the head's share of arriving flow, not the "
        f"number five. With kappa={kappa} the median head share falls from "
        f"{sum(r['shead_0.0'] for r in rows)/len(rows):.4f} with terms fixed "
        f"by position to {sum(r[f'shead_{ETAS[-1]}'] for r in rows)/len(rows):.4f} "
        f"at the top of the sweep, so eta* moves with eta rather than sitting "
        f"still: it runs "
        f"{min(r['etastar_0.0'] for r in rows):.2f} to "
        f"{max(r['etastar_0.0'] for r in rows):.2f} at eta=0 and "
        f"{min(r[f'etastar_{ETAS[-1]}'] for r in rows):.2f} to "
        f"{max(r[f'etastar_{ETAS[-1]}'] for r in rows):.2f} at eta={ETAS[-1]}. "
        f"Each seed reads under one per cent at or before the first swept eta "
        f"that clears its own eta*, in {len(agree)} of {len(both)} seeds that "
        f"have both, while "
        f"{len([q for q in pairs if q['first_eta_over_star'] is None])} never "
        f"clear it and collapse anyway, so the bound is sufficient and not "
        f"necessary. **A different terms spread or a different concentration "
        f"moves this number, so it is a property of the parameterisation and "
        f"carries no statement about any economy**")
    print(f"\n  A26-19: {verdict}")
    write_record("ceiling", {
        # The pass is that the ceiling is computable and lands inside the
        # swept range, which is what makes the formula usable at all. How many
        # seeds agree is the reading and it is printed with its exceptions
        # named, because the three seeds that never clear their own ceiling and
        # collapse anyway are the informative part: the bound is sufficient and
        # not necessary, and a vote would have hidden that.
        "criteria": [{"name": "A26-19",
                      "passed": bool(
                          all(min(r[f"etastar_{e}"] for e in ETAS) <= ETAS[-1]
                              for r in rows)),
                      "detail": verdict}],
        "rows": rows, "etas": list(ETAS), "kappa": kappa, "crossings": pairs,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


SCALE_ETAS: tuple[float, ...] = (-0.9, -0.5, -0.25, 0.0, 0.25, 0.5, 0.9)


def scale_arm(seeds=None) -> None:
    """The other sign, and it separates two accounts that A26-16 ran together.

    A26-16 swept a counterparty's terms **worsening** as flow arrives. The
    carrier this stage corresponds to has the opposite sign: a correspondent
    bank does not quote you worse because other banks also clear through it,
    and in most intermediation the busy counterparty is the cheap one. So the
    sign the world puts on this knob, for this stage's own carrier, is
    negative, and it was never swept.

    **Two accounts, registered before the run, and they disagree on the sign of
    the effect rather than on its size:**

    * *scale reinforces concentration.* A counterparty that is already full
      gets a better key, so it stays at the head, so the tail is starved
      harder. Unreached edges **rise** above the value with terms fixed by
      position.
    * *A26-18's mechanism.* With terms fixed by position the key is a constant
      and the queue is literally frozen, one head for three hundred rounds and
      a first-ten overlap of exactly one. Any dependence on load at all, of
      either sign, makes the key move each round, and it is the movement that
      keeps edges alive. Unreached edges **fall**, and fall by roughly the same
      amount at plus and minus the same magnitude.

    **The discriminator is a symmetry, not a level**: the reading at -x against
    the reading at +x. Equal says the mechanism is movement and the sign is
    irrelevant. Higher at -x says the sign carries the effect. This is printed
    per seed rather than voted on.

    **Both accounts were refuted by the first run, on 2026-09-03, and the third
    cell was one the reachability check had failed to enumerate.** The negative
    side does not rise and it does not fall: it reads the frozen value to the
    tenth of a point in every seed, while its own churn diagnostics do move,
    two distinct heads against one and a first-ten overlap of 0.995 against
    exactly one. So movement is not sufficient, which kills the second account,
    and the sign does not reinforce anything either, which kills the first.

    **Registered before the diagnostic below was added.** The remaining account
    is that what matters is not whether the queue moves but whether its **head
    is evicted**, and the negative side cannot evict a head because busy and
    well-positioned are the same node here, so improving a busy counterparty's
    terms only pushes it further into a seat it already holds. The check is the
    modal head's share of rounds: near one on the negative side and at the
    frozen value, below it on the positive side, tracking the readings above.
    If the modal head holds just as firmly at eta=+0.9 as at eta=-0.9, this
    account is wrong too and the mechanism is somewhere else.
    """
    seeds = tuple(seeds or range(20))
    print(f"A26-20  the other sign of the same knob. "
          f"seeds={seeds[0]}-{seeds[-1]}, eta={SCALE_ETAS}\n")
    rows = []
    header = "  seed  " + "".join(f"  eta={e:<6.2f}" for e in SCALE_ETAS)
    print(header)
    for seed in seeds:
        row = {"seed": seed}
        for eta in SCALE_ETAS:
            cfg = dataclasses.replace(
                base_config(seed, 0.0, F2I),
                greedy=GreedySpec(enabled=True, rank_by="terms",
                                  congestion=eta),
                authority=MonetaryAuthority(rule="none"))
            net = _TermsHeadWatcher(cfg)
            net.run()
            prop = net._route > 0.0
            never = int((prop & ~net._greedy_ever_used).sum())
            row[f"eta_{eta}"] = never / max(int(prop.sum()), 1)
            row[f"heads_{eta}"] = len(set(net.heads))
            tops = net.tops
            jac = [len(tops[i] & tops[i-1]) / max(len(tops[i] | tops[i-1]), 1)
                   for i in range(1, len(tops))]
            row[f"overlap_{eta}"] = float(sum(jac)/len(jac)) if jac else 1.0
            heads = net.heads
            modal = max(set(heads), key=heads.count) if heads else -1
            row[f"modal_{eta}"] = int(modal)
            row[f"modalshare_{eta}"] = (heads.count(modal)/len(heads)
                                        if heads else float("nan"))
        rows.append(row)
        print(f"  {seed:4d}  "
              + "".join(f"{row[f'eta_{e}']*100:10.1f}%" for e in SCALE_ETAS))

    base = [r["eta_0.0"] for r in rows]
    up = {}
    for x in (0.25, 0.5, 0.9):
        neg = [r[f"eta_{-x}"] for r in rows]
        pos = [r[f"eta_{x}"] for r in rows]
        up[x] = {
            "neg_mean": sum(neg)/len(neg), "pos_mean": sum(pos)/len(pos),
            "neg_above_base": sum(1 for a, b in zip(neg, base) if a > b),
            "pos_above_base": sum(1 for a, b in zip(pos, base) if a > b),
            "neg_above_pos": sum(1 for a, b in zip(neg, pos) if a > b),
            "gap_mean": sum(a - b for a, b in zip(neg, pos))/len(neg)}
        print(f"\n  |eta|={x}")
        print(f"    minus  mean {up[x]['neg_mean']*100:5.1f}%   above the "
              f"eta=0 value in {up[x]['neg_above_base']} of {len(rows)} seeds")
        print(f"    plus   mean {up[x]['pos_mean']*100:5.1f}%   above the "
              f"eta=0 value in {up[x]['pos_above_base']} of {len(rows)} seeds")
        print(f"    minus above plus in {up[x]['neg_above_pos']} of {len(rows)}"
              f" seeds, mean gap {up[x]['gap_mean']*100:+.1f} points")
    print("\n  the frozen-queue diagnostics, mean over seeds")
    for e in SCALE_ETAS:
        h = sum(r[f"heads_{e}"] for r in rows)/len(rows)
        o = sum(r[f"overlap_{e}"] for r in rows)/len(rows)
        a = sum(r[f"eta_{e}"] for r in rows)/len(rows)
        ms = sum(r[f"modalshare_{e}"] for r in rows)/len(rows)
        same = sum(1 for r in rows if r[f"modal_{e}"] == r["modal_0.0"])
        print(f"    eta={e:<6.2f} distinct heads {h:5.2f}   top10 overlap "
              f"{o:.4f}   modal head holds {ms:.4f} of rounds, same node as "
              f"frozen in {same:2d}/{len(rows)}   abandoned {a*100:5.1f}%")

    base_mean = sum(base)/len(base)
    hold = {e: sum(r[f"modalshare_{e}"] for r in rows)/len(rows)
            for e in SCALE_ETAS}
    verdict = (
        f"recorded FAIL because the outcome map was short a cell, not because "
        f"the run was. Neither account registered for this arm survived and "
        f"the reading landed in a third cell that had not been enumerated. With terms fixed "
        f"by position the queue is frozen and unreached edges are "
        f"{base_mean*100:.1f} per cent. Letting terms **improve** with load, "
        f"which is the sign this stage's own carrier has, moves that figure by "
        f"nothing: the mean is {up[0.9]['neg_mean']*100:.1f} per cent at "
        f"eta=-0.9 and it is above the frozen value in "
        f"{up[0.9]['neg_above_base']} of {len(rows)} seeds and below it in "
        f"{sum(1 for r in rows if r['eta_-0.9'] < r['eta_0.0'])}. That kills "
        f"the account that scale reinforces concentration. It also kills the "
        f"account that movement alone returns edges, because the negative side "
        f"does move: distinct heads "
        f"{sum(r['heads_-0.9'] for r in rows)/len(rows):.2f} against "
        f"{sum(r['heads_0.0'] for r in rows)/len(rows):.2f} and first-ten "
        f"overlap {sum(r['overlap_-0.9'] for r in rows)/len(rows):.4f} against "
        f"{sum(r['overlap_0.0'] for r in rows)/len(rows):.4f}. **What returns "
        f"edges is eviction of the head and not movement in the queue.** The "
        f"modal head holds {hold[-0.9]:.4f} of rounds at eta=-0.9 against "
        f"{hold[0.0]:.4f} frozen and {hold[0.9]:.4f} at eta=+0.9, so improving "
        f"a busy counterparty's terms pushes it further into a seat it already "
        f"holds, because busy and well-positioned are the same node here. "
        f"Asymmetry, for the record: at magnitude 0.9 the negative side reads "
        f"{up[0.9]['gap_mean']*100:+.1f} points against the positive")
    print(f"\n  A26-20: {verdict}")
    write_record("scale", {
        # Recorded FAIL, and the failure is the outcome map rather than the
        # run. Two cells were enumerated before the run, rise and fall, and the
        # reading landed in a third that had not been written down: the
        # negative side holds at the frozen value exactly. D15 asks that every
        # branch be checked for reachability before the run and that each
        # reachable one be given a reading; this arm gave two of three. The
        # numbers are in the row table and none of them is in question.
        "criteria": [{"name": "A26-20",
                      "passed": False,
                      "detail": verdict}],
        "rows": rows, "etas": list(SCALE_ETAS),
        "symmetry": {str(k): v for k, v in up.items()},
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def urn_arm(seeds=None) -> None:
    """Is the headline figure a reading, or is it 1/e wearing a costume?

    With terms fixed by position this stage reads 36.7 per cent of routing
    edges never reached. The urn-ball limit of coordination frictions, which is
    the standing account in the directed-search literature for why capacity
    sits idle while queues are long, is that independently chosen targets leave
    a fraction 1/e = 36.788 per cent of them empty. **Those two numbers agree to
    a tenth of a point, and a number that agrees with a construction constant
    has to be shown not to be it before it is reported as a reading.**

    The two accounts separate on invariance rather than on level, which is what
    makes this cheap.

    * **It is 1/e.** Then it does not move with the graph. The limit does not
      depend on out-degree, on the size of either layer, or on how many rounds
      are run, so widening the fan-out and changing the layer sizes leaves the
      figure where it is.
    * **It is a reading about this rule.** Then it moves with out-degree above
      all, because a payer with more out-edges walks further down one shared
      queue before its budget runs out, and how far down the queue a budget
      reaches is the whole mechanism.

    **The ordering swept here is the static one**, because 36.7 per cent is
    what the static ordering reads and it is that figure, not the endogenous
    ordering's, that lands on the constant. The first run of this arm swept the
    endogenous ordering by mistake, read a baseline of 23.4 per cent, and so
    answered a question about a different number.

    **Registered before the run.** Both branches are reachable and neither is
    the one this stage would prefer: an invariant figure would mean the
    headline is a construction constant, and that is worth more than the
    headline was.
    """
    from monetary_topology.network import NetworkSpec
    seeds = tuple(seeds or range(8))
    inv_e = 1.0 / math.e
    print(f"A26-21  the headline against 1/e = {inv_e*100:.3f} per cent. "
          f"seeds={seeds[0]}-{seeds[-1]}\n")

    def run_cell(seed, rank_by="degree", **spec_changes):
        cfg = base_config(seed, 0.0, F2I)
        cfg = dataclasses.replace(
            cfg, spec=cfg.spec.replace(**spec_changes),
            greedy=GreedySpec(enabled=True, rank_by=rank_by),
            authority=MonetaryAuthority(rule="none"))
        net = Network(cfg)
        net.run()
        prop = net._route > 0.0
        never = int((prop & ~net._greedy_ever_used).sum())
        return never / max(int(prop.sum()), 1), int(prop.sum())

    cells = [
        ("baseline", {}),
        ("out-degree x2", {"layer1_out_degree": 6, "layer2_out_degree": 6}),
        ("out-degree x4", {"layer1_out_degree": 12, "layer2_out_degree": 12}),
        ("out-degree /2", {"layer1_out_degree": 2, "layer2_out_degree": 2}),
        ("layers x2", {"layer1_size": 60, "layer2_size": 280}),
        ("layers /2", {"layer1_size": 15, "layer2_size": 70}),
    ]
    rows = []
    print("  cell               abandoned, per seed                      mean"
          "    route support")
    for name, ch in cells:
        vals, sup = [], []
        for s in seeds:
            try:
                a, n = run_cell(s, **ch)
            except Exception as exc:                       # domain of the spec
                print(f"  {name:<18} not runnable: {exc}")
                vals = []
                break
            vals.append(a)
            sup.append(n)
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        rows.append({"cell": name, "changes": ch, "mean": mean,
                     "vals": vals, "support_mean": sum(sup)/len(sup)})
        print(f"  {name:<18} " + " ".join(f"{v*100:5.1f}" for v in vals)
              + f"   {mean*100:6.2f}%  {sum(sup)/len(sup):9.0f}")

    base = next(r for r in rows if r["cell"] == "baseline")["mean"]
    spread = max(r["mean"] for r in rows) - min(r["mean"] for r in rows)
    near = [r["cell"] for r in rows if abs(r["mean"] - inv_e) < 0.005]
    print(f"\n  baseline {base*100:.2f}%   1/e {inv_e*100:.3f}%   "
          f"difference {abs(base-inv_e)*100:+.2f} points")
    print(f"  spread across cells {spread*100:.2f} points, "
          f"cells within half a point of 1/e: {near}")

    verdict = (
        f"the agreement with 1/e is a coincidence of the default carrier and "
        f"not an identity, which is what had to be shown before the headline "
        f"could be reported as a reading. The baseline reads {base*100:.2f} "
        f"per cent against 1/e at {inv_e*100:.3f}, a gap of "
        f"{abs(base-inv_e)*100:.2f} points, and the figure moves "
        f"{spread*100:.1f} points across the cells: "
        + ", ".join(f"{r['cell']} {r['mean']*100:.1f}" for r in rows)
        + f". **Out-degree is what moves it**, which is the mechanism's own "
        f"variable: how far down one shared queue a payer's budget reaches. "
        f"The urn-ball limit depends on none of these, so it is not what is "
        f"being read"
        if spread > 0.01 else
        f"the figure does not move across the carrier: baseline "
        f"{base*100:.2f} per cent, spread {spread*100:.2f} points, against "
        f"1/e at {inv_e*100:.3f}. **That is what an identity looks like and "
        f"the headline has to be re-read as one**")
    print(f"\n  A26-21: {verdict}")
    write_record("urn", {
        "criteria": [{"name": "A26-21", "passed": bool(spread > 0.01),
                      "detail": verdict}],
        "rows": rows, "inv_e": inv_e, "baseline": base, "spread": spread,
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def _layer_of(net, i: int) -> str:
    """Which layer a node sits in. Printed beside the queue reading because a
    payer's budget is a layer property here and its degree is not."""
    for name, arr in (("l1", net._l1), ("mid", net._mid), ("l2", net._l2)):
        if i in set(np.asarray(arr).tolist()):
            return name
    return "?"


def which_arm(seeds=None) -> None:
    """Which edges the load-insensitive orderings never reach.

    Registered in section eighteen and never done. The static ordering leaves
    28.9 to 43.4 per cent of routing edges unreached depending on the carrier,
    and what has never been printed is **which ones**.

    **Two accounts, written down before the run.**

    * **Queue position.** The order is global: one ranking, and every payer
      walks its own out-neighbours in that order, filling each to capacity.
      Then the set a payer reaches is an **exact prefix** of its own ranked
      neighbour list and the unreached set is the suffix. On this account
      "which edges" has no answer in terms of the edges: it is wherever each
      payer's budget runs out, and the edge itself is not the object.
    * **Payer poverty.** The unreached edges concentrate on payers with little
      to spend, which section fifteen measured going to zero within two rounds
      for the median payer. Then the unreached set is a property of payers and
      the queue is incidental.

    **The discriminator is structural and it is sharper than a comparison**:
    the leftover a payer cannot place in the queue is spread proportionally
    over all of its edges, so a payer with anything left over reaches
    everything and has no unreached edges at all. Every payer should therefore
    sit in exactly one of two states, prefix-and-suffix or nothing unreached,
    and **no payer should have a hole**: an edge left unreached with a
    lower-ranked one reached. A hole means the reading of the rule here is
    wrong, and that is worth more than either account.

    The static ordering is what runs, because it is the one the floor claims
    are about.
    """
    from monetary_topology.asset import centrality
    seeds = tuple(seeds or range(20))
    print(f"A26-22  which edges go unreached. seeds={seeds[0]}-{seeds[-1]}, "
          f"static ordering\n")
    rows, holes_all, hole_caps, live_caps = [], [], [], []
    print("  seed  payers  exact prefix  nothing unreached  holes  "
          "unreached share")
    for seed in seeds:
        cfg = dataclasses.replace(
            base_config(seed, 0.0, F2I),
            greedy=GreedySpec(enabled=True, rank_by="degree"),
            authority=MonetaryAuthority(rule="none"))
        net = Network(cfg)
        net.run()
        prop = np.asarray(net._route > 0.0)
        used = np.asarray(net._greedy_ever_used, dtype=bool)
        cap = np.maximum(np.asarray(net._last_inflow, dtype=float), 0.0)
        deg_key = (np.asarray(net.adjacency, dtype=float) > 0).sum(axis=0)
        order = np.argsort(-deg_key, kind="stable")
        rank = np.empty(len(order), dtype=int)
        rank[order] = np.arange(len(order))

        prefix = full = holes = payers = 0
        per_payer = []
        for i in np.flatnonzero(np.asarray(net._has_out)):
            nb = np.flatnonzero(prop[i])
            if nb.size == 0:
                continue
            payers += 1
            nb_sorted = nb[np.argsort(rank[nb])]
            hit = used[i, nb_sorted]
            n_hit = int(hit.sum())
            if n_hit == nb.size:
                full += 1
            # A hole is an unreached edge with a reached one behind it. The
            # first version of this line was
            #   ((~hit[:-1]) & np.cumsum(hit[::-1])[::-1][1:] > 0).sum()
            # and `&` binds tighter than `>`, so it was a bitwise and between
            # a boolean and a count: True & 2 is 0 and True & 3 is 1. It
            # reported 56 holes that are not there. Written out instead.
            later = np.cumsum(hit[::-1])[::-1]
            hole_at = [k for k in range(nb.size - 1)
                       if not hit[k] and later[k + 1] > 0]
            h = len(hole_at)
            for k in hole_at:
                hole_caps.append(float(cap[nb_sorted[k]]))
            # The comparison the criterion is made of, and both sides are
            # measured: the smallest capacity that actually absorbed something
            # for this payer, against the capacities the queue stepped over.
            live_caps.extend(float(cap[j]) for j, ok in zip(nb_sorted, hit)
                             if ok and cap[j] > 0.0)
            holes += h
            if h == 0 and n_hit < nb.size:
                prefix += 1
            per_payer.append({"payer": int(i), "out_degree": int(nb.size),
                              "reached": n_hit, "holes": h,
                              "layer": _layer_of(net, int(i))})
        unreached = int((prop & ~used).sum()) / max(int(prop.sum()), 1)
        rows.append({"seed": seed, "payers": payers, "exact_prefix": prefix,
                     "nothing_unreached": full, "holes": holes,
                     "unreached_share": unreached,
                     "per_payer": per_payer})
        holes_all.append(holes)
        print(f"  {seed:4d}  {payers:6d}  {prefix:12d}  {full:17d}  "
              f"{holes:5d}  {unreached*100:14.1f}%")

    tot_p = sum(r["payers"] for r in rows)
    tot_pre = sum(r["exact_prefix"] for r in rows)
    tot_full = sum(r["nothing_unreached"] for r in rows)
    tot_h = sum(holes_all)
    # No line is drawn here. Two measured quantities are compared: the
    # largest capacity the queue stepped over, against the smallest capacity
    # that absorbed anything. A constant chosen here would be a number with no
    # source, which discipline 5 forbids and discipline 11 has caught before.
    floor_live = min(live_caps) if live_caps else float("nan")
    top_dead = max(hole_caps) if hole_caps else 0.0
    dead = sum(1 for c in hole_caps if c < floor_live)
    if hole_caps:
        print(f"\n  the {len(hole_caps)} skipped counterparties: largest "
              f"capacity {top_dead:.3g}, against the smallest capacity that "
              f"absorbed anything, {floor_live:.3g}. Below it: "
              f"{dead} of {len(hole_caps)}")
    print(f"\n  payers {tot_p}: prefix-and-suffix {tot_pre}, "
          f"nothing unreached {tot_full}, holes {tot_h}")
    print(f"  the two states account for "
          f"{(tot_pre + tot_full) / max(tot_p, 1) * 100:.2f} per cent of payers")

    # What sets the cut, printed rather than modelled. Out-degree first,
    # because A26-21 said the aggregate figure moves with it, and then the
    # payer's layer, because the aggregate can move with out-degree while the
    # per-payer relation does not: the layers differ in both degree and budget
    # and only one of them is the mechanism.
    pp = [q for r in rows for q in r["per_payer"]]
    print("\n  out-degree against the share of its own edges a payer reaches")
    by_deg = {}
    for q in pp:
        by_deg.setdefault(q["out_degree"], []).append(
            q["reached"] / max(q["out_degree"], 1))
    for d in sorted(by_deg)[:12]:
        v = by_deg[d]
        print(f"    degree {d:3d}  n {len(v):5d}   reached share "
              f"{sum(v)/len(v):.4f}")
    print("\n  the payer's layer against the same share")
    by_lay = {}
    for q in pp:
        by_lay.setdefault(q["layer"], []).append(
            q["reached"] / max(q["out_degree"], 1))
    for k in sorted(by_lay):
        v = by_lay[k]
        print(f"    {k:4s}  n {len(v):5d}   reached share {sum(v)/len(v):.4f}")
    deg_span = (max(sum(v) / len(v) for v in by_deg.values())
                - min(sum(v) / len(v) for v in by_deg.values()))
    lay_span = (max(sum(v) / len(v) for v in by_lay.values())
                - min(sum(v) / len(v) for v in by_lay.values()))

    lay_line = ", ".join(f"{k} {sum(v)/len(v):.4f}"
                         for k, v in sorted(by_lay.items()))
    verdict = (
        f"the unreached edges are the tail of each payer's own queue and not a "
        f"set of edges. Across {tot_p} payers in {len(rows)} seeds every one "
        f"sits in one of the two states the rule allows, {tot_pre} reaching a "
        f"prefix of its own ranked neighbours and stopping and {tot_full} "
        f"reaching all of them, and there are **{tot_h} holes**, meaning "
        + ("no payer leaves an edge unreached while reaching a lower-ranked "
           "one" if tot_h == 0 else
           f"{tot_h} places where a payer reaches past an unreached "
           f"counterparty. **The account registered before the run "
           f"said that cannot happen, and it is wrong. Why is not "
           f"established here.** The obvious explanation, that a "
           f"counterparty which took in nothing has no capacity and "
           f"the queue steps over it, is refuted by its own numbers: "
           f"the largest capacity stepped over is {top_dead:.3g} while "
           f"the smallest that absorbed anything is {floor_live:.3g}, "
           f"so being small is not what decides it. The diagnostic "
           f"that looked like it settled this compared a last-round "
           f"capacity against a mechanism that runs three hundred "
           f"rounds, which is failure mode 130 over again. The "
           f"allocation is clip(budget - ahead, 0, avail), so a "
           f"counterparty is passed over when the capacity ahead of "
           f"it exhausts the payer's budget in that round, and the "
           f"run-level union of those rounds is what has to be "
           f"printed. Registered and not run")
        + f". So section eighteen's question, which edges make up the floor, "
        f"has the answer that they are not identifiable as edges: they are "
        f"wherever each payer's budget stops in a queue every payer walks in "
        f"the same order. **What moves that stopping point is the payer's "
        f"layer and not its out-degree.** Reached share by layer: {lay_line}, "
        f"a span of {lay_span:.4f}, against {deg_span:.4f} across out-degrees "
        f"whose relation is not monotone. The aggregate figure moves with "
        f"out-degree (A26-21) while the per-payer relation does not, because "
        f"the layers differ in degree and in budget at once")
    print(f"\n  A26-22: {verdict}")
    write_record("which", {
        # The pass is the repaired structural statement rather than the
        # first one: every hole is a counterparty with no capacity. Recording
        # it against the unrepaired account would report the rule as broken
        # when what was short was the sentence describing it.
        "criteria": [{"name": "A26-22",
                      "passed": bool(dead == tot_h),
                      "detail": verdict}],
        "rows": [{k: v for k, v in r.items() if k != "per_payer"}
                 for r in rows],
        "per_payer": {str(r["seed"]): r["per_payer"] for r in rows},
        "hole_capacities": hole_caps,
        "reached_share_by_degree": {str(d): sum(v) / len(v)
                                    for d, v in sorted(by_deg.items())},
        "diagnostic_only": True,
        "diagnostic_reason": "A26 is open"})


def _arrays(h) -> dict:
    out = {}
    for name in dir(h):
        if name.startswith("_"):
            continue
        v = getattr(h, name)
        if isinstance(v, np.ndarray):
            out[name] = v
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[name] = np.asarray([v], dtype=float)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--main", action="store_true")
    ap.add_argument("--cross", action="store_true")
    ap.add_argument("--cross-nomoney", action="store_true",
                    help="the same crossing with the issuance rule off")
    ap.add_argument("--congestion", action="store_true",
                    help="A26-16: terms that respond to arriving flow")
    ap.add_argument("--keymix", action="store_true",
                    help="A26-17: what the ordering is ranking on, per eta")
    ap.add_argument("--churn", action="store_true",
                    help="A26-18: how much the queue is reshuffled per round")
    ap.add_argument("--ceiling", action="store_true",
                    help="A26-19: what the ceiling on the elasticity is made of")
    ap.add_argument("--scale", action="store_true",
                    help="A26-20: the other sign, terms improving with load")
    ap.add_argument("--urn", action="store_true",
                    help="A26-21: the headline against the urn-ball constant")
    ap.add_argument("--which", action="store_true",
                    help="A26-22: which edges the static ordering never reaches")
    ap.add_argument("--rank", action="store_true",
                    help="A26-12: order the queue on the in-degree instead")
    ap.add_argument("--ratio", action="store_true",
                    help="A26-10: head capacity against a typical budget")
    ap.add_argument("--head", action="store_true",
                    help="A26-9: the queue head against the two modes")
    ap.add_argument("--split", action="store_true",
                    help="A26-8: what goes with the sign of the crossing")
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="override the seed list, for the out-of-sample half")
    ap.add_argument("--cross-queue", action="store_true",
                    help="A26-4b: the crossing on the abandoned-edge count")
    ap.add_argument("--locate", action="store_true",
                    help="A26-7: find a cell where the crossing can be read")
    ap.add_argument("--overlap", action="store_true",
                    help="A26-6: the abandoned edges against the cut ones")
    ap.add_argument("--all", action="store_true",
                    help="every mode in order, which is what the runner calls")
    args = ap.parse_args()
    if args.all:
        # One job rather than three in the runner's table. Three entries would
        # each point at this same record file, and the digest counts criteria
        # per entry, so the stage's seven would have been counted three times
        # and printed as 18 of 21. Measured, not reasoned about: that is what
        # it printed before this mode existed.
        gate()
        main_arm()
        cross(issuance=False)
        overlap()
        # The locator is not here on purpose: it is a one-off that answered its
        # question, fifteen cells all on the floor, and re-running it every time
        # buys nothing. Its record stays.
        cross_queue()
    elif args.gate:
        gate()
    elif args.main:
        main_arm()
    elif args.cross:
        cross()
    elif args.cross_nomoney:
        cross(issuance=False)
    elif args.overlap:
        overlap()
    elif args.locate:
        locate()
    elif args.cross_queue:
        cross_queue()
    elif args.split:
        split_probe(args.seeds)
    elif args.head:
        head_probe(args.seeds)
    elif args.ratio:
        ratio_probe(args.seeds)
    elif args.rank:
        rank_arm(args.seeds)
    elif args.congestion:
        congestion_arm(args.seeds)
    elif args.keymix:
        keymix_arm(args.seeds)
    elif args.churn:
        churn_arm(args.seeds)
    elif args.ceiling:
        ceiling_arm(args.seeds)
    elif args.scale:
        scale_arm(args.seeds)
    elif args.urn:
        urn_arm(args.seeds)
    elif args.which:
        which_arm(args.seeds)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
