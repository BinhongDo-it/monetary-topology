"""B101 step eight: pull the capital stock LEVELS out of the capital accounts
module, cache them, and say which mix definitions the two new files make live.

Why this file exists.  B101-18 closed void: with the smoothing sigma = alpha_ij
+ beta_j ln(K/L), a cross-country loop's holonomy is exactly the area the
intercept sweeps, and the fitted intercept returns alpha - beta * e, where e is
the series' own 2015 level of ln(L/K).  The growth accounts module carries the
mix as a QUANTITY INDEX based at 100 in 2015 in every series, so e reads exactly
zero for every country and the cross-country half cannot be formed there.  The
capital accounts module carries the stock in national currency with no index
base, which is half of what e needs.

This step does not test anything.  It reads, checks the arithmetic the module
claims about itself, and enumerates the mix definitions (rule 13 steps 1 to 3,
and D12: enumerate the whole set before choosing one).

    python experiments/b101_capital_load.py
    python experiments/b101_capital_load.py --describe
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "capital accounts.csv"
CACHE = ROOT / "data" / "cache" / "b101_capital.npz"
GROWTH = ROOT / "data" / "cache" / "b101_klems_basic.npz"

#: The ten asset types the module splits GFCF into, plus the total.
ASSETS = ["CT", "Cult", "IT", "OCon", "OIPP", "OMach", "RD", "Rstruc",
          "Soft_DB", "TraEq"]
#: What is read.  K_ is the stock at current prices in national currency, Kq_ is
#: the same stock as a quantity index, Kpyp_ is at previous year prices.
WANT = (["K_GFCF", "Kq_GFCF", "Kpyp_GFCF"]
        + [f"K_{a}" for a in ASSETS])


def build() -> dict:
    if not RAW.exists():
        sys.exit(f"missing: {RAW}")
    size = RAW.stat().st_size
    with RAW.open("rb") as fh:
        fh.seek(max(0, size - 8192))
        tail = fh.read().decode("utf-8", "replace").rstrip("\n")
    last = tail.rsplit("\n", 1)[-1]
    if last.count(",") < 80:
        sys.exit(f"last line has {last.count(',')} commas, expected at least 80: "
                 f"the file looks truncated, not read.\n  {last[:160]}")

    keys: list[tuple[str, str, int]] = []
    rows: list[list[float]] = []
    n = bad = 0
    with RAW.open(newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        missing = [w for w in WANT if w not in rd.fieldnames]
        if missing:
            sys.exit(f"columns absent from the file: {missing}")
        for row in rd:
            n += 1
            out = []
            for w in WANT:
                raw = row[w]
                if raw in ("NA", "", "NaN"):
                    out.append(np.nan); bad += 1
                else:
                    try:
                        out.append(float(raw))
                    except ValueError:
                        out.append(np.nan); bad += 1
            keys.append((row["nace_r2_code"], row["geo_code"], int(row["year"])))
            rows.append(out)
    print(f"read {n:,} rows, {bad:,} non-numeric fields, {len(keys):,} cells")

    idx = sorted(range(len(keys)), key=lambda i: keys[i])
    vals = np.array([rows[i] for i in idx], float)
    ks = [keys[i] for i in idx]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE,
        nace=np.array([k[0] for k in ks]),
        geo=np.array([k[1] for k in ks]),
        year=np.array([k[2] for k in ks]),
        vars=np.array(WANT),
        values=vals,
        source=np.array([RAW.name, str(size), str(n)]),
    )
    print(f"cache -> {CACHE.relative_to(ROOT)}  ({CACHE.stat().st_size:,} bytes)")
    return load()


def load() -> dict:
    d = np.load(CACHE, allow_pickle=False)
    return {k: d[k] for k in d.files}


def _cols(d):
    return {v: d["values"][:, i] for i, v in enumerate(list(d["vars"]))}


def describe(d: dict) -> None:
    nace, geo, year = d["nace"], d["geo"], d["year"]
    col = _cols(d)

    print()
    print("=" * 74)
    print("8.1  IS THERE AN INDEX BASE?  (the thing that killed B101-18)")
    print("     a series based at 100 reads exactly 100 once per series.")
    for v in ["K_GFCF", "Kq_GFCF", "Kpyp_GFCF"]:
        x = col[v]
        f = np.isfinite(x)
        at100 = int(np.sum(f & (np.abs(x - 100.0) < 1e-9)))
        print(f"     {v:<12s} n={f.sum():>7,d}  median {np.nanmedian(x):>16,.1f}  "
              f"max {np.nanmax(x):>18,.1f}   ==100 in {at100:,} rows")

    print()
    print("=" * 74)
    print("8.2  KNOWN ANSWER: does the total equal the sum of its ten asset types?")
    parts = np.array([col[f"K_{a}"] for a in ASSETS])
    tot = col["K_GFCF"]
    m = np.isfinite(tot) & np.all(np.isfinite(parts), axis=0)
    rel = np.abs(parts[:, m].sum(axis=0) - tot[m]) / np.maximum(np.abs(tot[m]), 1e-12)
    print(f"     {m.sum():,} cells carry the total and all ten parts")
    for q in (50, 90, 99, 100):
        print(f"       p{q:<3d} {np.percentile(rel, q):.3e}")
    print(f"     within 1e-9: {(rel < 1e-9).sum():,} ({100*(rel<1e-9).mean():.2f}%)")

    print()
    print("=" * 74)
    print("8.3  COVERAGE AGAINST THE GROWTH ACCOUNTS CELLS")
    if not GROWTH.exists():
        print("     growth cache absent; run b101_klems_load.py first")
        return
    g = np.load(GROWTH, allow_pickle=False)
    gcol = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    gkey = {(a, b, int(c)) for a, b, c in zip(g["nace"], g["geo"], g["year"])
            if True}
    have_lab = {(a, b, int(c)) for a, b, c, L in
                zip(g["nace"], g["geo"], g["year"], gcol["LAB"]) if np.isfinite(L)}
    kkey = {(a, b, int(c)) for a, b, c, K in
            zip(nace, geo, year, col["K_GFCF"]) if np.isfinite(K)}
    both = have_lab & kkey
    print(f"     growth cells with LAB      : {len(have_lab):,}")
    print(f"     capital cells with K_GFCF  : {len(kkey):,}")
    print(f"     both                       : {len(both):,}")
    print(f"     LAB present, K_GFCF absent : {len(have_lab - kkey):,}")
    yrs = sorted({y for _, _, y in both})
    print(f"     years {yrs[0]}..{yrs[-1]}")
    c15 = [k for k in both if k[2] == 2015]
    inds = {k[0] for k in c15}
    per = {}
    for j, gg, _ in c15:
        per.setdefault(j, set()).add(gg)
    sizes = sorted(len(v) for v in per.values())
    print(f"     2015 cross-section: {len(c15):,} cells, {len(inds)} industries, "
          f"countries per industry min {sizes[0]} median {sizes[len(sizes)//2]} "
          f"max {sizes[-1]}")
    print("     a cross-country loop needs at least three countries in one industry;")
    print(f"     industries with >= 3: {sum(1 for s in sizes if s >= 3)} of {len(sizes)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--describe", action="store_true")
    a = ap.parse_args()
    d = load() if (a.describe and CACHE.exists()) else build()
    describe(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
