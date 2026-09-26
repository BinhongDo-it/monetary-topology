"""B106 step three: does the leftover dissolve into position characteristics?

B106-3 reads an interaction of about four tenths of the field, and B106-4 shows
it repeats: the same position and class carry the same leftover next year at
+0.95 and a decade later at +0.67, while breaking the position pairing and
keeping every marginal drops it to +0.05. So it is a standing feature rather than
survey error.

The reading that competes with this one does not deny that. It says the ladder
differs between positions because the positions differ: capital per hour,
productivity, size, how much of the value added labour takes. On that reading a
handful of position characteristics, each allowed its own loading per class, is
enough to produce the leftover, and what remains after them is noise.

That is a quantity, so it is measured here rather than argued about. The
generous scope lets every country-year have its OWN class loadings, which is far
more freedom than the reading needs, and the strict scope solves one set for the
whole panel.

How much would have to be absorbed for the competing reading to close: B106-4
puts the non-repeating share of the interaction at about one minus the
adjacent-year correlation, so roughly five percent is sampling error and the
other ninety five is standing structure that something has to account for.

    python experiments/b106_absorption.py
    python experiments/b106_absorption.py --no-write
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
OUT = ROOT / "results" / "b106_absorption.json"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SEP = _mod("b106_separability")
SECTIONS, K = SEP.SECTIONS, SEP.K

#: The four position characteristics, named before anything is fitted. Each is a
#: property of the position and none of them reads the class breakdown, so none
#: of them can reach the field through a shared term: the field is a ratio of two
#: shares of the position's own totals, and those totals cancel out of it.
COVARS = ["ln_capital_per_hour", "ln_value_added_per_hour", "labour_share", "ln_hours"]


def covariates():
    g = np.load(ROOT / "data/cache/b101_klems_basic.npz", allow_pickle=False)
    k = np.load(ROOT / "data/cache/b101_capital.npz", allow_pickle=False)
    n = np.load(ROOT / "data/cache/b101_national.npz", allow_pickle=False)
    gc = {v: g["values"][:, i] for i, v in enumerate(list(g["vars"]))}
    kc = {v: k["values"][:, i] for i, v in enumerate(list(k["vars"]))}
    nc = {v: n["values"][:, i] for i, v in enumerate(list(n["vars"]))}
    ki = {(str(a), str(b), int(c)): i for i, (a, b, c) in
          enumerate(zip(k["nace"], k["geo"], k["year"]))}
    ni = {(str(a), str(b), int(c)): i for i, (a, b, c) in
          enumerate(zip(n["nace"], n["geo"], n["year"]))}
    out = {}
    for i, (a, b, c) in enumerate(zip(g["nace"], g["geo"], g["year"])):
        key = (str(a), str(b), int(c))
        if key[0] not in SECTIONS:
            continue
        j, m = ki.get(key), ni.get(key)
        if j is None or m is None:
            continue
        L, C, Y = gc["LAB"][i], gc["CAP"][i], gc["VA_CP"][i]
        Kp, H = kc["K_GFCF"][j], nc["H_EMP"][m]
        if not all(np.isfinite(v) for v in (L, C, Y, Kp, H)):
            continue
        if not (L > 0 and Y > 0 and Kp > 0 and H > 0 and L + C > 0):
            continue
        out[key] = np.array([np.log(Kp / H), np.log(Y / H), L / (L + C), np.log(H)])
    return out


def build_tables(cov):
    """One table per (country, year): rows are sections that carry both the class
    field and all four characteristics, columns are the 18 classes."""
    d = SEP.load()
    keep = np.isin(d["nace"], SECTIONS) & d["ok"]
    classes = sorted(set(d["cls"][keep]))
    ci = {c: i for i, c in enumerate(classes)}
    grid = {}
    for i in np.flatnonzero(keep):
        key = (str(d["nace"][i]), str(d["geo"][i]), int(d["year"][i]))
        if key not in cov:
            continue
        grid.setdefault((key[1], key[2]), {}).setdefault(key[0], {})[ci[str(d["cls"][i])]] = d["p"][i]
    out = {}
    for cy, rowmap in grid.items():
        full = sorted(r for r, v in rowmap.items() if len(v) == len(classes))
        if len(full) < 6:
            continue
        P = np.array([[rowmap[r][c] for c in range(len(classes))] for r in full])
        Z = np.array([cov[(r, cy[0], cy[1])] for r in full])
        out[cy] = (full, P, Z)
    return out, classes


def design(Z, K_):
    """The competing reading, written out: each characteristic gets its own
    loading per class. Both sides are centred the way the interaction is, so the
    design cannot reach the row or column effects that are already removed."""
    Zc = Z - Z.mean(axis=0, keepdims=True)
    cols = []
    for m in range(Zc.shape[1]):
        for kk in range(K_):
            M = np.zeros((Z.shape[0], K_))
            M[:, kk] = Zc[:, m]
            M -= M.mean(axis=1, keepdims=True)
            cols.append(M.ravel())
    return np.array(cols).T


def absorbed(r, X):
    y = r.ravel()
    if X.size == 0:
        return 0.0
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    tot = float(y @ y)
    return 1.0 - float(res @ res) / tot if tot > 0 else 0.0


# ------------------------------------------------------- B106-6 what joined

def check_join(tabs, cov):
    J = np.array([len(v[0]) for v in tabs.values()])
    dims = (J - 1) * (K - 1)
    params = len(COVARS) * (K - 1)
    ok = len(tabs) > 0 and params < int(np.median(dims))
    detail = (f"{len(cov):,} positions carry all four modules at section level. "
              f"{len(tabs):,} country-year tables with six or more sections, rows "
              f"min {J.min()} median {int(np.median(J))} max {J.max()}. The "
              f"interaction of the median table has {int(np.median(dims))} "
              f"dimensions and the competing reading spends {params} of them "
              f"per table, {len(COVARS)} characteristics times {K-1} free class "
              f"loadings, so it is a test and not a saturation.")
    return bool(ok), detail, {"positions": len(cov), "tables": len(tabs),
                              "rows_median": int(np.median(J)),
                              "interaction_dims_median": int(np.median(dims)),
                              "params_per_table": params,
                              "covariates": COVARS}


# ----------------------------------------------------- B106-7 planted answers

def check_planted(tabs, rng, reps):
    """Plant a leftover the competing reading can produce, and one it cannot.
    The first must come out fully absorbed; the second must come out at the
    degrees of freedom the design spends and no more."""
    keys = list(tabs)[:reps * 8]
    made, orth = [], []
    for t, cy in enumerate(keys):
        rows, P, Z = tabs[cy]
        X = design(Z, K)
        Zc = Z - Z.mean(axis=0, keepdims=True)
        c = rng.normal(size=K)
        r = np.outer(Zc[:, 0], c - c.mean())          # exactly the reading's shape
        made.append(absorbed(r, X))
        n = rng.normal(size=P.shape)                   # nothing to do with Z
        n = n - n.mean(axis=1, keepdims=True) - n.mean(axis=0, keepdims=True) + n.mean()
        orth.append(absorbed(n, X))
    worst_made = min(made)
    dims = np.array([(len(tabs[cy][0]) - 1) * (K - 1) for cy in keys])
    expect = len(COVARS) * (K - 1) / dims
    gap = float(np.max(np.abs(np.array(orth) - expect)))
    ok = worst_made > 1 - 1e-9 and gap < 0.15
    detail = (f"{len(keys)} tables. A leftover of exactly the competing reading's "
              f"shape, one characteristic times a class loading: absorbed "
              f"{100*worst_made:.4f}% at worst. A leftover with nothing to do "
              f"with the characteristics: absorbed a median "
              f"{100*np.median(orth):.1f}% against the "
              f"{100*np.median(expect):.1f}% the design spends by counting alone, "
              f"worst gap {gap:.3f}. So anything above that counting figure is "
              f"the characteristics doing work rather than the parameters.")
    return bool(ok), detail, {"worst_planted": worst_made,
                              "orthogonal_median": float(np.median(orth)),
                              "counting_median": float(np.median(expect)),
                              "worst_gap": gap}


# --------------------------------------------- B106-8 how much they absorb

def check_absorption(tabs):
    per, glob_num, glob_den, rows, counting = [], 0.0, 0.0, [], []
    Xs, rs = [], []
    for cy, (names, P, Z) in tabs.items():
        r, _ = SEP.interaction(P)
        X = design(Z, K)
        per.append(absorbed(r, X))
        counting.append(len(COVARS) * (K - 1) / ((len(names) - 1) * (K - 1)))
        Xs.append(X); rs.append(r.ravel())
        rows.append({"cell": f"{cy[0]}/{cy[1]}", "rows": len(names),
                     "absorbed": per[-1]})
    per = np.array(per); counting = np.array(counting)
    Xg = np.vstack(Xs); yg = np.concatenate(rs)
    beta, *_ = np.linalg.lstsq(Xg, yg, rcond=None)
    resg = yg - Xg @ beta
    glob = 1.0 - float(resg @ resg) / float(yg @ yg)
    net = float(np.median(per - counting))
    ok = True
    detail = (f"{len(per):,} country-year tables. Letting every table have its "
              f"own class loadings on the four characteristics, the generous "
              f"scope, absorbs a median {100*np.median(per):.1f}% of the "
              f"interaction, against {100*np.median(counting):.1f}% that the same "
              f"number of parameters absorbs from a leftover with no relation to "
              f"them, so the characteristics themselves account for about "
              f"{100*net:.1f} points. One set of loadings for the whole panel, "
              f"the strict scope, absorbs {100*glob:.1f}% with "
              f"{len(COVARS)*(K-1)} parameters against {len(yg):,} observations. "
              f"B106-4 puts the standing share of the interaction near 95%, so "
              f"that is what a reading built on position characteristics would "
              f"have to reach.")
    rows.sort(key=lambda r: -r["absorbed"])
    return bool(ok), detail, {
        "tables": int(len(per)),
        "per_table_median": float(np.median(per)),
        "per_table_p90": float(np.percentile(per, 90)),
        "counting_median": float(np.median(counting)),
        "net_of_counting_median": net,
        "global": glob, "global_params": len(COVARS) * (K - 1),
        "global_observations": int(len(yg)),
        "top20": rows[:20], "bottom20": rows[-20:]}


# -------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    cov = covariates()
    tabs, classes = build_tables(cov)
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B106-6", "instrument",
         "the join, and whether the competing reading is being given a test or a "
         "saturation", check_join(tabs, cov)),
        ("B106-7", "known_answer",
         "a leftover of the competing reading's own shape is fully absorbed, one "
         "unrelated to it only at the counting figure",
         check_planted(tabs, rng, a.reps)),
        ("B106-8", "own_reading",
         "how much of the leftover four position characteristics with their own "
         "class loadings can produce", check_absorption(tabs)),
    ]
    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        criteria.append({"name": name, "kind": kind, "criterion": what,
                         "passed": bool(passed), "detail": detail,
                         "payload": payload})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {
        "stage": "B106",
        "config": {"reps": a.reps, "seed": a.seed, "covariates": COVARS,
                   "field": "ln(Share_W / Share_E)", "classes": K,
                   "sections": SECTIONS,
                   "sources": ["labour accounts.csv", "growth accounts basic.csv",
                               "capital accounts.csv", "national accounts.csv"]},
        "criteria": criteria,
    }
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
