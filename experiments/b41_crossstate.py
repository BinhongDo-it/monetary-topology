"""B41-3 pooled across states: the cycles no single state's rectangle contains.

Every reading so far has been inside one state, and the model being tested is not
a statement about a state. A single scalar on positions and a single scalar on
commodities is a global claim, and the graph the claim lives on does not stop at a
state line: the commodity nodes are shared, so a position in Kansas and a position
in Ohio are joined through the soybean node whether or not anyone ever quotes them
side by side. The union graph is therefore connected, its cycle rank exceeds the
sum of the state cycle ranks, and the difference is a set of independent cycles
that no state rectangle has ever contained.

Those cycles are the same object as the within-state ones. Every term that depends
only on where a place is cancels between the two commodities, so a cycle spanning
two states is not measuring the distance between them.

Two blocks exist and they are set by the wheat class rather than chosen here. Soft
red winter wheat is quoted with soybeans in the eastern states, hard red winter in
the plains, and Missouri is in both.

The futures month rule that applies inside a state applies across them and is not
weaker: a commodity whose month is not the same at every position in the rectangle
on a given day drops that day whole, because differencing across months would
import a calendar spread. Measured before the design was written: the states agree
on one month for soybeans on 74 percent of days, soft red winter on 82, hard red
winter on 90.

    python experiments/b41_crossstate.py --block srw --describe
    python experiments/b41_crossstate.py --block srw --run
    python experiments/b41_crossstate.py --block hrw --run
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_joint as J
import b41_known_answer as K
import b41_persistence as P

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "b41"

SOY = ("Soybeans", "", "US #1", "", "Conventional", "Delivered", "Truck")
SRW = ("Wheat", "Soft Red Winter", "US #2", "Ordinary", "Conventional", "Delivered", "Truck")
HRW = ("Wheat", "Hard Red Winter", "US #1", "Ordinary", "Conventional", "Delivered", "Truck")
BLOCKS = {"srw": (SOY, SRW), "hrw": (SOY, HRW)}


def iso(s: str) -> str:
    s = (s or "").strip()
    return f"{s[6:10]}-{s[0:2]}-{s[3:5]}" if len(s) >= 10 and s[2] == "/" else s[:10]


def pooled(pair) -> dict:
    """day -> {(commodity, (state, position)): (midpoint, futures month)}."""
    struct = json.loads((OUT / "structure.json").read_text(encoding="utf-8"))
    out = defaultdict(dict)
    for r in struct["reports"]:
        rid, state = r["report"], r["state"]
        try:
            by = P.load_all(rid)
        except SystemExit:
            continue
        for day, rows in by.items():
            d = iso(day)
            for z in rows:
                if z.get("quote_type") != "Basis" or z.get("sale Type") != "Bid":
                    continue
                if z.get("delivery_start") or z.get("delivery_end"):
                    continue
                m_lo, m_hi = z.get("basis Min Futures Month"), z.get("basis Max Futures Month")
                if not m_lo or m_lo != m_hi:
                    continue
                com = (z.get("commodity"), z.get("class") or "", z.get("grade") or "",
                       z.get("protein") or "", z.get("conventional") or "",
                       z.get("freight") or "", z.get("trans_mode") or "")
                if com not in pair:
                    continue
                lo, hi = z.get("basis Min"), z.get("basis Max")
                pos = J.S.position(z)
                if lo is None or hi is None or not pos:
                    continue
                out[d][(com, (state, pos))] = ((float(lo) + float(hi)) / 2, m_lo)
    return out


def choose(per_day: dict, pair, min_coverage: float):
    seen = defaultdict(int)
    for c in per_day.values():
        for k in c:
            seen[k] += 1
    need = min_coverage * len(per_day)
    keep = {k for k, v in seen.items() if v >= need}
    sps = sorted({k[1] for k in keep if all((c, k[1]) in keep for c in pair)})
    return sps


def matrices(per_day: dict, pair, sps: list):
    """Complete days only, and one futures month per commodity across the block."""
    days, mats = [], []
    dropped = defaultdict(int)
    for d in sorted(per_day):
        c = per_day[d]
        if not all((cm, sp) in c for cm in pair for sp in sps):
            dropped["a position is missing"] += 1
            continue
        bad = False
        for cm in pair:
            if len({c[(cm, sp)][1] for sp in sps}) != 1:
                dropped["the futures month differs across positions"] += 1
                bad = True
                break
        if bad:
            continue
        days.append(d)
        mats.append(np.array([[c[(cm, sp)][0] for cm in pair] for sp in sps], float))
    return days, mats, dropped


def state_df(sps: list) -> dict:
    per = defaultdict(int)
    for s, _ in sps:
        per[s] += 1
    return {s: (n - 1) for s, n in per.items() if n >= 2}


def run(block: str, min_coverage: float, blocks: list[int], draws: int,
        seed: int, describe_only: bool) -> None:
    pair = BLOCKS[block]
    per_day = pooled(pair)
    print(f"\nblock {block}: {pair[1][1]} against soybeans")
    print(f"pooled days with at least one cell: {len(per_day)}")
    sps = choose(per_day, pair, min_coverage)
    if len(sps) < 2:
        print(f"fewer than two positions carry both at coverage {min_coverage:.0%}")
        return
    by_state = defaultdict(list)
    for s, p in sps:
        by_state[s].append(p)
    print(f"positions carrying both at coverage >= {min_coverage:.0%}: {len(sps)} "
          f"across {len(by_state)} states")
    for s in sorted(by_state):
        print(f"   {s}: {len(by_state[s])}")
    days, mats, dropped = matrices(per_day, pair, sps)
    for k, v in dropped.items():
        print(f"   {v:5d} days dropped: {k}")
    df = (len(sps) - 1) * (len(pair) - 1)
    inside = sum(state_df(sps).values())
    print(f"\ncycle rank of the pooled block   (|P|-1)(|C|-1) = {df}")
    print(f"cycle rank inside the states       sum over states = {inside}")
    print(f"cycles no state rectangle contains                = {df - inside}")
    print(f"complete days: {len(days)}")
    if describe_only or len(days) < 30:
        if len(days) < 30 and not describe_only:
            print("too few complete days to read")
        return

    res = []
    mask = np.ones(mats[0].shape, bool)
    for m in mats:
        r, _, _ = J.additive_residual(m, mask)
        res.append(r)
    res = np.array(res)

    # The cycles pooling adds are exactly the state by commodity interaction,
    # and there are k-1 of them for k states: a state block with p positions
    # carries p-1 cycles of its own, and the union carries (sum of p) - 1, so
    # the difference is the number of blocks minus one. Averaging the residual
    # over each state's own positions leaves precisely that component and drops
    # every cycle a single state already contained.
    order = [sp[0] for sp in sps]
    states_sorted = sorted(set(order))
    idx = {s: [i for i, o in enumerate(order) if o == s] for s in states_sorted}
    cross = np.array([[r[idx[s], 0].mean() for s in states_sorted] for r in res])
    cross = cross - cross.mean(axis=1, keepdims=True)
    k = len(states_sorted)
    cross_res = cross[:, :, None]
    cross_persistent = float(np.linalg.norm(cross.mean(axis=0)) / np.sqrt(k - 1))
    cross_daily = [float(np.linalg.norm(row) / np.sqrt(k - 1)) for row in cross]
    cross_magnitude = statistics.median(cross_daily)
    cross_p = K.boot_p(cross_res, blocks, draws, random.Random(seed + 1))
    print(f"\ncross-state component, the {k - 1} cycles no state rectangle contains")
    print(f"   persistent {cross_persistent:6.2f}   magnitude {cross_magnitude:6.2f}   "
          f"persistence {cross_persistent / cross_magnitude:.3f}")
    for b, pv in sorted(cross_p.items()):
        print(f"   block {b:4d}: recentred bootstrap p = {pv:.4f}")
    print("   per state, mean persistent residual in the soybean column, cents:")
    for s, v in zip(states_sorted, cross.mean(axis=0)):
        print(f"      {s:6s} {v:+7.2f}")
    persistent = K.persistent_rms(res, df)
    daily = [float(np.linalg.norm(r) / np.sqrt(df)) for r in res]
    magnitude = statistics.median(daily)
    rng = random.Random(seed)
    p_by_block = K.boot_p(res, blocks, draws, rng)
    print(f"\npersistent residual per cycle : {persistent:.2f} cents")
    print(f"magnitude, median over days   : {magnitude:.2f} cents")
    print(f"persistence                   : {persistent / magnitude:.3f}")
    for b, pv in sorted(p_by_block.items()):
        print(f"block {b:4d} trading days: recentred bootstrap p = {pv:.4f}")
    payload = dict(block=block, coverage=min_coverage, df=df, inside=inside,
                   new_cycles=df - inside, days=len(days),
                   states=sorted(by_state), positions=[list(x) for x in sps],
                   persistent=persistent, magnitude=magnitude,
                   persistence=persistent / magnitude,
                   cross_persistent=cross_persistent, cross_magnitude=cross_magnitude,
                   cross_by_state={s: float(v) for s, v in
                                   zip(states_sorted, cross.mean(axis=0))},
                   cross_p_by_block={str(a_): b_ for a_, b_ in cross_p.items()},
                   p_by_block={str(k): v for k, v in p_by_block.items()})
    dest = OUT / f"crossstate_{block}.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8", newline="\n")
    print(f"wrote {dest}")


def cross_stat(res: np.ndarray, order: list, k_states: list):
    """The state by commodity component, and the two readings taken from it."""
    idx = {s: [i for i, o in enumerate(order) if o == s] for s in k_states}
    cross = np.array([[r[idx[s], 0].mean() for s in k_states] for r in res])
    cross = cross - cross.mean(axis=1, keepdims=True)
    k = len(k_states)
    persistent = float(np.linalg.norm(cross.mean(axis=0)) / np.sqrt(k - 1))
    daily = [float(np.linalg.norm(row) / np.sqrt(k - 1)) for row in cross]
    return cross, persistent, statistics.median(daily)


def floor(block: str, min_coverage: float, blocks: list[int], draws: int,
          seed: int, reps: int) -> None:
    """What the cross-state statistic reads when there is no cross-state structure.

    The synthetic field carries everything the real one carries except the thing
    being measured: global position and commodity effects taken from the real fit,
    a persistent position by commodity interaction inside each state scaled to the
    measured one and centred within that state so it contributes nothing across
    states, and autocorrelated noise at the measured coefficient. A reading on this
    field is the floor, and the real reading is only interesting against it.
    """
    pair = BLOCKS[block]
    per_day = pooled(pair)
    sps = choose(per_day, pair, min_coverage)
    days, mats, _ = matrices(per_day, pair, sps)
    if len(days) < 30:
        print("too few complete days"); return
    order = [sp[0] for sp in sps]
    states_sorted = sorted(set(order))
    idx = {s: [i for i, o in enumerate(order) if o == s] for s in states_sorted}
    mask = np.ones(mats[0].shape, bool)
    res = np.array([J.additive_residual(m, mask)[0] for m in mats])
    _, real_p, real_m = cross_stat(res, order, states_sorted)

    # measured inputs: within-state persistent interaction, and the noise
    mean_res = res.mean(axis=0)
    within = mean_res.copy()
    for s in states_sorted:
        within[idx[s]] -= within[idx[s]].mean(axis=0)
    within_sd = float(np.sqrt((within ** 2).mean()))
    dev = res - mean_res
    noise_sd = float(np.sqrt((dev ** 2).mean()))
    flat = dev[:, :, 0]
    rho = float(np.mean([np.corrcoef(flat[:-1, j], flat[1:, j])[0, 1]
                         for j in range(flat.shape[1])]))
    n, R, C = res.shape
    print(f"\n" + f"block {block}: {n} days, {len(states_sorted)} states, "
          f"{len(sps)} positions")
    print(f"measured within-state persistent interaction sd {within_sd:.2f} cents, "
          f"noise sd {noise_sd:.2f}, lag-one autocorrelation {rho:+.3f}")
    print(f"the real panel reads persistent {real_p:.2f}, magnitude {real_m:.2f}")
    rng = np.random.default_rng(seed)
    got = []
    for rep in range(reps):
        w = rng.normal(0.0, within_sd, size=(R, C))
        w = w - w.mean(axis=1, keepdims=True)
        for s in states_sorted:
            w[idx[s]] -= w[idx[s]].mean(axis=0)
        noise = K.ar1_noise((n, R, C), rho, noise_sd, rng)
        synth = np.array([w + noise[t] for t in range(n)])
        sres = np.array([J.additive_residual(m, mask)[0] for m in synth])
        _, ps, ms = cross_stat(sres, order, states_sorted)
        cross_s = cross_stat(sres, order, states_sorted)[0]
        pv = K.boot_p(cross_s[:, :, None], blocks, draws, random.Random(seed + rep))
        got.append(ps)
        print(f"   rep {rep + 1}: persistent {ps:6.2f}  magnitude {ms:6.2f}  "
              + "  ".join(f"p@{b} {v:.3f}" for b, v in sorted(pv.items())))
    lo, hi = min(got), max(got)
    mean_floor = sum(got) / len(got)
    print(f"   five reps span {lo:.2f} to {hi:.2f}; "
          f"the real cross-state reading is {real_p / mean_floor:.1f} times the mean floor")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", choices=sorted(BLOCKS), required=True)
    ap.add_argument("--min-coverage", type=float, default=0.60)
    ap.add_argument("--blocks", type=int, nargs="+", default=[20, 100])
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--floor", action="store_true",
                    help="what the cross-state statistic reads with no cross-state "
                         "structure present")
    ap.add_argument("--reps", type=int, default=5)
    a = ap.parse_args()
    if a.floor:
        floor(a.block, a.min_coverage, a.blocks, a.draws, a.seed, a.reps)
        return 0
    run(a.block, a.min_coverage, a.blocks, a.draws, a.seed,
        a.describe or not a.run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
