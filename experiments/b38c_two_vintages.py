"""B38c: how much of that residual survives to the next vintage.

B38 read the rank of the obstruction against two floors: one from the carrier's
measured noise, one from taking the whole residual as noise. Both are arguments
about a noise level. **This station needs no noise level at all.**

The archive exists in two vintages of the same source, a short interval apart:
67 per cent of shared cells differ, by a median of 1.45 per cent, in a
systematically positive direction, which is a stretch of time rather than a
re-cleaning of one instant.

    Noise does not correlate across vintages. Structure does.

So take the two-way residual in each vintage, `R1` and `R2`, and ask, for each
singular direction of `R1`, how much of `R2` it still accounts for. A direction
that was noise in the first vintage accounts for nothing in the second; a
direction that is structure comes back at close to its own size. **The count of
directions that come back is the rank, measured rather than thresholded.**

The null is built by permutation: shuffle the cities of `R2` so the pairing is
broken, and recompute the same quantity. That gives the size a direction reaches
when there is no correspondence at all, and it costs one pass.

**A limit this cannot clear.** Both vintages come from one source and largely one
set of contributors, so a contributor's persistent idiosyncrasy persists too and
would be counted as structure here. That is a property of the carrier and it is
not repaired by more vintages of the same carrier.

Run:
    python experiments\\b38c_two_vintages.py
"""

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
OUT = ROOT / "results" / "b38c_two_vintages.json"
V1 = ROOT / "data" / "raw" / "cost-of-living.csv"
V2 = ROOT / "data" / "raw" / "cost-of-living_v2.csv"
SEED = 20260901
N_PERM = 200


def value(raw):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def load(path):
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    return {(r["city"].strip(), r["country"].strip()): r for r in rows}


def two_way(M):
    a = M.mean(axis=1, keepdims=True)
    b = (M - a).mean(axis=0, keepdims=True)
    return M - a - b


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    cols = [c for c, m in spec["mapping"].items()
            if m.get("agrees") and "in %" not in m["item"].lower()]
    items = [spec["mapping"][c]["item"] for c in cols]
    d1, d2 = load(V1), load(V2)

    keys = sorted(k for k in set(d1) & set(d2)
                  if all(value(d1[k][c]) for c in cols)
                  and all(value(d2[k][c]) for c in cols))
    M1 = np.log(np.array([[value(d1[k][c]) for c in cols] for k in keys])).T
    M2 = np.log(np.array([[value(d2[k][c]) for c in cols] for k in keys])).T
    R1, R2 = two_way(M1), two_way(M2)
    I, C = R1.shape

    print("=" * 78)
    print("B38c: how much of the residual is still there in the next vintage")
    print("=" * 78)
    print("  %d items x %d cities complete in BOTH vintages" % (I, C))
    d = M2 - M1
    print("  vintage gap, cell by cell: median %+.4f in logs (%.2f%%), sd %.4f"
          % (float(np.median(d)), 100 * (math.exp(float(np.median(d))) - 1),
             float(d.std())))

    cell_r = float(np.corrcoef(R1.ravel(), R2.ravel())[0, 1])
    print("\n  cell-by-cell correlation of the two residuals   %+.4f" % cell_r)
    print("  share of the residual's variance that persists  %.1f%%"
          % (100 * cell_r ** 2))

    U, S, Vt = np.linalg.svd(R1, full_matrices=False)
    # how much of R2 each of R1's directions still carries
    carried = np.array([float(U[:, k] @ R2 @ Vt[k, :]) for k in range(len(S))])

    rng = np.random.default_rng(SEED)
    null = np.empty((N_PERM, len(S)))
    for t in range(N_PERM):
        perm = rng.permutation(C)
        R2p = R2[:, perm]
        null[t] = [float(U[:, k] @ R2p @ Vt[k, :]) for k in range(len(S))]
    hi = np.percentile(np.abs(null), 99, axis=0)

    print("\n  each direction of the first vintage, and what it still carries")
    print("  in the second. The null is the same quantity after the cities of")
    print("  the second vintage are shuffled, so the pairing is destroyed.")
    print("  %-4s %10s %10s %8s %10s  %s"
          % ("k", "sigma in v1", "carried", "ratio", "null p99", ""))
    survive = 0
    for k in range(len(S)):
        keep = abs(carried[k]) > hi[k]
        survive += keep
        if k < 15 or (keep and k < 40):
            print("  %-4d %10.3f %10.3f %8.3f %10.3f  %s"
                  % (k + 1, S[k], carried[k], carried[k] / S[k] if S[k] else 0,
                     hi[k], "survives" if keep else "gone"))
    print("  ...")
    print("\n  directions surviving the permutation null: %d of %d"
          % (survive, len(S)))
    med_ratio = float(np.median([carried[k] / S[k] for k in range(len(S))
                                 if abs(carried[k]) > hi[k]])) if survive else None
    if med_ratio is not None:
        print("  median carried/sigma among the survivors: %.3f" % med_ratio)
    print("\n  No threshold is registered on any singular value here. The count")
    print("  above rests on a permutation of the data itself, not on a noise")
    print("  level, and it replaces the two floors B38 had to argue about.")
    print("\n  WHAT THIS SEPARATES, AND WHAT IT DOES NOT.")
    print("  It separates the residual from transient noise: an entry that is")
    print("  wrong in one vintage and not in the next cannot survive this.")
    print("  It does NOT separate it from a persistent per-cell bias. The two")
    print("  vintages come from one source whose published figure is an average")
    print("  over a rolling window, so a short gap between them means they")
    print("  share most of their underlying entries by construction. A high")
    print("  correlation is therefore the expected result under a stable bias")
    print("  as much as under structure, and this number cannot tell them")
    print("  apart. The station that speaks to persistent bias is B38b, where")
    print("  the main structured-bias story, one name meaning different things")
    print("  in different cities, was tested on its own prediction and did not")
    print("  carry the residual.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "items": I, "cities": C,
        "vintage_gap_median_log": float(np.median(d)),
        "vintage_gap_sd_log": float(d.std()),
        "cell_correlation": cell_r,
        "variance_share_persisting": cell_r ** 2,
        "sigma_v1": [float(x) for x in S[:40]],
        "carried_in_v2": [float(x) for x in carried[:40]],
        "null_p99": [float(x) for x in hi[:40]],
        "directions_surviving": int(survive),
        "median_carried_over_sigma": med_ratio,
        "n_permutations": N_PERM,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
