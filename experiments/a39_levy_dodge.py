"""A39: who pays the levy when some of the graph has withdrawn.

Two stations had to land first. A37 registered a criterion against the claim
that a fixed burden is shared per head among those who did not withdraw, and
that carrier held no debt at all, so the claim had nothing there to be about;
it was recorded as a premise that does not hold and withdrawn. A38 made the
width of a withdrawal a knob, which is the axis such a claim needs, because a
curve cannot be scored at one point.

Both are in now. The sovereign's levy is built and measured, the width is set
from outside, and this stage adds the one quantity neither had: what the levy
takes from each node.

    python experiments/a39_levy_dodge.py --gate      # rule 19, then nothing else
    python experiments/a39_levy_dodge.py --selftest  # seed a fault, require a report

The gate has three halves. The default reproduces the module before the field.
The sovereign station's recorded cells come back. And the per-node vector sums
to the scalar the module already recorded, every round, which is an identity
and not a threshold.
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

PRE_MODULE = SRC / "network.py.expired_20260914_pre_A39"
A29_RECORD = RESULTS / "a29_maturity.json"

#: The sovereign station rounds what it records to six decimals, so the band
#: here is tied to that rounding and not to machine precision: two units in the
#: last recorded place, plus a relative term for the cross-build last digit that
#: A38 measured at 1.3e-15 on one machine and 0 on the other.
RECORD_BAND_ABS = 2e-6
RECORD_BAND_REL = 1e-9

#: The carrier this station runs, fixed here so the gate and the grid cannot
#: drift apart. Every field is one the sovereign station already ran.
KEY = dict(authority="endogenous", need=0.20, park=0.02, elasticity=0.5,
           landing="production", seed=0, route="levy", funding="levy",
           levy_base="equal", maturity=0.1, coupon=0.02)


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def compare(a, b) -> tuple[list[str], list[str]]:
    """Every field the two histories share, bitwise, plus the names only one has.

    Only the intersection, because a gate written against a frozen backup stops
    running the moment a later stage adds a field, which is when it is most
    needed. What fell outside is printed rather than dropped.
    """
    bad = []
    names_a = {f.name for f in dataclasses.fields(a)}
    names_b = {f.name for f in dataclasses.fields(b)}
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
    return bad, sorted(names_a ^ names_b)


def gate_configs(mod) -> list[tuple[str, object]]:
    """Off and on. Off is rule 19's question; on is where a perturbed draw or a
    misplaced line inside the debt service would show."""
    from a29_maturity import cell_config
    out: list[tuple[str, object]] = []
    C, S = mod.NetworkConfig, mod.NetworkSpec
    out.append(("bare default", C(rounds=60)))
    out.append(("bare seed 7", C(spec=S(seed=7), seed=7, rounds=60)))
    for base in ("equal", "threshold"):
        for fund in ("levy", "creditors", "issuance"):
            k = dict(KEY, levy_base=base, funding=fund, route=fund)
            out.append((f"{fund}/{base}", cell_config(k)))
    for width in (0.40, 1.00):
        k = dict(KEY)
        out.append((f"levy + width {width:.2f}",
                    dataclasses.replace(cell_config(k), edge_cut=EdgeCutSpec(
                        mode="self_cut", share=0.30, trigger=2.0,
                        cutter_share=width))))
    return out


def half_one(perturb: str | None) -> tuple[bool, list[str]]:
    """Rule 19: the default reproduces the module before the field, bitwise."""
    if not PRE_MODULE.exists():
        return False, [f"  FAIL no backup at {PRE_MODULE.name}"]
    old = _load(PRE_MODULE, "monetary_topology._network_pre_a39")
    import monetary_topology.network as new

    lines, ok, shown = [], True, False
    for (name, cfg_new), (_, cfg_old) in zip(gate_configs(new), gate_configs(old)):
        bad, only = compare(new.Network(cfg_new).run(), old.Network(cfg_old).run())
        ok = ok and not bad
        lines.append(f"  {'ok  ' if not bad else 'FAIL'} {name:22s} "
                     f"differing fields: {len(bad)}"
                     + (f"   {'; '.join(bad[:4])}" if bad else ""))
        if only and not shown:
            shown = True
            lines.append(f"       compared the fields both modules have; "
                         f"only one side carries {only}")
    return ok, lines


def half_two(perturb: str | None) -> tuple[bool, list[str]]:
    """The sovereign station's recorded cells come back on this module."""
    import monetary_topology.network as new
    from a29_maturity import KEY_FIELDS, one_cell

    if not A29_RECORD.exists():
        return False, [f"  FAIL no record at {A29_RECORD.name}"]
    rows = json.loads(A29_RECORD.read_text(encoding="utf-8"))["sections"]["run"]["rows"]
    want = [r for r in rows if r.get("funding") == "levy" and r.get("seed") == 0
            and r.get("elasticity") == 0.5 and r.get("park") == 0.02
            and r.get("landing") == "production" and r.get("maturity") == 0.1
            and r.get("coupon") == 0.02]
    if not want:
        return False, ["  FAIL no matching cell in the record"]
    exact = ("below_close", "books_close")
    within = ("circulating_close", "parked_close", "levied_total",
              "due_total", "support_tail", "volume_tail", "capitalized_total")
    lines, ok, worst, where = [], True, 0.0, None
    for r in want[:4]:
        key = {k: r[k] for k in KEY_FIELDS}
        got = one_cell(key)
        if perturb == "record":
            got = dict(got, levied_total=float(got["levied_total"]) * 1.01)
        bad = [k for k in exact if got[k] != r[k]]
        for k in within:
            a, b = float(got[k]), float(r[k])
            d = abs(a - b)
            rel = d / max(abs(b), 1.0)
            if rel > worst:
                worst, where = rel, (k, key["levy_base"], key["maturity"])
            if d > RECORD_BAND_ABS + RECORD_BAND_REL * abs(b):
                bad.append(f"{k} {a!r} vs {b!r}")
        ok = ok and not bad
        if bad:
            lines.append(f"  FAIL {key['levy_base']} mu {key['maturity']} "
                         f"cr {key['coupon']}   {bad[:3]}")
    lines.append(f"  {'ok  ' if ok else 'FAIL'} {len(want[:4])} cells against the "
                 f"sovereign record, worst relative difference {worst:.3e}"
                 + (f" at {where}" if where else ""))
    return ok, lines


