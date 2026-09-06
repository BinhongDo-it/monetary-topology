"""B41-2: run a field that is additive by construction through the same code.

Two questions, and they are not the same one.

  the code       does this pipeline report zero when the truth is zero, or does
                 it manufacture a residual out of its own arithmetic
  the floor      at this graph size and this many days, how large a persistent
                 residual would the machine report anyway

The second is the one that matters for a small graph. A four by two grid has
few cells and the additive fit has m+n-1 parameters to spend on them, so a
genuinely additive field still leaves a nonzero sample residual, and a genuinely
non-additive one can be partly absorbed. Reading the real number against a floor
measured at the same shape is the only way to tell those apart.

The synthetic field is built from the state's own fitted row and column effects,
so the potential has the real dynamics, plus noise at the measured scale. Noise
comes in two forms because they give different floors: independent day to day,
and an AR(1) at the residual's own measured lag-one autocorrelation. The second
is the honest one, since a persistent noise process leaves a persistent looking
sample mean and the white one does not.

Five replicates per state, printed one line each rather than averaged, per the
rule that says the right number of repeats is the smallest one that still closes
the question and that a tight spread is itself the evidence.

    python experiments/b41_known_answer.py --report 3186 3225 2851 2886
"""

from __future__ import annotations

import argparse
import io
import json
import contextlib
import random
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_joint as J  # noqa: E402
import b41_persistence as P  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "b41"


# The rectangle rule lives in b41_joint. It used to be copied here, and the
# two copies were checked line by line on 2026-09-03 and found to agree, which
# is luck rather than a mechanism: a rule with two implementations only has to
# be edited once on one side to start selecting a different block on each. The
# floor and the reading have to be taken on the same block or the multiple
# means nothing, so there is one implementation now.
rectangle = J.rectangle


def state_of(report: int) -> str:
    """The state label, read off the rows rather than a hand list.

    It used to be a seven-entry dict written when seven states had been read.
    Four states added later printed a blank label and Montana printed its
    report number in the place where a state belongs, in the one table where
    Montana is the row a reader would look for. A label that names the object
    has to come from the object."""
    with contextlib.redirect_stdout(io.StringIO()):
        by_day = P.load_all(report)
    for rows in by_day.values():
        for r in rows:
            st = (r.get("market_location_state") or "").strip()
            if st:
                return st
    return ""


def real_panel(report: int, min_cov: float, one_com=None):
    with contextlib.redirect_stdout(io.StringIO()):
        by_day = P.load_all(report)
    per = {d: J.day_cells(r) for d, r in by_day.items()}
    per = {d: c for d, c in per.items() if c}
    got = rectangle(per, min_cov, one_com)
    if got is None:
        return None
    _, coms, poss = got
    need = {(c, p) for c in coms for p in poss}
    mats, rows, cols = [], [], []
    for d, cells in per.items():
        if not need <= set(cells):
            continue
        mat = np.array([[cells[(c, p)] for p in poss] for c in coms])
        r, _, _ = J.additive_residual(mat, np.ones_like(mat, dtype=bool))
        fit = mat - r
        rows.append(fit.mean(axis=1))
        cols.append(fit.mean(axis=0) - fit.mean())
        mats.append(r)
    return coms, poss, np.stack(mats), np.stack(rows), np.stack(cols)


def persistent_rms(res: np.ndarray, df: int) -> float:
    return float(np.linalg.norm(res.mean(axis=0)) / np.sqrt(df))


