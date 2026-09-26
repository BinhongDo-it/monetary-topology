"""A37: what the node that cuts its own out-edges ends up holding.

Ruled 2026-09-13. A17 read the volume this arm produces and stopped there: at
``trigger=2.0`` a share of 0.5 leaves total flow at 0.849 of its twin and a
share of 0.7 leaves it at 0.0199, a fall of 43 with one empty grid point in
between, and the 0.7 column collapses at all five triggers. What A17 never
split was the holding: the stage asks whether the nodes that cut are better or
worse off than the nodes that did not, and at which share the sign turns over.

Three steps, one at a time and in this order:

    python experiments/a37_lying_flat.py --gate      # rule 19, then nothing else runs
    python experiments/a37_lying_flat.py --time      # seconds per cell, measured
    python experiments/a37_lying_flat.py --run       # the grid

``--run`` does not start until ``--gate`` has passed on the module and this
script as they are now. ``--selftest`` seeds a fault and requires the gate to
report it: a gate that has never failed is not a gate.

The criteria are written in this file and the record carries their text, so
the quantities this run produced are all reported.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "monetary_topology"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    EdgeCutSpec,
    Network,
    NetworkConfig,
    NetworkSpec,
)

#: The module as it stood before ``cut_out`` was added, under the repository's
#: backup convention. The gate compares against this file and not against a
#: remembered number, because a number written into a script checks the script's
#: memory rather than the module.
PRE_MODULE = SRC / "network.py.expired_20260913_pre_A37"

#: The field this stage adds. Excluded from the field-by-field comparison
#: because the old module has no such attribute, and asserted separately.
NEW_FIELD = "cut_out"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def _cut(mode: str, share: float, **kw) -> EdgeCutSpec:
    return EdgeCutSpec(mode=mode, share=share, **kw)


def gate_configs(mod) -> list[tuple[str, object]]:
    """Configurations the gate runs on both modules.

    Two halves, and both are needed. **Off** is the ordinary rule 19 question:
    a run that does not ask for the switch takes the path it always took. **On**
    is the half a switch that only adds a field still has to answer, because
    the added lines sit inside ``_cut_edges`` and could perturb the cut itself.
    """
    C, S, EC = mod.NetworkConfig, mod.NetworkSpec, mod.EdgeCutSpec
    out: list[tuple[str, object]] = []

    # Off: the library default and four perturbations of the construction.
    out.append(("default", C(rounds=60)))
    out.append(("seed 7", C(spec=S(seed=7), seed=7, rounds=60)))
    out.append(("small", C(spec=S(layer1_size=8, layer2_size=40), rounds=60)))
    out.append(("f2i 30", C(spec=S(intermediate_size=30,
                                   financial_to_intermediate_edges=30), rounds=60)))
    out.append(("rounds 120", C(rounds=120)))

    # On: three modes, two shares each, at A17's trigger.
    for mode, extra in (("shock", {"at_round": 10}),
                        ("self_cut", {"trigger": 2.0}),
                        ("run", {"trigger": 2.0})):
        for share in (0.30, 0.70):
            out.append((f"{mode} {share:.2f}",
                        C(edge_cut=EC(mode=mode, share=share, **extra), rounds=60)))
    # On, targeted: the other half of the shock arm's own switch.
    out.append(("shock degree 0.50",
                C(edge_cut=EC(mode="shock", share=0.50, at_round=10,
                              targeting="degree"), rounds=60)))
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


def run_gate(perturb: str | None = None) -> bool:
    """Rule 19. Prints one line per configuration and returns whether it passed.

    ``perturb`` is the selftest's hook: it names a fault to seed into the new
    module's output so the gate has something it must catch.
    """
    if not PRE_MODULE.exists():
        print(f"FAIL: no backup at {PRE_MODULE.name}")
        return False
    # The name has to sit inside the package or the module's own relative
    # imports have no parent to resolve against.
    old = _load(PRE_MODULE, "monetary_topology._network_pre_a37")
    import monetary_topology.network as new

    shared = ({f.name for f in dataclasses.fields(new.NetworkHistory)}
              & {f.name for f in dataclasses.fields(old.NetworkHistory)})
    print(f"gate: {len(shared)} shared fields per configuration, bitwise\n")

    ok = True
    for (name, cfg_new), (_, cfg_old) in zip(gate_configs(new), gate_configs(old)):
        h_new = new.Network(cfg_new).run()
        h_old = old.Network(cfg_old).run()
        bad, only = compare(h_new, h_old)

        cut_on = cfg_new.edge_cut.active
        got = getattr(h_new, NEW_FIELD, None)
        if perturb == "stale" and cut_on and got is not None:
            got = np.roll(got, 1, axis=0)          # last round's vector, one late
        if perturb == "missing" and cut_on:
            got = None

        notes = []
        if cut_on:
            if got is None:
                notes.append("cut_out is None while the switch is on")
            else:
                total = float(got.sum())
                if total <= 0:
                    notes.append("cut_out is all zero while edges were cut")
                # **The shock arm cuts once, at one named round.** So the set of
                # rounds with a non-zero row is known before the run and is a
                # single number. Without this the gate cannot tell a vector
                # written for round t from one written for round t-1, and a
                # gate that cannot see a stale vector is not guarding the field
                # this stage adds.
                if cfg_new.edge_cut.mode == "shock":
                    fired = sorted(int(r) for r in np.flatnonzero(got.sum(axis=1)))
                    if fired != [cfg_new.edge_cut.at_round]:
                        notes.append(
                            f"shock fired on rounds {fired}, "
                            f"expected [{cfg_new.edge_cut.at_round}]")
        else:
            if got is not None:
                notes.append("cut_out is not None while the switch is off")

        good = not bad and not notes
        ok = ok and good
        flag = "ok  " if good else "FAIL"
        extra = f"  cut_out sum {float(got.sum()):.0f}" if (cut_on and got is not None) else ""
        print(f"  {flag} {name:20s} differing fields: {len(bad)}{extra}"
              + (f"   {'; '.join(bad[:4])}" if bad else "")
              + (f"   {'; '.join(notes)}" if notes else ""))
    print("\ngate:", "PASS" if ok else "FAIL")
    return ok


def selftest() -> bool:
    """Seed a fault, require the gate to report it (`11f`)."""
    print("selftest: the gate must fail on each seeded fault\n")
    results = []
    for fault in ("stale", "missing"):
        print(f"--- fault: {fault}")
        caught = not run_gate(perturb=fault)
        print(f"--- caught: {caught}\n")
        results.append(caught)
    print("selftest:", "PASS" if all(results) else "FAIL")
    return all(results)


#: A17's carrier, imported at run time rather than restated, so the control
#: arm is bitwise the arm that station already recorded.
from a17_edge_cut import ELASTICITY, F2I, ROUNDS, base_config  # noqa: E402

#: Three of A17's five triggers. Its 8.0 and 12.0 columns read the same number
#: at every share it ran, so the fifth is spent on nothing (rule 12).
TRIGGERS = (2.0, 4.0, 8.0)

#: Nine shares. The first three and the seventh are A17's own, which is what
#: lets A37-0 check the two harnesses against each other; the rest densify the
#: interval where A17's volume fell by 43 with one empty point inside it.
SHARES = (0.10, 0.30, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80)

SEEDS = (0, 1, 2, 3, 4)

#: Two carriers. The floor off reads what withdrawal does with no absorbing
#: wall anywhere; the floor on reads who crosses it. A17 ran the first only.
NEEDS = (0.0, 0.20)

TIMING = RESULTS / "a37_timing.json"
RECORD = RESULTS / "a37_lying_flat.json"


def _med(x: np.ndarray) -> float:
    return float(np.median(x)) if x.size else float("nan")


def one_cell(need: float, trigger: float, share: float, seed: int,
             ctrl_cache: dict) -> dict:
    """One treated run against its own twin, and the two groups read apart."""
    key = (need, seed)
    if key not in ctrl_cache:
        ctrl_cache[key] = Network(base_config(seed, need=need)).run()
    ctrl = ctrl_cache[key]

    cfg = base_config(seed, need=need)
    cfg = dataclasses.replace(
        cfg, edge_cut=EdgeCutSpec(mode="self_cut", share=share, trigger=trigger))
    hist = Network(cfg).run()

    # **The grouping comes out of the module.** Recomputing the trigger here
    # would be a second definition of the same set, which is the twelfth
    # category error and what A16-2 was written against.
    flat = hist.cut_out.sum(axis=0) > 0
    h_t, h_c = hist.holdings[-1], ctrl.holdings[-1]

    # Each group against itself in the twin, so a group that was poor to begin
    # with does not read as a group that lost. A15-4b: this figure's sign drifts
    # on the baseline alone, so an absolute level carries nothing.
    def rel(mask):
        base = _med(h_c[mask])
        return float(_med(h_t[mask]) / base) if base > 0 else float("nan")

    # **Shares, not levels.** The treated arm issues claims its twin does not,
    # so a ratio of levels is a ratio whose two denominators are different
    # money, which is the fourth category error. Dividing each arm by its own
    # total puts the two on one scale before any group is compared, and the M
    # ratio below is printed next to it so the size of that correction is in
    # the record rather than inferred from it.
    def _norm(v):
        s = float(v.sum())
        return v / s if s > 0 else v

    s_t, s_c = _norm(h_t), _norm(h_c)

    def rel_share(mask):
        base = _med(s_c[mask])
        return float(_med(s_t[mask]) / base) if base > 0 else float("nan")

    # The module's own headline field, 1 / HHI of inflow. Read over the last
    # tenth of the run rather than the final round, so one round's noise does
    # not become the reading, and against this cell's own twin.
    tail = max(1, hist.effective_support.size // 10)
    sup_t = float(np.median(hist.effective_support[-tail:]))
    sup_c = float(np.median(ctrl.effective_support[-tail:]))

    # The flow that is trade, which is the flow minus the wage the rule pays
    # out. **A cell can have its trading economy end and still show inflow**,
    # because the wage keeps being paid to a fixed roster, and 1 / HHI of one
    # uniform payment to k accounts is exactly k. That is the roster's size and
    # not a receiving set, so the quantity that says whether there is anything
    # left to measure has to be carried in the record rather than inferred from
    # the support figure that the degenerate case corrupts.
    trade_t = float(hist.total_volume[-tail:].sum()
                    - hist.wage_paid[-tail:].sum())
    trade_c = float(ctrl.total_volume[-tail:].sum()
                    - ctrl.wage_paid[-tail:].sum())
    m_t, m_c = float(h_t.sum()), float(h_c.sum())
    iss_t, iss_c = float(hist.issuance.sum()), float(ctrl.issuance.sum())

    vol_t = float(hist.total_volume.sum())
    vol_c = float(ctrl.total_volume.sum())
    return {
        "need": need, "trigger": trigger, "share": share, "seed": seed,
        "n_flat": int(flat.sum()), "n_not": int((~flat).sum()),
        "gap_flat": rel(flat), "gap_not": rel(~flat),
        "share_flat": rel_share(flat), "share_not": rel_share(~flat),
        "m_ratio": m_t / m_c if m_c > 0 else float("nan"),
        "issuance_ratio": iss_t / iss_c if iss_c > 0 else float("nan"),
        "support_ratio": sup_t / sup_c if sup_c > 0 else float("nan"),
        "support_t": sup_t, "support_c": sup_c,
        "trade_t": trade_t, "trade_c": trade_c,
        # A cell whose treated arm came back bitwise its twin was not treated,
        # whatever the switch says. It is a third state and not a reading of
        # zero effect, so it is named here and mapped to no verdict (11c).
        "inert": bool(np.array_equal(h_t, h_c)),
        "volume_ratio": vol_t / vol_c if vol_c > 0 else float("nan"),
        "edges_cut": float(hist.cut_out.sum()),
        # A17-8: below a twentieth of the twin's flow the level readings do not
        # carry, in either direction. Flagged rather than dropped.
        "thin": bool(vol_c > 0 and vol_t / vol_c < 0.05),
    }


def grid(smoke: bool = False):
    needs = NEEDS[:1] if smoke else NEEDS
    trigs = TRIGGERS[:1] if smoke else TRIGGERS
    shares = (0.10, 0.70) if smoke else SHARES
    seeds = SEEDS[:1] if smoke else SEEDS
    return [(n, t, s, d) for n in needs for t in trigs for s in shares for d in seeds]


def run_grid(smoke: bool = False) -> list[dict]:
    cells = grid(smoke)
    cache: dict = {}
    rows = []
    for i, (n, tr, sh, sd) in enumerate(cells, 1):
        rows.append(one_cell(n, tr, sh, sd, cache))
        if i % 25 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}", flush=True)
    return rows


# --------------------------------------------------------------------------
# criteria


def _by_share(rows, need, trigger, key):
    out = []
    for sh in sorted({r["share"] for r in rows}):
        vals = [r[key] for r in rows
                if r["need"] == need and r["trigger"] == trigger
                and r["share"] == sh and not np.isnan(r[key])]
        out.append((sh, float(np.median(vals)) if vals else float("nan"), len(vals)))
    return out


def criteria(rows: list[dict]) -> list[dict]:
    c: list[dict] = []

    # A37-1: print the two groups, every cell, no cross-cell mean.
    printed = sum(1 for r in rows if not np.isnan(r["gap_flat"])
                  or not np.isnan(r["gap_not"]))
    c.append(dict(name="A37-1  both groups printed per cell", kind="own_reading",
                  passed=printed == len(rows) and len(rows) > 0,
                  detail=f"{printed}/{len(rows)} cells carry at least one group ratio"))

    # A37-2: the difference against share. Three-way, and the undecided branch
    # maps to no verdict (11c).
    # **Read on shares of the arm's own stock, not on levels.** The first
    # version read levels, and the treated arm's stock is up to forty times its
    # twin's, so the difference it reported was the issuance and not the two
    # groups. The level columns stay in the record and A37-1 still counts them.
    verdicts = []
    for need in sorted({r["need"] for r in rows}):
        for tr in sorted({r["trigger"] for r in rows}):
            diff = [(sh, f - n if not (np.isnan(f) or np.isnan(n)) else float("nan"))
                    for (sh, f, _), (_, n, _)
                    in zip(_by_share(rows, need, tr, "share_flat"),
                           _by_share(rows, need, tr, "share_not"))]
            live = [(s, d) for s, d in diff if not np.isnan(d)]
            if len(live) < 3:
                verdicts.append((need, tr, "no object", diff)); continue
            signs = {np.sign(d) for _, d in live if d != 0}
            if len(signs) == 1:
                verdicts.append((need, tr, "one sign throughout", diff))
            else:
                cross = [live[i][0] for i in range(1, len(live))
                         if np.sign(live[i][1]) != np.sign(live[i - 1][1])]
                verdicts.append((need, tr, f"sign turns at share {cross}", diff))
    lines = "; ".join(f"need {n} trigger {t}: {v}" for n, t, v, _ in verdicts)
    c.append(dict(name="A37-2  the sign of the difference between the two "
                       "groups, in shares, against the depth of withdrawal",
                  kind="own_reading", passed=bool(verdicts), detail=lines[:900]))

    # A37-3: flow and split side by side, thin cells named.
    thin = sum(1 for r in rows if r["thin"])
    c.append(dict(name="A37-3  flow and split printed together", kind="own_reading",
                  passed=True,
                  detail=f"{thin}/{len(rows)} cells below a twentieth of their "
                         f"twin's flow; their level readings do not carry"))

    # A37-4: WITHDRAWN 2026-09-13, kept and not deleted (18a). Registered as
    # "the rival's point prediction does not hold on these cells", so PASS
    # would have meant the rival is wrong (11e). Two things are wrong with it
    # and the second is the one that settles it.
    #
    # One, the entailment was written on levels, and the treated arm's stock is
    # many times its twin's, so what the cells were above was the issuance.
    #
    # Two, and this is the premise failing: the rival's premise is a fixed
    # total of bad debt shared per head, and **this carrier has no debt in it**.
    # Neither the hub liability, the sovereign, nor the write-off is on in the
    # configuration this station runs, so the group that does not withdraw is
    # not carrying anything for the group that does. The prediction has no
    # object here, which is a premise failure and not a reading (11d), and a
    # premise failure says the criteria that depend on it have nothing to
    # judge. It says nothing for or against the framework.
    #
    # Recorded the way B60-2 was: the numbers stay, the verdict comes off.
    # **The rival supplies the curve, so nothing here is a threshold of ours.**
    # Its closed form makes the per-head burden go as 1/(1-L); anchored on the
    # lowest share actually run, it predicts gap_not(L) = gap_not(L0)*(1-L)/(1-L0).
    # The verdict is a count of cells above that curve, not a line drawn on an
    # estimate (rule 11).
    above = below = 0
    lines = []
    for need in sorted({r["need"] for r in rows}):
        for tr in sorted({r["trigger"] for r in rows}):
            series = [(s, v) for s, v, k in _by_share(rows, need, tr, "gap_not")
                      if not np.isnan(v)]
            if len(series) < 2:
                continue
            l0, v0 = series[0]
            for L, v in series[1:]:
                pred = v0 * (1.0 - L) / (1.0 - l0)
                if v > pred:
                    above += 1
                else:
                    below += 1
            lines.append(f"need {need} trigger {tr}: "
                         + " ".join(f"{L:.2f}:{v:.3f}/{v0*(1-L)/(1-l0):.3f}"
                                    for L, v in series[1:]))
    total = above + below
    if total == 0:
        verdict, note = False, "no object: fewer than two live shares anywhere"
    elif above == total:
        verdict, note = True, f"above the rival's curve at all {total} cells"
    elif below == total:
        verdict, note = False, f"at or below the rival's curve at all {total} cells"
    else:
        verdict, note = False, (f"mixed, {above}/{total} above: no verdict, "
                                f"report the ratio (11c third branch)")
    c.append(dict(name="A37-4  the non-withdrawing group is not on the rival's "
                       "curve  [WITHDRAWN 2026-09-13]",
                  kind="premise", passed=False, withdrawn=True,
                  withdrawn_reason="the premise names a fixed total of bad debt "
                                   "shared per head, and this carrier carries no "
                                   "debt: hub liability, sovereign and write-off "
                                   "are all off in the configuration run. The "
                                   "reading was also taken on levels, which the "
                                   "treated arm's own issuance moves.",
                  rival_shape="point prediction",
                  rival_premise="the bad debt to be absorbed is a fixed total, "
                                "shared per head among those who have not withdrawn",
                  rival_entailment="per-head burden goes as 1/(1-L), so the "
                                   "holding of the non-withdrawing group falls "
                                   "as (1-L) once anchored on the lowest share run",
                  detail="Void: premise does not hold on this carrier, the "
                         "criterion has no object and is not evaluated. Numbers "
                         "kept for the record: " + note
                         + "  |  observed/predicted, on levels: " + "; ".join(lines)))

    # A37-7: the instrument, and it comes before A37-6 because it says which
    # cells A37-6 may read at all.
    #
    # ``effective_support`` is 1 / HHI of inflow, and it has two branches that
    # return a number without measuring anything. Its own code returns 0.0 when
    # total inflow is zero. And 1 / HHI of one payment made in equal parts to k
    # accounts is exactly k, so a cell whose trade has ended while the wage is
    # still being paid reads the size of the wage roster.
    #
    # **Both branches are the same state, and the statistic reports them at
    # opposite ends**, one at zero and one above the live readings. So the line
    # that matters is whether any trade is left, which is an accounting fact
    # this record carries, and not a level of flow.
    #
    # A17-8's registered thin flag is a level of flow, and it is printed here
    # against the accounting fact rather than used as the scope. Two things can
    # fail: a cell with its trade ended reading something other than one of the
    # two branches, which would mean the branch story is wrong, and a cell with
    # trade left reading zero, which cannot happen if the field means what its
    # code says.
    def _is_int(x):
        return np.isfinite(x) and abs(x - round(x)) <= 1e-9 * max(1.0, abs(x))

    bad = []
    if any(r.get("trade_t") is None for r in rows):
        bad.append("record predates trade_t, rerun the grid")
        ended, alive = [], []
    else:
        for r in rows:
            if r["trade_t"] < -1e-9:
                bad.append(f"negative trade at need {r['need']} share "
                           f"{r['share']} seed {r['seed']}: {r['trade_t']:.3e}")
        ended = [r for r in rows
                 if r["trade_t"] <= 1e-9 * max(1.0, r.get("trade_c", 1.0))]
        alive = [r for r in rows if r not in ended]
        for r in alive:
            if r["support_t"] == 0.0:
                bad.append(f"trade left but support zero: need {r['need']} "
                           f"share {r['share']} seed {r['seed']}")
        for r in ended:
            if r["support_t"] != 0.0 and not _is_int(r["support_t"]):
                bad.append(f"trade ended on neither branch: need {r['need']} "
                           f"share {r['share']} seed {r['seed']}, support "
                           f"{r['support_t']!r}")
    zero = [r for r in ended if r["support_t"] == 0.0]
    roster = [r for r in ended if r["support_t"] != 0.0]
    ks = sorted({int(round(r["support_t"])) for r in roster})
    agree = sum(1 for r in rows if bool(r["thin"]) == (r in ended))
    c.append(dict(name="A37-7  every cell whose trade has ended sits on one of "
                       "the instrument's two degenerate branches",
                  kind="instrument", passed=not bad,
                  detail=(f"{len(ended)}/{len(rows)} cells have no trade left in "
                          f"the tail: {len(zero)} read support 0 because inflow "
                          f"is zero, {len(roster)} read an exact integer {ks} "
                          f"because the only inflow left is one uniform wage. "
                          f"Every cell with trade left reads neither. A17-8's "
                          f"registered flow flag agrees with this on "
                          f"{agree}/{len(rows)} cells."
                          if not bad else "  |  ".join(bad[:6]))[:1200]))

    # A37-6: the framework's own bet, and this one is the framework's. Volume
    # one, section eight: the total can go up while the set that actually
    # receives contracts. **The quantity is the module's own headline field**,
    # 1 / HHI of inflow, not anything this script defines, and it is read
    # against each cell's own twin so the two arms stand on one scale.
    #
    # Scope: the cells that still have trade in them, which A37-7 establishes
    # and which is an accounting fact rather than a level. The cells whose
    # trading economy has ended are not dropped, they are reported on their own
    # line, because they are the end of the same road and not a separate
    # finding: a receiving set of nobody, with the stock many times its twin.
    #
    # Three states. A cell that came back bitwise its twin was not treated, so
    # it carries no object either way and maps to no verdict rather than to a
    # pass (11c). The verdict counts cells; it draws no line on an estimate,
    # and the per-depth medians are printed so the object is in the record and
    # not only its count (rule 11).
    live_rows = [r for r in rows if r in alive and not r.get("inert")
                 and not np.isnan(r.get("support_ratio", float("nan")))]
    down = sum(1 for r in live_rows if r["support_ratio"] < 1.0)
    up = sum(1 for r in live_rows if r["support_ratio"] > 1.0)
    live = down + up
    m_up = sum(1 for r in live_rows if not np.isnan(r.get("m_ratio", float("nan")))
               and r["m_ratio"] > 1.0)
    m_ended = ([r["m_ratio"] for r in ended
                if not np.isnan(r.get("m_ratio", float("nan")))] or [float("nan")])
    worst = max((r["support_ratio"] for r in live_rows), default=float("nan"))
    shown = []
    for need in sorted({r["need"] for r in rows}):
        for tr in sorted({r["trigger"] for r in rows}):
            sup = _by_share(live_rows, need, tr, "support_ratio")
            mm = dict((s, v) for s, v, _ in _by_share(live_rows, need, tr, "m_ratio"))
            body = " ".join(f"{s:.2f}:{v:.3f}/M{mm.get(s, float('nan')):.1f}[{k}]"
                            for s, v, k in sup if k)
            if body:
                shown.append(f"need {need} trigger {tr}: " + body)
    tail_line = ((f"  |  the other {len(ended)} cells have no trading economy "
                  f"left at all, and their stock is up by a median of "
                  f"{float(np.median(m_ended)):.1f} times (A37-7)")
                 if ended else "")
    if live == 0:
        passed, note = False, ("Void: no cell whose flow carries has a live "
                               "support ratio")
    elif down == live:
        passed, note = True, (f"the receiving set contracts on all {live} cells "
                              f"whose flow carries, the widest of them at "
                              f"{worst:.4f} of its twin, while the stock rises "
                              f"on {m_up} of them")
    elif up == live:
        passed, note = False, (f"the receiving set widens on all {live} cells "
                               "whose flow carries: this reading is withdrawn")
    else:
        passed, note = False, (f"Void: mixed, {down}/{live} contract, no verdict, "
                               "the ratio is the reading (11c third branch)")
    c.append(dict(name="A37-6  the receiving set contracts while the stock rises",
                  kind="own_reading", passed=passed,
                  detail=(note + tail_line + "  |  support ratio by depth / M "
                          "ratio [cells]: " + "; ".join(shown))[:1500]))
    return c


def selftest_criteria() -> bool:
    """11f: seed a fault into the rows and require each criterion to report it.

    Not "could this criterion fail" but "make it fail and watch". The gate
    already paid for this rule once on this station: its first version was
    blind to a stale vector because nothing was ever planted in one.
    """
    base = [dict(need=0.0, trigger=2.0, share=s, seed=0, n_flat=10, n_not=190,
                 gap_flat=1.0, gap_not=1.0, share_flat=1.0, share_not=1.0,
                 m_ratio=2.0, issuance_ratio=2.0, support_ratio=0.5,
                 support_t=5.0, support_c=10.0, inert=False,
                 trade_t=10.0, trade_c=20.0,
                 volume_ratio=1.0, edges_cut=5.0, thin=False) for s in SHARES]

    def pick(rows, nm):
        return [x for x in criteria(rows) if x["name"].startswith(nm)][0]

    ok = []
    # fault one: the receiving set widens instead of contracting
    rows = [dict(r, support_ratio=1.4) for r in base]
    got = pick(rows, "A37-6")
    ok.append(not got["passed"])
    print(f"  support widens   -> A37-6 passed={got['passed']} (want False)")

    # fault two: half the cells go each way, so there is no verdict to give
    rows = [dict(r, support_ratio=(0.5 if i % 2 else 1.4))
            for i, r in enumerate(base)]
    got = pick(rows, "A37-6")
    ok.append(not got["passed"] and got["detail"].startswith("Void"))
    print(f"  mixed signs      -> A37-6 passed={got['passed']} "
          f"void={got['detail'][:4]!r} (want False, 'Void')")

    # fault three: nothing was treated at all, so no cell carries an object
    rows = [dict(r, inert=True) for r in base]
    got = pick(rows, "A37-6")
    ok.append(not got["passed"] and got["detail"].startswith("Void"))
    print(f"  all cells inert  -> A37-6 passed={got['passed']} "
          f"void={got['detail'][:4]!r} (want False, 'Void')")

    # fault four: the two groups cross in shares, which A37-2 has to name
    rows = [dict(r, share_flat=1.0 + (s - 0.4), share_not=1.0 - (s - 0.4))
            for r, s in zip(base, SHARES)]
    got = pick(rows, "A37-2")
    ok.append("sign turns" in got["detail"])
    print(f"  groups cross     -> A37-2 says {got['detail'][:46]!r} "
          "(want 'sign turns')")

    # fault five: a cell whose trade has ended reads neither branch, which
    # would mean the branch story is wrong and the scope with it
    rows = [dict(r, trade_t=0.0, support_t=3.5) for r in base]
    got = pick(rows, "A37-7")
    ok.append(not got["passed"] and "neither branch" in got["detail"])
    print(f"  ended, support 3.5 -> A37-7 passed={got['passed']} (want False)")

    # fault six: a cell with trade left reads zero support, which the field's
    # own code cannot produce while inflow is positive
    rows = [dict(r) for r in base]
    rows[1]["support_t"] = 0.0
    got = pick(rows, "A37-7")
    ok.append(not got["passed"] and "trade left but support zero" in got["detail"])
    print(f"  alive, support 0   -> A37-7 passed={got['passed']} (want False)")

    # fault seven: the accounting comes back negative, so the wage is not part
    # of the flow the way this column assumes
    rows = [dict(r) for r in base]
    rows[2]["trade_t"] = -3.0
    got = pick(rows, "A37-7")
    ok.append(not got["passed"] and "negative trade" in got["detail"])
    print(f"  negative trade     -> A37-7 passed={got['passed']} (want False)")

    # fault eight: a uniform-inflow cell with trade ended is the roster branch
    # and must be named as such rather than read as a wide receiving set
    rows = [dict(r, trade_t=0.0, support_t=75.00000000000001) for r in base]
    got = pick(rows, "A37-7")
    ok.append(got["passed"] and "[75]" in got["detail"])
    print(f"  roster branch      -> A37-7 passed={got['passed']} (want True, [75])")

    # fault nine: no cell carries a ratio
    rows = [dict(r, gap_flat=float('nan'), gap_not=float('nan')) for r in base]
    got = pick(rows, "A37-1")
    ok.append(not got["passed"])
    print(f"  empty ratios     -> A37-1 passed={got['passed']} (want False)")

    # A37-4 is withdrawn, so what is checked is that it says so rather than
    # that it judges: a criterion whose premise failed must not come back a
    # verdict in either direction (11c, 11d).
    got = pick([dict(r) for r in base], "A37-4")
    ok.append(got["kind"] == "premise" and got["withdrawn"] is True
              and got["detail"].startswith("Void") and got["passed"] is False)
    print(f"  withdrawn        -> A37-4 kind={got['kind']} "
          f"withdrawn={got.get('withdrawn')} void={got['detail'][:4]!r}")
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
        import json, time
        cache: dict = {}
        t0 = time.time(); one_cell(0.0, 2.0, 0.50, 0, cache); t1 = time.time()
        one_cell(0.20, 2.0, 0.50, 0, cache); t2 = time.time()
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
        import json
        if not args.smoke and not TIMING.exists():
            print("refusing: run --time first (D38)"); return 1
        rows = run_grid(smoke=args.smoke)
        crit = criteria(rows)
        for x in crit:
            tag = "VOID" if x.get("withdrawn") else ("PASS" if x["passed"] else "FAIL")
            print(f"  {tag}[{x['kind']}] {x['name']}")
            print(f"        {x['detail'][:400]}")
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
            return 0
        rec = {"stage": "A37",
               # Rule 22: the flag is a boolean and the reason is its own key,
               # because a field that is only ever read through ``if x:`` has
               # nothing guarding its type.
               "diagnostic_only": True,
               "diagnostic_reason": (
                   "Station not closed. The axis this grid measures is the "
                   "depth of withdrawal, how much of its own out-edges a "
                   "triggered node cuts, and not the breadth, how many nodes "
                   "withdraw: breadth is endogenous here and runs to the full "
                   "population on its own. A37-4 is withdrawn, its premise "
                   "names a debt this carrier does not carry. The readings "
                   "that stand are the collapse boundary, the endogenous "
                   "count, and A37-6."),
               "config": {"triggers": list(TRIGGERS), "shares": list(SHARES),
                          "seeds": list(SEEDS), "needs": list(NEEDS),
                          "f2i": F2I, "elasticity": ELASTICITY, "rounds": ROUNDS,
                          "mode": "self_cut",
                          "revision": 2,
                          "revision_note": "group comparisons read shares of "
                                           "each arm's own stock, not levels; "
                                           "A37-4 withdrawn, premise failed; "
                                           "A37-6 added on the module's own "
                                           "support field",
                          # Named because nothing else in the record says so and
                          # the withdrawal of A37-4 turns on it: no liability
                          # anywhere in this carrier.
                          "hub_debt": False, "sovereign": False,
                          "write_off": False},
               "criteria": crit, "runs": rows}
        RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"\nwrote {RECORD}")
        # A withdrawn criterion is not a failure to report: it was not
        # evaluated, and counting it would put a number in the exit code that
        # names nothing (11c second clause).
        return 0 if all(x["passed"] for x in crit if not x.get("withdrawn")) else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
