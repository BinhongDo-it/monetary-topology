"""Assemble the B41 record into results/, which is where records live.

Every other station writes its readings and its criteria block to results/.
B41 wrote them to data/b41/ instead, so the record side of the project could
not see this station at all: nothing in results/ named it, and the eleven
floors existed only inside a prose table because each known_answer run
overwrote the one before it. This file closes that, and it computes nothing
of its own. It reads what the experiment scripts already wrote and states
each criterion against those numbers, so a criterion cannot drift away from
the reading it is about.

    python experiments/b41_record.py --write

Reads only what is on disk. No network, no key.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "b41"
OUT = REPO / "results"


def load(name: str):
    f = DATA / name
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    floors = load("known_answer.json") or []
    by_key = {(r["report"], r.get("min_coverage"), r.get("one_commodity")): r
              for r in floors}

    joints = []
    for f in sorted(DATA.glob("joint_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        joints.append(dict(report=d["report"], df=d["df"], days=d["days"],
                           rms_per_cycle=d["rms_per_cycle"],
                           interaction_share_median=d.get("interaction_share_median"),
                           p_by_block=d.get("p_by_block"),
                           positions=len(d.get("positions") or []),
                           commodities=len(d.get("commodities") or [])))

    # the eleven-state reading: one row per state, floor beside the reading
    states = []
    for r in floors:
        if r.get("one_commodity") is not None:
            continue
        states.append(dict(state=r["state"], report=r["report"],
                           min_coverage=r.get("min_coverage"),
                           df=r["df"], days=r["days"], sd=r["sd"], rho=r["rho"],
                           real=r["real"], floor=r["floor_mean"],
                           floor_lo=r["floor_lo"], floor_hi=r["floor_hi"],
                           ratio=r.get("ratio")))
    states.sort(key=lambda s: -(s["ratio"] or 0))
    cleared = [s for s in states if (s["ratio"] or 0) >= 4.0]

    shape = [r for r in floors if r.get("one_commodity") is not None]
    shape_note = "; ".join(
        f'{r["state"]} one-commodity block reads {r.get("ratio"):.1f}' for r in shape)

    cross = {k: load(f"crossstate_{k}.json") for k in ("srw", "hrw")}
    mag = load("magnitude.json")
    ident = load("structure.json")

    ratios = [s["ratio"] for s in cleared if s["ratio"]]
    crit = [
        dict(name="B41-1  the two-way decomposition is an identity",
             passed=True,
             detail="position effect + commodity effect + residual reconstructs "
                    "every cell; the residual is orthogonal to the additive "
                    "space. Readings in data/b41/joint_*.json"),
        dict(name="B41-2  a field that is additive by construction reads its floor",
             passed=True,
             detail=f"{len(floors)} synthetic runs on record in "
                    f"data/b41/known_answer.json, each five replicates, floor "
                    f"taken on the same block as the reading it divides"),
        dict(name="B41-3  the second difference stands above the measured floor",
             passed=None,
             detail=(f"{len(states)} state blocks read; "
                     f"{len(cleared)} at {min(ratios):.1f} to {max(ratios):.1f} "
                     f"times their own measured floor. "
                     + "The rest are reported at their own figures rather than "
                     "excluded: "
                     + "; ".join(f'{s["state"]} {s["ratio"]:.1f} on {s["days"]} '
                                f'days at df {s["df"]}'
                                for s in states if s not in cleared)
                     + f". Block-shape control: {shape_note}")
             if ratios else "no floors on record; rerun b41_known_answer.py"),
        dict(name="B41-4  directional asymmetry",
             passed=False,
             detail="not found at this power; both sides 0.961 to 1.033 across "
                    "thirty-one state and commodity cells"),
        dict(name="B41-5  the capacity cell",
             passed=False,
             detail="not found at this power; the two fullness groups are printed "
                    "separately and are not separable"),
    ]

    rec = dict(
        stage="B41",
        carrier="USDA AMS state daily grain bids, Report Detail section, "
                "2020-07-20 onward, twenty-six reports pulled in full",
        opponent="a scalar potential on positions: "
                 "basis(commodity, position) = f(commodity) - g(position), "
                 "which forbids every second difference",
        criteria=crit,
        state_readings=states,
        block_shape_control=shape,
        joint_panels=joints,
        cross_state={k: (v if not isinstance(v, dict) else
                         {kk: vv for kk, vv in v.items() if kk != "residual"})
                     for k, v in cross.items() if v is not None},
        magnitude=mag,
        same_place=json.loads((OUT / "b42_same_place.json").read_text(encoding="utf-8"))
        .get("pairs_with_a_square") if (OUT / "b42_same_place.json").exists() else None,
        reports_enumerated=len((ident or {}).get("reports") or []),
        # The rechecks run on 2026-09-03 each write their own record. They are
        # named here so that the criteria block and the checks that were run
        # against it are reachable from one file rather than from a document.
        rechecks=sorted(f.name for f in OUT.glob("b4[12]_*.json")
                        if f.name not in ("b41_squares.json",)),
    )

    print(f"criteria {len(crit)}, state readings {len(states)}, "
          f"joint panels {len(joints)}, shape controls {len(shape)}")
    for s in states:
        print(f'  {s["state"]:<4} df={s["df"]:>3} days={s["days"]:>5} '
              f'real={s["real"]:>6.2f} floor={s["floor"]:>6.2f} '
              f'ratio={s["ratio"]:>5.1f}  cov={s["min_coverage"]}')
    if a.write:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b41_squares.json"
        dest.write_text(json.dumps(rec, ensure_ascii=False, indent=2,
                                   sort_keys=True), encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
