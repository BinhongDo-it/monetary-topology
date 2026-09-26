"""A31's side probe: what the three positions leave behind, node by node.

A31-3 read the same integer difference in the count below the floor under all
three positions, in every cell and every seed. This is the diagnostic behind
that: on one cell it prints the closing distribution itself, so the reason is
on the record rather than in an argument. Spending is pro rata to what an
account holds and so is the withdrawal, so a position changes the level of the
stock and the trade mixes the shape back within rounds.

One cell, four runs, a few seconds:

    python experiments/a31_mixing_probe.py --run

``--no-write`` prints and writes nothing.
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
SRC = ROOT / "src" / "monetary_topology"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import WithdrawSpec  # noqa: E402

RECORD = RESULTS / "a31_mixing_probe.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A31 = _load(ROOT / "experiments" / "a31_withdrawal.py", "_a31_for_probe")

#: The cell A31-3's one block move sits on, and the seed that loses it.
CELL = {"need": 0.20, "stress": "leak_recycled", "elasticity": 0.5,
        "position": "none", "gain": None, "shock": "none", "size": 0.0,
        "seed": 1}
RULES = (("none", None), ("financial", 1.0), ("proportional", 1.0),
         ("production", 1.0))
TAIL = _A31.TAIL


def probe() -> dict:
    runs = {}
    for position, gain in RULES:
        key = dict(CELL, position=position, gain=gain)
        net, _ = _A31.drive(_A31.cell_config(key), "none", 0.0)
        hold = np.asarray(net._history.holdings, dtype=float)[-TAIL:].mean(axis=0)
        runs[position] = {
            "tail": hold,
            "total": float(hold.sum()),
            "layer2_share_of_stock": float(hold[net._l2].sum() / hold.sum()),
            "below_close": int(net._below.sum()),
            "withdrawn_total": float(0.0 if net._history.withdrawn is None
                                     else np.asarray(net._history.withdrawn).sum()),
        }
    out = {"cell": {k: v for k, v in CELL.items()
                    if k in ("need", "stress", "elasticity", "seed")},
           "tail": TAIL, "runs": {}, "against_financial": {}}
    for position, run in runs.items():
        out["runs"][position] = {k: _A31._num(v) if isinstance(v, float) else v
                                 for k, v in run.items() if k != "tail"}
    base = runs["financial"]["tail"]
    shape_base = base / base.sum()
    for position in ("proportional", "production", "none"):
        t = runs[position]["tail"]
        shape = t / t.sum()
        out["against_financial"][position] = {
            "stock_ratio": _A31._num(t.sum() / base.sum()),
            "node_share_max_absolute_difference": _A31._num(
                float(np.abs(shape - shape_base).max())),
            "node_share_mean_absolute_difference": _A31._num(
                float(np.abs(shape - shape_base).mean())),
            "node_share_correlation": _A31._num(
                float(np.corrcoef(shape, shape_base)[0, 1])),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    if not args.run:
        ap.error("pass --run")
    out = probe()
    print("stage A31, side probe: one cell, need %.2f %s e %.1f seed %d, the "
          "closing distribution under each position\n"
          % (CELL["need"], CELL["stress"], CELL["elasticity"], CELL["seed"]))
    for position, run in out["runs"].items():
        print("   %-13s stock %8.3f  Layer 2 share %.4f  below the floor %3d  "
              "taken back %8.3f" % (position, run["total"],
                                    run["layer2_share_of_stock"],
                                    run["below_close"], run["withdrawn_total"]))
    print()
    for position, cmp_ in out["against_financial"].items():
        print("   %-13s against financial: stock ratio %.5f, node share max "
              "difference %.2e, mean %.2e, correlation %.8f"
              % (position, cmp_["stock_ratio"],
                 cmp_["node_share_max_absolute_difference"],
                 cmp_["node_share_mean_absolute_difference"],
                 cmp_["node_share_correlation"]))
    if args.no_write:
        return 0
    doc = {"stage": "A31", "diagnostic_only": True,
           "diagnostic_reason": ("a side probe of A31-3, one cell: the closing "
                                 "distribution under each position"),
           "config": _A31._fmt(_A31.station_config()),
           "sections": {"probe": _A31._fmt(out)}}
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\n   record: %s" % RECORD.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
