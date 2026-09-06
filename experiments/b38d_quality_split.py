"""B38d: is the rank a property of the prices, or of how thin the sample is.

B38 read the rank of the two-way residual on 1,280 cities and reported at
least eight directions above the floor that concedes the entire residual to
measurement. The objection a reader reaches for first is that the archive is
crowdsourced: thin cities are noisy, that noise is heteroskedastic, and a
heteroskedastic noise matrix grows directions of its own. The floors in B38
do not answer this, because both of them assume one noise level for the whole
matrix and argue only about how high it is.

That objection has a name in this project's own record. B7's rank-two reading
was withdrawn when a field with no interaction at all returned exactly two on
the same design, twenty times out of twenty: two classes held 1.18 and 1.37
observations per cell, and each of them produced an indicator direction. The
floor there came from the design being unbalanced, not from the noise being
large. B38's matrix is complete, so that exact mechanism cannot occur, but
the continuous version of it can.

This station answers it without a noise model at all. The carrier ships a
per-city quality flag. Split the matrix on that flag and run the same
decomposition on each half:

  - if the rank belongs to the sampling, the two halves disagree, and the
    thin half carries more directions than the thick one;
  - if the thin half is imputed or smoothed rather than collected, it sits
    near rank one and its residual sd collapses;
  - if the rank belongs to the prices, the two halves agree.

A second reading comes free. The archive exists in two vintages, so the same
split can be run on the cell-by-cell movement between them, which is a
different axis from the cross-section entirely.

Every criterion here is an object printed. There is no threshold anywhere,
and no permutation: the halves are the carrier's own.

Run:

    python experiments\\b38d_quality_split.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "b30_5" / "column_map.json"
V1 = ROOT / "data" / "raw" / "cost-of-living.csv"
V2 = ROOT / "data" / "raw" / "cost-of-living_v2.csv"
OUT = ROOT / "results" / "b38d_quality_split.json"

# B38's own main-arm readings, for the reproduction check (discipline 19).
B38_MAIN = {"cities": 1280, "b1": 66508, "sd_R": 0.4521, "above": 8,
            "sv3": (61.50, 36.79, 33.30)}
QUALITY = "data_quality"


def value(raw):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def two_way(M):
    a = M.mean(axis=1, keepdims=True)
    b = (M - a).mean(axis=0, keepdims=True)
    return a, b, M - a - b


def noise_edge(sigma, n, m):
    return sigma * (math.sqrt(n) + math.sqrt(m))


def load(path, cols):
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    return [r for r in rows if all(value(r[c]) for c in cols)]


def spectrum(sub, cols):
    """The same decomposition B38 runs, on whatever subset is handed in."""
    M = np.log(np.array([[value(r[c]) for c in cols] for r in sub],
                        dtype=float)).T
    I, C = M.shape
    _, _, R = two_way(M)
    sv = np.linalg.svd(R, compute_uv=False)
    sd = float(R.std())
    edge = noise_edge(sd, I, C)
    return {"items": I, "cities": C, "b1": I * C - (I + C) + 1,
            "sd_residual": sd, "conservative_floor": edge,
            "above_conservative": int((sv > edge).sum()),
            "singular_values_top5": [float(x) for x in sv[:5]]}


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    cols = [c for c, m in spec["mapping"].items()
            if m.get("agrees") and "in %" not in m["item"].lower()]
    full = load(V2, cols)

    print("=" * 78)
    print("B38d: does the rank belong to the prices or to the sampling")
    print("=" * 78)
    print("  carrier   %s, %d items, %d complete cities"
          % (V2.name, len(cols), len(full)))
    print("  split on  %s, a per-city flag the carrier ships" % QUALITY)

    thick = [r for r in full if r[QUALITY] == "1"]
    thin = [r for r in full if r[QUALITY] == "0"]
    arms = {"all": spectrum(full, cols),
            "quality_1_thick": spectrum(thick, cols),
            "quality_0_thin": spectrum(thin, cols)}

    # --- B38d-1: reproduce B38's main arm to the digit (discipline 19) ---
    a = arms["all"]
    ok = (a["cities"] == B38_MAIN["cities"] and a["b1"] == B38_MAIN["b1"]
          and abs(a["sd_residual"] - B38_MAIN["sd_R"]) < 5e-5
          and a["above_conservative"] == B38_MAIN["above"]
          and all(abs(x - y) < 5e-3
                  for x, y in zip(a["singular_values_top5"][:3],
                                  B38_MAIN["sv3"])))
    print("\n  B38d-1  the full arm reproduces B38")
    print("          cities %d (B38: %d), b1 %d (B38: %d), sd %.4f (B38: %.4f),"
          % (a["cities"], B38_MAIN["cities"], a["b1"], B38_MAIN["b1"],
             a["sd_residual"], B38_MAIN["sd_R"]))
    print("          above the conservative floor %d (B38: %d)"
          % (a["above_conservative"], B38_MAIN["above"]))
    print("          %s" % ("PASS" if ok else "FAIL"))

    # --- B38d-2: the two halves, printed and not judged ---
    print("\n  B38d-2  the same decomposition on each half, printed")
    print("  %-18s %6s %9s %9s %9s   %s"
          % ("subset", "cities", "sd(R)", "floor", "above", "top three"))
    for name in ("all", "quality_1_thick", "quality_0_thin"):
        d = arms[name]
        print("  %-18s %6d %9.4f %9.2f %9d   %7.2f %7.2f %7.2f"
              % (name, d["cities"], d["sd_residual"], d["conservative_floor"],
                 d["above_conservative"], *d["singular_values_top5"][:3]))

    # --- B38d-3: the two axes disagree, and both are printed ---
    v1 = {(r["city"], r["country"]): r for r in load(V1, cols)}
    v2 = {(r["city"], r["country"]): r for r in full}
    both = sorted(set(v1) & set(v2))
    A = np.array([[value(v1[k][c]) for c in cols] for k in both])
    B = np.array([[value(v2[k][c]) for c in cols] for k in both])
    q = np.array([int(v2[k][QUALITY]) for k in both])
    moved = A != B
    D = np.log(B) - np.log(A)
    D = D - np.median(D[moved])
    per_city, keep = [], []
    for i in range(len(both)):
        m = moved[i]
        if m.sum() >= 20:
            per_city.append(float(D[i][m].std()))
            keep.append(q[i])
    per_city, keep = np.array(per_city), np.array(keep)

    print("\n  B38d-3  the movement between the two vintages, split the same way")
    print("          %d cities complete in both; cells that moved: %d of %d"
          % (len(both), int(moved.sum()), moved.size))
    print("  %-18s %6s %14s %10s"
          % ("subset", "cities", "median sd(move)", "p90"))
    move = {}
    for lab, m in (("quality_1_thick", keep == 1), ("quality_0_thin", keep == 0)):
        s = per_city[m]
        move[lab] = {"cities": int(m.sum()),
                     "median_sd_move": float(np.median(s)),
                     "p90_sd_move": float(np.percentile(s, 90))}
        print("  %-18s %6d %14.4f %10.4f"
              % (lab, m.sum(), np.median(s), np.percentile(s, 90)))

    print("\n  B38d-4  the two ratios, thin over thick, printed side by side")
    r_move = (move["quality_0_thin"]["median_sd_move"]
              / move["quality_1_thick"]["median_sd_move"])
    r_cross = (arms["quality_0_thin"]["sd_residual"]
               / arms["quality_1_thick"]["sd_residual"])
    print("          movement between vintages   %.3f" % r_move)
    print("          dispersion in the section   %.3f" % r_cross)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"reproduces_b38_main_arm": bool(ok), "b38_main_arm_expected": B38_MAIN,
         "cross_section": arms, "vintage_movement": move,
         "ratios_thin_over_thick": {"movement": r_move, "cross_section": r_cross}},
        ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print("\nwritten: %s" % OUT)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
