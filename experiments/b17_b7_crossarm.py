"""B17 x B7: the same estimand on a second carrier, and the same null.

B7 measured the rank of the non-integrable part of a price field on a US
mortgage panel and reported two dimensions, a tilt and a curvature. B17 measures
the same object on Argentina's parallel conversion tracks. This script does not
re-run either stage. It reads B7's committed cross-fold record and computes, on
that record alone, the comparator spectrum B17 uses: what the spectrum would look
like if each class carried only its own independent deviation.

    python experiments/b17_b7_crossarm.py

The comparator is `P diag(d) P` with `P = I - 11'/C` and `d` the recorded
diagonal of the cross-fold second-moment matrix. B7's balanced arms already have
their all-ones component at machine zero, so they are the same construction.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "b7_crossfold.json"
OUT = ROOT / "results" / "b17_b7_crossarm.json"

ARMS = ["drop_thinnest_2_balanced", "all_19_balanced"]


def comparator(diag):
    """Spectrum under independent per-class deviation, centred the same way."""
    d = np.clip(np.asarray(diag, dtype=float), 0.0, None)
    n = len(d)
    P = np.eye(n) - np.ones((n, n)) / n
    w = np.sort(np.linalg.eigvalsh(P @ np.diag(d) @ P))[::-1]
    return d, w


def main():
    rec = json.loads(SRC.read_text(encoding="utf-8"))
    out = {"stage": "B17xB7", "source_record": SRC.name, "arms": {}}

    for arm in ARMS:
        a = rec["arms"][arm]
        labels = a["labels"]
        obs = np.asarray(a["eigenvalues"], dtype=float)
        d, null = comparator(a["diag"])
        n = len(labels)
        k = n - 1

        def share(v):
            pos = v[:k][v[:k] > 0]
            return [float(x / pos.sum()) for x in v[:4]]

        entry = {
            "n_classes": n,
            "all_ones_component_recorded": float(a["all_ones_component"]),
            "negative_diagonal_entries_clipped": int(np.sum(np.asarray(a["diag"]) < 0)),
            "largest_diagonal": float(d.max()),
            "largest_diagonal_class": labels[int(np.argmax(d))],
            "second_largest_diag_recorded": float(a["second_largest_diag"]),
            "comparator_lambda2": float(null[1]),
            "comparator_reproduces_recorded_second_largest_diag_to":
                float(abs(null[1] - a["second_largest_diag"]) / a["second_largest_diag"]),
            "observed_eigenvalues_top4": [float(x) for x in obs[:4]],
            "comparator_eigenvalues_top4": [float(x) for x in null[:4]],
            "observed_shares_top4": share(obs),
            "comparator_shares_top4": share(null),
            "ratio_lambda1_observed_over_comparator": float(obs[0] / null[0]),
            "ratio_lambda2_observed_over_comparator": float(obs[1] / null[1]),
            "lambda1_share_reproduced_by_largest_single_class":
                float(d.max() / obs[0]),
            "permutation_null_lambda2_mean_recorded": float(a["lambda2_null_mean"]),
            "permutation_null_lambda2_z_recorded": float(a["lambda2_z"]),
        }
        out["arms"][arm] = entry

        print("== %s, %d classes ==" % (arm, n))
        print("   recorded all-ones component  %.3e  (this arm is already centred)"
              % entry["all_ones_component_recorded"])
        print("   negative diagonal entries clipped to zero: %d"
              % entry["negative_diagonal_entries_clipped"])
        print("   largest diagonal %.6f on class %s"
              % (entry["largest_diagonal"], entry["largest_diagonal_class"]))
        print("   %-4s %14s %14s %8s" % ("k", "observed", "comparator", "ratio"))
        for i in range(4):
            print("   %-4d %14.6f %14.6f %8.2f"
                  % (i + 1, obs[i], null[i], obs[i] / null[i] if null[i] > 0 else float("nan")))
        print("   comparator lambda2 %.6f against the record's second_largest_diag %.6f, "
              "relative difference %.4f"
              % (entry["comparator_lambda2"], entry["second_largest_diag_recorded"],
                 entry["comparator_reproduces_recorded_second_largest_diag_to"]))
        print("   lambda1 reproduced by one class's own diagonal: %.4f"
              % entry["lambda1_share_reproduced_by_largest_single_class"])
        print()

    out["diagnostic_only"] = True
    out["diagnostic_reason"] = (
        "Cross-arm comparator computed from a committed record. It withdraws "
        "nothing, revises no coefficient, and no criterion in either stage rests "
        "on it."
    )
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True, default=str),
                   encoding="utf-8", newline="\n")
    print("wrote %s" % OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
