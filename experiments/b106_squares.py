"""B106 step six: the squares themselves, one at a time, against a floor measured
from this panel's own year-to-year noise.

B106-3 reports the share of the field the interaction takes, and B106-4 reports
that the interaction repeats. Neither reports a square. A square here is two
positions by two classes,

    s = [p(j,k) - p(j,k')] - [p(j',k) - p(j',k')]

the difference in differences of log relative pay, and it is the object the
competing reading puts at exactly zero. Reporting it directly makes this station
comparable with the ones that report a loop sum or a square sum, rather than a
variance share that has to be translated first.

Only (J-1)(K-1) of the squares are independent; the rest are their sums. So the
basis is taken against one reference industry and one reference class, which is
306 squares per country-year at 19 industries and 18 classes.

The floor is measured, not declared. If a square were a standing feature and the
survey added independent error each year, then the year-over-year change in a
square is pure noise of size sqrt(2) times the per-reading error, so half that
difference's spread is the floor for a single reading. That floor is this
panel's own, per table, and nothing about it is borrowed.

    python experiments/b106_squares.py
    python experiments/b106_squares.py --no-write
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b106_squares.json"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SEP = _mod("b106_separability")
K = SEP.K


def squares(P):
    """The independent basis: every industry against row 0, every class against
    column 0. Returns an array of shape (J-1, K-1)."""
    return (P[1:, 1:] - P[1:, :1]) - (P[:1, 1:] - P[:1, :1])


# ------------------------------------------------- B106-15 the squares and a floor

def check_squares(tabs):
    """One entry per (country, year, industry, class) square, its value now and
    its value next year. The floor comes from the second of those."""
    store, byyear = {}, {}
    for (geo, yr), (rows, classes, P, E) in tabs.items():
        S = squares(P)
        for a in range(S.shape[0]):
            for b in range(S.shape[1]):
                store[(geo, rows[a + 1], classes[b + 1], yr)] = S[a, b]
        byyear.setdefault(geo, []).append(yr)

    # A ladder of lags rather than one number, because the assumption behind the
    # floor bends both ways and neither direction is settled by argument.
    # Assuming the square is constant year to year makes any real drift count as
    # noise, which INFLATES the floor and works against this reading. Survey
    # error correlated between adjacent years would DEFLATE it. A longer lag
    # carries more drift, so its floor is an upper bound: if the reading clears
    # that too, the floor's construction is not what it rests on.
    lags = {}
    for L in (1, 2, 5):
        a_, b_ = [], []
        for (geo, ind, cls, yr), v in store.items():
            w = store.get((geo, ind, cls, yr + L))
            if w is not None:
                a_.append(v); b_.append(w)
        if len(a_) > 100:
            lags[L] = {"pairs": len(a_),
                       "floor": float(np.std(np.array(b_) - np.array(a_)) / np.sqrt(2.0))}
    floor = lags[1]["floor"]
    flo_pairs = lags[1]["pairs"]

    vals = np.abs(np.array(list(store.values())))
    over = vals / floor
    for L, d in lags.items():
        o = vals / d["floor"]
        d["over_floor"] = int((o > 1).sum())
        d["fraction_over"] = float((o > 1).mean())
    ok = len(vals) > 0 and floor > 0
    detail = (f"{len(vals):,} independent squares over {len(tabs):,} country-year "
              f"tables, {(SEP.K-1)} classes against a reference class and every "
              f"industry against a reference industry. Floor measured from this "
              f"panel's own year-to-year change in the same square, "
              f"{flo_pairs:,} pairs: {floor:.4f} in log points. "
              f"|square| median {np.median(vals):.4f}, p90 "
              f"{np.percentile(vals,90):.4f}, max {vals.max():.4f}. "
              f"Above the floor: {int((over > 1).sum()):,} "
              f"({100*(over>1).mean():.1f}%); above twice it "
              f"{int((over > 2).sum()):,} ({100*(over>2).mean():.1f}%). "
              f"Median square is {np.median(over):.2f} times the floor. "
              + "Floor by lag, where a longer lag carries more real drift and so "
                "is an upper bound on the noise: "
              + ", ".join(f"{L}y {d['floor']:.4f} clears "
                          f"{100*d['fraction_over']:.1f}%"
                          for L, d in sorted(lags.items()))
              + ". The competing reading puts every one of these at exactly zero.")
    return bool(ok), detail, {
        "n_squares": int(len(vals)), "tables": len(tabs),
        "floor": floor, "floor_pairs": flo_pairs, "floor_by_lag": lags,
        "median_abs": float(np.median(vals)),
        "p90_abs": float(np.percentile(vals, 90)),
        "max_abs": float(vals.max()),
        "over_floor": int((over > 1).sum()),
        "over_twice_floor": int((over > 2).sum()),
        "median_over_floor": float(np.median(over))}


# ----------------------------------------------- B106-16 the basis is a basis

def check_basis(tabs, rng, reps):
    """Two answers known in advance. A separable field has every square exactly
    zero. And the basis spans: any square between two arbitrary industries and
    two arbitrary classes is a combination of four basis squares, so rebuilding
    it from them has to return the same number."""
    worst_zero, worst_rebuild = 0.0, 0.0
    keys = list(tabs)[:reps * 4]
    for r, cy in enumerate(keys):
        rows, classes, P, E = tabs[cy]
        J = P.shape[0]
        a = rng.normal(size=(J, 1)); b = rng.normal(size=(1, K))
        worst_zero = max(worst_zero, float(np.abs(squares(a + b)).max()))
        S = squares(P)
        for _ in range(20):
            j1, j2 = rng.integers(1, J, 2)
            k1, k2 = rng.integers(1, K, 2)
            direct = (P[j1, k1] - P[j1, k2]) - (P[j2, k1] - P[j2, k2])
            viabasis = (S[j1 - 1, k1 - 1] - S[j1 - 1, k2 - 1]
                        - S[j2 - 1, k1 - 1] + S[j2 - 1, k2 - 1])
            worst_rebuild = max(worst_rebuild, abs(direct - viabasis))
    ok = worst_zero < 1e-12 and worst_rebuild < 1e-9
    detail = (f"separable in, every square zero: worst {worst_zero:.2e} over "
              f"{len(keys)} tables. An arbitrary square rebuilt from four basis "
              f"squares against the direct calculation: worst "
              f"{worst_rebuild:.2e} over {20*len(keys)} draws. So the "
              f"{(SEP.K-1)} by (J-1) basis spans them and nothing is being "
              f"counted twice.")
    return bool(ok), detail, {"worst_zero": worst_zero,
                              "worst_rebuild": worst_rebuild,
                              "tables_checked": len(keys)}


# ------------------------------------------- B106-17 the rival, on the squares

def check_rival_squares(tabs):
    """The competing reading is that a class's pay at a position is a scalar on
    the position times a factor for the class. Every square is then identically
    zero. This is the same rival B106-4 scores, read on the object itself rather
    than on whether the leftover repeats."""
    ok_payload = check_squares(tabs)[2]
    frac = ok_payload["over_floor"] / ok_payload["n_squares"]
    ok = frac > 0.5
    detail = (f"{ok_payload['over_floor']:,} of {ok_payload['n_squares']:,} "
              f"squares ({100*frac:.1f}%) stand above the panel's own measured "
              f"floor of {ok_payload['floor']:.4f} log points, and "
              f"{ok_payload['over_twice_floor']:,} stand above twice it. The "
              f"median square is {ok_payload['median_over_floor']:.2f} times the "
              f"floor and the largest is {ok_payload['max_abs']:.4f}. A point "
              f"prediction of exactly zero, so PASS here means the prediction "
              f"does not hold.")
    return bool(ok), detail, ok_payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    d = SEP.load()
    tabs = SEP.tables(d, "industry")
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B106-16", "known_answer",
         "a separable field has every square zero, and the basis spans the rest",
         check_basis(tabs, rng, a.reps)),
        ("B106-15", "own_reading",
         "the squares themselves against a floor measured from this panel's own "
         "year-to-year noise", check_squares(tabs)),
        ("B106-17", "rival",
         "the position-scalar reading puts every square at exactly zero",
         check_rival_squares(tabs)),
    ]
    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        c = {"name": name, "kind": kind, "criterion": what,
             "passed": bool(passed), "detail": detail, "payload": payload}
        if kind == "rival":
            c.update({
                "grid": "B",
                "rival_shape": "point prediction",
                "rival_premise":
                    "there is a scalar on the position and a factor for the "
                    "class, so in logs the pay field is additively separable",
                "rival_entailment":
                    "under that premise p(j,k) = a_j + b_k, so every difference "
                    "in differences across two positions and two classes "
                    "cancels term by term and is identically zero. The squares "
                    "read here are that quantity.",
                "grid_note": {
                    "ours": "two classes at one position are on different terms "
                            "and the terms are the position's own, so the "
                            "squares do not vanish",
                    "rival": "every square is exactly zero",
                    "reality": "filled in by this run",
                },
            })
        criteria.append(c)
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {"stage": "B106",
              "config": {"reps": a.reps, "seed": a.seed,
                         "basis": "every industry against row 0, every class "
                                  "against column 0",
                         "floor": "sd of the year-over-year change in the same "
                                  "square, divided by sqrt(2)",
                         "sources": ["labour accounts.csv"]},
              "criteria": criteria}
    body = json.dumps(record, indent=2, sort_keys=True, default=float)
    print(f"\n{sum(c['passed'] for c in criteria)}/{len(criteria)} pass, "
          f"{time.time()-t0:.2f}s, sha256 "
          f"{hashlib.sha256(body.encode()).hexdigest()[:16]}")
    if not a.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(body, encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
