"""A19: industries as clusters of agents, and which layer of the mechanism
carries the aggregate.

Part one of the record: the reproduction gates and conservation. Every gate
here runs the code that existed *before* a switch was added, against the
current code with that switch at zero, and compares all 26 history fields bit
for bit. The old files are the ``.expired`` backups the project keeps, so the
check is run rather than argued (rule 19: the comparison is something you run,
not something you derive).

Writes ``results/a19_industry.json``. Exits non-zero if any criterion fails.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, fields
from importlib.machinery import SourceFileLoader
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import monetary_topology  # noqa: E402  (path set above)
from monetary_topology.industry import IndustrySpec  # noqa: E402
from monetary_topology.config import WageChannel  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
    run_network,
)

#: Claims are conserved exactly up to floating point. Same constant and meaning
#: as ``economy.py``'s ``SFC_TOLERANCE``.
SFC_TOLERANCE = 1e-9

#: Decimal places every reported float is rounded to before it is written, so
#: two BLAS builds cannot differ in the last digit and surface as a text diff.
DIGITS = 12

#: The backups this stage compares against, newest last. Each one is the file
#: as it stood immediately before the named switch was wired into the main
#: loop, so each pair below isolates exactly one switch.
BACKUPS = {
    "pre_industry": "network.py.expired_20260829_pre_产业层",
    "pre_switch": "network.py.expired_20260829_pre_转业",
    "pre_recovery": "network.py.expired_20260829_pre_恢复期",
    "pre_supply": "network.py.expired_20260829_pre_供给约束",
    "pre_spread": "network.py.expired_20260829_pre_异质摩擦",
    "pre_theta": "network.py.expired_20260829_pre_技术系数",
}

#: The carrier. A2's two-layer graph at its registered size; the defaults on
#: ``NetworkSpec`` already are 20 and 180, restated here so the record carries
#: the number rather than a default resolved at call time.
LAYER1_SIZE = 20
LAYER2_SIZE = 180
ROUNDS = 300

#: Seeds per arm. Rule 12's reference value. Held at five while the direction
#: is unanimous and the spread does not straddle zero; not raised to ten
#: without a reason that belongs to the arm.
SEEDS = (0, 1, 2, 3, 4)

#: The setting the direction readings run at. Subsistence on with a ten round
#: grace period, wage elasticity at 0.10, supply constraint binding fully.
#: ``e <= 0.2`` is the usable range: at 0.3 the production layer falls to 20
#: live nodes, which is the financial layer alone, and every arm reads the same.
LIVE = dict(elasticity=0.10, need=0.0914, grace=10, mode="exit")

#: The same carrier with neither the subsistence line nor the wage channel, so
#: a direction that survives both settings is not an artefact of either.
BARE = dict(elasticity=0.0, need=0.0, grace=1, mode="exit")

#: Where the recovery arm sits on the ``min_share`` sweep. Chosen from the
#: sweep printed below, on the far side of the cliff, so an unstable reading
#: there cannot be blamed on a treatment that moved nothing (D28).
MIN_SHARE = 1.1

#: The sweep itself. Cheap, and it is the evidence for the line above.
MIN_SHARE_SWEEP = (0.0, 0.5, 0.7, 0.9, 1.1, 1.3)

#: The industry structure used by every gate that has industries on. Twenty
#: industries, six of them financial, so the production layer holds fourteen.
ON = dict(
    count=20,
    financial_count=6,
    column_sum=0.50,
    weight_shape=2.0,
    seed=0,
)


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str


def load_backup(tag: str) -> object:
    """Load one ``.expired`` copy of ``network.py`` as a module.

    Two details are load bearing. The module name carries the package, so the
    relative imports inside the file resolve; and the loader is named
    explicitly, because ``spec_from_file_location`` picks its loader off the
    file extension and ``.py.expired_...`` is not one it knows.
    """
    path = SRC / "monetary_topology" / BACKUPS[tag]
    name = "monetary_topology._a19_" + tag
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    # Register before executing: ``dataclass`` looks the defining module up in
    # ``sys.modules`` while it processes annotations.
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


def run_with(mod, industry: dict | None, seed: int = 0):
    """One run on ``mod``'s own classes, so old and new code stay separable."""
    spec = mod.NetworkSpec(layer1_size=LAYER1_SIZE, layer2_size=LAYER2_SIZE, seed=seed)
    kw = dict(spec=spec, rounds=ROUNDS, seed=seed)
    if industry is not None:
        if not any(f.name == "industry" for f in fields(mod.NetworkConfig)):
            raise RuntimeError("this build has no industry field")
        kw["industry"] = mod.IndustrySpec(**industry)
    cfg = mod.NetworkConfig(**kw)
    return mod.run_network(cfg)


