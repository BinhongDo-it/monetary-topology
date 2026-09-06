"""A23: is a returnable park a mechanism, or a second name for a slower leak.

A18 added ``ParkSpec`` and its docstring says of itself: *one way. A parked
claim does not come back.* The manuscript's first section says the opposite in
as many words -- both sides keep the right to come back, and a claim outside
the system can return to the market to buy resource. So the gap is one line
wide and it is not a new premise, it is the missing half of one that is
already written down.

``ParkSpec.return_rate`` closes it. **The switch is triggered, not timed**: a
parked claim comes back when this graph's own circulating stock has fallen
below where it opened, in proportion to that shortfall. A rate alone would be
a number with no source; the trigger is a state of the graph and costs no new
parameter beyond the strength.

**What this stage measures is whether that switch carries anything.** A
one-parameter family of leaks traces a curve in the plane whose axes are what
circulates and what does not. If the two-way cells land on that curve, the
switch is a reparameterisation of the leak rate and should not be added. If
they land off it, the two arms are separable and the mechanism is real.

The floor is not the test. The enumeration written before this ran said the
one-way arm drains to zero and the two-way arm settles at a positive floor.
**Both arms have positive floors**, measured, with resupply on and with it off,
because parking bites on one layer and the rest of the graph keeps trading.
That reading killed the first criterion shape before any grid was bought. What
survives is the pair of quantities A18 itself declared for this arm: what
circulates and what does not, recorded separately and never as a ratio,
because a ratio hides which of the two moved.

Usage

    python experiments/a23_two_way_park.py --plan
    python experiments/a23_two_way_park.py --smoke
    python experiments/a23_two_way_park.py
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.network import (  # noqa: E402
    Network,
    ParkSpec,
    ResupplySpec,
    WriteOffSpec,
)

RECORD = RESULTS / "a23_two_way_park.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_A18 = _load(ROOT / "experiments" / "a18_policy_paths.py", "_a18")
config_for = _A18.config_for
r = _A18.r
ROUNDS = _A18.ROUNDS
SEEDS = _A18.SEEDS

#: The park strengths the two-way cells are read at. A18's own levels minus
#: zero, because a return path on a park of zero has nothing to return.
TWO_WAY_PARK: tuple[float, ...] = (0.05, 0.20, 0.50)

#: Return strengths. Three, spanning the interval the field is defined on.
TWO_WAY_RETURN: tuple[float, ...] = (0.25, 0.50, 1.00)

#: The one-way sweep. Forty-one points on ``[0, 0.80]``: the curve has to be
#: dense enough to interpolate on, and the top of the range has to sit below
#: every two-way floor so no cell needs extrapolating.
ONE_WAY_GRID: tuple[float, ...] = tuple(round(0.02 * i, 4) for i in range(41))

#: Both resupply settings. With resupply the stock is being created while it
#: is being parked; without it the opening stock is all there is. The arm is
#: read on both because neither is the privileged one, and because printing
#: both is what this track binds instead of a timestamp.
RESUPPLY_RATES: tuple[float, ...] = (0.0, 2.0)

NEED = 0.50
TARGET = "financial"
FUNDING = "issuance"

#: The window the floor and the parked stock are both read over. A18's closing
#: reads are single-round; a floor is a level, so it is a mean, and the two
#: quantities use the same window so that a difference between them is not a
#: difference between two windows.
TAIL = 50

#: The resolution multiple gate six is read at. **Not a theory constant**: it
#: is this repository's own convention for a measured noise floor, set by B18
#: (``|A_s| >= 2 se``) and reused rather than reinvented. The raw multiple is
#: printed for every cell, so the reading does not depend on it.
FLOOR_MULTIPLE = 2.0


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


# ---------------------------------------------------------------------------
# One cell.
# ---------------------------------------------------------------------------

def cell(park: float, ret: float, rate: float, seed: int,
         need: float = NEED) -> dict:
    cfg = config_for("drawdown", WriteOffSpec(), "endogenous", need, seed,
                     resupply_rate=rate)
    cfg = dataclasses.replace(
        cfg,
        resupply=ResupplySpec(rate=rate, funding=FUNDING),
        park=ParkSpec(rate=park, target=TARGET, return_rate=ret))
    h = Network(cfg).run()
    circ = np.asarray(h.total_claims, dtype=float)
    parked = np.asarray(h.parked, dtype=float)
    returned = np.asarray(h.returned, dtype=float)

    floor = float(circ[-TAIL:].mean())
    park_level = float(parked[-TAIL:].mean())
    # A23-6, printed and not judged: when it gets there, and whether it goes
    # past. **Both read off the series, no threshold on either.**
    band = 0.01 * abs(floor) if floor else 0.0
    inside = np.flatnonzero(np.abs(circ - floor) <= band)
    settled = int(inside[0]) if inside.size else -1
    # **Both extremes, signed, not one number called an overshoot.** A series
    # that climbs to its floor and one that dips below it on the way have
    # opposite shapes, and a single min collapses them into the same reading.
    head = circ[:settled] if settled > 0 else circ[:1]
    below = float(head.min() - floor)
    above = float(head.max() - floor)

    return {
        "park": float(park), "return_rate": float(ret), "resupply": float(rate),
        "seed": int(seed), "need": float(need),
        "floor": r(floor),
        "parked": r(park_level),
        "stock": r(floor + park_level),
        "returned_total": r(float(returned.sum())),
        "returned_is_zero": bool(np.all(returned == 0.0)),
        "open_circulating": r(float(circ[0])),
        "settled_round": settled,
        "lowest_before_floor": r(below),
        "highest_before_floor": r(above),
    }


def grid(seeds=SEEDS) -> list:
    rows = []
    for rate in RESUPPLY_RATES:
        for seed in seeds:
            for pk in ONE_WAY_GRID:
                rows.append(cell(pk, 0.0, rate, seed))
            for pk in TWO_WAY_PARK:
                for rr in TWO_WAY_RETURN:
                    rows.append(cell(pk, rr, rate, seed))
    return rows


def plan() -> dict:
    n = len(RESUPPLY_RATES) * len(SEEDS) * (
        len(ONE_WAY_GRID) + len(TWO_WAY_PARK) * len(TWO_WAY_RETURN))
    return {
        "stage": "A23",
        "question": "is a returnable park a mechanism or a slower leak",
        "one_way_grid": len(ONE_WAY_GRID),
        "two_way_cells": len(TWO_WAY_PARK) * len(TWO_WAY_RETURN),
        "resupply_rates": list(RESUPPLY_RATES),
        "seeds": list(SEEDS),
        "rounds": ROUNDS,
        "tail_window": TAIL,
        "cells": n,
        "seconds_at_0.337s_per_cell": round(n * 0.337),
        "gates": "two and three do not apply, no estimator and no band; six "
                 "applies and its floor is measured from seed dispersion",
        "read": "the pair (circulating, parked), never their ratio",
    }


# ---------------------------------------------------------------------------
# The comparison. One-way sweep -> a curve; two-way cells -> points.
# ---------------------------------------------------------------------------

def _curve(rows: list, rate: float, seed: int):
    """The one-way family for one (resupply, seed), sorted by floor."""
    pts = [x for x in rows if x["return_rate"] == 0.0
           and x["resupply"] == rate and x["seed"] == seed]
    pts.sort(key=lambda x: x["floor"])
    return (np.array([x["floor"] for x in pts]),
            np.array([x["parked"] for x in pts]),
            np.array([x["park"] for x in pts]))


def compare(rows: list) -> list:
    """For every two-way cell: the one-way arm's parked stock at the same
    circulating level, and the gap. **Interpolated on the curve, not fitted.**
    Cells whose floor falls outside the swept range are flagged rather than
    extrapolated."""
    out = []
    for x in rows:
        if x["return_rate"] == 0.0:
            continue
        f, q, pk = _curve(rows, x["resupply"], x["seed"])
        if f.size < 2 or not (f[0] <= x["floor"] <= f[-1]):
            out.append({**{k: x[k] for k in
                           ("park", "return_rate", "resupply", "seed", "floor",
                            "parked")},
                        "in_range": False, "one_way_parked": None,
                        "one_way_park": None, "gap": None, "gap_pct": None})
            continue
        out.append({**{k: x[k] for k in
                       ("park", "return_rate", "resupply", "seed", "floor",
                        "parked")},
                    "in_range": True,
                    "one_way_parked": r(float(np.interp(x["floor"], f, q))),
                    "one_way_park": r(float(np.interp(x["floor"], f, pk))),
                    "gap": r(float(np.interp(x["floor"], f, q) - x["parked"])),
                    "gap_pct": r(100.0 * (float(np.interp(x["floor"], f, q))
                                          - x["parked"]) / x["parked"])
                    if x["parked"] else None})
    return out


def _by_config(pairs: list) -> dict:
    d = {}
    for p in pairs:
        d.setdefault((p["park"], p["return_rate"], p["resupply"]), []).append(p)
    return d


# ---------------------------------------------------------------------------
# Criteria.
# ---------------------------------------------------------------------------

def criterion_a23_1(rows: list) -> Criterion:
    """Default off. **Structural, no threshold.**

    Two halves. Every ``return_rate = 0`` cell must have an all-zero
    ``returned`` series, and a ``ParkSpec`` built without the field at all must
    give a cell identical in every key to one built with the field set to zero.
    The second half is the one that catches a default that was written down but
    not wired."""
    one_way = [x for x in rows if x["return_rate"] == 0.0]
    leaked = [x for x in one_way if not x["returned_is_zero"]]

    probe = []
    for rate in RESUPPLY_RATES:
        for pk in (0.0, 0.20, 0.50):
            a = cell(pk, 0.0, rate, 0)
            cfg = config_for("drawdown", WriteOffSpec(), "endogenous", NEED, 0,
                             resupply_rate=rate)
            cfg = dataclasses.replace(
                cfg, resupply=ResupplySpec(rate=rate, funding=FUNDING),
                park=ParkSpec(rate=pk, target=TARGET))   # field omitted
            h = Network(cfg).run()
            # **The whole series, element for element, not two summaries.** A
            # mean over fifty rounds can agree while the path underneath it
            # does not, and the thing being checked here is that the field
            # changes nothing at all when it is left out.
            cfg_a = dataclasses.replace(
                cfg, park=ParkSpec(rate=pk, target=TARGET, return_rate=0.0))
            ha = Network(cfg_a).run()
            same = all(np.array_equal(np.asarray(getattr(h, k), dtype=float),
                                      np.asarray(getattr(ha, k), dtype=float))
                       for k in ("total_claims", "parked", "holdings",
                                 "total_ratio", "total_volume"))
            probe.append((rate, pk, bool(same)))
    mismatched = [p for p in probe if not p[2]]
    ok = not leaked and not mismatched
    return Criterion(
        "A23-1  the switch is off by default and off means absent",
        ok,
        "returned is identically zero in %d of %d one-way cells | omitting the "
        "field reproduces setting it to zero in %d of %d probes%s"
        % (len(one_way) - len(leaked), len(one_way),
           len(probe) - len(mismatched), len(probe),
           "" if ok else " | offenders: %s" % (leaked[:3] + mismatched[:3],)))


def criterion_a23_2(pairs: list) -> Criterion:
    """The plane. **Printed and not judged** (rule 11: print the object).

    The one-way family is a curve. Each two-way cell is a point. What is
    printed is where the point sits relative to the curve at the same
    circulating level. Whether that distance is readable is gate six's
    question, and it is A23-3's."""
    good = [p for p in pairs if p["in_range"]]
    out = []
    for key, g in sorted(_by_config(good).items()):
        pk, rr, rate = key
        out.append("(park %.2f, return %.2f, resupply %.1f): floor %.4f, "
                   "parked %.2f vs one-way %.2f at park* %.4f, gap %+.2f%%"
                   % (pk, rr, rate,
                      float(np.mean([x["floor"] for x in g])),
                      float(np.mean([x["parked"] for x in g])),
                      float(np.mean([x["one_way_parked"] for x in g])),
                      float(np.mean([x["one_way_park"] for x in g])),
                      float(np.mean([x["gap_pct"] for x in g]))))
    return Criterion(
        "A23-2  where the two-way point sits relative to the one-way curve",
        len(good) == len(pairs),
        "%d of %d cells fell inside the swept range | %s"
        % (len(good), len(pairs), " | ".join(out)))


