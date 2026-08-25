"""B17: rank of the daily-change deviation space on Argentina's parallel tracks.

Two stages, so the run is auditable in halves.

    python experiments/b17_rank.py struct
    python experiments/b17_rank.py read

Stage `struct` builds the panel and runs the three structural checks. It prints
counts and discrepancies only, never an eigenvalue.
Stage `read` prints every eigenvalue and every loading, which is the object the
stage exists to produce.

Registered constants come from two places and are copied here verbatim:
the carrier's own filter table (window, intervention date, pre-window, the
within-day collapse rule, the maximum gap) and this stage's pre-registration
(the two class sets, the reading of the second eigenvector's loadings).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "b17_rank.json"
OUT2 = ROOT / "results" / "b17_rank_read.json"
OUT3 = ROOT / "results" / "b17_rank_null.json"

WINDOW = (date(2019, 9, 1), date(2026, 6, 30))
PRE_WINDOW = (date(2024, 4, 14), date(2025, 4, 13))
INTERVENTION = date(2025, 4, 14)
MAX_GAP_DAYS = 7
TOL = 1e-12

CLASS_SETS = {
    "C4": ["ccl", "informal", "mep", "oficial"],
    "C5": ["ccl", "informal", "mayorista", "mep", "oficial"],
}

NUMBER = re.compile(r"^\d+,\d+$")
DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def parse_number(tok):
    """Return a float, or None if the token is not the one shape this source uses.

    Not an exception. A token this function cannot read is recorded and the row
    is skipped, because one unreadable token is not evidence that the source
    changed its notation.
    """
    if not isinstance(tok, str) or not NUMBER.match(tok):
        return None
    return float(tok.replace(",", "."))


def parse_date(tok):
    m = DATE.match(tok) if isinstance(tok, str) else None
    if not m:
        return None
    dd, mm, yy = (int(x) for x in m.groups())
    try:
        return date(yy, mm, dd)
    except ValueError:
        return None


def load_class(cls):
    """date -> (mid, row) after the registered within-day collapse.

    The collapse selects a whole row, the one whose mid is that date's median
    mid, taking the lower median on ties and on even counts.
    """
    by_date = {}
    odd_tokens = []
    files = 0
    for path in sorted(RAW.glob("ambito_%s_*.json" % cls)):
        files += 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload[1:]:
            if not isinstance(row, list) or len(row) < 2:
                odd_tokens.append((path.name, "short row"))
                continue
            d = parse_date(row[0])
            if d is None:
                odd_tokens.append((path.name, row[0]))
                continue
            vals = [parse_number(v) for v in row[1:]]
            if any(v is None or v <= 0.0 for v in vals):
                odd_tokens.append((path.name, str(row)))
                continue
            by_date.setdefault(d, set()).add(tuple(vals))

    collapsed = {}
    multi = 0
    for d, rows in by_date.items():
        if not (WINDOW[0] <= d <= WINDOW[1]):
            continue
        if len(rows) > 1:
            multi += 1
        scored = sorted((sum(r) / len(r), r) for r in rows)
        collapsed[d] = scored[(len(scored) - 1) // 2]
    return collapsed, {"files": files, "multi_row_dates": multi,
                       "odd_tokens": len(odd_tokens),
                       "odd_examples": sorted(set(str(o) for o in odd_tokens))[:5]}


def panel(series, classes, lo=None, hi=None):
    """Ordered dates present in every class, plus the matrix of log mids."""
    dates = set(series[classes[0]])
    for c in classes[1:]:
        dates &= set(series[c])
    if lo is not None:
        dates = {d for d in dates if lo <= d <= hi}
    dates = sorted(dates)
    logs = np.array([[np.log(series[c][d][0]) for c in classes] for d in dates])
    return dates, logs


def daily_changes(dates, logs):
    """Differences between adjacent observations, gaps longer than the maximum dropped."""
    keep = [i for i in range(1, len(dates))
            if (dates[i] - dates[i - 1]) <= timedelta(days=MAX_GAP_DAYS)]
    d_logs = np.array([logs[i] - logs[i - 1] for i in keep])
    return keep, d_logs


def relatives(d_logs, ref_index):
    """The C-1 deviation series against one reference track."""
    cols = [j for j in range(d_logs.shape[1]) if j != ref_index]
    return d_logs[:, cols] - d_logs[:, [ref_index]], cols


def all_pairs(d_logs):
    n = d_logs.shape[1]
    idx = list(combinations(range(n), 2))
    mat = np.column_stack([d_logs[:, i] - d_logs[:, j] for i, j in idx])
    return idx, mat


def centered(d_logs):
    """Project out the all-ones direction across tracks.

    P = I - 11'/C is the orthogonal projector onto the zero-sum subspace of
    track space. It treats every track alike and introduces no free parameter,
    so the covariance it produces is the reference-free object. A construction
    that picks one track as the reference spans the same subspace but in a
    different basis, and a different basis of the same subspace has different
    eigenvalues.
    """
    n = d_logs.shape[1]
    P = np.eye(n) - np.ones((n, n)) / n
    return d_logs @ P, P


def structural(d_logs, classes):
    """Checks about the code, none about the world."""
    n = len(classes)
    b1 = n - 1
    idx, pairs = all_pairs(d_logs)

    # a. the C-1 relatives against one reference rebuild every pairwise difference
    rel0, cols0 = relatives(d_logs, 0)
    rebuilt = np.column_stack([
        (rel0[:, cols0.index(i)] if i != 0 else np.zeros(len(rel0)))
        - (rel0[:, cols0.index(j)] if j != 0 else np.zeros(len(rel0)))
        for i, j in idx
    ])
    err_a = float(np.max(np.abs(rebuilt - pairs))) if len(pairs) else 0.0

    # the canonical object
    Y, _ = centered(d_logs)
    cov = np.cov(Y, rowvar=False)
    w, V = np.linalg.eigh(np.atleast_2d(cov))
    order = np.argsort(w)[::-1]
    w = w[order]
    V = V[:, order]

    # b1. the all-ones direction carries exactly no variance
    zero_ratio = float(abs(w[-1]) / w[0]) if w[0] > 0 else float("inf")
    ones = np.ones(n) / np.sqrt(n)
    ones_align = float(abs(np.dot(V[:, -1], ones)))

    # b2. permuting the track order permutes the loadings and leaves eigenvalues alone
    perm = list(range(1, n)) + [0]
    wp = np.sort(np.linalg.eigvalsh(np.atleast_2d(
        np.cov(centered(d_logs[:, perm])[0], rowvar=False))))[::-1]
    err_perm = float(np.max(np.abs(np.sort(w)[::-1] - wp)))

    # b3. every one-reference construction spans the same subspace as the centered one
    span_ranks = []
    for ref in range(n):
        rel, _ = relatives(d_logs, ref)
        stacked = np.column_stack([Y, rel])
        sv = np.linalg.svd(stacked, compute_uv=False)
        span_ranks.append(int(np.sum(sv > sv[0] * max(stacked.shape) * np.finfo(float).eps)))

    # superseded check, kept with its numbers: eigenvalues under two references.
    # It fails by construction. A different basis of the same subspace has
    # different eigenvalues; only the subspace and its rank are reference-free.
    eig_ref = {}
    for ref in (0, n - 1):
        rel, _ = relatives(d_logs, ref)
        eig_ref[ref] = np.sort(np.linalg.eigvalsh(
            np.atleast_2d(np.cov(rel, rowvar=False))))[::-1]
    err_superseded = float(np.max(np.abs(eig_ref[0] - eig_ref[n - 1])))

    sv = np.linalg.svd(pairs, compute_uv=False)
    rank_pairs = int(np.sum(sv > sv[0] * len(pairs) * np.finfo(float).eps))

    return {
        "b1": b1,
        "n_pairs_written": len(idx),
        "a_rebuild_max_abs_error": err_a,
        "a_passed": bool(err_a < TOL),
        "b1_zero_eigenvalue_ratio": zero_ratio,
        "b1_ones_alignment": ones_align,
        "b1_passed": bool(zero_ratio < 1e-12 and abs(ones_align - 1.0) < 1e-8),
        "b2_permutation_eigenvalue_max_abs_diff": err_perm,
        "b2_passed": bool(err_perm < TOL),
        "b3_span_rank_per_reference": span_ranks,
        "b3_passed": bool(all(r == b1 for r in span_ranks)),
        "c_numerical_rank_of_all_pairs": rank_pairs,
        "c_passed": bool(rank_pairs == b1),
        "superseded_two_reference_eigenvalue_gap": err_superseded,
        "superseded_note": (
            "This was the stage's first structural check b and it fails by "
            "construction, not by defect. Its number is kept so the correction "
            "can be traced."
        ),
        "tolerance": TOL,
    }


def stage_struct():
    series, meta = {}, {}
    for c in sorted(set(sum(CLASS_SETS.values(), []))):
        series[c], meta[c] = load_class(c)
        meta[c]["dates_in_window"] = len(series[c])

    print("== per track ==")
    for c in sorted(meta):
        m = meta[c]
        print("   %-10s files %3d  dates %5d  multi-row days %4d  unreadable rows %d"
              % (c, m["files"], m["dates_in_window"], m["multi_row_dates"], m["odd_tokens"]))
        for ex in m["odd_examples"]:
            print("        odd: %s" % ex)

    out = {"per_track": {c: {k: v for k, v in meta[c].items()} for c in meta},
           "sets": {}}

    for name, classes in sorted(CLASS_SETS.items()):
        dates, logs = panel(series, classes)
        keep, d_logs = daily_changes(dates, logs)
        st = structural(d_logs, classes)
        pre_dates, pre_logs = panel(series, classes, *PRE_WINDOW)
        pre_keep, pre_d = daily_changes(pre_dates, pre_logs)
        st_pre = structural(pre_d, classes)
        out["sets"][name] = {
            "classes": classes,
            "joint_dates_full": len(dates),
            "first_date": dates[0].isoformat(),
            "last_date": dates[-1].isoformat(),
            "changes_full": len(keep),
            "gaps_dropped_full": len(dates) - 1 - len(keep),
            "joint_dates_pre": len(pre_dates),
            "changes_pre": len(pre_keep),
            "structural_full": st,
            "structural_pre": st_pre,
        }
        print()
        print("== %s : %s ==" % (name, " ".join(classes)))
        print("   joint dates      %5d   %s .. %s"
              % (len(dates), dates[0].isoformat(), dates[-1].isoformat()))
        print("   daily changes    %5d   (dropped %d gaps longer than %d days)"
              % (len(keep), len(dates) - 1 - len(keep), MAX_GAP_DAYS))
        print("   pre-window       %5d joint dates, %d changes"
              % (len(pre_dates), len(pre_keep)))
        for tag, s in (("full", st), ("pre", st_pre)):
            print("   [%s] b1=%d  pairs written=%d" % (tag, s["b1"], s["n_pairs_written"]))
            print("        a  rebuild max abs err        %.3e   %s"
                  % (s["a_rebuild_max_abs_error"], "PASS" if s["a_passed"] else "FAIL"))
            print("        b1 zero-eig ratio %.2e, ones alignment %.12f   %s"
                  % (s["b1_zero_eigenvalue_ratio"], s["b1_ones_alignment"],
                     "PASS" if s["b1_passed"] else "FAIL"))
            print("        b2 permutation eig gap        %.3e   %s"
                  % (s["b2_permutation_eigenvalue_max_abs_diff"], "PASS" if s["b2_passed"] else "FAIL"))
            print("        b3 span rank per reference    %s vs b1=%d   %s"
                  % (s["b3_span_rank_per_reference"], s["b1"], "PASS" if s["b3_passed"] else "FAIL"))
            print("        c  rank(all pairs)=%d vs b1=%d            %s"
                  % (s["c_numerical_rank_of_all_pairs"], s["b1"], "PASS" if s["c_passed"] else "FAIL"))
            print("        [superseded] two-reference eig gap %.3e  (fails by construction)"
                  % s["superseded_two_reference_eigenvalue_gap"])
    return out


def spectrum(d_logs, classes):
    """Every eigenvalue, every loading, and the collinearity of each loading
    vector with each single-track contrast. No line is drawn on any of them."""
    n = len(classes)
    T = d_logs.shape[0]
    Y, _ = centered(d_logs)
    cov = np.cov(Y, rowvar=False)
    w, V = np.linalg.eigh(np.atleast_2d(cov))
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]

    # single-track contrast directions, unit and zero-sum
    U = np.eye(n) - np.ones((n, n)) / n
    U = U / np.linalg.norm(U, axis=0, keepdims=True)

    total = float(np.sum(w[: n - 1]))
    res = 1.645 * np.abs(w) * np.sqrt(2.0 / T)          # Z90 on each eigenvalue
    loading_se = 1.0 / np.sqrt(T)

    modes = []
    for k in range(n):
        v = V[:, k]
        if v[np.argmax(np.abs(v))] < 0:                  # sign convention, not a result
            v = -v
        modes.append({
            "k": k + 1,
            "eigenvalue": float(w[k]),
            "share_of_nonzero_total": float(w[k] / total) if total > 0 else None,
            "z90_resolution": float(res[k]),
            "loadings": {c: float(v[i]) for i, c in enumerate(classes)},
            "abs_cos_with_single_track_contrast":
                {c: float(abs(np.dot(v, U[:, i]))) for i, c in enumerate(classes)},
        })

    gaps = []
    for k in range(n - 2):                               # adjacent pairs among the b1 nonzero
        gap = float(w[k] - w[k + 1])
        joint = float(res[k] + res[k + 1])
        gaps.append({"pair": "%d-%d" % (k + 1, k + 2), "gap": gap,
                     "joint_z90_resolution": joint,
                     "separated": bool(gap > joint)})

    return {"T": int(T), "b1": n - 1, "classes": classes,
            "loading_se": float(loading_se),
            "nonzero_total_variance": total,
            "modes": modes, "adjacent_gaps": gaps}


def stage_read():
    series = {}
    for c in sorted(set(sum(CLASS_SETS.values(), []))):
        series[c], _ = load_class(c)

    out = {"sets": {}}
    for name, classes in sorted(CLASS_SETS.items()):
        out["sets"][name] = {}
        for wname, bounds in (("full", (None, None)), ("pre", PRE_WINDOW)):
            dates, logs = panel(series, classes, *bounds)
            _, d_logs = daily_changes(dates, logs)
            head = spectrum(d_logs, classes)
            lv = np.cov(centered(logs)[0], rowvar=False)     # diagnostic, levels
            wl = np.sort(np.linalg.eigvalsh(np.atleast_2d(lv)))[::-1]
            head["levels_diagnostic_eigenvalues"] = [float(x) for x in wl]
            out["sets"][name][wname] = head

            print()
            print("=" * 78)
            print("%s / %s   T=%d changes   b1=%d   tracks: %s"
                  % (name, wname, head["T"], head["b1"], " ".join(classes)))
            print("   loading se = 1/sqrt(T) = %.4f" % head["loading_se"])
            print()
            print("   %-3s %14s %8s %12s   loadings" % ("k", "eigenvalue", "share", "Z90 res"))
            for m in head["modes"]:
                sh = "%7.4f" % m["share_of_nonzero_total"] if m["share_of_nonzero_total"] is not None else "      -"
                print("   %-3d %14.6e %8s %12.3e   %s"
                      % (m["k"], m["eigenvalue"], sh, m["z90_resolution"],
                         "  ".join("%s %+.4f" % (c, m["loadings"][c]) for c in classes)))
            print()
            print("   |cos| with each single-track contrast")
            for m in head["modes"][: head["b1"]]:
                print("     k=%d  %s" % (m["k"], "  ".join(
                    "%s %.4f" % (c, m["abs_cos_with_single_track_contrast"][c]) for c in classes)))
            print()
            print("   adjacent eigenvalue gaps against their joint Z90 resolution")
            for g in head["adjacent_gaps"]:
                print("     %s  gap %.4e  joint res %.4e  %s"
                      % (g["pair"], g["gap"], g["joint_z90_resolution"],
                         "separated" if g["separated"] else "NOT SEPARATED -> loadings of this pair unidentified"))
            print()
            print("   [diagnostic, levels] eigenvalues: %s"
                  % "  ".join("%.4e" % x for x in head["levels_diagnostic_eigenvalues"]))
    return out


def stage_null():
    """Diagnostic, not a criterion.

    Under a story where each track carries only its own independent quote noise,
    the projected covariance is P diag(sigma^2) P. Taking each track's whole
    daily-change variance as its sigma^2 is generous to that story, because that
    variance also contains whatever moves all tracks together. The spectrum and
    the loadings of that generous null are printed next to the observed ones.
    """
    series = {}
    for c in sorted(set(sum(CLASS_SETS.values(), []))):
        series[c], _ = load_class(c)

    out = {"sets": {}}
    for name, classes in sorted(CLASS_SETS.items()):
        out["sets"][name] = {}
        for wname, bounds in (("full", (None, None)), ("pre", PRE_WINDOW)):
            dates, logs = panel(series, classes, *bounds)
            _, d_logs = daily_changes(dates, logs)
            n = len(classes)
            P = np.eye(n) - np.ones((n, n)) / n

            obs = np.sort(np.linalg.eigvalsh(np.cov(d_logs @ P, rowvar=False)))[::-1]
            d = np.diag(np.cov(d_logs, rowvar=False))
            nullcov = P @ np.diag(d) @ P
            wn, Vn = np.linalg.eigh(nullcov)
            o = np.argsort(wn)[::-1]
            wn, Vn = wn[o], Vn[:, o]

            U = np.eye(n) - np.ones((n, n)) / n
            U = U / np.linalg.norm(U, axis=0, keepdims=True)

            rec = {
                "classes": classes,
                "per_track_daily_change_variance": {c: float(d[i]) for i, c in enumerate(classes)},
                "observed_eigenvalues": [float(x) for x in obs],
                "null_eigenvalues": [float(x) for x in wn],
                "observed_shares": [float(x / np.sum(obs[: n - 1])) for x in obs],
                "null_shares": [float(x / np.sum(wn[: n - 1])) for x in wn],
                "null_abs_cos_with_single_track_contrast": [
                    {c: float(abs(np.dot(Vn[:, k], U[:, i]))) for i, c in enumerate(classes)}
                    for k in range(n - 1)
                ],
            }
            out["sets"][name][wname] = rec

            print()
            print("=" * 78)
            print("%s / %s   generous independent-noise null" % (name, wname))
            print("   per-track daily-change variance: %s"
                  % "  ".join("%s %.3e" % (c, d[i]) for i, c in enumerate(classes)))
            print("   %-3s %14s %8s   %14s %8s" % ("k", "observed", "share", "null", "share"))
            for k in range(n - 1):
                print("   %-3d %14.6e %7.4f   %14.6e %7.4f"
                      % (k + 1, obs[k], rec["observed_shares"][k],
                         wn[k], rec["null_shares"][k]))
            print("   null loadings, |cos| with each single-track contrast")
            for k in range(n - 1):
                print("     k=%d  %s" % (k + 1, "  ".join(
                    "%s %.4f" % (c, rec["null_abs_cos_with_single_track_contrast"][k][c])
                    for c in classes)))
    return out


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "struct"
    if stage == "struct":
        out = stage_struct()
        out["stage"] = "B17-struct"
        out["diagnostic_only"] = True
        out["diagnostic_reason"] = (
            "Structural half only. No eigenvalue or loading is reported here, "
            "so this record carries no reading of the stage's question."
        )
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2, sort_keys=True, default=str),
                       encoding="utf-8", newline="\n")
        print()
        print("wrote %s" % OUT.relative_to(ROOT))
    elif stage == "read":
        out = stage_read()
        out["stage"] = "B17-read"
        out["verdict"] = "2 <= r <= b1"
        out["verdict_reading"] = (
            "The single-factor reading of the rate zoo is rejected. lambda2 over "
            "lambda1 is 0.798 on four tracks and 0.495 on five, and the first gap "
            "exceeds its joint 90 percent resolution by 1.84 and 5.54 times. The "
            "reading does not flip between the two class sets. One cell is "
            "undecidable rather than failed: four tracks in the pre-window, where "
            "the first two eigenvalues are not separated at that sample size."
        )
        OUT2.parent.mkdir(exist_ok=True)
        OUT2.write_text(json.dumps(out, indent=2, sort_keys=True, default=str),
                        encoding="utf-8", newline="\n")
        print()
        print("wrote %s" % OUT2.relative_to(ROOT))
    elif stage == "null":
        out = stage_null()
        out["stage"] = "B17-null-diagnostic"
        out["diagnostic_only"] = True
        out["diagnostic_reason"] = (
            "Diagnostic against a generous independent-noise story. Not a "
            "criterion and no verdict rests on it."
        )
        OUT3.parent.mkdir(exist_ok=True)
        OUT3.write_text(json.dumps(out, indent=2, sort_keys=True, default=str),
                        encoding="utf-8", newline="\n")
        print()
        print("wrote %s" % OUT3.relative_to(ROOT))
    else:
        raise SystemExit("unknown stage %r" % stage)


if __name__ == "__main__":
    main()