def half_three(perturb: str | None) -> tuple[bool, list[str]]:
    """The identity: the per-node vector sums to the scalar already recorded.

    **An identity and not a threshold.** The two are the same sum written twice,
    so the only thing between them is the order the floats were added, and the
    residual is reported next to the bound it is being held to.
    """
    from a29_maturity import cell_config

    lines, ok = [], True
    for base in ("equal", "threshold"):
        for width in (None, 0.40, 1.00):
            cfg = cell_config(dict(KEY, levy_base=base))
            if width is not None:
                cfg = dataclasses.replace(cfg, edge_cut=EdgeCutSpec(
                    mode="self_cut", share=0.30, trigger=2.0, cutter_share=width))
            h = Network(cfg).run()
            got = h.levy_out
            if perturb == "stale" and got is not None:
                got = np.roll(got, 1, axis=0)
            if perturb == "missing":
                got = None
            if perturb == "scale" and got is not None:
                got = got * 0.5
            label = f"{base} width {'off' if width is None else f'{width:.2f}'}"
            if got is None:
                ok = False
                lines.append(f"  FAIL {label:24s} levy_out is None while a levy runs")
                continue
            scal = np.asarray(h.debt_levied, dtype=float)
            resid = float(np.abs(got.sum(axis=1) - scal).max())
            bound = 1e-9 * max(1.0, float(scal.max()))
            good = resid <= bound
            ok = ok and good
            lines.append(f"  {'ok  ' if good else 'FAIL'} {label:24s} "
                         f"max |rowsum - debt_levied| {resid:.3e} against {bound:.3e}"
                         f"   total {float(got.sum()):.4f}")
    # The route that takes nothing must record nothing, rather than zeros: a
    # field of zeros says a levy ran and took nothing, which is a different
    # statement from no levy having run.
    for fund in ("creditors", "issuance"):
        h = Network(cell_config(dict(KEY, funding=fund, route=fund))).run()
        good = h.levy_out is None
        ok = ok and good
        lines.append(f"  {'ok  ' if good else 'FAIL'} funding {fund:12s} "
                     f"levy_out is {'None' if h.levy_out is None else 'set'}")
    return ok, lines


