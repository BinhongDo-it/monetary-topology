"""A37 probe: what the eight widening cells are actually reading.

A37-6 came back mixed on the full grid, 262 cells down and 8 up. The eight
share two marks that no other cell has: their treated support reads exactly
75.000, and their flow is two to three percent of their twin's. An exact
round number repeated across eight independent seeds is not a measurement of
anything, so this file opens the object rather than the count (rule 11).

    python experiments/a37_probe_widen.py

It writes nothing. Its readings belong in the station's result file.
"""
from __future__ import annotations
import sys, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "experiments")]

import dataclasses  # noqa: E402
from monetary_topology.network import Network, EdgeCutSpec  # noqa: E402
from a17_edge_cut import base_config  # noqa: E402

#: Two of the eight, and one contracting cell next to them for contrast.
CELLS = [(0.2, 8.0, 0.5, 0, "widens"), (0.0, 2.0, 0.7, 4, "widens"),
         (0.2, 8.0, 0.5, 1, "contracts")]


def run(need, trigger, share, seed, treated=True):
    cfg = base_config(seed, need=need)
    cfg = dataclasses.replace(cfg, snapshot_every=10)
    if treated:
        cfg = dataclasses.replace(
            cfg, edge_cut=EdgeCutSpec(mode="self_cut", share=share, trigger=trigger))
    return Network(cfg).run()


def describe(hist, label):
    tail = max(1, hist.effective_support.size // 10)
    sup = float(np.median(hist.effective_support[-tail:]))
    rounds = sorted(r for r in hist.snapshots if r >= hist.effective_support.size - tail)
    if not rounds:
        print(f"  {label}: no snapshot in the tail"); return
    r = rounds[-1]
    inflow = np.asarray(hist.snapshots[r]).sum(axis=0)
    live = inflow[inflow > 0]
    share = live / live.sum() if live.size else live
    print(f"  {label}: support(tail median)={sup:.3f}  snapshot round {r}")
    print(f"      nodes with inflow > 0: {live.size}")
    if live.size:
        print(f"      inflow min/max/mean: {live.min():.6f} / {live.max():.6f} / "
              f"{live.mean():.6f}   max/min = {live.max() / live.min():.6f}")
        print(f"      1/HHI of this snapshot: {1.0 / np.square(share).sum():.6f}")
        print(f"      distinct inflow values (6 dp): "
              f"{len(set(np.round(live, 6).tolist()))}")
    print(f"      wage owed/paid this round: {hist.wage_owed[r-1]:.4f} / "
          f"{hist.wage_paid[r-1]:.4f}   total flow: {hist.total_volume[r-1]:.4f}")


def main() -> int:
    for need, trig, share, seed, tag in CELLS:
        print(f"\nneed {need} trigger {trig} share {share} seed {seed}  ({tag})")
        describe(run(need, trig, share, seed, treated=False), "control")
        describe(run(need, trig, share, seed, treated=True), "treated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