def compare(a, b) -> tuple[bool, list[str], int]:
    """Bit-for-bit over every field of ``NetworkHistory``.

    Field list comes from ``dataclasses.fields`` rather than being typed out,
    because a hand written field list is exactly the thing that silently drops
    a new field (rule 19's second half).
    """
    names = [f.name for f in fields(type(a))]
    differ = []
    for n in names:
        x, y = getattr(a, n), getattr(b, n)
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            same = np.array_equal(np.asarray(x), np.asarray(y))
        elif isinstance(x, dict):
            same = set(x) == set(y) and all(
                np.array_equal(np.asarray(x[k]), np.asarray(y[k])) for k in x
            )
        else:
            same = x == y
        if not same:
            differ.append(n)
    return (not differ), differ, len(names)


def conservation(h) -> float:
    """Residual of held claims against everything issued, over the whole run.

    The in-loop assertion spans the payroll and discretionary transfers only.
    This spans the run, so it also covers issuance and anything a post-round
    hook does.
    """
    held = h.holdings[-1].sum() + h.frozen_holdings[-1] + h.parked[-1]
    made = 100.0 + h.issuance.sum() - h.written_off.sum()
    return float(abs(held - made))


#: Every run this stage needs, keyed by what defines it. A run takes about
#: thirteen seconds here, the stage needs forty one of them, and the shell it
#: runs in is capped well below that, so the readings are built up across
#: calls. Rule 6's principle applied to compute rather than to downloads: a
#: number that will not change once computed gets written down.
CACHE = RESULTS / "a19_cache.json"


