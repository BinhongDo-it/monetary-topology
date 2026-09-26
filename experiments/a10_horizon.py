"""A10 at four horizons: what the refill gives back, what it costs, and where the unrefilled arm stops.

The registered reading of A10 runs 300 rounds on twelve seeds
(``results/a10_writeoff.json``). This reads the same carrier with the same code
at 300, 600, 1200 and 2400 rounds, on three seeds and the two settings the A10
horizon reading in ``RESULTS.md`` uses: the mildest write-off on the grid
(trigger 2, rate 0.02) and a heavier one (trigger 10, rate 0.10), each with and
without the refill, beside the control.

What it prints, every quantity for every arm and horizon, means over the three
seeds:

* ``M/R`` at the last round, and its ratio to the control's;
* effective support at the last round and as the mean of the last ``TAIL`` rounds,
  each with its ratio to the control's (the reported table used the first for its
  ratio column and the second for its level column, and both are kept);
* the Gini of the last round's holdings, and its difference from the control's;
* the top-1% share of the last round's holdings (the top ``ceil(n/100)`` nodes),
  and its difference from the control's;
* cumulative destruction;
* for each seed, the round at which ``M/R`` peaks, and the median over seeds.

Two criteria, neither of them a verdict on A10:

* A10H-1, instrument: claims are conserved in every run, destruction entering
  the identity. The tolerance is the 300-round stage's ``SFC_TOLERANCE`` taken
  relative to the largest term of the identity. As an absolute bound it is
  exceeded at 2400 rounds by accumulation alone: cumulative issuance and
  destruction reach 3.5 million on the heavier refilled arm, the gaps reach
  8e-9, and relative to the identity's largest term they stay below 2e-14.
  The gaps themselves are printed and not written: their last digits belong to
  the build, not to the model.
* A10H-2, known answer: the horizon table reported for this station is
  reproduced to the digits it was printed with.

    python experiments/a10_horizon.py

Writes ``results/a10_horizon.json``. Exits non-zero if a criterion fails.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from a10_writeoff import SFC_TOLERANCE, TAIL, arm, base_config  # noqa: E402
from monetary_topology.asset import carrier_model  # noqa: E402
from monetary_topology.mechanisms import gini  # noqa: E402
from monetary_topology.network import WriteOffSpec  # noqa: E402

RESULTS = ROOT / "results"
OUT = RESULTS / "a10_horizon.json"

SEEDS = (0, 1, 2)
HORIZONS = (300, 600, 1200, 2400)
LOW = {"trigger": 2.0, "rate": 0.02}
HIGH = {"trigger": 10.0, "rate": 0.10}
ARMS = {
    "control": WriteOffSpec(),
    "refill, low": WriteOffSpec(refill=True, **LOW),
    "refill, high": WriteOffSpec(refill=True, **HIGH),
    "no refill, low": WriteOffSpec(refill=False, **LOW),
    "no refill, high": WriteOffSpec(refill=False, **HIGH),
}

#: The table as it was reported, as the strings it was printed as, so the check
#: compares at the printed precision. Relative columns are against the control.
REPORTED = {
    ("mr", 300): {"control": "33.54", "refill, low": "33.52", "no refill, low": "5.48", "no refill, high": "9.37"},
    ("mr", 600): {"control": "66.44", "refill, low": "66.46", "no refill, low": "5.49", "no refill, high": "9.52"},
    ("mr", 1200): {"control": "132.24", "refill, low": "132.32", "no refill, low": "5.49", "no refill, high": "9.50"},
    ("mr", 2400): {"control": "263.84", "refill, low": "264.05", "no refill, low": "5.49", "no refill, high": "9.12"},
    ("mr_rel", 2400): {"refill, low": "1.0008", "refill, high": "0.9842", "no refill, low": "0.0208", "no refill, high": "0.0346"},
    ("support_last_rel", 2400): {"refill, low": "1.0043", "refill, high": "0.9952", "no refill, low": "1.1323", "no refill, high": "1.0758"},
    ("support_tail", 2400): {"control": "13.67", "refill, low": "13.73", "no refill, low": "15.48", "no refill, high": "14.70"},
    ("gini_diff", 2400): {"refill, low": "0.0009", "refill, high": "0.0055", "no refill, low": "-0.0088", "no refill, high": "-0.0051"},
    ("top1_diff", 2400): {"refill, low": "0.0134", "refill, high": "0.0621", "no refill, low": "0.0058", "no refill, high": "0.0032"},
    ("top1", 2400): {"control": "0.2306", "refill, high": "0.2927"},
    ("destroyed", 2400): {"refill, low": "648346", "refill, high": "3456069", "no refill, low": "26395", "no refill, high": "25780"},
}
PEAK_REPORTED = {"arm": "no refill, high", "median_round": 86}


def r6(x: float) -> float:
    return round(float(x), 6)


def one(spec: WriteOffSpec, seed: int, rounds: int) -> dict:
    h = carrier_model(arm(base_config(seed, rounds), spec), asset=False).run()
    hold = np.asarray(h.holdings, dtype=float)
    last = hold[-1]
    issued = np.asarray(h.issuance, dtype=float)
    destroyed = np.asarray(h.written_off, dtype=float)
    m = hold.sum(axis=1)
    gap = float(np.abs(m - (m[0] + np.cumsum(issued) - np.cumsum(destroyed))).max())
    k = max(1, math.ceil(last.size / 100))
    support = np.asarray(h.effective_support, dtype=float)
    mr = np.asarray(h.total_ratio, dtype=float)
    scale = max(1.0, float(np.abs(m).max()), float(issued.sum()), float(destroyed.sum()))
    return {
        "mr": float(mr[-1]),
        "support_last": float(support[-1]),
        "support_tail": float(support[-TAIL:].mean()),
        "gini": float(gini(last)),
        "top1": float(np.sort(last)[::-1][:k].sum() / last.sum()),
        "destroyed": float(destroyed.sum()),
        "peak_round": int(np.argmax(mr)),
        "gap": gap,
        "gap_rel": gap / scale,
        "conserved": bool(gap / scale < SFC_TOLERANCE),
        "nodes": int(last.size),
    }


def main() -> int:
    runs = {(name, H, s): one(spec, s, H) for name, spec in ARMS.items() for H in HORIZONS for s in SEEDS}

    table = {}
    for H in HORIZONS:
        mean = {name: {q: statistics.fmean(runs[(name, H, s)][q] for s in SEEDS)
                       for q in ("mr", "support_last", "support_tail", "gini", "top1", "destroyed")}
                for name in ARMS}
        c = mean["control"]
        for name in ARMS:
            a = mean[name]
            peaks = [runs[(name, H, s)]["peak_round"] for s in SEEDS]
            table[(name, H)] = {
                "mr": a["mr"], "mr_rel": a["mr"] / c["mr"],
                "support_last": a["support_last"], "support_last_rel": a["support_last"] / c["support_last"],
                "support_tail": a["support_tail"], "support_tail_rel": a["support_tail"] / c["support_tail"],
                "gini": a["gini"], "gini_diff": a["gini"] - c["gini"],
                "top1": a["top1"], "top1_diff": a["top1"] - c["top1"],
                "destroyed": a["destroyed"],
                "peak_rounds": peaks, "peak_median": int(statistics.median(peaks)),
            }

    print("A10 at four horizons (means over seeds 0 to 2)\n")
    print(f"{'arm':16s} {'H':>5s} | {'M/R':>8s} {'x ctrl':>7s} | {'sup,last':>8s} {'x ctrl':>7s} {'sup,tail':>8s} | "
          f"{'gini':>7s} {'d':>8s} | {'top1%':>7s} {'d':>8s} | {'destroyed':>11s} | peaks")
    for H in HORIZONS:
        for name in ARMS:
            t = table[(name, H)]
            print(f"{name:16s} {H:5d} | {t['mr']:8.2f} {t['mr_rel']:7.4f} | {t['support_last']:8.2f} "
                  f"{t['support_last_rel']:7.4f} {t['support_tail']:8.2f} | {t['gini']:7.4f} {t['gini_diff']:+8.4f} | {t['top1']:7.4f} "
                  f"{t['top1_diff']:+8.4f} | {t['destroyed']:11,.0f} | {t['peak_rounds']} -> {t['peak_median']}")
        print()

    conserved = [k for k, v in runs.items() if not v["conserved"]]
    c1 = {"name": "A10H-1 claims conserved in every run, destruction entering the identity",
          "kind": "instrument", "passed": not conserved,
          "detail": (f"{len(runs) - len(conserved)} of {len(runs)} runs conserve claims to {SFC_TOLERANCE:g} of the "
                     f"identity's largest term")}
    print(f"  largest relative gap {max(v['gap_rel'] for v in runs.values()):.1e}, "
          f"largest absolute gap {max(v['gap'] for v in runs.values()):.1e} (printed, not written)")

    misses = []
    for (q, H), cells in REPORTED.items():
        for name, want in cells.items():
            got = table[(name, H)][q]
            places = len(want.split(".")[1]) if "." in want else 0
            if f"{got:.{places}f}" != want:
                misses.append(f"{q} {name} {H}: reported {want}, got {got:.6f}")
    peak_ok = all(table[(PEAK_REPORTED["arm"], H)]["peak_median"] == PEAK_REPORTED["median_round"] for H in HORIZONS)
    if not peak_ok:
        misses.append("median peak round of the unrefilled high-rate arm is not 86 at every horizon")
    n_cells = sum(len(v) for v in REPORTED.values()) + 1
    c2 = {"name": "A10H-2 the reported horizon table is reproduced to its printed digits",
          "kind": "known_answer", "passed": not misses,
          "detail": (f"{n_cells - len(misses)} of {n_cells} reported values reproduced"
                     + ("" if not misses else "; " + "; ".join(misses)))}

    for c in (c1, c2):
        print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}\n         {c['detail']}")

    record = {
        "stage": "A10H",
        "config": {"seeds": list(SEEDS), "horizons": list(HORIZONS), "low": LOW, "high": HIGH,
                   "tail": TAIL, "top_share_nodes": "ceil(n / 100) of the last round's holdings",
                   "carrier": "A10 registered carrier, asset layer off"},
        "nodes": runs[("control", HORIZONS[0], SEEDS[0])]["nodes"],
        "table": [{"arm": name, "horizon": H,
                   **{k: (round(v, 3) if k == "destroyed" else r6(v) if isinstance(v, float) else v)
                      for k, v in table[(name, H)].items()}}
                  for H in HORIZONS for name in ARMS],
        "criteria": [c1, c2],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0 if (c1["passed"] and c2["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