def run_gate(perturb: str | None = None) -> bool:
    blocks = [("rule 19: the default reproduces the module before the field",
               half_one(perturb)),
              ("the sovereign station's recorded cells come back", half_two(perturb)),
              ("the identity: per node sums to the scalar already recorded",
               half_three(perturb))]
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
    for fault in ("stale", "missing", "scale", "record"):
        print(f"\n{'='*60}\n--- fault: {fault}")
        caught = not run_gate(perturb=fault)
        print(f"--- caught: {caught}")
        results.append(caught)
    print("\nselftest:", "PASS" if all(results) else "FAIL")
    return all(results)


# --------------------------------------------------------------------------
# the grid

#: Two bases. The sovereign station measured what each collects: the per-head
#: one got 0.3084 of what fell due and the progressive one all of it, so they
#: are two different machines and not two settings of one.
BASES = ("equal", "threshold")

#: Seven widths, dense at the low end. The reachability check measured the
#: count below the floor jumping from 75 to 150 at the first increment and
#: barely moving after, so the largest step is the first one.
WIDTHS = (0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00)

SEEDS = (0, 1, 2, 3, 4)

#: One depth and one carrier, each closed by a reading rather than a guess:
#: A38 read the sign as width-invariant across all three of its depths, and
#: read no direction at all on the carrier with no floor.
DEPTH = 0.30
TRIGGER = 2.0

TIMING = RESULTS / "a39_timing.json"
RECORD = RESULTS / "a39_levy_dodge.json"


def _cell_key(base: str, seed: int) -> dict:
    return dict(KEY, levy_base=base, seed=seed)


def one_cell(base: str, width: float | None, seed: int, ctrl_cache: dict) -> dict:
    """One treated run against its own twin, and the levy read per group."""
    from a29_maturity import cell_config

    key = (base, seed)
    if key not in ctrl_cache:
        ctrl_cache[key] = Network(cell_config(_cell_key(base, seed))).run()
    ctrl = ctrl_cache[key]

    cfg = cell_config(_cell_key(base, seed))
    if width is not None:
        cfg = dataclasses.replace(cfg, edge_cut=EdgeCutSpec(
            mode="self_cut", share=DEPTH, trigger=TRIGGER, cutter_share=width))
    net = Network(cfg)
    hist = net.run()

    n = len(hist.holdings[0])
    cut = (hist.cut_out.sum(axis=0) > 0 if hist.cut_out is not None
           else np.zeros(n, dtype=bool))
    will = net._will_cut
    will = np.ones(n, dtype=bool) if will is None else will
    idle = will & ~cut
    unwilling = ~will

    levy = hist.levy_out
    per = levy.sum(axis=0) if levy is not None else np.zeros(n)

    def mean_of(mask):
        return float(per[mask].mean()) if mask.any() else float("nan")

    starved = float(np.asarray(hist.starved)[-1])
    live = n - starved
    L = float(cut.sum()) / n
    due = float(np.asarray(hist.debt_due).sum())
    got = float(np.asarray(hist.debt_levied).sum())

    tail = max(1, hist.effective_support.size // 10)
    return {
        "base": base, "width": 0.0 if width is None else width, "seed": seed,
        "n": n, "n_cut": int(cut.sum()), "n_idle": int(idle.sum()),
        "n_unwilling": int(unwilling.sum()),
        # The levy each group carried, per node of that group. **Per node and
        # not per group total**: the groups are different sizes by construction,
        # so a total would answer how many there are rather than what each paid.
        "levy_cut": mean_of(cut), "levy_idle": mean_of(idle),
        "levy_unwilling": mean_of(unwilling), "levy_all": float(per.mean()),
        "n_live": live, "L": L,
        # The two candidate curves, both measured on this cell. Neither is a
        # threshold and neither is fitted: they are the two arithmetics the two
        # accounts each say the burden follows.
        "rival_curve": (1.0 / (1.0 - L)) if L < 1.0 else float("inf"),
        "ours_curve": (n / live) if live > 0 else float("inf"),
        "due_total": due, "levied_total": got,
        "collected": got / due if due > 0 else float("nan"),
        "support_ratio": (float(np.median(hist.effective_support[-tail:]))
                          / float(np.median(ctrl.effective_support[-tail:]))
                          if float(np.median(ctrl.effective_support[-tail:])) > 0
                          else float("nan")),
        "volume_ratio": (float(hist.total_volume.sum())
                         / float(ctrl.total_volume.sum())
                         if float(ctrl.total_volume.sum()) > 0 else float("nan")),
    }


def grid(smoke: bool = False):
    bases = BASES[:1] if smoke else BASES
    widths = (0.20, 1.00) if smoke else WIDTHS
    seeds = SEEDS[:1] if smoke else SEEDS
    # **The twin is a row too.** Every ratio here is against it, and a record
    # that carries only ratios cannot say what the twin itself did, so the
    # quantities the twin produced are reported alongside rather than left
    # implicit in a denominator.
    return ([(b, None, s) for b in bases for s in seeds]
            + [(b, w, s) for b in bases for w in widths for s in seeds])


def run_grid(smoke: bool = False) -> list[dict]:
    cells = grid(smoke)
    cache: dict = {}
    rows = []
    for i, (b, w, s) in enumerate(cells, 1):
        rows.append(one_cell(b, w, s, cache))
        if i % 10 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}", flush=True)
    return rows


