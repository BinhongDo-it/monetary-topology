"""B106 step one: the labour accounts module is a two-index price field with
LABELLED classes, which is the one thing B2A's carrier could not supply.

B2A reads dispersion at a position: two borrowers in the same cell paying
different rates. That is an H0 statement. It cannot form a square, because the
borrowers carry no labels, so there is no "the same class at another position"
to compare against.

This module labels them. At every position (country, industry, year) it reports,
for each of 3 education x 3 age x 2 gender cells, that cell's share of employment
and its share of the wage bill. Their ratio is the class's pay relative to that
position's average, and it is a survey reading rather than an imputation, which
is what set the employee and self-employed split aside in B101-34.

So the field is p(position, class), and the question the framework asks of it is
the one it asks of every price field: is it the difference of a scalar on
positions, which here means is it additively separable,

    p(j, k) = a_j + b_k    <->    the class ladder is the same everywhere

Non-separability is the square: two positions by two classes, and the
difference in differences of log relative pay. The additive subspace of a J by K
table has dimension J + K - 1 out of JK, so the obstruction carries
(J - 1)(K - 1) independent cycles, which is B79's product count again.

This file only reads and describes. Nothing is tested here.

    python experiments/b106_labour_classes.py
    python experiments/b106_labour_classes.py --describe
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "labour accounts.csv"
CACHE = ROOT / "data" / "cache" / "b106_labour.npz"

#: The coarse partition the module reports everywhere: 3 x 3 x 2 = 18 cells.
#: Codes 11..17 are a finer breakdown present for a handful of positions only,
#: and mixing them in would double count, so the loader keeps the coarse set and
#: counts what it drops rather than filtering silently.
COARSE = {"1", "2", "3"}
GENDERS = {"1", "2"}


def build() -> dict:
    if not RAW.exists():
        sys.exit(f"missing: {RAW}")
    size = RAW.stat().st_size
    with RAW.open("rb") as fh:
        fh.seek(max(0, size - 4096))
        tail = fh.read().decode("utf-8", "replace").rstrip("\n")
    if tail.rsplit("\n", 1)[-1].count(",") < 8:
        sys.exit("the file looks truncated, not read")

    rows, n, fine, bad = [], 0, 0, 0
    with RAW.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n += 1
            ed, ag, ge = r["education"], r["age"], r["gender"]
            if ed not in COARSE or ag not in COARSE or ge not in GENDERS:
                fine += 1
                continue
            try:
                e, w = float(r["Share_E"]), float(r["Share_W"])
            except ValueError:
                bad += 1
                continue
            rows.append((r["nace_r2_code"], r["geo_code"], int(r["year"]),
                         ed + ag + ge, e, w))
    rows.sort()
    print(f"read {n:,} rows; kept {len(rows):,} on the coarse 3x3x2 partition, "
          f"skipped {fine:,} on the finer breakdown, {bad:,} non-numeric")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE,
        nace=np.array([r[0] for r in rows]),
        geo=np.array([r[1] for r in rows]),
        year=np.array([r[2] for r in rows], int),
        cls=np.array([r[3] for r in rows]),
        share_e=np.array([r[4] for r in rows], float),
        share_w=np.array([r[5] for r in rows], float),
        source=np.array([RAW.name, str(size), str(n)]),
    )
    print(f"cache -> {CACHE.relative_to(ROOT)} ({CACHE.stat().st_size:,} bytes)")
    return load()


def load() -> dict:
    d = np.load(CACHE, allow_pickle=False)
    return {k: d[k] for k in d.files}


def describe(d: dict) -> None:
    e, w = d["share_e"], d["share_w"]
    pos = {}
    for i, (a, b, c) in enumerate(zip(d["nace"], d["geo"], d["year"])):
        pos.setdefault((a, b, int(c)), []).append(i)

    print()
    print("=" * 74)
    print("1. THE WORST CELL, NOT THE AVERAGE  (rule 13 step 1)")
    sizes = np.array([len(v) for v in pos.values()])
    print(f"   {len(pos):,} positions; classes per position min {sizes.min()}, "
          f"median {int(np.median(sizes))}, max {sizes.max()}")
    full = int(np.sum(sizes == 18))
    print(f"   positions carrying all 18 classes: {full:,} "
          f"({100*full/len(pos):.2f}%)")

    print()
    print("=" * 74)
    print("2. DOES THE MODULE'S OWN ARITHMETIC HOLD?  shares should sum to 100")
    se = np.array([e[v].sum() for v in pos.values()])
    sw = np.array([w[v].sum() for v in pos.values()])
    print(f"   sum of Share_E over a position: median {np.median(se):.6f}, "
          f"worst |100 - sum| {np.max(np.abs(se-100)):.3e}")
    print(f"   sum of Share_W over a position: median {np.median(sw):.6f}, "
          f"worst |100 - sum| {np.max(np.abs(sw-100)):.3e}")
    print(f"   -> both summing to 100 means the relative wage w = Share_W/Share_E")
    print(f"      has an employment-weighted mean of exactly one at every")
    print(f"      position, so the position's level is normalised away by")
    print(f"      construction and what is left is the LADDER.")

    print()
    print("=" * 74)
    print("3. WHAT IS LOST TO A LOG")
    ok = (e > 0) & (w > 0)
    print(f"   {len(e):,} class-cells; usable for ln(Share_W/Share_E): "
          f"{ok.sum():,} ({100*ok.mean():.3f}%)")
    print(f"      Share_E == 0: {int(np.sum(e == 0)):,}   "
          f"Share_E < 0: {int(np.sum(e < 0)):,}")
    print(f"      Share_W == 0: {int(np.sum(w == 0)):,}   "
          f"Share_W < 0: {int(np.sum(w < 0)):,}")
    intact = sum(1 for v in pos.values() if len(v) == 18 and ok[v].all())
    print(f"   positions with all 18 classes usable: {intact:,} "
          f"({100*intact/len(pos):.2f}%)")

    print()
    print("=" * 74)
    print("4. THE LADDER ITSELF")
    p = np.log(w[ok] / e[ok])
    print(f"   ln relative pay: p1 {np.percentile(p,1):+.3f}  "
          f"median {np.median(p):+.3f}  p99 {np.percentile(p,99):+.3f}")
    by = {}
    for c, x in zip(d["cls"][ok], p):
        by.setdefault(c, []).append(x)
    print("   by class (education, age, gender), median ln relative pay:")
    for c in sorted(by):
        v = np.array(by[c])
        print(f"      {c}  n={len(v):>6,d}  median {np.median(v):+.4f}  "
              f"sd {v.std():.4f}")
    print("   -> a ladder that were the same everywhere would have sd near zero")
    print("      inside each row once the position level is taken out. The next")
    print("      step is exactly that decomposition, and it is not run here.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--describe", action="store_true")
    a = ap.parse_args()
    d = load() if (a.describe and CACHE.exists()) else build()
    describe(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
