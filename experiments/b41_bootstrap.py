"""B41-3: the time mean of each square, with an error that respects the panel.

Two things break an ordinary standard error here. The square is persistent in
time, so days are not separate readings; and the squares are cross-correlated,
because a set of m positions and n commodities admits only (m-1)(n-1)
independent cycles however many pairs can be written down.

Both are handled the same way. An independent basis of cycles is chosen first,
anchored on one reference position, so the count is the topological one rather
than the combinatorial one. Then a moving-block bootstrap resamples whole runs
of consecutive dates, the same dates for every series at once, which keeps the
serial dependence inside a block and the cross-sectional dependence across
series.

Block length is a choice, so it is not made once and hidden: results are printed
for several lengths and the reader sees whether the answer moves. The number of
resamples is likewise justified by printing how much the interval endpoints move
between two draw counts rather than by citing a convention.

Reads only what b41_ams_probe.py has cached. No network, no key.

    python experiments/b41_bootstrap.py --report 3186
    python experiments/b41_bootstrap.py --report 3186 --blocks 20 60 100 --draws 500
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_persistence as P  # noqa: E402
import b41_square_smoke as S  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "b41"


def as_date(d: str) -> date:
    return date(int(d[6:]), int(d[:2]), int(d[3:5]))


def panel(by_day: dict, ca: str, cb: str):
    """{(pos_i, pos_j, wheat class): {date: value}} on the current window."""
    out: dict[tuple, dict[str, float]] = defaultdict(dict)
    for day, rows in by_day.items():
        by_key, _ = S.cells(rows)
        for s in S.squares(by_key, ca, cb):
            if s["gap"] != 0 or not s["same_facility"]:
                continue
            if not s["key_a"][3].startswith("current"):
                continue
            out[(s["pos_i"], s["pos_j"], s["key_b"][1])][day] = s["mid"]
    return out


def anchors_of(cols: dict) -> list[str]:
    return sorted({p for k in cols for p in k[:2]})


def basis(cols: dict, forced: str | None = None):
    """An independent set of cycles, anchored on the busiest position.

    A square between two positions that both differ from the anchor is the
    difference of two anchored squares, so it carries no separate information.
    Orientation is fixed as anchor first, and a square stored the other way
    round enters with its sign flipped."""
    seen = defaultdict(int)
    for (i, j, _), obs in cols.items():
        seen[i] += len(obs)
        seen[j] += len(obs)
    anchor = forced or max(seen, key=seen.get)
    chosen = {}
    for (i, j, w), obs in cols.items():
        if i == anchor:
            chosen[(j, w)] = {d: +v for d, v in obs.items()}
        elif j == anchor:
            chosen[(i, w)] = {d: -v for d, v in obs.items()}
    return anchor, chosen


def block_boot(series: dict, dates: list[str], block: int, draws: int, rng):
    """Moving-block bootstrap, the same date blocks for every series."""
    n = len(dates)
    starts = max(n - block + 1, 1)
    nblocks = max(n // block, 1)
    out = {k: [] for k in series}
    for _ in range(draws):
        picked = []
        for _ in range(nblocks):
            s0 = rng.randrange(starts)
            picked.extend(dates[s0:s0 + block])
        for k, obs in series.items():
            vals = [obs[d] for d in picked if d in obs]
            out[k].append(mean(vals) if vals else float("nan"))
    return out


def pct(xs: list[float], q: float) -> float:
    ok = sorted(x for x in xs if x == x)
    if not ok:
        return float("nan")
    i = min(int(q * (len(ok) - 1) + 0.5), len(ok) - 1)
    return ok[i]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, required=True)
    ap.add_argument("--pair", nargs=2, default=["Soybeans", "Wheat"])
    ap.add_argument("--blocks", type=int, nargs="+", default=[20, 60, 100])
    ap.add_argument("--draws", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260902)
    a = ap.parse_args()

    by_day = P.load_all(a.report)
    cols = panel(by_day, *a.pair)
    anchor, ser = basis(cols)
    print(f"\n{len(cols)} squares in all; anchor position {anchor!r}")
    print(f"{len(ser)} independent cycles after anchoring, which is the (m-1)(n-1) count")
    dates = sorted({d for obs in ser.values() for d in obs}, key=as_date)
    print(f"{len(dates)} distinct dates in the union; coverage per cycle: "
          f"{sorted(len(v) for v in ser.values())}")

    print(f"\nmean of each cycle by calendar year, printed rather than summarised:")
    years = sorted({d[6:] for d in dates})
    hdr = f"{'cycle':<34}" + "".join(f"{y:>9}" for y in years) + f"{'all':>9}"
    print(hdr); print("-" * len(hdr))
    for k, obs in sorted(ser.items()):
        line = f'{(k[0].split("|")[0].strip() + " " + ("HRS" if "Spring" in k[1] else "HRW")):<34}'
        for y in years:
            v = [x for d, x in obs.items() if d[6:] == y]
            line += f"{mean(v):>+9.1f}" if v else f'{"":>9}'
        line += f"{mean(obs.values()):>+9.1f}"
        print(line)

    rng = random.Random(a.seed)
    results = {}
    for block in a.blocks:
        boots = block_boot(ser, dates, block, a.draws, rng)
        excl = 0
        print(f"\nblock length {block} trading days, {a.draws} resamples")
        hdr = f"{'cycle':<34}{'mean':>9}{'5%':>9}{'95%':>9}{'zero':>7}"
        print(hdr); print("-" * len(hdr))
        for k, obs in sorted(ser.items()):
            m = mean(obs.values())
            lo, hi = pct(boots[k], 0.05), pct(boots[k], 0.95)
            out = not (lo <= 0 <= hi)
            excl += out
            name = k[0].split("|")[0].strip() + " " + ("HRS" if "Spring" in k[1] else "HRW")
            print(f"{name:<34}{m:>+9.2f}{lo:>+9.2f}{hi:>+9.2f}{'OUT' if out else 'in':>7}")
        print(f"  {excl} of {len(ser)} independent cycles have a 90 percent "
              f"interval clear of zero")
        results[block] = dict(excluded=excl, total=len(ser),
                              bounds={f"{k[0]}|{k[1]}": [pct(boots[k], 0.05),
                                                         pct(boots[k], 0.95)]
                                      for k in ser})

    half = max(a.draws // 2, 50)
    rng2 = random.Random(a.seed + 1)
    b1 = block_boot(ser, dates, a.blocks[0], half, rng2)
    moves = [abs(pct(b1[k], 0.05) - results[a.blocks[0]]["bounds"][f"{k[0]}|{k[1]}"][0])
             for k in ser]
    print(f"\nhalving the resamples to {half} moves the 5 percent endpoint by at most "
          f"{max(moves):.2f} cents, median {sorted(moves)[len(moves)//2]:.2f}. "
          f"That is what justifies {a.draws}, not a convention.")

    # The count of cycles clear of zero is not basis free: a different anchor
    # spans the same space with a different eight vectors, and the nonzero part
    # is not spread evenly over them. Print every anchor rather than the one
    # that flatters, and quote the floor.
    print("\nthe same space through every anchor, since the count is basis dependent:")
    sweep = {}
    for anc in anchors_of(cols):
        _, ser_a = basis(cols, anc)
        if len(ser_a) != len(ser):
            continue
        rng_a = random.Random(a.seed + 17)
        line = f'  {anc.split("|")[0].strip():<18}'
        counts = []
        for block in a.blocks:
            bo = block_boot(ser_a, dates, block, a.draws, rng_a)
            e = sum(not (pct(bo[k], 0.05) <= 0 <= pct(bo[k], 0.95)) for k in ser_a)
            counts.append(e)
            line += f"  block {block}: {e}/{len(ser_a)}"
        sweep[anc] = counts
        print(line)
    if sweep:
        floor = min(min(v) for v in sweep.values())
        print(f"  floor across anchors and block lengths: {floor} of {len(ser)} "
              f"independent cycles clear of zero. Quote the floor.")

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"bootstrap_{a.report}.json"
    dest.write_text(json.dumps(dict(report=a.report, pair=a.pair, anchor=anchor,
                                    draws=a.draws, seed=a.seed, results=results,
                                    anchor_sweep={k: v for k, v in sweep.items()}),
                               ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8")
    print(f"wrote {dest.relative_to(REPO)}")


if __name__ == "__main__":
    main()
