"""A7-B: probe P1, how much of a one-off transfer survives a generation, and
the rest of leg B.

Section 5.8 of `docs/a7_continuous_c.md` requires P1 and P2 to run and the
section 5.3 trigger to be decided before any `d(X, s)` is computed. P1 is the
default entry and `--check`. The same file runs P2 (`--p2`) and leg B's cells
(`--legb`) on the nine-point `GRID` below, the section 5.4 fence (`--fence`)
at its two endpoints, and the `I` and `M` switch cells at one point (`--im`).
Their verdicts are assembled by `experiments/a7_continuous_c.py --verdicts`.

Why this exists
---------------

Section 5.2 rules `I` and `M` unreadable for direction on this carrier, and the
whole ruling rests on one table in `docs/a4_causal_primitive.md` section 9: what
a one-off transfer leaves behind after a generation, `28.06%` on the stratified
arm and `0.00%` on the uniform one, moving in the same direction as the
amplification the leg would be claiming.

**That table has no producer in this repository.** `28.06` appears in three
markdown files and in no code and no stored record. The method is one sentence
under the table, and a sibling instrument exists, `_shock_trace` in
`experiments/a3_asset_channel.py`, but it runs `A3Model` and reads
`net_worth_history` while the table is about A2's transaction balance on A4's
carrier. So the ruling that removed half of leg B's competitors currently rests
on a memory.

This file is that measurement, built to the sentence under the table, and the
first thing it does is try to reproduce the table's own `C = 1` rows.

What the shock is, exactly
--------------------------

Copied from `_shock_trace` rather than from the prose, because the two differ in
a way that matters. The prose says ten per cent of the claim stock is injected
into one node. The code takes it **uniformly from every node first**, so the
stock is conserved and the operation is a transfer rather than an injection:

    gift = holdings.sum() * 0.10
    holdings -= gift / n
    holdings[target] += gift

Retention is the deviation of the target's path from its own unperturbed path,
divided by that deviation at the shock round.

What is not compared
--------------------

**The `s = 1` rung may not be read against the table's `C = 0` rows.** Section
2.4 measured that the two differ in five of six ways: only the adjacency
matches, while the payroll incidence, the routing, the propensities and the
opening holdings stay stratified here. Only the `s = 0` rung is a comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.mechanisms import (  # noqa: E402
    A4Config,
    A4Model,
    Switches,
    gini,
)
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402

RESULTS = ROOT / "results"

#: `experiments/a3_asset_channel.py` registers both. Reused rather than
#: re-chosen, so a difference between this probe and A3-6's reading cannot be a
#: difference of horizon.
SHOCK_ROUND = 150
HORIZON = 40

#: The fraction moved, from `_shock_trace`.
SHOCK_FRACTION = 0.10

#: Horizons reported, so the half-life and the table's two columns come out of
#: one trace rather than three runs.
REPORTED = (1, 2, 5, 10, 20, 40, 80)

#: `docs/a4_causal_primitive.md` section 9, the two rows this probe can be
#: compared against. The `C = 0` rows are deliberately absent: see the module
#: docstring.
SECTION_9_C1 = {
    "richest": {"half_life": 2, 10: 0.322, 40: 0.2806},
    "median": {"half_life": 5, 10: 0.002, 40: 0.0000},
}

#: Leg B's grid: nine of leg A's seventeen points. The registration says the
#: same grid as leg A; the eight points leg A has and this one does not are
#: 0.15, 0.3, 0.4, 0.6, 0.7, 0.8, 0.95 and 0.99, and "every grid point" in
#: the leg-B readings means these nine.
GRID: tuple[float, ...] = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 0.9, 1.0)

#: Section 5.4's cells. `I` and `M` are absent because section 5.2 rules them
#: unreadable for direction. Section 12.1 went further and said that above the
#: cliff they have nothing to transmit at all; that does not hold, and
#: ``im_point`` below is the reading that says so. They stay off this grid
#: on section 5.2's ruling. `E+K` runs as a diagnostic on the interaction and is not
#: scored, since section 5.5 registers criteria on `E` and `K` separately.
LEGB_CELLS: dict[str, dict] = {
    "none": {},
    "E": {"education": True},
    "K": {"capital": True},
    "E+K": {"education": True, "capital": True},
}


def _model(seed: int, rounds: int, s: float, arm: str) -> A4Model:
    """The A2 control: connectivity on, every competitor off.

    Section 9's table is about the carrier rather than about any mechanism, so
    the competitors are off. `Switches.demography_active` is then false and the
    demographic layer does not fire, which is what makes this the same economy
    the table describes.
    """
    spec = NetworkSpec(seed=seed, shortcut_rate=s, shortcut_mode=arm)
    return A4Model(
        A4Config(
            switches=Switches(connectivity=True),
            network=NetworkConfig(spec=spec, seed=seed, rounds=rounds),
        )
    )


def trace(seed: int, rounds: int, s: float, arm: str, target: int):
    """``(retention_by_horizon, deviation at the shock round)`` for one node."""
    base = _model(seed, rounds, s, arm)
    base_hist = np.asarray(base.run().holdings)

    shocked = _model(seed, rounds, s, arm)
    original = shocked._pre_round

    def hook(t: int, _m=shocked, _i=target, _pre=original) -> None:
        _pre(t)
        if t == SHOCK_ROUND:
            gift = _m.holdings.sum() * SHOCK_FRACTION
            _m.holdings -= gift / _m._n
            _m.holdings[_i] += gift

    shocked._pre_round = hook  # type: ignore[method-assign]
    shock_hist = np.asarray(shocked.run().holdings)

    dev = shock_hist[:, target] - base_hist[:, target]
    start = float(dev[SHOCK_ROUND])
    if start == 0.0:
        return {h: float("nan") for h in REPORTED}, start
    out = {}
    for h in REPORTED:
        at = min(SHOCK_ROUND + h, dev.size - 1)
        out[h] = float(dev[at] / start)
    return out, start


def half_life(retention: dict[int, float]) -> float:
    """First reported horizon at or below one half, or nan if it never gets
    there. Reported on the registered horizon grid rather than interpolated,
    because the table it is compared against gives whole rounds."""
    for h in REPORTED:
        v = retention[h]
        if v == v and v <= 0.5:
            return float(h)
    return float("nan")


def targets(seed: int, rounds: int, s: float, arm: str) -> dict[str, int]:
    """The richest and the median node **as of the shock round**.

    Ranked on the unperturbed path at the round the shock lands, which is the
    reading `_holders_at_shock` uses for its own population and the one the
    table's wording implies. Ranking at the opening would be a different
    selection and `docs/a5_reachability.md` section 8.2 is what a misplaced
    origin costs.
    """
    base = _model(seed, rounds, s, arm)
    hist = np.asarray(base.run().holdings)
    at = hist[SHOCK_ROUND]
    order = np.argsort(at)
    return {"richest": int(order[-1]), "median": int(order[order.size // 2])}


def run_point(seeds: range, rounds: int, s: float, arm: str) -> dict:
    rows: dict[str, dict] = {}
    for name in ("richest", "median"):
        per_seed, halves, layers = [], [], []
        for seed in seeds:
            tgt = targets(seed, rounds, s, arm)[name]
            ret, start = trace(seed, rounds, s, arm, tgt)
            per_seed.append(ret)
            halves.append(half_life(ret))
            spec = NetworkSpec(seed=seed, shortcut_rate=s, shortcut_mode=arm)
            layers.append("financial" if tgt < spec.layer1_size else "production")
        rows[name] = {
            "mean_by_horizon": {
                str(h): float(np.mean([r[h] for r in per_seed])) for h in REPORTED
            },
            "by_seed": [{str(h): r[h] for h in REPORTED} for r in per_seed],
            "half_life_mean": float(np.nanmean(halves)),
            "half_life_by_seed": halves,
            "target_layer": layers,
        }
    return {"s": s, "arm": arm, "nodes": rows}


def print_point(point: dict, compare: bool) -> None:
    print(f"\n  s = {point['s']}   arm {point['arm']}")
    for name, r in point["nodes"].items():
        m = r["mean_by_horizon"]
        line = (
            f"    {name:8s} half-life {r['half_life_mean']:5.2f}"
            f"   +10 {m['10']:+8.4f}   +40 {m['40']:+8.4f}"
            f"   +80 {m['80']:+8.4f}"
        )
        if compare:
            ref = SECTION_9_C1[name]
            line += (
                f"   || section 9: half-life {ref['half_life']}"
                f"   +10 {ref[10]:+.4f}   +40 {ref[40]:+.4f}"
            )
        print(line)
        if compare:
            d10 = m["10"] - SECTION_9_C1[name][10]
            d40 = m["40"] - SECTION_9_C1[name][40]
            verdict = (
                "reproduces" if abs(d10) < 0.02 and abs(d40) < 0.02
                else "DOES NOT REPRODUCE"
            )
            print(f"    {'':8s} {verdict}: +10 differs by {d10:+.4f},"
                  f" +40 by {d40:+.4f}")
        layers = set(r["target_layer"])
        print(f"    {'':8s} target layer across seeds: {sorted(layers)}")
        if compare:
            per = [d["40"] for d in r["by_seed"]]
            print(f"    {'':8s} +40 per seed: "
                  + " ".join(f"{v:+.4f}" for v in per))
            print(f"    {'':8s} +40 range [{min(per):+.4f}, {max(per):+.4f}]"
                  f"   seed 0 alone {per[0]:+.4f}"
                  f"   section 9 {SECTION_9_C1[name][40]:+.4f}")


def _effective_holders(h: np.ndarray) -> float:
    """`1 / HHI`, the effective number of holders. Threshold-free, and the
    measure `a4_causal_primitive.md` section 3 reports beside the Gini."""
    total = float(h.sum())
    if total <= 0.0:
        return float("nan")
    share = h / total
    return float(1.0 / float((share ** 2).sum()))


def p2_point(seeds: range, rounds: int, s: float, arm: str) -> dict:
    """P2: the control arm's level and its distance to the bound.

    Section 5.2 records that `E` and `K` are compressed by a ceiling: the
    control cell reaches a Gini of `0.935`, so a competitor under `C = 1` has
    `0.065` of room against `0.99` under `C = 0`, and section 11.3 of
    `a4_causal_primitive.md` measured that this compression alone is the
    difference between `A(K) = 0.06` and `A(K) = 5.31`. Leg B's registered
    outcome is `log(1/HHI)` for that reason, and this probe measures how much of
    the exposure survives the change of measure.

    **Room is directional.** Competitors raise the Gini, so its room is the
    distance up to the bound, which is `(n-1)/n` rather than one. Competitors
    lower the effective holder count, so its room is the distance down to a
    floor of one holder, which on the log scale is `log(1/HHI)` itself.
    """
    rows = []
    for seed in seeds:
        spec = NetworkSpec(seed=seed, shortcut_rate=s, shortcut_mode=arm)
        model = _model(seed, rounds, s, arm)
        hold = np.asarray(model.run().holdings)[-1]
        k = spec.layer1_size
        n = hold.size
        rows.append({
            "gini": gini(hold),
            "gini_prod": gini(hold[k:]),
            "log_inv_hhi": float(np.log(_effective_holders(hold))),
            "log_inv_hhi_prod": float(np.log(_effective_holders(hold[k:]))),
            "gini_bound": (n - 1) / n,
            "gini_bound_prod": (n - k - 1) / (n - k),
        })
    mean = {k2: float(np.mean([r[k2] for r in rows])) for k2 in rows[0]}
    return {
        "s": s, "arm": arm, "mean": mean, "by_seed": rows,
        "room_gini": mean["gini_bound"] - mean["gini"],
        "room_log_inv_hhi": mean["log_inv_hhi"],
        "room_gini_prod": mean["gini_bound_prod"] - mean["gini_prod"],
        "room_log_inv_hhi_prod": mean["log_inv_hhi_prod"],
    }


def _measures(hold: np.ndarray, k: int) -> dict:
    return {
        "gini": gini(hold),
        "gini_prod": gini(hold[k:]),
        "log_inv_hhi": float(np.log(_effective_holders(hold))),
        # Section 12.3's decision: this is leg B's primary outcome, because it
        # is the only one of the four whose room stays inside the registered
        # band across the grid.
        "log_inv_hhi_prod": float(np.log(_effective_holders(hold[k:]))),
    }


def legb_point(seeds: range, rounds: int, s: float, arm: str,
               pooling: str = "round") -> dict:
    """One grid point: every cell, and `d(X, s)` per seed against `none`.

    `d` is taken **within seed** against the same seed's control, so the graph
    draw cancels and what is left is the competitor.
    """
    per_cell: dict[str, list[dict]] = {}
    for name, flags in LEGB_CELLS.items():
        rows = []
        for seed in seeds:
            spec = NetworkSpec(seed=seed, shortcut_rate=s, shortcut_mode=arm)
            model = A4Model(
                A4Config(
                    switches=Switches(connectivity=True, **flags),
                    network=NetworkConfig(spec=spec, seed=seed, rounds=rounds),
                    pooling=pooling,
                )
            )
            rows.append(_measures(np.asarray(model.run().holdings)[-1],
                                  spec.layer1_size))
        per_cell[name] = rows

    keys = ("log_inv_hhi_prod", "log_inv_hhi", "gini_prod", "gini")
    out = {"s": s, "arm": arm, "pooling": pooling, "levels": {
        n: {k: float(np.mean([r[k] for r in rows])) for k in keys}
        for n, rows in per_cell.items()
    }, "d": {}}
    for name in ("E", "K", "E+K"):
        out["d"][name] = {}
        for k in keys:
            d = [per_cell[name][i][k] - per_cell["none"][i][k]
                 for i in range(len(per_cell["none"]))]
            out["d"][name][k] = {
                "mean": float(np.mean(d)),
                "by_seed": d,
                "range": [float(min(d)), float(max(d))],
                "n_positive": sum(1 for v in d if v > 0),
                "same_sign_across_seeds": bool(
                    all(v > 0 for v in d) or all(v < 0 for v in d)),
            }
    return out


#: Section 12.1 recorded `I` and `M` as having nothing to transmit above the
#: retention cliff and section 13.5 recorded them as not run for that reason.
#: These are the two switch cells that argument was about, put to the model at
#: one interior point so that the argument is a reading and not an inference.
IM_CELLS: dict[str, dict] = {
    "none": {},
    "I": {"inheritance": True},
    "M": {"mating": True},
}

#: Where the switch cells are read: `a7_continuous_c.PROBE_S`, interior and well
#: above the cliff in both arms.
IM_POINT = 0.5


def difference_block(cell: list[dict], control: list[dict], key: str) -> dict:
    """One measure, switch cell against control, within seed."""
    d = [c[key] - n[key] for c, n in zip(cell, control, strict=True)]
    return {
        "mean": float(np.mean(d)),
        "by_seed": d,
        "range": [float(min(d)), float(max(d))],
        "n_positive": sum(1 for v in d if v > 0),
        "n_negative": sum(1 for v in d if v < 0),
        "same_sign_across_seeds": bool(
            all(v > 0 for v in d) or all(v < 0 for v in d)),
    }


def im_point(seeds: range, rounds: int, s: float, arm: str) -> dict:
    """The `I` and `M` switch cells against `none`, at one grid point.

    **Not leg B's grid for `I` and `M`, which stays not run.** One point, to
    read whether the two switch cells differ from the control at all. Section
    12.1 argued they could not: a one-off transfer leaves nothing after a
    generation above the cliff, so a transmitting mechanism has nothing to
    transmit. What vanishes there is the memory of a perturbation. Holdings
    still circulate, and the demographic layer acts on current holdings.

    **What a difference here is, and what it is not.** `Switches.
    demography_active` is `inheritance or mating`, so switching either on also
    switches on households and generations, which pool and split holdings
    whether or not anything is inherited. A difference is the switch cell
    against the control. It is not an effect of inheritance or of mating alone,
    and no cell exists that has the demographic layer on and both channels off.
    """
    per_cell: dict[str, list[dict]] = {}
    finals: dict[str, list[np.ndarray]] = {}
    for name, flags in IM_CELLS.items():
        rows, ends = [], []
        for seed in seeds:
            spec = NetworkSpec(seed=seed, shortcut_rate=s, shortcut_mode=arm)
            model = A4Model(
                A4Config(
                    switches=Switches(connectivity=True, **flags),
                    network=NetworkConfig(spec=spec, seed=seed, rounds=rounds),
                )
            )
            end = np.asarray(model.run().holdings)[-1]
            ends.append(end)
            rows.append(_measures(end, spec.layer1_size))
        per_cell[name], finals[name] = rows, ends

    keys = ("log_inv_hhi_prod", "log_inv_hhi", "gini_prod", "gini")
    out: dict = {
        "s": s, "arm": arm,
        "levels": {
            n: {k: float(np.mean([r[k] for r in rows])) for k in keys}
            for n, rows in per_cell.items()
        },
        "final_holdings_differ_from_none": {},
        "d": {},
    }
    for name in ("I", "M"):
        out["final_holdings_differ_from_none"][name] = sum(
            1 for a, b in zip(finals[name], finals["none"], strict=True)
            if not np.array_equal(a, b)
        )
        out["d"][name] = {
            k: difference_block(per_cell[name], per_cell["none"], k)
            for k in keys
        }
    return out


def _rounded(obj):
    """Floats to ten significant figures, as `a7_continuous_c` writes them."""
    if isinstance(obj, (float, np.floating)):
        return float(format(float(obj), ".10g"))
    if isinstance(obj, dict):
        return {k: _rounded(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_rounded(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="s = 0 only, against section 9's C = 1 rows")
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--p2", action="store_true",
                    help="the room probe, section 5.3's second")
    ap.add_argument("--legb", action="store_true",
                    help="leg B proper, section 5.4")
    ap.add_argument("--fence", action="store_true",
                    help="section 5.4's pooling fence at the two endpoints")
    ap.add_argument("--im", action="store_true",
                    help="the I and M switch cells against the control, at one "
                         "point; leg B's grid for them stays not run")
    ap.add_argument("--s", type=float, default=IM_POINT,
                    help="the grid point --im reads")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--arm", choices=("uniform", "preferential"),
                    default="uniform")
    args = ap.parse_args()

    if args.im:
        print(
            f"\nI AND M  the two switch cells against the control at"
            f" s = {args.s}, arm {args.arm}, {args.seeds} seeds,"
            f" {args.rounds} rounds.\n  One point. Leg B's grid for `I` and `M`"
            f" stays not run. Switching either on also switches on\n  the"
            f" demographic layer, so a difference is the switch cell against the"
            f" control and not\n  an effect of inheritance or mating alone.\n"
        )
        p = im_point(range(args.seeds), args.rounds, args.s, args.arm)
        for name in ("I", "M"):
            d = p["d"][name]["log_inv_hhi_prod"]
            print(f"    {name}: final holdings differ from the control in "
                  f"{p['final_holdings_differ_from_none'][name]}/{args.seeds}"
                  f" seeds; production-layer log(1/HHI) {d['mean']:+.7f},"
                  f" range [{d['range'][0]:+.7f}, {d['range'][1]:+.7f}],"
                  f" negative in {d['n_negative']}/{args.seeds}")
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            f"a7b_im_switch.offparam_{args.arm}_{args.seeds}x{args.rounds}.json")
        out.write_text(json.dumps(_rounded(
            {"stage": "A7-B I and M switch cells", "diagnostic_only": True,
             "diagnostic_reason":
                 "one grid point, read to test the argument that I and M have "
                 "nothing to act on above the retention cliff; it scores "
                 "nothing and leg B's grid for I and M stays not run",
             "what_a_difference_is": (
                 "the switch cell against the control. Either switch also "
                 "turns on the demographic layer, so it is not an effect of "
                 "inheritance or of mating alone"),
             "primary_outcome": "log_inv_hhi_prod",
             "seeds": args.seeds, "rounds": args.rounds, "point": p}),
            indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        print(f"\n  written: {out.name}\n")
        return 0

    if args.fence:
        print("\nFENCE  section 5.4: `pooling = generation` at the two"
              " endpoints.\n  `pooling` is read only where the demographic"
              " layer fires, and leg B's cells keep\n  `I` and `M` off, so this"
              " has to be a bitwise no-op. Verified rather than argued.\n")
        ok = True
        for s in (0.0, 1.0):
            a = legb_point(range(args.seeds), args.rounds, s, args.arm, "round")
            b = legb_point(range(args.seeds), args.rounds, s, args.arm,
                           "generation")
            same = all(
                a["levels"][n][k] == b["levels"][n][k]
                for n in LEGB_CELLS for k in a["levels"]["none"]
            )
            ok &= same
            print(f"  s = {s}: identical across pooling  {same}")
        print(f"\n  {'no-op confirmed' if ok else 'POOLING MOVED SOMETHING'}\n")
        return 0

    if args.legb:
        print(f"\nLEG B  section 5.4, {args.seeds} seeds, {args.rounds}"
              f" rounds, arm {args.arm}."
              f"\n  Primary outcome is the production-layer-only log(1/HHI),"
              f" per section 12.3.\n")
        print("    s      d(E) prim   [n+/N, same]      d(K) prim   [n+/N, same]"
              "     d(E+K) prim")
        rows = []
        for s in GRID:
            p = legb_point(range(args.seeds), args.rounds, s, args.arm)
            f = lambda n: p["d"][n]["log_inv_hhi_prod"]
            print(f"  {s:<5}  {f('E')['mean']:+9.5f}"
                  f"  [{f('E')['n_positive']:2d}/{args.seeds},"
                  f"{'Y' if f('E')['same_sign_across_seeds'] else 'n'}]"
                  f"     {f('K')['mean']:+9.5f}"
                  f"  [{f('K')['n_positive']:2d}/{args.seeds},"
                  f"{'Y' if f('K')['same_sign_across_seeds'] else 'n'}]"
                  f"     {f('E+K')['mean']:+9.5f}")
            rows.append(p)
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            f"a7b_legb.offparam_{args.arm}_{args.seeds}x{args.rounds}.json")
        out.write_text(json.dumps(
            {"stage": "A7-B leg B", "diagnostic_only": True,
             "diagnostic_reason":
                 "verdicts are written in docs/a7_continuous_c.md; this record "
                 "is the measurement behind them and is not a RESULTS heading "
                 "until the stage closes",
             "primary_outcome": "log_inv_hhi_prod",
             "seeds": args.seeds, "rounds": args.rounds, "rows": rows},
            indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        print(f"\n  written: {out.name}\n")
        return 0

    if args.p2:
        print(
            f"\nP2  room in the control arm, {args.seeds} seeds,"
            f" {args.rounds} rounds, arm {args.arm}.\n"
        )
        print("    s      Gini   room    log(1/HHI) room"
              "   |  prod: Gini   room    log    room")
        rows = []
        for s in GRID:
            p = p2_point(range(args.seeds), args.rounds, s, args.arm)
            m = p["mean"]
            print(f"  {s:<5}  {m['gini']:.4f}  {p['room_gini']:.4f}"
                  f"    {m['log_inv_hhi']:.4f}   {p['room_log_inv_hhi']:.4f}"
                  f"   |  {m['gini_prod']:.4f}  {p['room_gini_prod']:.4f}"
                  f"   {m['log_inv_hhi_prod']:.4f}  {p['room_log_inv_hhi_prod']:.4f}")
            rows.append(p)
        base = rows[0]
        print("\n  room relative to s = 0, which is what the section 5.3"
              " trigger reads:")
        for key in ("room_gini", "room_log_inv_hhi", "room_gini_prod",
                    "room_log_inv_hhi_prod"):
            line = "".join(f"  {r['s']}:{r[key] / base[key]:5.2f}"
                           for r in rows) if base[key] else ""
            print(f"    {key:24s}{line}")
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            f"a7b_p2_room.offparam_{args.arm}_{args.seeds}x{args.rounds}.json")
        out.write_text(json.dumps(
            {"stage": "A7-B P2 room", "diagnostic_only": True,
             "diagnostic_reason":
                 "a section 5.3 probe; it gates and scores nothing",
             "seeds": args.seeds, "rounds": args.rounds, "rows": rows},
            indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        print(f"\n  written: {out.name}\n")
        return 0

    if not (args.check or args.grid):
        ap.print_help()
        return 2

    print(
        f"\nP1  retention of a one-off transfer, {args.seeds} seeds,"
        f" {args.rounds} rounds."
        f"\n  Shock at round {SHOCK_ROUND}: {SHOCK_FRACTION:.0%} of the stock"
        f" taken uniformly and given to one node,\n  so the stock is conserved"
        f" and this is a transfer. Retention is the target's deviation\n  from"
        f" its own unperturbed path, over that deviation at the shock round.\n"
    )

    points = [0.0] if args.check else list(GRID)
    rows = []
    for s in points:
        p = run_point(range(args.seeds), args.rounds, s, args.arm)
        print_point(p, compare=(s == 0.0))
        rows.append(p)

    if args.check:
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / (
            f"a7b_p1_check.offparam_{args.arm}_{args.seeds}x{args.rounds}.json"
        )
        out.write_text(
            json.dumps(
                {
                    "stage": "A7-B P1 check against a4 section 9",
                    "diagnostic_only": True,
                    "diagnostic_reason": (
                        "a reproduction check for a table that has no producer "
                        "in the repository; it scores nothing"
                    ),
                    "shock_round": SHOCK_ROUND,
                    "shock_fraction": SHOCK_FRACTION,
                    "seeds": args.seeds,
                    "rounds": args.rounds,
                    "section_9_c1_reference": {
                        k: {str(kk): vv for kk, vv in v.items()}
                        for k, v in SECTION_9_C1.items()
                    },
                    "measured": rows[0],
                },
                indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\n  written: {out.name}")
        print(
            "\n  If the two rows do not reproduce, stop. Either this is built"
            " wrong, or section 9's\n  table is older than the code that would"
            " produce it, and this repository has hit the\n  second case three"
            " times today. Section 5.2's ruling on `I` and `M` rests on it"
            " either way.\n"
        )
        return 0

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / (
        f"a7b_p1_retention.offparam_{args.arm}_{args.seeds}x{args.rounds}.json"
    )
    payload = {
        "stage": "A7-B P1 retention",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "a probe registered in section 5.3 to run before anything is "
            "scored; it decides readability and scores nothing"
        ),
        "shock_round": SHOCK_ROUND,
        "shock_fraction": SHOCK_FRACTION,
        "seeds": args.seeds,
        "rounds": args.rounds,
        "rows": rows,
    }
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\n  written: {out.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