def boot_p(res: np.ndarray, blocks: list[int], draws: int, rng) -> dict:
    n = len(res)
    rbar = res.mean(axis=0)
    obs = float(np.linalg.norm(rbar))
    out = {}
    for b in blocks:
        nb = max(n // b, 1)
        starts = max(n - b + 1, 1)
        worse = 0
        for _ in range(draws):
            idx = []
            for _ in range(nb):
                s0 = rng.randrange(starts)
                idx.extend(range(s0, min(s0 + b, n)))
            m = res[np.array(idx)].mean(axis=0)
            if np.linalg.norm(m - rbar) >= obs:
                worse += 1
        out[b] = worse / draws
    return out


def ar1_noise(shape, rho, sd, rng: np.random.Generator):
    n = shape[0]
    e = rng.normal(0.0, sd * np.sqrt(max(1 - rho * rho, 1e-9)), size=shape)
    out = np.empty(shape)
    out[0] = rng.normal(0.0, sd, size=shape[1:])
    for t in range(1, n):
        out[t] = rho * out[t - 1] + e[t]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=int, nargs="+", required=True)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--blocks", type=int, nargs="+", default=[20, 100])
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260902)
    ap.add_argument("--min-coverage", type=float, default=0.60)
    ap.add_argument("--one-commodity", metavar="NAME", default=None,
                    help="see b41_joint; the floor has to be taken "
                         "on the same block as the reading")
    a = ap.parse_args()

    summary = []
    for rep_id in a.report:
        got = real_panel(rep_id, a.min_coverage, a.one_commodity)
        if got is None:
            print(f"{rep_id}: no rectangle"); continue
        coms, poss, res, rows, cols = got
        n_c, n_p = len(coms), len(poss)
        days, df = len(res), (n_c - 1) * (n_p - 1)
        sd = float(np.std(res))
        flat = res.reshape(days, -1)
        rho = float(np.mean([np.corrcoef(flat[:-1, k], flat[1:, k])[0, 1]
                             for k in range(flat.shape[1])
                             if np.std(flat[:, k]) > 0]))
        real_rms = persistent_rms(res, df)
        print(f"\n=== {state_of(rep_id) or rep_id} ({rep_id}) "
              f"{n_p} positions x {n_c} commodities, df {df}, {days} days ===")
        print(f"measured residual scale {sd:.2f} cents, lag-one "
              f"autocorrelation {rho:+.3f}")
        print(f"the real panel reads {real_rms:.2f} cents per cycle")

        for label, mk in (("independent", lambda g: g.normal(0, sd, (days, n_c, n_p))),
                          ("AR(1) at the measured rho",
                           lambda g: ar1_noise((days, n_c, n_p), rho, sd, g))):
            print(f"\n  synthetic additive field, noise {label}:")
            floors = []
            for k in range(a.reps):
                g = np.random.default_rng(a.seed + 1000 * rep_id + k)
                synth = (rows[:, :, None] + cols[:, None, :] + mk(g))
                sres = np.stack([J.additive_residual(
                    synth[t], np.ones((n_c, n_p), dtype=bool))[0]
                    for t in range(days)])
                rms = persistent_rms(sres, df)
                floors.append(rms)
                ps = boot_p(sres, a.blocks, a.draws,
                            random.Random(a.seed + k + rep_id))
                print(f"    rep {k + 1}: {rms:6.2f} cents per cycle   "
                      + "   ".join(f"p@{b} {v:.3f}" for b, v in ps.items()))
            lo, hi = min(floors), max(floors)
            print(f"    five reps span {lo:.2f} to {hi:.2f}; the real panel is "
                  f"{real_rms / max(np.mean(floors), 1e-9):.1f} times the mean floor")
            if label.startswith("AR"):
                summary.append(dict(report=rep_id, state=state_of(rep_id),
                                    df=df, days=days, positions=n_p,
                                    commodities=n_c, sd=sd, rho=rho,
                                    real=real_rms, floor_lo=lo, floor_hi=hi,
                                    floor_mean=float(np.mean(floors))))

    if summary:
        print(f"\n{'=' * 78}\nagainst the persistent-noise floor, one line each\n{'=' * 78}")
        hdr = (f"{'state':<6}{'df':>4}{'days':>6}{'sd':>7}{'rho':>7}"
               f"{'real':>8}{'floor':>8}{'ratio':>8}")
        print(hdr); print("-" * len(hdr))
        for s in sorted(summary, key=lambda s: -s["real"] / max(s["floor_mean"], 1e-9)):
            print(f'{s["state"]:<6}{s["df"]:>4}{s["days"]:>6}{s["sd"]:>7.2f}'
                  f'{s["rho"]:>7.3f}{s["real"]:>8.2f}{s["floor_mean"]:>8.2f}'
                  f'{s["real"] / max(s["floor_mean"], 1e-9):>8.1f}')
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / "known_answer.json"
        # Accumulate by (report, coverage, one_commodity) rather than replace.
        # Every run used to overwrite the file, so the floor of the state read
        # before this one was destroyed by the run after it, and eleven floors
        # existed only inside a prose table. A floor that is not on disk beside
        # the reading it divides cannot be checked against it later.
        keep = []
        if dest.exists():
            try:
                keep = json.loads(dest.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                keep = []
        tag = lambda s: (s.get("report"), s.get("min_coverage"),
                         s.get("one_commodity"))
        for s in summary:
            s["min_coverage"] = a.min_coverage
            s["one_commodity"] = a.one_commodity
            s["ratio"] = s["real"] / max(s["floor_mean"], 1e-9)
        fresh = {tag(s) for s in summary}
        merged = [s for s in keep if tag(s) not in fresh] + summary
        merged.sort(key=lambda s: (str(s.get("state")), s.get("report") or 0,
                                   s.get("min_coverage") or 0,
                                   str(s.get("one_commodity"))))
        dest.write_text(json.dumps(merged, ensure_ascii=False, indent=2,
                                   sort_keys=True), encoding="utf-8")
        print(f"\nwrote {dest.relative_to(REPO)}  ({len(merged)} row(s))")


if __name__ == "__main__":
    main()