def _sides(rows, base, key_a, key_b):
    """At each width, how many seeds put a above b, and how many below."""
    out = []
    for w in sorted({r["width"] for r in rows}):
        g = [r for r in rows if r["base"] == base and r["width"] == w]
        pairs = [(r[key_a], r[key_b]) for r in g
                 if not np.isnan(r[key_a]) and not np.isnan(r[key_b])]
        if not pairs:
            continue
        up = sum(1 for a, b in pairs if a > b)
        out.append((w, up, len(pairs) - up, len(pairs)))
    return out


# --------------------------------------------------------------------------
# criteria


def criteria(rows: list[dict]) -> list[dict]:
    c: list[dict] = []
    treated = [r for r in rows if r["width"] > 0]
    control = [r for r in rows if r["width"] == 0]

    # A39-1: does withdrawing reduce your own levy? Counts, no threshold.
    verdicts, shown = [], []
    for base in sorted({r["base"] for r in rows}):
        sides = _sides(treated, base, "levy_cut", "levy_unwilling")
        if not sides:
            verdicts.append((base, "no object")); continue
        agreed = [(w, "cut pays more" if u == k else "cut pays less")
                  for w, u, d, k in sides if u == 0 or u == k]
        split = [w for w, u, d, k in sides if 0 < u < k]
        if not agreed:
            v = f"Void: the seeds agree on no width, {len(split)} of {len(sides)} split"
        elif len({s for _, s in agreed}) == 1:
            v = (f"every width the seeds agree on says {agreed[0][1]}, "
                 f"{len(agreed)} of {len(sides)}"
                 + (f"; {len(split)} split at {split}" if split else "; none split"))
        else:
            v = f"the side the seeds agree on turns across widths {[w for w, _ in agreed]}"
        verdicts.append((base, v))
        body = []
        for w in sorted({r["width"] for r in treated}):
            g = [r for r in treated if r["base"] == base and r["width"] == w]
            if not g:
                continue
            def _m(k):
                v2 = [r[k] for r in g if not np.isnan(r[k])]
                return float(np.median(v2)) if v2 else float("nan")
            body.append(f"{w:.2f}:cut{_m('levy_cut'):.4f}/stay{_m('levy_unwilling'):.4f}")
        shown.append(f"{base}: " + " ".join(body))
    c.append(dict(name="A39-1  what the levy takes from the ones who withdrew "
                       "against the ones who would not",
                  kind="own_reading", passed=bool(verdicts),
                  detail=("; ".join(f"{b}: {v}" for b, v in verdicts)
                          + "  |  levy per node: " + "; ".join(shown))[:1800]))

    # A39-2: the rival's curve, scored against ours on the same cells.
    #
    # **Both curves are measured, neither is fitted, and nothing is compared to
    # a threshold.** Each is anchored on the lowest width actually run and the
    # comparison is in log distance, since both curves are multiplicative.
    #
    # **A cell can only score the two apart where they are apart.** At a small
    # withdrawn share both curves sit near one, so the difference between what
    # they predict is smaller than the spread the seeds produce, and a cell
    # there says nothing about either. That is gate six's question and its
    # answer is measured rather than declared: the floor at each width is the
    # spread of the observed ratio across seeds at that width, and a cell whose
    # two predictions differ by less than it is counted apart and scored for
    # neither side.
    # **Scored per base, not pooled.** The sovereign station measured the two
    # collecting 0.3084 and 1.0000 of what falls due, so they are two machines
    # and a count that adds their cells answers about neither. A39-3 was
    # registered on that same ground before this ran.
    lines, tally, below_floor = [], {}, 0
    per_width: dict = {}
    for base in sorted({r["base"] for r in rows}):
        widths = sorted({r["width"] for r in treated})
        if not widths:
            continue
        # The floor first, from the data: how far apart the seeds put the same
        # observed ratio at each width.
        obs_by_width: dict = {}
        for seed in sorted({r["seed"] for r in treated}):
            seq = [r for w in widths for r in treated
                   if r["base"] == base and r["width"] == w and r["seed"] == seed]
            seq = [r for r in seq if not np.isnan(r["levy_unwilling"])
                   and r["levy_unwilling"] > 0 and np.isfinite(r["rival_curve"])
                   and np.isfinite(r["ours_curve"])]
            if len(seq) < 3:
                continue
            a = seq[0]
            for r in seq[1:]:
                obs = r["levy_unwilling"] / a["levy_unwilling"]
                if obs > 0:
                    obs_by_width.setdefault(r["width"], []).append(np.log(obs))
        floor = {w: (float(np.std(v)) if len(v) > 1 else 0.0)
                 for w, v in obs_by_width.items()}

        tally.setdefault(base, [0, 0, 0, 0])
        for seed in sorted({r["seed"] for r in treated}):
            seq = [r for w in widths for r in treated
                   if r["base"] == base and r["width"] == w and r["seed"] == seed]
            seq = [r for r in seq if not np.isnan(r["levy_unwilling"])
                   and r["levy_unwilling"] > 0 and np.isfinite(r["rival_curve"])
                   and np.isfinite(r["ours_curve"])]
            if len(seq) < 3:
                continue
            a = seq[0]
            for r in seq[1:]:
                obs = r["levy_unwilling"] / a["levy_unwilling"]
                pr = r["rival_curve"] / a["rival_curve"]
                po = r["ours_curve"] / a["ours_curve"]
                if obs <= 0 or pr <= 0 or po <= 0:
                    continue
                gap = abs(np.log(pr) - np.log(po))
                slot = per_width.setdefault((base, r["width"]),
                                            [0, 0, 0, 0, gap, floor.get(r["width"], 0.0)])
                if gap <= floor.get(r["width"], 0.0):
                    below_floor += 1
                    tally[base][3] += 1
                    slot[3] += 1
                    continue
                dr = abs(np.log(obs) - np.log(pr))
                do = abs(np.log(obs) - np.log(po))
                if dr < do:
                    tally[base][1] += 1; slot[1] += 1
                elif do < dr:
                    tally[base][0] += 1; slot[0] += 1
                else:
                    tally[base][2] += 1; slot[2] += 1
        body = []
        for w in sorted({r["width"] for r in treated}):
            g = [r for r in treated if r["base"] == base and r["width"] == w]
            if not g:
                continue
            def _m(k):
                v2 = [r[k] for r in g if not np.isnan(r[k]) and np.isfinite(r[k])]
                return float(np.median(v2)) if v2 else float("nan")
            s = per_width.get((base, w))
            tag = (f"[{s[0]}ours/{s[1]}rival/{s[3]}underfloor "
                   f"gap {s[4]:.3f} floor {s[5]:.3f}]" if s else "")
            body.append(f"{w:.2f}:burden{_m('levy_unwilling'):.4f}"
                        f"/rival{_m('rival_curve'):.2f}/ours{_m('ours_curve'):.2f}{tag}")
        lines.append(f"{base}: " + " ".join(body))
    verdict_by_base, notes = {}, []
    for base, (n_ours, n_rival, n_tie, n_floor) in sorted(tally.items()):
        total = n_ours + n_rival + n_tie
        if total == 0:
            v = "no object"
            notes.append(f"{base}: Void, no cell can tell the two curves apart, "
                         f"{n_floor} below the floor")
        elif n_rival == 0:
            v = "B"
            notes.append(f"{base}: the rival's curve is the further one at every "
                         f"one of {total} cells that can tell them apart, "
                         f"{n_floor} more below the floor")
        elif n_ours == 0:
            v = "C"
            notes.append(f"{base}: the rival's curve is the closer one at every "
                         f"one of {total} cells that can tell them apart, "
                         f"{n_floor} below the floor")
        else:
            v = "mixed"
            notes.append(f"{base}: Void, mixed, {n_ours} closer to ours and "
                         f"{n_rival} to the rival of {total} that can tell them "
                         f"apart, {n_floor} below the floor")
        verdict_by_base[base] = v
    # **"mixed" names two different things and the first fix missed that.**
    # At the base level it means *this base returned no verdict*: some of its
    # cells sat nearer one curve and some nearer the other, and that base's own
    # note opens with Void. At the grid level it means *the bases landed in
    # different cells of the four-cell table*, which is a reading. The line
    # that set ``grid_cell`` read a base-level "mixed" and passed it straight
    # through as a grid-level one, so a criterion on which neither base could
    # tell the curves apart went out carrying an occupancy of two cells. Every
    # count printed normally and nothing reported it: the twelfth category
    # error, one identifier standing for two objects.
    #
    # The two void shapes at the base level are therefore "no object" (not one
    # cell could tell) and "mixed" (some each way). Neither occupies a cell.
    VOID_BASE = {"no object", "mixed"}
    decided = {b: v for b, v in verdict_by_base.items() if v not in VOID_BASE}
    cells = set(decided.values())
    if not verdict_by_base:
        grid_cell, passed = None, None
    elif not decided:
        # every base void: nothing was read into any cell
        grid_cell, passed = "unread", None
    elif "C" in cells:
        # the rival's curve is the closer one somewhere, and that is a reading
        # whichever way the other bases went
        grid_cell, passed = ("C" if cells == {"C"} else "mixed"), False
    elif len(decided) < len(verdict_by_base):
        # **B on what could be read, and the rest unread.** Not a pass: the
        # criterion is registered across the bases, so half the evidence
        # missing is the undecided state, which maps to neither verdict.
        grid_cell, passed = "B", None
    else:
        grid_cell, passed = "B", True
    unread = grid_cell in ("unread", None) or passed is None
    # **The criterion's own state goes first, in one sentence.** The failure
    # census reads a criterion by looking for a word anywhere in its detail, so
    # a detail that opens with one base's sub-verdict hands it that sub-verdict
    # as if it were the whole. Here both bases happen to be void and the count
    # is right either way; the sentence is put in front so it stays right when
    # one base has a verdict and the other does not.
    if passed:
        head = "the rival's curve is the further one on every base scored"
    elif "C" in cells:
        head = ("the rival's curve is the closer one on "
                + ", ".join(b for b, v in sorted(verdict_by_base.items())
                            if v == "C"))
    elif not decided:
        head = "Void: no base returned a verdict"
    else:
        head = ("Void: the rival's curve is the further one on "
                + ", ".join(sorted(decided))
                + " and no verdict holds on "
                + ", ".join(b for b in sorted(verdict_by_base) if b not in decided))
    note = head + "  |  " + "; ".join(notes)
    c.append(dict(name="A39-2  the per-head burden on the ones who stayed "
                       "does not follow the rival's curve",
                  kind="rival", passed=passed, grid=grid_cell,
                  # **Keyed by cell, because that is what a split is.** The
                  # first version keyed it by levy base, which is how the cells
                  # were grouped and not what they are; the guard for rule 11e
                  # said so on the first run. The per-base grouping keeps its
                  # own field and the detail keeps the full breakdown.
                  grid_split=({"B": sum(v[0] for v in tally.values()),
                               "C": sum(v[1] for v in tally.values())}
                              if grid_cell == "mixed" else None),
                  grid_note=({"B": f"not claimed: {sum(v[0] for v in tally.values())}"
                                   " cells sat nearer our curve and "
                                   f"{sum(v[1] for v in tally.values())} nearer the "
                                   "rival's, and the bases that returned no "
                                   "verdict are "
                                   + ", ".join(b for b, v in sorted(verdict_by_base.items())
                                               if v in VOID_BASE)
                                   + ", so neither count is an occupancy"}
                             if unread else None),
                  by_base=({b: {"ours": v[0], "rival": v[1], "tie": v[2],
                                "below_floor": v[3], "cell": verdict_by_base[b]}
                            for b, v in sorted(tally.items())} or None),
                  rival_shape="point prediction",
                  rival_premise="the burden to be absorbed is a fixed total "
                                "shared per head among those who have not "
                                "withdrawn",
                  rival_entailment="the per-head burden then goes as 1/(1-L) "
                                   "in the withdrawn share L, so the levy paid "
                                   "per node by those who stayed rises with L "
                                   "and diverges as L approaches one",
                  detail=(note + "  |  the two curves, both measured on these "
                          "cells, anchored on the lowest width run: " +
                          "; ".join(lines))[:2600]))

    # A39-3: the base is a machine, not a setting.
    body = []
    for base in sorted({r["base"] for r in rows}):
        ctl = [r for r in control if r["base"] == base]
        if ctl:
            def _c(k):
                v2 = [r[k] for r in ctl if not np.isnan(r[k])]
                return float(np.median(v2)) if v2 else float("nan")
            body.append(f"{base} twin: collected {_c('collected'):.4f} "
                        f"live {_c('n_live'):.0f} "
                        f"live per seed {[int(r['n_live']) for r in sorted(ctl, key=lambda x: x['seed'])]}")
        for w in sorted({r["width"] for r in rows}):
            g = [r for r in rows if r["base"] == base and r["width"] == w]
            if not g:
                continue
            def _m(k):
                v2 = [r[k] for r in g if not np.isnan(r[k])]
                return float(np.median(v2)) if v2 else float("nan")
            # **The seeds, not only their median.** The count still above the
            # floor comes back in one of two states here rather than on a
            # continuum, and a median of a two-state quantity is a number no
            # cell produced. Five seeds cannot separate a rate between two
            # states, so the states are printed and no rate is quoted.
            live = [int(r["n_live"]) for r in sorted(g, key=lambda x: x["seed"])]
            body.append(f"{base} {w:.2f}: collected {_m('collected'):.4f} "
                        f"live {live} sup {_m('support_ratio'):.3f} "
                        f"vol {_m('volume_ratio'):.3f}")
    c.append(dict(name="A39-3  what each levy base collects once some of the "
                       "graph has withdrawn", kind="own_reading", passed=True,
                  detail=("; ".join(body))[:1800]))
    return c


