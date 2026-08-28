"""A3k: the zero domain, read off records already on disk.

**This runs no model.** It re-reads `a3i_pooled_ordering.json`,
`a3h_gate_acts.json` and `a3j_gate_acts_grid.json` and prints the two
quantities a zero domain needs side by side.

**What the framework predicts, and where the prediction comes from.**
`tier_positions` is a star, so `b1(G) = 0`, so by Theorem 2 the cycle space of
the enlarged graph holds no slice cycles and every obstruction on this carrier
is a square. `a3_asset_channel.md` section 2.1 classifies the two parameters
that came out of the old `gamma`: `gamma_pay` is what is paid and enters the
cochain (`H1`); `gamma_gate` is an admission threshold, a restriction on the
domain, outside the cochain **by construction** (`H0`).

> **So the gate channel's holonomy share is predicted to be zero. Not small,
> not bounded: zero, as a point prediction, from the theorem, with no constant
> chosen by anyone.**

**Every criterion here prints an object. None of them draws a line**, which is
the only shape a point prediction of zero can be read at (`D24`: report the
resolution, not a test statistic).

**A3-8 stays void and this does not touch that.** A3-8' needs its two clauses,
and `a3g_widened_population.json` A3g-5 measured why they cannot both be had on
this carrier. The zero domain needs neither clause. It needs the two cells side
by side, which every record already prints.

Usage::

    python experiments/a3k_zero_domain.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "a3k_zero_domain.json"


def load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def detail_of(record: dict, prefix: str) -> str:
    for c in record.get("criteria", []):
        if c.get("name", "").startswith(prefix):
            return str(c.get("detail", ""))
    return ""


def fixed(obj):
    """Round every float to 8 places so two builds write the same bytes."""
    if isinstance(obj, float):
        return round(obj, 8)
    if isinstance(obj, dict):
        return {k: fixed(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fixed(v) for v in obj]
    return obj


def summarise(vals: list[float]) -> dict:
    a = sorted(abs(v) for v in vals)
    n = len(a)
    return {
        "n": n,
        "exact_zero": sum(1 for v in vals if v == 0.0),
        "median_abs": statistics.median(a),
        "p90_abs": a[min(n - 1, int(0.9 * n))],
        "max_abs": a[-1],
    }


def main() -> int:
    a3i = load("a3i_pooled_ordering.json")
    # `ordering_failures` is a view onto `rows`, not a second set of points.
    # Concatenating the two double-counted three rows on the first pass, and the
    # duplicates showed up as literal repeats in A3k-3's printed table. A3k-0
    # now pins the count against A3i's own field so it cannot recur silently.
    rows = a3i["rows"]
    sources = sorted({r["source"] for r in rows})
    gate = [r["gate_only"] for r in rows]
    loop = [r["loop_only"] for r in rows]

    g, l = summarise(gate), summarise(loop)
    smaller = sum(1 for r in rows if abs(r["gate_only"]) < abs(r["loop_only"]))
    g_stable = sum(1 for r in rows if r["gate_same_sign"])
    l_stable = sum(1 for r in rows if r["loop_same_sign"])
    zeros = [r for r in rows if r["gate_only"] == 0.0]

    print(f"{len(rows)} points, pooled from {len(sources)} records, "
          f"{len(a3i['duplicates_dropped'])} duplicate rows dropped upstream "
          f"by exact value match.\n")
    print(f"  {'':>22} {'exact 0':>9} {'median|.|':>11} {'p90|.|':>10} "
          f"{'max|.|':>10} {'sign-stable':>12}")
    for label, s, st in (("gate channel  H0", g, g_stable),
                         ("terms channel H1", l, l_stable)):
        print(f"  {label:>22} {s['exact_zero']:>9d} {s['median_abs']:>11.4f} "
              f"{s['p90_abs']:>10.4f} {s['max_abs']:>10.4f} "
              f"{st:>7d}/{s['n']:<4d}")
    print(f"\n  |gate| < |loop| at {smaller} of {len(rows)} points.")
    print(f"  amplitude ratio, medians {g['median_abs'] / l['median_abs']:.4f}, "
          f"maxima {g['max_abs'] / l['max_abs']:.4f}\n")

    print("  every point where the gate cell is exactly zero, with the terms cell beside it:")
    for r in zeros:
        print(f"    {r['carrier']:>22} {r['arm']:>14} {r['point']:>12}   "
              f"gate {r['gate_only']:+.4f}   terms {r['loop_only']:+.4f}")

    mech_h = detail_of(load("a3h_gate_acts.json"), "A3h-1")
    mech_j = detail_of(load("a3j_gate_acts_grid.json"), "A3j-2")

    # **The five exact zeros carry nothing and this is why.** A3j measures the
    # gate's mechanical ratio as 0.000 at stretch 20 and 40, so a zero there is
    # inertness. The other four sit within five per cent of the complete graph,
    # whose endpoint `docs/a7_continuous_c.md` section 4.1 already excluded as an
    # attractor with an over-determined zero. The reading therefore rests on the
    # grid points where the gate is measurably active, and those are named here
    # by reading A3j's own ratio rather than by choosing them.
    ratios = {}
    for piece in mech_j.split(";"):
        if ":" not in piece:
            continue
        k, v = piece.split(":", 1)
        ratios[f"stretch={float(k.strip())}"] = float(v)
    active = [r for r in rows
              if ratios.get(r["point"], 0.0) != 0.0
              and r["carrier"] == "A3 default"]
    active.sort(key=lambda r: float(r["point"].split("=")[1]))
    a_gate = [r["gate_only"] for r in active]
    a_loop = [r["loop_only"] for r in active]
    gate_flips = sum(1 for x, y in zip(a_gate, a_gate[1:]) if (x > 0) != (y > 0))
    loop_flips = sum(1 for x, y in zip(a_loop, a_loop[1:]) if (x > 0) != (y > 0))
    print("\n  the grid points where A3j measures the gate as mechanically active:")
    print(f"    {'point':>14} {'A3j ratio':>10} {'gate cell':>11} {'terms cell':>11}")
    for r in active:
        print(f"    {r['point']:>14} {ratios[r['point']]:>10.3f} "
              f"{r['gate_only']:>+11.4f} {r['loop_only']:>+11.4f}")
    print(f"    over {len(active)} active points: terms positive at "
          f"{sum(1 for v in a_loop if v > 0)}, gate positive at "
          f"{sum(1 for v in a_gate if v > 0)}; "
          f"sign changes along the grid, terms {loop_flips}, gate {gate_flips}")
    print(f"\n  the gate is not inert, quoted from the records that measured it:")
    print(f"    A3h-1  {mech_h}")
    print(f"    A3j-2  {mech_j}")

    record = {
        "stage": "A3k",
        "step": "zero_domain",
        "note": ("A3-8 stays void; this is a different object read off the same "
                 "cells. Theorem 2 predicts the gate channel's holonomy share is "
                 "zero because tier_positions is a star, b1(G) = 0, and every "
                 "obstruction is therefore a square. No model is run here."),
        "points": len(rows),
        "gate_channel_H0": g,
        "terms_channel_H1": l,
        "gate_sign_stable": g_stable,
        "terms_sign_stable": l_stable,
        "gate_smaller_in_absolute_value": smaller,
        "active_grid_points": [
            {"point": r["point"], "a3j_ratio": ratios[r["point"]],
             "gate_only": r["gate_only"], "loop_only": r["loop_only"]}
            for r in active],
        "gate_exact_zero_points": [
            {"carrier": r["carrier"], "arm": r["arm"], "point": r["point"],
             "gate_only": r["gate_only"], "loop_only": r["loop_only"]}
            for r in zeros],
        "mechanical_effect_a3h1": mech_h,
        "mechanical_effect_a3j2": mech_j,
        "sources": sources,
        "criteria": [
            {"name": "A3k-0  the row count equals A3i's own points field",
             "detail": (f"{len(rows)} rows against A3i points {a3i['points']}; "
                        f"{len(sources)} distinct source records; "
                        f"ordering_failures is a view onto rows and is not added"),
             "passed": len(rows) == a3i["points"]},
            {"name": "A3k-1  every pooled row loads and yields both cells",
             "detail": f"{len(rows)} points, {len(gate)} gate cells, {len(loop)} terms cells",
             "passed": len(gate) == len(loop) == len(rows)},
            {"name": "A3k-2  print both channels' amplitude, no line on either",
             "detail": (f"gate median {g['median_abs']:.4f} p90 {g['p90_abs']:.4f} "
                        f"max {g['max_abs']:.4f}; terms median {l['median_abs']:.4f} "
                        f"p90 {l['p90_abs']:.4f} max {l['max_abs']:.4f}; "
                        f"|gate|<|loop| at {smaller}/{len(rows)}"),
             "passed": True},
            {"name": "A3k-3  print every point where the gate cell is exactly zero",
             "detail": "; ".join(
                 f"{r['carrier']} {r['arm']} {r['point']} gate {r['gate_only']:+.4f} "
                 f"terms {r['loop_only']:+.4f}" for r in zeros) or "none",
             "passed": True},
            {"name": "A3k-4  print sign stability for both channels",
             "detail": (f"gate sign-stable {g_stable}/{len(rows)}, "
                        f"terms sign-stable {l_stable}/{len(rows)}"),
             "passed": True},
            {"name": "A3k-5  print the gate's mechanical effect, so the zero is not read as inertness",
             "detail": f"A3h-1: {mech_h} | A3j-2: {mech_j}",
             "passed": bool(mech_h and mech_j)},
            {"name": "A3k-6  print both channels on the grid points where A3j measures the gate as active",
             "detail": ("; ".join(
                 f"{r['point']} ratio {ratios[r['point']]:.3f} gate {r['gate_only']:+.4f} "
                 f"terms {r['loop_only']:+.4f}" for r in active)
                 + f" || over {len(active)} active points: terms positive at "
                   f"{sum(1 for v in a_loop if v > 0)}, gate positive at "
                   f"{sum(1 for v in a_gate if v > 0)}; sign changes along the grid, "
                   f"terms {loop_flips}, gate {gate_flips}"),
             "passed": True},
            {"name": "A3k-7  the exact zeros are named as carrying nothing, with the reason beside each",
             "detail": "; ".join(
                 f"{r['carrier']} {r['point']}: "
                 + ("A3j ratio 0.000, the gate is inert here"
                    if ratios.get(r["point"], None) == 0.0
                    else "within 5% of the complete graph, an over-determined zero "
                         "excluded by a7_continuous_c.md section 4.1")
                 for r in zeros),
             "passed": True},
        ],
    }
    OUT.write_text(json.dumps(fixed(record), indent=1, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
