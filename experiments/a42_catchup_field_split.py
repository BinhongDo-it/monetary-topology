"""A42: with the field forced exact, does the pair still read what A40 read?

A40 started two graphs apart on one number, joined them, and printed which gaps
close. A22 forced ``w = d phi`` on A3's carrier and found that the whole
holonomy carries `1.33%` of the support contraction there, the graph carrying
the rest. Catch-up is a different phenomenon and the split between the two
channels can be different, so this runs A40's reading on both arms.

**Numbered A42.** A40 and A41 were taken the same day, A41 by another line
(`a41_same_ticket`). Discipline 20's five greps were run before the number was
used; `A42` and `a42_` are zero across both repositories.

**Two pieces of machinery are imported and neither is rewritten.** The pair and
its clearing boundary come from A25, so this settles the boundary with the same
code and the same conservation assertion. The treatment is A22's, three knobs
together, because `kappa = 0` also lowers the mean acquisition cost and without
holding that the flat cell is also the cheap cell.

**Half of this station cannot fail and says so.** The treated arm's holonomy is
zero by algebra, so reading it back is a structural check on the wiring, not a
finding. The reading is whether A40's gaps survive.

    python experiments/a42_catchup_field_split.py --selftest
    python experiments/a42_catchup_field_split.py --run
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
from a3_asset_channel import loop_sum_from_graph, terms_pair  # noqa: E402
from monetary_topology.asset import A3Config, A3Model, AssetSpec  # noqa: E402
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # dataclass resolves annotations through here
    spec.loader.exec_module(mod)
    return mod


A25 = _load("a25", ROOT / "experiments" / "a25_boundary.py")

OUT = ROOT / "results" / "a42_catchup_field_split.json"

#: The registered spread, read off the dataclass so the control arm cannot
#: drift away from the registered configuration without anyone noticing.
KAPPA_REF = AssetSpec().terms_spread
#: The only value at which the field is exact. Not tuned.
KAPPA_FLAT = 0.0

ROUNDS = 80
SEEDS = (0, 1, 2, 3, 4)
#: **Widened after the first run, and the reason is on the record.** At widths
#: up to 0.10 the boundary moved the level gap by 0.032 against a seed spread of
#: 0.044 on this carrier: the move sat inside the floor, so the split between
#: the two channels was a ratio of two quantities that were both noise. The A3
#: carrier's seed dispersion is twenty times the plain one's, which is why A40
#: could read the same move and this could not. Discipline 12 says buy that with
#: a design change rather than with repetitions, and the move scales with the
#: width, so the width is what moves.
WIDTHS = (0.0, 0.10, 0.25, 0.40)
LAG = 0.5
TAIL = 15

GAPS = {
    "level": lambda h: np.asarray(h.total_volume, float),
    "support": lambda h: np.asarray(h.effective_support, float),
    "layer1_volume": lambda h: np.asarray(h.layer1_volume, float),
}

#: A22's treatment, all three knobs. ``kappa = 0`` alone would also make the
#: flat cell the cheap cell, and the gate is pinned so one switch cannot move
#: both who pays what and who may enter at the opening. The pricing pool
#: still follows the payment terms, so the treatment levels it too.
TREATED = {"terms_spread": KAPPA_FLAT, "hold_mean_cost": True,
           "mean_cost_reference": KAPPA_REF, "gate_spread": KAPPA_REF}


def cfg(seed: int, claims: float, **asset_kw) -> A3Config:
    return A3Config(
        asset=AssetSpec(**asset_kw),
        network=NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed,
                              rounds=ROUNDS, initial_claims=claims))


def pair(seed: int, width: float, treated: bool):
    kw = dict(TREATED) if treated else {}
    g1, g2, hist = A25.run_pair(cfg(seed, 100.0, **kw), cfg(seed, 100.0 * LAG, **kw),
                                A25.BoundarySpec(width=width), rounds=ROUNDS,
                                network_cls=A3Model)
    gaps = {}
    for name, f in GAPS.items():
        a, b = f(g1._history), f(g2._history)
        n = min(len(a), len(b)); a, b = a[:n], b[:n]
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        d = np.full(n, np.nan); d[ok] = np.log(a[ok]) - np.log(b[ok])
        gaps[name] = d
    return g1, g2, hist, gaps


def holonomy_of(model) -> float:
    better, worse = terms_pair(model)
    _, h, _ = loop_sum_from_graph(model, better, worse)
    return float(h)


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    crit, report = [], {}

    # ---- A42-0 the boundary shut is two solo runs (rule 19)
    worst, fields = 0.0, 0
    for seed in SEEDS[:2]:
        g1, g2, _, _ = pair(seed, 0.0, treated=False)
        for g, claims in ((g1, 100.0), (g2, 100.0 * LAG)):
            solo = A3Model(cfg(seed, claims)).run()
            for k in ("total_volume", "effective_support", "layer1_volume",
                      "active_nodes", "layer2_reached"):
                a = np.asarray(getattr(solo, k), float)
                b = np.asarray(getattr(g._history, k), float)
                if a.shape != b.shape:
                    continue
                fields += 1
                d = np.abs(a - b); d = d[np.isfinite(d)]
                if d.size:
                    worst = max(worst, float(d.max()))
    crit.append(_crit(
        "A42-0  the boundary shut is two graphs that never met, on this carrier",
        "instrument", worst < 1e-12,
        f"two seeds, both sides, {fields} series against the same configuration run "
        f"alone: worst absolute difference {worst:.3e}. Rule 19."))
    report["default_off"] = {"worst": worst, "series": fields}

    # ---- A42-1 the treatment does what it says (structural, cannot fail)
    hol = {"control": [], "treated": []}
    for seed in SEEDS:
        for tag, tr in (("control", False), ("treated", True)):
            g1, _, _, _ = pair(seed, 0.0, treated=tr)
            hol[tag].append(holonomy_of(g1))
    hc = np.array(hol["control"]); ht = np.array(hol["treated"])
    report["holonomy"] = {"control": hol["control"], "treated": hol["treated"]}
    crit.append(_crit(
        "A42-1  the treated arm's field is exact",
        "instrument", float(np.abs(ht).max()) < 1e-12,
        f"structural, and it cannot fail: the treated holonomy is zero by the algebra "
        f"that defines the treatment, so this checks the wiring and reads nothing about "
        f"the world. Treated: {np.abs(ht).max():.3e} worst over {len(ht)} seeds. "
        f"Control: mean {hc.mean():.6f}, sd {hc.std():.6f}, per seed "
        + ", ".join(f"{x:.4f}" for x in hc) + "."))

    # ---- A42-2 the reading: does A40's table survive the treatment
    rows = []
    for tag, tr in (("control", False), ("treated", True)):
        for width in WIDTHS:
            for seed in SEEDS:
                _, _, _, gp = pair(seed, width, treated=tr)
                for name, d in gp.items():
                    fin = d[np.isfinite(d)]
                    if fin.size < TAIL + 2:
                        continue
                    rows.append({"arm": tag, "width": width, "seed": seed, "gap": name,
                                 "open": float(fin[0]),
                                 "close": float(np.median(fin[-TAIL:]))})
    report["gap_rows"] = rows

    summ = {}
    for name in GAPS:
        for tag in ("control", "treated"):
            for width in WIDTHS:
                sel = [r for r in rows if r["gap"] == name and r["arm"] == tag
                       and r["width"] == width]
                if sel:
                    c = np.array([r["close"] for r in sel])
                    summ.setdefault(name, {}).setdefault(tag, {})[str(width)] = {
                        "open": float(np.median([r["open"] for r in sel])),
                        "close": float(np.median(c)), "sd": float(np.std(c))}
    report["gap_summary"] = summ

    lines, carried = [], {}
    for name in GAPS:
        s = summ.get(name)
        if not s:
            continue
        c0, t0 = s["control"]["0.0"]["close"], s["treated"]["0.0"]["close"]
        cw = s["control"][str(WIDTHS[-1])]["close"]
        tw = s["treated"][str(WIDTHS[-1])]["close"]
        move_c, move_t = cw - c0, tw - t0
        # **A ratio, not a share.** The first version reported "the field carries
        # x% of the move" as 1 - treated/control, and the answer came out
        # negative, which is a sign that the quantity was the wrong shape: the
        # treated arm moves MORE, so there is no share of anything to report.
        # The ratio says what happened without pretending to decompose it.
        frac = (move_t / move_c) if abs(move_c) > 1e-12 else float("nan")
        carried[name] = {"control_shut": c0, "treated_shut": t0,
                         "control_widest": cw, "treated_widest": tw,
                         "control_move": move_c, "treated_move": move_t,
                         "treated_over_control_move": frac,
                         "floor_sd_control": s["control"]["0.0"]["sd"]}
        fl = s["control"]["0.0"]["sd"]
        lines.append(f"{name}: the boundary moves the gap {move_c:+.4f} with the field "
                     f"live and {move_t:+.4f} with it forced exact, a ratio of "
                     f"{frac:+.2f}, against a seed floor of {fl:.4f} which the control "
                     f"move clears {abs(move_c)/max(fl,1e-12):.1f} times over")
    report["field_share"] = carried
    crit.append(_crit(
        "A42-2  how much of what the boundary does is carried by the field",
        "own_reading", None,
        "Void: printed, not adjudicated, because no criterion was registered on the "
        "size of the split before the run. A22 read the field's share of the support "
        "contraction at 1.33% on one graph; this asks what forcing the field exact does "
        "to what a clearing boundary achieves between two. **The answer is not a share: "
        "the treated arm moves more, so the field is not carrying the convergence, it "
        "is standing against it.** " + " | ".join(lines)
        + ". Floor measured from the seed spread at a shut boundary, where nothing "
          "crossed and so nothing should have moved."))

    crit.append(_crit(
        "A42-3  what this does not settle", "bookkeeping", True,
        "it does not say catch-up is or is not carried by the field in general: one "
        "carrier, one way of starting the pair apart, three widths. And half of it is "
        "structural by construction. A40's registered arm is now run and this is what "
        "it returned."))

    record = {"stage": "A42",
              "config": {"rounds": ROUNDS, "seeds": list(SEEDS), "widths": list(WIDTHS),
                         "lag_share_of_claims": LAG, "tail": TAIL,
                         "kappa_reference": KAPPA_REF, "kappa_flat": KAPPA_FLAT,
                         "treatment": TREATED, "carrier": "A3 asset channel, paired",
                         "pair_machinery": "a25_boundary.run_pair",
                         "boundary_swing": A25.SWING_HISTORICAL, "gaps": list(GAPS)},
              "criteria": crit, "report": report}
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:520]}\n")
    print("  gap closings, log lead over lag, control against treated")
    print(f"     {'gap':>14}  {'arm':>8} " + " ".join(f"{('w=%g'%w):>9}" for w in WIDTHS))
    for name in GAPS:
        if name not in summ:
            continue
        for tag in ("control", "treated"):
            print(f"     {name:>14}  {tag:>8} "
                  + " ".join(f"{summ[name][tag][str(w)]['close']:>9.3f}" for w in WIDTHS))
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nrecord -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


def selftest():
    ok = []
    g1, _, _, gp = pair(0, 0.0, treated=False)
    fin = gp["level"][np.isfinite(gp["level"])]
    ok.append(fin.size > TAIL and abs(fin[0]) > 0.1)
    print(f"  the pair starts apart      -> opening level gap {fin[0]:+.3f}")

    hc = holonomy_of(g1)
    g1t, _, _, _ = pair(0, 0.0, treated=True)
    ht = holonomy_of(g1t)
    ok.append(abs(hc) > 1e-6 and abs(ht) < 1e-12)
    print(f"  control holonomy {hc:+.5f}, treated {ht:+.3e}  (want nonzero, then zero)")

    # the treatment has to change the run, or the arm is a no-op wearing a name
    a = np.asarray(g1._history.total_volume, float)
    b = np.asarray(g1t._history.total_volume, float)
    n = min(len(a), len(b))
    moved = float(np.abs(a[:n] - b[:n]).max())
    ok.append(moved > 1e-9)
    print(f"  the treatment moves the run -> worst volume difference {moved:.4f}")

    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(selftest() if a.selftest else run(write=not a.no_write))