def criterion_a23_3(pairs: list) -> Criterion:
    """Gate six. **The floor is measured, not declared**: it is the dispersion
    of the gap across seeds at the same configuration.

    Passing is one cell clearing it, not every cell. The claim under test is
    that the two-way arm sits off the one-way curve, and one readable cell
    establishes that. Requiring all of them would be setting the criterion at
    its strictest reading rather than at a sufficient one, which this
    repository has paid for four times."""
    good = [p for p in pairs if p["in_range"]]
    rows, cleared = [], 0
    for key, g in sorted(_by_config(good).items()):
        gaps = np.array([x["gap"] for x in g], dtype=float)
        if gaps.size < 2:
            continue
        se = float(gaps.std(ddof=1))
        mult = float(abs(gaps.mean()) / se) if se > 0 else float("inf")
        if mult >= FLOOR_MULTIPLE:
            cleared += 1
        rows.append("(park %.2f, return %.2f, resupply %.1f): gap %+.3f, "
                    "floor %.4f, %.2fx" % (key[0], key[1], key[2],
                                           float(gaps.mean()), se, mult))
    return Criterion(
        "A23-3  the gap against the measured resolution floor",
        cleared > 0,
        "%d of %d configurations clear %.1fx the seed floor | %s"
        % (cleared, len(rows), FLOOR_MULTIPLE, " | ".join(rows)))