def cache_key(industry: dict, seed: int, env: dict) -> str:
    ind = IndustrySpec(**industry)
    parts = [f"{f.name}={getattr(ind, f.name)!r}" for f in fields(IndustrySpec)]
    parts += [f"env.{k}={env[k]!r}" for k in sorted(env)]
    parts += [f"seed={seed}", f"rounds={ROUNDS}",
              f"carrier={LAYER1_SIZE}x{LAYER2_SIZE}"]
    return "|".join(parts)


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(c: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")


#: Every key ``quantities`` returns. A cached entry missing one of these was
#: written by an older version of this file and is recomputed rather than
#: patched, so the cache can never hand back a half filled row.
REQUIRED = ("scar_depth", "wage_peak", "wage_trough", "wage_close",
            "active_nodes", "total_volume", "l2_support", "l2_inflow",
            "non_empty_industries", "non_empty_alive", "damaged_industries",
            "switches")


def measure(industry: dict, seed: int, env: dict, cache: dict) -> dict:
    k = cache_key(industry, seed, env)
    if k in cache and all(f in cache[k] for f in REQUIRED):
        return cache[k]
    h, m = run_full(industry, seed, env)
    q = {a: round(b, DIGITS) if isinstance(b, float) else b
         for a, b in quantities(h, m).items()}
    cache[k] = q
    save_cache(cache)
    return q


def run_full(industry: dict, seed: int, env: dict):
    """One run, returning the history and the model, so the diagnostics that
    live on the model (switch count, industry labels) are readable without
    adding a 27th field to ``NetworkHistory`` and breaking every gate above."""
    spec = NetworkSpec(layer1_size=LAYER1_SIZE, layer2_size=LAYER2_SIZE, seed=seed)
    cfg = NetworkConfig(
        spec=spec,
        rounds=ROUNDS,
        seed=seed,
        wages=WageChannel(elasticity=env["elasticity"]),
        subsistence=SubsistenceSpec(need=env["need"], grace=env["grace"],
                                    mode=env["mode"]),
        industry=IndustrySpec(**industry),
    )
    m = Network(cfg)
    return m.run(), m


def quantities(h, m) -> dict:
    """The five printed objects. No threshold is applied to any of them."""
    paid = np.asarray(h.wage_paid, dtype=float)
    peak = float(paid.max()) if paid.size else 0.0
    # Two readings of "how many industries are left", because they are not the
    # same object and one of them is degenerate here. ``_alive`` is the
    # subsistence exit flag: under the live setting the whole production layer
    # is out, so it reads 6 -- the financial layer -- for every arm and every
    # seed, and a quantity with one value cannot separate anything (rule 13,
    # step 1: measure the worst cell, not the average one). The active reading
    # uses the same cutoff ``active_nodes`` does, so it moves.
    g = getattr(m, "_industry_of", None)
    alive = getattr(m, "_alive", None)
    inflow = getattr(m, "_last_inflow", None)
    non_empty = non_empty_alive = 0
    if g is not None and np.size(g):
        g = np.asarray(g)
        if alive is not None:
            non_empty_alive = int(np.unique(g[np.asarray(alive) & (g >= 0)]).size)
        if inflow is not None:
            hot = np.asarray(inflow) > float(h.epsilon_absolute)
            non_empty = int(np.unique(g[hot & (g >= 0)]).size)
    return dict(
        scar_depth=float(paid[-1] / peak) if peak else float("nan"),
        wage_peak=peak,
        wage_trough=float(paid.min()) if paid.size else 0.0,
        wage_close=float(paid[-1]) if paid.size else 0.0,
        active_nodes=float(h.active_nodes[-1]),
        total_volume=float(np.asarray(h.total_volume, dtype=float).sum()),
        l2_support=float(h.effective_support_l2[-1]),
        l2_inflow=float(np.asarray(h.layer2_inflow, dtype=float)[-1]),
        non_empty_industries=non_empty,
        non_empty_alive=non_empty_alive,
        damaged_industries=int((np.asarray(getattr(m, "_damaged_for", []))
                                >= 0).sum()),
        switches=int(getattr(m, "_switch_count", 0)),
    )


#: The quantities A19-4 through A19-6 read a paired difference on. Order is
#: the order they are printed in and is fixed so two runs diff cleanly.
READ = ("scar_depth", "active_nodes", "total_volume", "l2_support", "l2_inflow")


def paired(name, treat: dict, control: dict, env: dict, crit, out, cache):
    """Treatment minus control, seed by seed. Signs are printed, not scored
    against a threshold (rule 11). A criterion here asserts only that the run
    produced a number for every seed and every quantity."""
    rows = []
    for s_ in SEEDS:
        t = measure(treat, s_, env, cache)
        c = measure(control, s_, env, cache)
        rows.append({k: round(t[k] - c[k], DIGITS) for k in READ}
                    | {"seed": s_,
                       "switches_treat": t["switches"],
                       "switches_control": c["switches"],
                       "non_empty_treat": t["non_empty_industries"],
                       "non_empty_control": c["non_empty_industries"]})
    print(f"\n{name}")
    print("  " + "seed  " + "  ".join(f"{k:>14}" for k in READ))
    for r in rows:
        print(f"  {r['seed']:<4}  " + "  ".join(f"{r[k]:>14.6f}" for k in READ))
    summary = {}
    for k in READ:
        v = [r[k] for r in rows]
        pos = sum(1 for x in v if x > 0)
        neg = sum(1 for x in v if x < 0)
        zer = len(v) - pos - neg
        summary[k] = dict(positive=pos, zero=zer, negative=neg,
                          lo=round(min(v), DIGITS), hi=round(max(v), DIGITS))
        print(f"  {k:>16}  {pos} pos  {zer} zero  {neg} neg"
              f"   [{min(v):+.6f}, {max(v):+.6f}]")
    dsw = [r["switches_treat"] - r["switches_control"] for r in rows]
    print(f"  {'switches':>16}  treat {[r['switches_treat'] for r in rows]}")
    print(f"  {'':>16}  ctrl  {[r['switches_control'] for r in rows]}")
    tot_t = sum(r["switches_treat"] for r in rows)
    tot_c = sum(r["switches_control"] for r in rows)
    if tot_c:
        print(f"  {'':>16}  total {tot_t} vs {tot_c}, "
              f"{(tot_t - tot_c) / tot_c:+.1%}")
    dne = [r["non_empty_treat"] - r["non_empty_control"] for r in rows]
    print(f"  {'non-empty ind':>16}  delta {dne}   "
          f"treat {[r['non_empty_treat'] for r in rows]}  "
          f"ctrl {[r['non_empty_control'] for r in rows]}")
    complete = all(np.isfinite(r[k]) for r in rows for k in READ)
    crit.append(Criterion(f"{name} produced a number for every seed and quantity",
                          complete,
                          f"{len(rows)} seeds x {len(READ)} quantities, "
                          f"all finite" if complete else "non-finite entries"))
    out[name] = dict(rows=rows, summary=summary, switch_delta=dsw,
                     non_empty_delta=dne,
                     switches_total=[tot_t, tot_c])
    return summary


def part_gates() -> list[Criterion]:
    mods = {t: load_backup(t) for t in BACKUPS}
    cur = sys.modules["monetary_topology.network"]

    crit: list[Criterion] = []
    gates: list[dict] = []

    def gate(name, mod_a, ind_a, mod_b, ind_b, note):
        a = run_with(mod_a, ind_a)
        b = run_with(mod_b, ind_b)
        ok, differ, n = compare(a, b)
        crit.append(
            Criterion(
                name,
                ok,
                f"{n - len(differ)}/{n} history fields identical"
                + ("" if ok else "; differ: " + ", ".join(differ)),
            )
        )
        gates.append(
            dict(name=name, passed=ok, fields=n, differing=differ, what=note)
        )
        print(f"  {'PASS' if ok else 'FAIL':4}  {name:34}  "
              f"{n - len(differ)}/{n} fields identical")
        return a, b

    print("reproduction gates (rule 19: run, do not derive)")
    # Walk the backup chain one link at a time. Three links carry code that a
    # zero switch should not reach, so they are gates; the fourth carries a
    # routing fix as well as a switch, so it is a reading and not a gate. Which
    # link is which was measured, not assumed: with industries on and every
    # switch off, pre_switch equals pre_recovery and pre_supply equals current
    # bit for bit, and the whole difference sits on the one link between them.
    gate("A19-2a industry layer added",
         mods["pre_industry"], None, cur, dict(count=0),
         "code before the industry module, against count=0 on current code")
    gate("A19-2b switching added",
         mods["pre_switch"], ON, mods["pre_recovery"], ON,
         "the switching link, industries on and switching off")
    gate("A19-2c supply constraint added",
         mods["pre_supply"], ON, cur, dict(ON, supply_elasticity=0.0),
         "the supply link, against the constraint at zero")
    gate("A19-2f friction spread added",
         mods["pre_spread"], dict(ON, supply_elasticity=1.0, switch_rate=0.2,
                                  switch_cost=0.3, min_share=MIN_SHARE,
                                  recovery_friction=5.0),
         cur, dict(ON, supply_elasticity=1.0, switch_rate=0.2,
                   switch_cost=0.3, min_share=MIN_SHARE,
                   recovery_friction=5.0, friction_spread=0.0),
         "per-industry friction, against the flat scalar it replaces")
    # No gate on the row/column rename. That backup imports the function name
    # the rename replaced, so it cannot be loaded against the current package:
    # a backup chain breaks at an API rename, not at a behaviour change. The
    # link is covered anyway, and covered harder, by the gate below, which
    # reaches back past the rename to the build that had no perturbation at all
    # and compares it against every drift set to zero.
    gate("A19-2g coefficient perturbation added",
         mods["pre_theta"], dict(ON, supply_elasticity=1.0, switch_rate=0.2,
                                 switch_cost=0.3, min_share=MIN_SHARE,
                                 recovery_friction=1.0, friction_spread=1.04),
         cur, dict(ON, supply_elasticity=1.0, switch_rate=0.2,
                   switch_cost=0.3, min_share=MIN_SHARE,
                   recovery_friction=1.0, friction_spread=1.04,
                   row_drift=0.0, col_drift=0.0),
         "the perturbation link: a live coefficient matrix, against a frozen one")

    # Both of these run entirely inside the current build, so no backup and no
    # link is involved: a knob set to its off value has to reproduce the run
    # without it, and a knob priced out of reach has to reproduce the knob
    # being off.
    gate("A19-2d switching priced out",
         cur, dict(ON, switch_rate=0.0), cur, dict(ON, switch_rate=0.2, switch_cost=20.0),
         "nobody switches because nobody can afford to")
    gate("A19-2e damage without friction",
         cur, dict(ON, min_share=0.0, recovery_friction=0.0),
         cur, dict(ON, min_share=0.7, recovery_friction=0.0),
         "marking an industry damaged has no consequence when the lag is zero")

    # Not a gate. This link carries the fix for the routing error as well as
    # the supply switch, so a difference here is expected and its size is the
    # mechanical weight of that fix (rule 11: print the object).
    print("\nthe one link that is a reading, not a gate")
    ra = run_with(mods["pre_recovery"], ON)
    rb = run_with(mods["pre_supply"], ON)
    _, rdiff, rn = compare(ra, rb)
    rel = {}
    for f in rdiff:
        x = np.asarray(getattr(ra, f), dtype=float)
        y = np.asarray(getattr(rb, f), dtype=float)
        if x.size:
            rel[f] = round(float(np.abs(x - y).max()
                                 / max(np.abs(x).max(), 1e-30)), DIGITS)
    print(f"  {rn - len(rdiff)}/{rn} fields identical across the routing fix")
    for f in sorted(rel, key=lambda k: -rel[k])[:6]:
        print(f"    {f:24} relative {rel[f]:.4%}")
    routing_fix = dict(fields_differing=rdiff, n_fields=rn, relative=rel,
                       what="final demand split by industry; the link between "
                            "pre_recovery and pre_supply carries this fix as "
                            "well as the supply switch")

    # Not a gate. ``column_sum`` prices the intermediate half only; the final
    # demand half is split by industry regardless, so no value of it returns
    # the identity. Printed because the size of what is left over IS the
    # mechanical weight of that half (rule 11: print the object).
    print("\nfinal-demand half, measured by driving column_sum to zero")
    lo = run_with(cur, dict(ON, column_sum=1e-12))
    off = run_with(cur, dict(count=0))
    _, differ, n = compare(lo, off)
    dv = float(abs(lo.total_volume.sum() - off.total_volume.sum())
               / max(off.total_volume.sum(), 1e-30))
    ds = float(abs(lo.effective_support_l2[-1] - off.effective_support_l2[-1]))
    print(f"  {len(differ)}/{n} history fields still differ at column_sum=1e-12")
    print(f"  total volume differs by {dv:.4%}, closing L2 support by {ds:.4f}")
    final_half = dict(fields_differing=differ, n_fields=n,
                      total_volume_relative=round(dv, DIGITS),
                      l2_support_absolute=round(ds, DIGITS))

    # Rule 19's second half: ``IndustrySpec.replace`` carries a hand written
    # field list, and a hand written field list is what silently drops a new
    # field back to its default.
    declared = {f.name for f in fields(IndustrySpec)}
    probe = IndustrySpec(**ON)
    listed = set(probe.replace().__dict__)
    same = declared == listed
    crit.append(Criterion(
        "A19-0 replace() lists every field", same,
        f"{len(listed)}/{len(declared)} fields carried"
        + ("" if same else f"; missing {sorted(declared - listed)}")))
    print(f"\n  {'PASS' if same else 'FAIL':4}  A19-0 replace() lists every field  "
          f"{len(listed)}/{len(declared)}")

    print("\nconservation")
    combos = {
        "off": dict(count=0),
        "on": dict(ON),
        "on+switch": dict(ON, switch_rate=0.2, switch_cost=0.3),
        "on+recovery": dict(ON, min_share=0.7, recovery_friction=5.0),
        "on+supply": dict(ON, supply_elasticity=1.0),
        "all": dict(ON, switch_rate=0.2, switch_cost=0.3, min_share=0.7,
                    recovery_friction=5.0, supply_elasticity=1.0),
    }
    resid = {}
    for k, ind in combos.items():
        resid[k] = conservation(run_with(cur, ind))
        print(f"  {k:14} residual {resid[k]:.3e}")
    worst = max(resid.values())
    crit.append(Criterion("A19-3 claims conserved", worst < SFC_TOLERANCE,
                          f"worst residual {worst:.3e} over "
                          f"{len(combos)} switch combinations, tolerance "
                          f"{SFC_TOLERANCE:.0e}"))
    print(f"  {'PASS' if worst < SFC_TOLERANCE else 'FAIL':4}  "
          f"A19-3 claims conserved  worst {worst:.3e}")

    n_pass = sum(c.passed for c in crit)
    print(f"\n  {n_pass}/{len(crit)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a19_industry.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A19",
                "part": "reproduction gates and conservation",
                "diagnostic_only": True,
                "diagnostic_reason": (
                    "Part one of A19. The direction readings A19-4 through "
                    "A19-7 are not in this file yet, so nothing here is a "
                    "closed reading of the stage."
                ),
                "carrier": {
                    "layer1_size": LAYER1_SIZE,
                    "layer2_size": LAYER2_SIZE,
                    "rounds": ROUNDS,
                    "industry_on": ON,
                },
                "backups_compared_against": BACKUPS,
                "gates": gates,
                "final_demand_half": final_half,
                "routing_fix_link": routing_fix,
                "conservation": {k: round(v, DIGITS) for k, v in resid.items()},
                "sfc_tolerance": SFC_TOLERANCE,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in crit
                ],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return crit


def part_directions() -> list[Criterion]:
    """A19-4 to A19-7: what the industry layer does, and what it does not.

    Every reading is a paired difference over five seeds with the signs
    printed. Nothing here is scored against a threshold, so the criteria only
    assert that a number came back for every seed and every quantity; the
    reading is the table.
    """
    crit: list[Criterion] = []
    out: dict = {}
    cache = load_cache()
    print(f"  cache holds {len(cache)} runs")

    print("A19-4  the industry layer, against no industries")
    paired("A19-4 industry layer (live setting)",
           dict(ON, supply_elasticity=1.0), dict(count=0), LIVE, crit, out, cache)
    paired("A19-4b industry layer (no subsistence, no wage channel)",
           dict(ON, supply_elasticity=1.0), dict(count=0), BARE, crit, out, cache)

    print("\nA19-5  the switching knob, both arms with industries on")
    base5 = dict(ON, supply_elasticity=1.0)
    paired("A19-5 switching", dict(base5, switch_rate=0.2, switch_cost=0.3),
           base5, LIVE, crit, out, cache)

    print("\nA19-6  the recovery lag, both arms switching")
    print("  min_share sweep at seed 0, to locate the cliff before reading it")
    print("  %-10s %-9s %-11s %-13s %-8s"
          % ("min_share", "damaged", "switch f=0", "switch f=inf", "change"))
    sweep = []
    b6 = dict(ON, supply_elasticity=1.0, switch_rate=0.2, switch_cost=0.3)
    for ms in MIN_SHARE_SWEEP:
        a = measure(dict(b6, min_share=ms, recovery_friction=0.0), 0, LIVE, cache)
        b = measure(dict(b6, min_share=ms, recovery_friction=float("inf")),
                    0, LIVE, cache)
        ch = (b["switches"] - a["switches"]) / a["switches"] if a["switches"] else 0.0
        sweep.append(dict(min_share=ms, damaged=a["damaged_industries"],
                          switches_no_friction=a["switches"],
                          switches_infinite=b["switches"],
                          relative_change=round(ch, DIGITS)))
        print("  %-10.2f %-9d %-11d %-13d %+.1f%%"
              % (ms, a["damaged_industries"], a["switches"], b["switches"], ch * 100))
    out["A19-6 min_share sweep"] = sweep

    # ``min_share`` is swept first, because the sweep is what says where this
    # knob has an object. At 0.7 the entry threshold clears anyway and the
    # friction moves almost nothing; the cliff sits between 0.9 and 1.1. Sitting
    # on the flat part and calling the treatment inert is the error this stage
    # already paid for twice, so the arm runs at 1.1.
    base6 = dict(ON, supply_elasticity=1.0, switch_rate=0.2, switch_cost=0.3,
                 min_share=MIN_SHARE)
    paired("A19-6 recovery friction",
           dict(base6, recovery_friction=float("inf")),
           dict(base6, recovery_friction=0.0), LIVE, crit, out, cache)

    # A19-7: the level side of the scar, industries off. Read as a shape --
    # does the trough equal the close -- not as a gini, which is what A15's
    # design file said could not see it.
    print("\nA19-7  the level side of the scar, industries off")
    q7 = measure(dict(count=0), 0, LIVE, cache)
    flat = abs(q7["wage_trough"] - q7["wage_close"])
    print(f"  wage peak {q7['wage_peak']:.4f}  trough {q7['wage_trough']:.4f}"
          f"  close {q7['wage_close']:.4f}")
    print(f"  trough to close {flat:.6f}, i.e. "
          f"{flat / max(q7['wage_peak'], 1e-30):.4%} of the peak")
    out["A19-7"] = {k: round(v, DIGITS) for k, v in q7.items()}
    crit.append(Criterion("A19-7 wage path produced peak, trough and close",
                          all(np.isfinite(q7[k]) for k in
                              ("wage_peak", "wage_trough", "wage_close")),
                          f"peak {q7['wage_peak']:.4f}, trough "
                          f"{q7['wage_trough']:.4f}, close "
                          f"{q7['wage_close']:.4f}"))

    n_pass = sum(c.passed for c in crit)
    print(f"\n  {n_pass}/{len(crit)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "a19_directions.json"
    path.write_text(
        json.dumps(
            {
                "stage": "A19",
                "part": "direction readings",
                "diagnostic_only": True,
                "diagnostic_reason": (
                    "Directions are printed, not scored: no threshold is "
                    "applied to any difference in this file. The criteria "
                    "here assert only that every seed and quantity returned "
                    "a number."
                ),
                "carrier": {
                    "layer1_size": LAYER1_SIZE,
                    "layer2_size": LAYER2_SIZE,
                    "rounds": ROUNDS,
                    "seeds": list(SEEDS),
                    "industry_on": ON,
                    "live_setting": LIVE,
                    "bare_setting": BARE,
                },
                "readings": out,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in crit
                ],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  wrote {path.relative_to(ROOT)}")
    return crit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("gates", "directions", "all"),
                    default="all")
    args = ap.parse_args()
    crit: list[Criterion] = []
    if args.part in ("gates", "all"):
        crit += part_gates()
    if args.part in ("directions", "all"):
        crit += part_directions()
    n = sum(c.passed for c in crit)
    print(f"\nA19 total  {n}/{len(crit)} criteria passed")
    return 0 if n == len(crit) else 1


if __name__ == "__main__":
    raise SystemExit(main())
