"""B101 step eleven: the third module, and what it carries beyond the mix.

The quantity mix GRV uses needs hours or persons in levels, and neither growth
accounts file carries them: basic has 33 variables, extended 68, and EMP and
H_EMP are in neither.  They are in the national accounts module, which also
carries something this station did not go looking for.

    EMP   persons employed          EMPE   employees
    H_EMP hours, all employed       H_EMPE hours, employees
    COMP  compensation of employees

So the panel separates employees from the self employed at every position, in
both headcount and hours, and the growth accounts' LAB is the wider concept:
compensation of employees plus an imputation for self employed labour.  That is
two classes at one position with their own terms, which is this framework's own
object, and whether it carries anything turns on one question that is answered by
arithmetic rather than by argument: is the self employed hourly wage imputed at
the employee wage?  If it is, the second class is a construction and reads
nothing.  Section 11.3 asks it.

    python experiments/b101_national_load.py
    python experiments/b101_national_load.py --describe
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "national accounts.csv"
CACHE = ROOT / "data" / "cache" / "b101_national.npz"
GROWTH = ROOT / "data" / "cache" / "b101_klems_basic.npz"
CAPITAL = ROOT / "data" / "cache" / "b101_capital.npz"

WANT = ["COMP", "EMP", "EMPE", "H_EMP", "H_EMPE",
        "GO_CP", "GO_Q", "II_CP", "II_Q", "VA_CP", "VA_PI", "VA_Q"]


def build() -> dict:
    if not RAW.exists():
        sys.exit(f"missing: {RAW}")
    size = RAW.stat().st_size
    with RAW.open("rb") as fh:
        fh.seek(max(0, size - 8192))
        tail = fh.read().decode("utf-8", "replace").rstrip("\n")
    last = tail.rsplit("\n", 1)[-1]
    if last.count(",") < 20:
        sys.exit(f"last line has {last.count(',')} commas, expected at least 20: "
                 f"the file looks truncated, not read.\n  {last[:160]}")

    keys, rows, n, bad = [], [], 0, 0
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
    ks = [keys[i] for i in idx]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        CACHE,
        nace=np.array([k[0] for k in ks]),
        geo=np.array([k[1] for k in ks]),
        year=np.array([k[2] for k in ks], int),
        vars=np.array(WANT),
        values=np.array([rows[i] for i in idx], float),
        source=np.array([RAW.name, str(size), str(n)]),
    )
    print(f"cache -> {CACHE.relative_to(ROOT)}  ({CACHE.stat().st_size:,} bytes)")
    return load()


def load() -> dict:
    d = np.load(CACHE, allow_pickle=False)
    return {k: d[k] for k in d.files}


def describe(d: dict) -> None:
    col = {v: d["values"][:, i] for i, v in enumerate(list(d["vars"]))}

    print()
    print("=" * 74)
    print("11.1  IS THERE AN INDEX BASE?  levels read 100 in no row of their own")
    for v in ("EMP", "EMPE", "H_EMP", "H_EMPE", "COMP", "VA_CP", "VA_Q", "VA_PI"):
        x = col[v]; f = np.isfinite(x)
        at100 = int(np.sum(f & (np.abs(x - 100.0) < 1e-9)))
        print(f"     {v:<8s} n={f.sum():>7,d}  median {np.nanmedian(x):>14,.2f}  "
              f"==100 in {at100:>6,d} rows")
    print("     VA_PI is the one with a base, as a price index should be.")

    print()
    print("=" * 74)
    print("11.2  COVERAGE AGAINST THE JOINED PANEL")
    g = np.load(GROWTH, allow_pickle=False)
    k = np.load(CAPITAL, allow_pickle=False)
    gcol = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    kcol = {v: k["values"][:, i] for i, v in enumerate(list(k["vars"]))}
    have = {(a, b, int(c)) for a, b, c, L, C in
            zip(g["nace"], g["geo"], g["year"], gcol["LAB"], gcol["CAP"])
            if np.isfinite(L) and np.isfinite(C)}
    have &= {(a, b, int(c)) for a, b, c, K in
             zip(k["nace"], k["geo"], k["year"], kcol["K_GFCF"]) if np.isfinite(K)}
    hrs = {(a, b, int(c)) for a, b, c, H in
           zip(d["nace"], d["geo"], d["year"], col["H_EMP"]) if np.isfinite(H) and H > 0}
    print(f"     value arm cells (LAB, CAP, K_GFCF)  : {len(have):,}")
    print(f"     cells with H_EMP                    : {len(hrs):,}")
    print(f"     both, so the quantity arm can run   : {len(have & hrs):,}")
    print(f"     lost by adding hours                : {len(have - hrs):,}")

    print()
    print("=" * 74)
    print("11.3  IS THE SELF EMPLOYED WAGE IMPUTED AT THE EMPLOYEE WAGE?")
    print("      if it is, the second class is a construction and reads nothing.")
    idx = {(a, b, int(c)): i for i, (a, b, c) in
           enumerate(zip(d["nace"], d["geo"], d["year"]))}
    gi = {(a, b, int(c)): i for i, (a, b, c) in
          enumerate(zip(g["nace"], g["geo"], g["year"]))}
    rows = []
    for key in sorted(have & hrs):
        i, j = idx.get(key), gi.get(key)
        if i is None or j is None:
            continue
        LAB, COMP = gcol["LAB"][j], col["COMP"][i]
        HE, HEE = col["H_EMP"][i], col["H_EMPE"][i]
        if not all(np.isfinite(v) for v in (LAB, COMP, HE, HEE)):
            continue
        dh = HE - HEE
        if not (dh > 0 and HEE > 0 and COMP > 0):
            continue
        rows.append((COMP / HEE, (LAB - COMP) / dh, dh / HE))
    if not rows:
        print("     no cell carries all four series")
        return
    we = np.array([r[0] for r in rows]); ws = np.array([r[1] for r in rows])
    sh = np.array([r[2] for r in rows])
    ratio = ws / we
    print(f"     {len(rows):,} cells carry LAB, COMP, H_EMP and H_EMPE with a "
          f"positive self employed hour count")
    print(f"     self employed share of hours: median {np.median(sh):.4f}, "
          f"p10 {np.percentile(sh,10):.4f}, p90 {np.percentile(sh,90):.4f}")
    print(f"     implied hourly wage ratio, self employed over employee:")
    for q in (1, 10, 25, 50, 75, 90, 99):
        print(f"        p{q:<3d} {np.percentile(ratio, q):+.4f}")
    at_one = int(np.sum(np.abs(ratio - 1.0) < 1e-6))
    print(f"     exactly one to 1e-6: {at_one:,} of {len(rows):,} "
          f"({100*at_one/len(rows):.2f}%)")
    print(f"     negative: {int(np.sum(ratio < 0)):,} "
          f"({100*np.mean(ratio < 0):.2f}%)")
    print("     -> exactly one everywhere would mean the imputation is the employee")
    print("        wage and the second class carries nothing. Anything else means")
    print("        the two classes are priced differently in this panel.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--describe", action="store_true")
    a = ap.parse_args()
    d = load() if (a.describe and CACHE.exists()) else build()
    describe(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
