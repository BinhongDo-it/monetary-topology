"""Is the Missouri agreement between the two pooled blocks an independent check?

The result document reports that Missouri is the only state in both pooled
blocks and that each block gives it a negative figure on its own, and reads
that as a cross-check. A sign agreement is only evidence if the sign was free
to disagree, and this file asks whether it was. Three things could make the
agreement mechanical rather than found:

  the per-state vector is re-centred across states every day, so it sums to
  zero and some state is negative whatever the data say;

  a state holding a large share of a block's positions is close to the
  balancing term of that block by arithmetic, because the residual sums to
  zero over positions;

  the two blocks may share the position that carries the reading.

None of these is visible in the number itself. All three are countable.

    python experiments/b41_crossstate_audit.py --check

Reads only what is cached. No network, no key.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_crossstate as C   # noqa: E402
import b41_joint as J        # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results"
COV = {"srw": 0.80, "hrw": 0.85}


def build(block: str):
    pair = C.BLOCKS[block]
    per_day = C.pooled(pair)
    sps = C.choose(per_day, pair, COV[block])
    days, mats, _ = C.matrices(per_day, pair, sps)
    mask = np.ones((len(sps), 2), bool)
    res = np.array([J.additive_residual(m, mask)[0] for m in mats])
    order = [sp[0] for sp in sps]
    return dict(block=block, sps=sps, order=order, days=days, res=res)


def state_means(res, order, states, recentre: bool):
    idx = {s: [i for i, o in enumerate(order) if o == s] for s in states}
    cross = np.array([[r[idx[s], 0].mean() for s in states] for r in res])
    if recentre:
        cross = cross - cross.mean(axis=1, keepdims=True)
    return dict(zip(states, cross.mean(axis=0)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if not (a.check or a.record):
        ap.print_help(); return

    out = {}
    built = {b: build(b) for b in ("srw", "hrw")}

    for b, d in built.items():
        states = sorted(set(d["order"]))
        n = Counter(d["order"])
        raw = state_means(d["res"], d["order"], states, recentre=False)
        cen = state_means(d["res"], d["order"], states, recentre=True)
        # the residual sums to zero over positions on every day
        per_day_sum = np.abs(d["res"][:, :, 0].sum(axis=1)).max()
        weighted = sum(n[s] * raw[s] for s in states)
        print(f"\n=== {b.upper()} block, {len(d['sps'])} positions, "
              f"{len(d['days'])} complete days")
        print(f"  max |sum of the residual over positions| on any day: "
              f"{per_day_sum:.2e}   (zero by construction)")
        print(f"  sum over states of n_s * raw_s : {weighted:+.2e}")
        print(f"  {'state':<6}{'positions':>10}{'share':>8}"
              f"{'raw':>9}{'centred':>9}")
        for s in states:
            print(f"  {s:<6}{n[s]:>10}{n[s]/len(d['order']):>8.2f}"
                  f"{raw[s]:>+9.2f}{cen[s]:>+9.2f}")
        out[b] = dict(positions=len(d["sps"]), days=len(d["days"]),
                      counts=dict(n), raw={k: float(v) for k, v in raw.items()},
                      centred={k: float(v) for k, v in cen.items()})

    # 1. do the two blocks share days?
    ds, dh = set(built["srw"]["days"]), set(built["hrw"]["days"])
    print(f"\n--- day sets: srw {len(ds)}, hrw {len(dh)}, "
          f"shared {len(ds & dh)} ({len(ds & dh) / len(ds):.1%} of srw)")
    out["shared_days"] = len(ds & dh)

    # 2. do the two blocks share the positions Missouri contributes?
    mo_s = [p for st, p in built["srw"]["sps"] if st == "MO"]
    mo_h = [p for st, p in built["hrw"]["sps"] if st == "MO"]
    print(f"--- Missouri positions: srw {len(mo_s)}, hrw {len(mo_h)}, "
          f"shared {len(set(mo_s) & set(mo_h))}")
    for p in mo_s:
        print(f"      srw  {p}{'   <-- also in hrw' if p in mo_h else ''}")
    for p in mo_h:
        print(f"      hrw  {p}")
    out["mo_positions"] = dict(srw=mo_s, hrw=mo_h,
                               shared=sorted(set(mo_s) & set(mo_h)))

    # 3. is Missouri's sign free? drop each other state and recompute
    print("\n--- jackknife: drop one other state, recompute Missouri")
    for b, d in built.items():
        states = sorted(set(d["order"]))
        base = state_means(d["res"], d["order"], states, True)["MO"]
        print(f"  {b}: all states {base:+.2f}")
        for s in states:
            if s == "MO":
                continue
            keep = [x for x in states if x != s]
            v = state_means(d["res"], d["order"], keep, True)["MO"]
            print(f"     without {s}: {v:+7.2f}")
        # and against each other state alone
        for s in states:
            if s == "MO":
                continue
            v = state_means(d["res"], d["order"], ["MO", s], True)["MO"]
            print(f"     MO vs {s} alone: {v:+7.2f}")

    # 4. inside Missouri: does the srw figure survive dropping the shared position?
    d = built["srw"]
    states = sorted(set(d["order"]))
    idx = {s: [i for i, o in enumerate(d["order"]) if o == s] for s in states}
    mo_idx = idx["MO"]
    names = [p for st, p in d["sps"] if st == "MO"]
    print("\n--- srw Missouri, one position at a time (raw, before re-centring)")
    for i, nm in zip(mo_idx, names):
        print(f"     {d['res'][:, i, 0].mean():+7.2f}   {nm}")
    shared = out["mo_positions"]["shared"]
    if shared:
        drop = [i for i, nm in zip(mo_idx, names) if nm not in shared]
        alt = np.array([[r[drop, 0].mean() if s == "MO"
                         else r[idx[s], 0].mean() for s in states]
                        for r in d["res"]])
        alt = alt - alt.mean(axis=1, keepdims=True)
        v = dict(zip(states, alt.mean(axis=0)))["MO"]
        print(f"     srw Missouri without the position the two blocks share: "
              f"{v:+.2f}")
        out["srw_mo_without_shared"] = float(v)

    if a.record:
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "b41_crossstate_audit.json"
        dest.write_text(json.dumps(dict(
            stage="B41", diagnostic_only=True,
            diagnostic_reason="recheck of the Missouri cross-block agreement: "
                              "how much of the sign was free to disagree",
            **out), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