def criterion_a23_4(pairs: list) -> Criterion:
    """Direction. **A count, not a rate, and no threshold on the count.**

    The mechanical prediction is that the return path drains the pool, so at a
    matched circulating level the two-way arm holds less parked stock. Passing
    is structural: every in-range cell produced a comparison. The sign count is
    the reading."""
    good = [p for p in pairs if p["in_range"]]
    less = sum(1 for p in good if p["gap"] > 0)
    more = sum(1 for p in good if p["gap"] < 0)
    tie = len(good) - less - more
    return Criterion(
        "A23-4  which side holds less parked stock at a matched floor",
        len(good) == len(pairs) and len(good) > 0,
        "two-way holds less in %d cells, more in %d, equal in %d, of %d "
        "compared" % (less, more, tie, len(good)))


def criterion_a23_5(rows: list) -> Criterion:
    """How much of the pool actually came back. **Printed and not judged.**

    This is the trigger's scope, not a claim. Where circulating stock rises
    above its opening level the shortfall is negative and nothing returns,
    which is the trigger doing its job rather than failing."""
    out = []
    two = [x for x in rows if x["return_rate"] > 0.0]
    for key, g in sorted(_by_config(two).items()):
        out.append("(park %.2f, return %.2f, resupply %.1f): returned %.1f, "
                   "parked %.1f, ratio %.3f"
                   % (key[0], key[1], key[2],
                      float(np.mean([x["returned_total"] for x in g])),
                      float(np.mean([x["parked"] for x in g])),
                      float(np.mean([x["returned_total"] / x["parked"]
                                     if x["parked"] else 0.0 for x in g]))))
    return Criterion(
        "A23-5  how much of the parked pool returned", True,
        "printed and not judged | " + " | ".join(out))