def selftest_criteria() -> bool:
    """11f: seed a fault into the rows and require each criterion to report it."""
    base_rows = []
    for b in BASES:
        for w in WIDTHS:
            for s in SEEDS:
                L = 0.9 * w
                base_rows.append(dict(
                    base=b, width=w, seed=s, n=200, n_cut=int(200 * L),
                    n_idle=2, n_unwilling=200 - int(200 * L) - 2,
                    levy_cut=1.0, levy_idle=1.0, levy_unwilling=1.0,
                    levy_all=1.0, n_live=100.0, L=L,
                    rival_curve=1.0 / (1.0 - L), ours_curve=2.0,
                    due_total=10.0, levied_total=5.0, collected=0.5,
                    support_ratio=0.9, volume_ratio=1.0))

    def pick(rows, nm):
        return [x for x in criteria(rows) if x["name"].startswith(nm)][0]

    ok = []
    rows = [dict(r, levy_cut=0.5) for r in base_rows]
    got = pick(rows, "A39-1")
    ok.append("cut pays less" in got["detail"])
    print(f"  cut pays less  -> A39-1 says {got['detail'][:46]!r}")

    rows = [dict(r, levy_cut=(0.5 if r["seed"] % 2 else 2.0)) for r in base_rows]
    got = pick(rows, "A39-1")
    ok.append("Void" in got["detail"])
    print(f"  seeds disagree -> A39-1 says {got['detail'][:46]!r}")

    # the rival's curve is exactly followed: the criterion must not pass
    rows = [dict(r, levy_unwilling=r["rival_curve"]) for r in base_rows]
    got = pick(rows, "A39-2")
    ok.append(not got["passed"] and got["grid"] == "C")
    print(f"  rival followed -> A39-2 passed={got['passed']} grid={got['grid']} "
          "(want False, C)")

    # ours is followed: the criterion must pass, and say the rival is further
    rows = [dict(r, levy_unwilling=r["ours_curve"] * (1 + 0.01 * r["width"]))
            for r in base_rows]
    got = pick(rows, "A39-2")
    ok.append(got["passed"] and got["grid"] == "B")
    print(f"  ours followed  -> A39-2 passed={got['passed']} grid={got['grid']} "
          "(want True, B)")

    # nothing to score
    rows = [dict(r, levy_unwilling=float("nan")) for r in base_rows]
    got = pick(rows, "A39-2")
    # **Not ``not passed``.** ``None`` is falsy, so the first version of this
    # line passed while the record went out carrying a verdict and a two-cell
    # split. The state has to be named.
    ok.append(got["passed"] is None and got["grid"] == "unread"
              and got["grid_split"] is None
              and "no cell can tell" in got["detail"])
    print(f"  no object      -> A39-2 passed={got['passed']} grid={got['grid']} "
          f"split={got['grid_split']} (want None, unread, None)")

    # **one base reads B and the other cannot tell.** Planted rather than
    # assumed reachable: the first version of the unread fix looked only for
    # "no object" and this shape never reached it, which is why the record went
    # out carrying a two-cell split on a criterion neither base had read.
    rows = [dict(r, levy_unwilling=(r["ours_curve"] * (1 + 0.01 * r["width"])
                                    if r["base"] == "equal"
                                    else (r["rival_curve"] if r["seed"] % 2
                                          else r["ours_curve"])))
            for r in base_rows]
    got = pick(rows, "A39-2")
    ok.append(got["passed"] is None and got["grid"] == "B"
              and got["grid_split"] is None
              and got["by_base"]["equal"]["cell"] == "B"
              and got["by_base"]["threshold"]["cell"] in ("mixed", "no object"))
    print(f"  half unread    -> A39-2 passed={got['passed']} grid={got['grid']} "
          f"by_base={ {b: v['cell'] for b, v in got['by_base'].items()} } "
          "(want None, B, one base void)")

    # **every base void by the "mixed" shape, not the "no object" shape.**
    # This is the case that actually occurs on the registered grid.
    rows = [dict(r, levy_unwilling=(r["rival_curve"] if r["seed"] % 2
                                    else r["ours_curve"]))
            for r in base_rows]
    got = pick(rows, "A39-2")
    ok.append(got["passed"] is None and got["grid"] == "unread"
              and got["grid_split"] is None
              and all(v["cell"] == "mixed" for v in got["by_base"].values()))
    print(f"  both void      -> A39-2 passed={got['passed']} grid={got['grid']} "
          f"split={got['grid_split']} "
          f"by_base={ {b: v['cell'] for b, v in got['by_base'].items()} } "
          "(want None, unread, None)")

    # the two bases disagree: one follows ours and the other the rival, so no
    # verdict holds across them and the pooled count would have hidden it
    rows = [dict(r, levy_unwilling=(r["ours_curve"] * (1 + 0.01 * r["width"])
                                    if r["base"] == "equal" else r["rival_curve"]))
            for r in base_rows]
    got = pick(rows, "A39-2")
    ok.append(not got["passed"] and got["grid"] == "mixed"
              and set(got["grid_split"]) == {"B", "C"}
              and got["by_base"]["equal"]["cell"] == "B"
              and got["by_base"]["threshold"]["cell"] == "C")
    print(f"  bases disagree -> A39-2 passed={got['passed']} grid={got['grid']} "
          f"split={got['grid_split']} "
          f"by_base={ {b: v['cell'] for b, v in got['by_base'].items()} } "
          "(want False, mixed, B and C)")
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
        t0 = time.time(); one_cell("equal", 0.40, 0, cache); t1 = time.time()
        one_cell("threshold", 0.40, 0, cache); t2 = time.time()
        per = {"equal_seconds": round(t1 - t0, 4),
               "threshold_seconds": round(t2 - t1, 4),
               "cells_total": len(grid()),
               "note": "measured, not assumed (D38). A run reads this file; "
                       "without it no hour figure may be quoted."}
        per["estimate_seconds"] = round(
            len(grid()) * (per["equal_seconds"] + per["threshold_seconds"]) / 2, 1)
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
            print(f"        {x['detail'][:500]}")
        if args.smoke or args.no_write:
            print("\n(smoke or --no-write: nothing written)")
            return 0
        rec = {"stage": "A39",
               "diagnostic_only": True,
               "diagnostic_reason": (
                   "Station not closed. This is the first carrier in the A "
                   "track that holds both a debt and a withdrawal, so the "
                   "per-head burden claim has an object here for the first "
                   "time; the write-off shape and the rest of the sovereign's "
                   "dimensions stay where they were measured."),
               "config": {"bases": list(BASES), "widths": list(WIDTHS),
                          "seeds": list(SEEDS), "depth": DEPTH,
                          "trigger": TRIGGER, "mode": "self_cut",
                          "carrier_key": KEY},
               "criteria": crit, "runs": rows}
        RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"\nwrote {RECORD}")
        return 0 if all(x["passed"] for x in crit) else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
