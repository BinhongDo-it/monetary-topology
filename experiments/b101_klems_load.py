"""B101 step one: pull the six series the station needs out of EU KLEMS, cache
them, and describe the object before anything is tested.

Order is the one rule 13 fixes: measure the worst cell first, then describe,
then ask whether the description has already answered the question. No sampling
and no test here.

Which file, and why.  The release ships ``growth accounts basic`` and ``growth
accounts extended``.  Extended adds the intangible-capital decomposition and
drops the value-added LEVEL series: it carries ``VAadj_G`` only, a growth rate
on a value-added concept that capitalises intangibles national accounts do not.
That is a different Y, so under D11 it is a different definition and cannot sit
in the same column.  This station reads BASIC, which is the national-accounts
construction GRV used.  Extended is a second arm, reported separately if it runs.

    python experiments/b101_klems_load.py            # build the cache, describe
    python experiments/b101_klems_load.py --describe # describe from the cache
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "growth accounts basic.csv"
CACHE = ROOT / "data" / "cache" / "b101_klems_basic.npz"

#: The six series, and what each is for. Nothing else is read.
WANT = {
    "VA_Q":   "value added, volume            -> Y",
    "LAB_QI": "labour services, quantity index -> L",
    "CAP_QI": "capital services, quantity index-> K",
    "VA_CP":  "value added, current prices     -> the share's denominator",
    "LAB":    "labour compensation             -> the share's numerator",
    "CAP":    "capital compensation            -> asked for so the identity can be checked",
}


def build() -> dict:
    """Stream the raw file once. Never loads it whole.

    Rule 6: downloaded data is treated as unrepeatable, so this only reads. It
    also refuses a file whose last line is short, rather than reading a
    truncated download silently.
    """
    if not RAW.exists():
        sys.exit(f"missing: {RAW}")
    size = RAW.stat().st_size
    with RAW.open("rb") as fh:
        fh.seek(max(0, size - 4096))
        tail = fh.read().decode("utf-8", "replace").rstrip("\n")
    last = tail.rsplit("\n", 1)[-1]
    if last.count(",") < 7:
        sys.exit(f"last line has {last.count(',')} commas, expected at least 7: "
                 f"the file looks truncated, not read.\n  {last[:120]}")

    table: dict[tuple[str, str, int], dict[str, float]] = {}
    n = kept = bad = 0
    with RAW.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n += 1
            v = row["var"]
            if v not in WANT:
                continue
            raw = row["value"]
            if raw in ("NA", "", "NaN"):
                bad += 1
                continue
            try:
                x = float(raw)
            except ValueError:
                bad += 1
                continue
            key = (row["nace_r2_code"], row["geo_code"], int(row["year"]))
            table.setdefault(key, {})[v] = x
            kept += 1
    print(f"read {n:,} rows, kept {kept:,} of the six series, "
          f"{bad:,} non-numeric, {len(table):,} (industry, country, year) cells")

    keys = sorted(table)
    order = sorted(WANT)
    vals = np.full((len(keys), len(order)), np.nan)
    for r, k in enumerate(keys):
        for c, v in enumerate(order):
            if v in table[k]:
                vals[r, c] = table[k][v]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE,
        nace=np.array([k[0] for k in keys]),
        geo=np.array([k[1] for k in keys]),
        year=np.array([k[2] for k in keys]),
        vars=np.array(order),
        values=vals,
        source=np.array([RAW.name, str(size), str(n)]),
    )
    print(f"cache -> {CACHE.relative_to(ROOT)}  ({CACHE.stat().st_size:,} bytes)")
    return load()


def load() -> dict:
    d = np.load(CACHE, allow_pickle=False)
    return {k: d[k] for k in d.files}


def describe(d: dict) -> None:
    nace, geo, year = d["nace"], d["geo"], d["year"]
    order = list(d["vars"]); V = d["values"]
    col = {v: V[:, i] for i, v in enumerate(order)}

    print()
    print("=" * 74)
    print("1. THE WORST CELL, NOT THE AVERAGE  (rule 13 step 1)")
    need = ["VA_Q", "LAB_QI", "CAP_QI", "VA_CP", "LAB"]
    ok = np.ones(len(nace), bool)
    for v in need:
        ok &= np.isfinite(col[v])
    print(f"   {len(nace):,} cells on disk; {ok.sum():,} carry all five the station needs "
          f"({100*ok.sum()/len(nace):.1f}%)")
    # a square needs one (industry, country) present in two adjacent years, and
    # a second country in the same two. Count the country-years per industry.
    pairs = {}
    for i in np.flatnonzero(ok):
        pairs.setdefault(nace[i], {}).setdefault(geo[i], set()).add(int(year[i]))
    runs = []
    for j, gs in pairs.items():
        for g, ys in gs.items():
            ys = sorted(ys)
            best = cur = 1
            for a, b in zip(ys, ys[1:]):
                cur = cur + 1 if b == a + 1 else 1
                best = max(best, cur)
            runs.append((j, g, len(ys), best))
    runs.sort(key=lambda r: r[3])
    print(f"   {len(runs):,} (industry, country) series. Longest run of consecutive years:")
    print(f"      worst three: " + ", ".join(f"{j}/{g} run {b}" for j, g, _, b in runs[:3]))
    print(f"      median {int(np.median([r[3] for r in runs]))}, "
          f"max {max(r[3] for r in runs)}")
    thin = sum(1 for r in runs if r[3] < 2)
    print(f"      series that cannot form a single square (run < 2): {thin}")
    per_ind = {j: len(gs) for j, gs in pairs.items()}
    lo = sorted(per_ind.items(), key=lambda kv: kv[1])[:3]
    print(f"   countries per industry: min {min(per_ind.values())} "
          f"({', '.join(f'{j}={c}' for j, c in lo)}), "
          f"median {int(np.median(list(per_ind.values())))}, max {max(per_ind.values())}")
    print("   a square needs TWO countries in the SAME industry and the SAME two years,")
    print("   so an industry with one country contributes nothing.")

    print()
    print("=" * 74)
    print("2. IS CAPITAL COMPENSATION A RESIDUAL?  VA_CP == LAB + CAP ?")
    m = np.isfinite(col["VA_CP"]) & np.isfinite(col["LAB"]) & np.isfinite(col["CAP"])
    resid = col["VA_CP"][m] - (col["LAB"][m] + col["CAP"][m])
    rel = np.abs(resid) / np.maximum(np.abs(col["VA_CP"][m]), 1e-12)
    print(f"   {m.sum():,} cells have all three. |VA - (LAB + CAP)| / |VA|:")
    for q in (50, 90, 99, 100):
        print(f"      p{q:<3d} {np.percentile(rel, q):.3e}")
    print(f"   exact to 1e-12: {(rel < 1e-12).sum():,} of {m.sum():,} "
          f"({100*(rel<1e-12).mean():.2f}%)")
    print("   -> if this is an identity, CAP carries no information the share does not,")
    print("      and the capital-side wedge has no independent object, as section 5 of")
    print("      the theory note says it cannot.")

    print()
    print("=" * 74)
    print("3. THE OBJECT ITSELF: the labour share against the log capital-labour ratio")
    s = col["LAB"][ok] / col["VA_CP"][ok]
    x = np.log(col["LAB_QI"][ok] / col["CAP_QI"][ok])
    fin = np.isfinite(s) & np.isfinite(x)
    s, x = s[fin], x[fin]
    print(f"   {fin.sum():,} usable cells")
    print(f"   share  min {s.min():+.3f}  p1 {np.percentile(s,1):+.3f}  "
          f"median {np.median(s):+.3f}  p99 {np.percentile(s,99):+.3f}  max {s.max():+.3f}")
    print(f"   share outside [0, 1]: {((s < 0) | (s > 1)).sum():,} "
          f"({100*((s<0)|(s>1)).mean():.2f}%)")
    print(f"   ln(L/K) min {x.min():+.3f}  median {np.median(x):+.3f}  max {x.max():+.3f}")
    b, a = np.polyfit(x, s, 1)
    r = s - (a + b * x)
    print(f"   pooled fit  share = {a:+.4f} {b:+.4f} * ln(L/K)   residual sd {r.std():.4f}")
    print(f"   -> the residual sd is the part of the share that the mix does not")
    print(f"      explain. GRV let it vary by country-industry; the station reads the")
    print(f"      area that variation sweeps.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--describe", action="store_true",
                    help="describe from the cache, do not rebuild it")
    a = ap.parse_args()
    d = load() if (a.describe and CACHE.exists()) else build()
    describe(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