def criterion_a23_6(rows: list) -> Criterion:
    """Settling. **Printed and not judged**, and not registered before the run:
    the enumeration said this one depends on how long the lag is.

    ``approach from a to b`` is how far the series got below and above its own
    floor before reaching it. A monotone climb reads as a large negative and a
    near-zero positive; a genuine overshoot is the pair with both signs
    large."""
    out = []
    for key, g in sorted(_by_config(rows).items()):
        out.append("(park %.2f, return %.2f, resupply %.1f): settled round "
                   "%.1f, approach from %+.2f to %+.2f"
                   % (key[0], key[1], key[2],
                      float(np.mean([x["settled_round"] for x in g])),
                      float(np.mean([x["lowest_before_floor"] for x in g])),
                      float(np.mean([x["highest_before_floor"] for x in g]))))
    return Criterion(
        "A23-6  when it settles and whether it goes past", True,
        "printed and not judged | " + " | ".join(out[:12]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="three seeds, to read the homogeneity before paying "
                         "for five")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    if args.plan:
        for k, v in plan().items():
            print("  %-28s %s" % (k, v))
        return 0

    seeds = (0, 1, 2) if args.smoke else SEEDS
    rows = grid(seeds=seeds)
    pairs = compare(rows)
    crits = [criterion_a23_1(rows), criterion_a23_2(pairs),
             criterion_a23_3(pairs), criterion_a23_4(pairs),
             criterion_a23_5(rows), criterion_a23_6(rows)]

    print("stage A23: is a returnable park a mechanism or a slower leak\n")
    for c in crits:
        print("  [%s] %s" % ("PASS" if c.passed else "FAIL", c.name))
        print("        %s" % c.detail)
    passed = sum(1 for c in crits if c.passed)
    print("\n  %d/%d" % (passed, len(crits)))

    if args.no_write:
        return 0 if passed == len(crits) else 1

    out = RECORD
    if args.smoke:
        out = RESULTS / "subset" / RECORD.name
        out.parent.mkdir(exist_ok=True)
    record = {
        "stage": "A23",
        "diagnostic_only": True,
        "diagnostic_reason": "the station is not closed",
        "carrier": "A18's park carrier with the return path switched on",
        "plan": plan(),
        "seeds_run": list(seeds),
        "criteria": [c.as_dict() for c in crits],
        "pairs": sorted(pairs, key=lambda x: (x["resupply"], x["park"],
                                              x["return_rate"], x["seed"])),
        "runs": sorted(rows, key=lambda x: (x["resupply"], x["return_rate"],
                                            x["park"], x["seed"])),
    }
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("\n  wrote %s (%d rows, %d pairs)%s"
          % (out.name, len(rows), len(pairs),
             "  [reduced run, results/subset]" if args.smoke else ""))
    return 0 if passed == len(crits) else 1


if __name__ == "__main__":
    raise SystemExit(main())
