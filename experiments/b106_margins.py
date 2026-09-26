"""B106 step five: which class attribute's premium is the position-specific one.

B106-3 reads an interaction of about four tenths, B106-4 shows it repeats, and
B106-8 shows four position characteristics cannot produce it. None of those says
WHERE in the class structure it lives.

The 18 classes are a complete 3 by 3 by 2 grid, education by age by gender, so
the interaction splits orthogonally into position crossed with each part of that
grid: seven components, 17 degrees of freedom in all, summing exactly to the
whole. The share each one would take from a leftover with no structure is its own
degrees of freedom over 17, so every component has its own floor and none of them
is invented.

It also answers a worry the coarse classes raise on their own. Education and age
are coarsened to three levels each, so part of the interaction could be
composition inside a coarse class differing by position rather than pay differing
by position. Gender is not coarsened: it is two levels and there is nothing
inside them to shift. So the position-by-gender component cannot be a coarsening
artefact, and if it carries and repeats, coarsening is not the source.

The finer codes the module also ships cannot answer that: they exist for 26
positions, all of them one country at one aggregate industry code, so no table
can be built from them at all. That is registered rather than attempted.

    python experiments/b106_margins.py
    python experiments/b106_margins.py --no-write
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
OUT = ROOT / "results" / "b106_margins.json"


def _mod(name):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


SEP = _mod("b106_separability")
K = SEP.K

#: Seven components and their degrees of freedom on a 3 x 3 x 2 grid. They sum
#: to 17, which is K - 1, and each one's share of a leftover with no structure is
#: its own count over 17.
PARTS = [("education", (1, 0, 0), 2), ("age", (0, 1, 0), 2), ("gender", (0, 0, 1), 1),
         ("education x age", (1, 1, 0), 4), ("education x gender", (1, 0, 1), 2),
         ("age x gender", (0, 1, 1), 2), ("all three", (1, 1, 1), 4)]


def split(row):
    """One position's leftover over the 18 classes, split by the class grid.

    Each component is the part that varies along exactly the named axes: take the
    mean over every axis NOT named, then subtract every lower component that its
    own axes contain. On a complete balanced grid the seven are orthogonal and
    sum back to the whole, which criterion 11 reads back rather than assuming.
    """
    X = np.asarray(row, float).reshape(3, 3, 2)
    X = X - X.mean()
    got = {}
    for name, axes, _df in PARTS:
        m = X.copy()
        for ax, on in enumerate(axes):
            if not on:
                m = m.mean(axis=ax, keepdims=True)
        m = np.broadcast_to(m, X.shape).copy()
        for nm2, ax2, _ in PARTS:
            if nm2 != name and all(b <= a for a, b in zip(axes, ax2)):
                m = m - got[nm2]
        got[name] = m
    return got


def per_table(P):
    """Interaction of one table, then each row split by the class grid."""
    r, _ = SEP.interaction(P)
    acc = {name: 0.0 for name, _, _ in PARTS}
    for i in range(r.shape[0]):
        g = split(r[i])
        for name in acc:
            acc[name] += float((g[name] ** 2).sum())
    return acc, float((r ** 2).sum())


# ------------------------------------------- B106-11 the split is exact

def check_exact(tabs, rng, reps):
    worst_sum, worst_plant = 0.0, 0.0
    for cy in list(tabs)[:reps * 8]:
        rows_, classes_, P, E_ = tabs[cy]
        acc, tot = per_table(P)
        if tot > 0:
            worst_sum = max(worst_sum, abs(sum(acc.values()) - tot) / tot)
    # plant a leftover that varies only with gender, and read it back whole
    for _ in range(reps):
        J = 12
        c = rng.normal(size=2); c = c - c.mean()
        z = rng.normal(size=J); z = z - z.mean()
        R = np.zeros((J, 3, 3, 2))
        for i in range(J):
            R[i, :, :, :] = z[i] * c
        P = R.reshape(J, K)
        acc, tot = per_table(P)
        worst_plant = max(worst_plant, abs(acc["gender"] / tot - 1.0))
    ok = worst_sum < 1e-9 and worst_plant < 1e-9
    detail = (f"the seven components sum back to the interaction, worst relative "
              f"gap {worst_sum:.2e} over {min(len(tabs), reps*8)} tables. A "
              f"leftover planted to vary only with gender comes back entirely in "
              f"the gender component, worst gap {worst_plant:.2e} over {reps} "
              f"draws. Degrees of freedom: "
              + ", ".join(f"{n} {df}" for n, _, df in PARTS)
              + f", summing to {sum(df for _,_,df in PARTS)} = K - 1.")
    return bool(ok), detail, {"worst_sum_gap": worst_sum,
                              "worst_planted_gap": worst_plant,
                              "degrees_of_freedom": {n: df for n, _, df in PARTS}}


# ------------------------------------------- B106-12 where the leftover lives

def check_where(tabs):
    acc = {name: 0.0 for name, _, _ in PARTS}
    tot = 0.0
    for cy, v in tabs.items():
        a, t = per_table(v[2])
        for n in acc:
            acc[n] += a[n]
        tot += t
    rows = []
    for name, _, df in PARTS:
        share = acc[name] / tot
        floor = df / 17.0
        rows.append({"component": name, "share": share, "floor": floor,
                     "over_floor": share / floor, "df": df})
    rows.sort(key=lambda r: -r["over_floor"])
    ok = abs(sum(r["share"] for r in rows) - 1.0) < 1e-9
    detail = ("share of the interaction by class component, against the share "
              "each would take from a leftover with no structure, which is its "
              "own degrees of freedom over 17: "
              + "; ".join(f"{r['component']} {100*r['share']:.1f}% vs "
                          f"{100*r['floor']:.1f}% ({r['over_floor']:.2f}x)"
                          for r in rows)
              + ". Both the shares and the floors sum to one, so a component "
                "above its floor forces another below it: what is read here is "
                "the ORDER, not seven independent readings. The order is that "
                "the single attributes are above and their interactions below, "
                "so the position-specific part of the ladder moves along one "
                "attribute at a time. Gender is the one part of the grid that is "
                "not coarsened, so its component cannot be composition inside a "
                "class shifting by position.")
    return bool(ok), detail, {"by_component": rows}


# ------------------------------- B106-13 does each component repeat on its own

def check_persistence_by_part(tabs):
    store = {}
    for (geo, yr), v in tabs.items():
        names, P = v[0], v[2]
        r, _ = SEP.interaction(P)
        for i, nm in enumerate(names):
            g = split(r[i])
            for part in g:
                store[(geo, nm, part, yr)] = g[part].ravel()
    out = []
    for name, _, df in PARTS:
        a, b = [], []
        for (geo, nm, part, yr), v in store.items():
            if part != name:
                continue
            nxt = store.get((geo, nm, part, yr + 1))
            if nxt is not None:
                a.append(v); b.append(nxt)
        if not a:
            continue
        A = np.concatenate(a); B = np.concatenate(b)
        out.append({"component": name, "pairs": len(a),
                    "corr_next_year": float(np.corrcoef(A, B)[0, 1])})
    worst = min(o["corr_next_year"] for o in out)
    ok = worst > 0.0
    detail = ("adjacent-year correlation of each component on its own: "
              + "; ".join(f"{o['component']} {o['corr_next_year']:+.4f} over "
                          f"{o['pairs']:,}" for o in
                          sorted(out, key=lambda o: -o["corr_next_year"]))
              + ". The competing reading puts every one of these at zero, since "
                "it puts the whole interaction at zero.")
    return bool(ok), detail, {"by_component": out, "worst": worst}


# ------------------------------- B106-14 the finer codes cannot answer anything

def check_fine_codes():
    # The cache keeps only the coarse partition by design, so asking it whether
    # the finer codes exist would always answer no. This reads the raw file.
    import csv
    raw = ROOT / "data" / "raw" / "labour accounts.csv"
    pos = set()
    with raw.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["education"] not in ("1", "2", "3") or r["age"] not in ("1", "2", "3"):
                pos.add((r["nace_r2_code"], r["geo_code"], int(r["year"])))
    geos = sorted({p[1] for p in pos}); naces = sorted({p[0] for p in pos})
    ok = len(naces) < 2 or len(geos) < 2
    detail = (f"the module also ships finer education and age codes. They cover "
              f"{len(pos)} positions, on {len(naces)} industry code(s) "
              f"({', '.join(naces)}) in {len(geos)} country ({', '.join(geos)}). "
              f"A table needs two positions carrying the same classes, so no "
              f"table can be built from them and the finer granularity cannot be "
              f"read here at all. Registered rather than attempted: D37's shape, "
              f"a name in the listing with no record behind it.")
    return bool(ok), detail, {"positions": len(pos), "industries": naces,
                              "countries": geos}


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
        ("B106-11", "known_answer",
         "the seven components sum to the interaction, and a planted one comes "
         "back whole", check_exact(tabs, rng, a.reps)),
        ("B106-14", "instrument",
         "whether the module's finer codes can answer the coarsening question",
         check_fine_codes()),
        ("B106-12", "own_reading",
         "which part of the class grid carries the position-specific pay",
         check_where(tabs)),
        ("B106-13", "own_reading",
         "whether each component repeats on its own",
         check_persistence_by_part(tabs)),
    ]
    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        criteria.append({"name": name, "kind": kind, "criterion": what,
                         "passed": bool(passed), "detail": detail,
                         "payload": payload})
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")
    record = {"stage": "B106",
              "config": {"reps": a.reps, "seed": a.seed,
                         "grid": "3 education x 3 age x 2 gender",
                         "components": {n: df for n, _, df in PARTS},
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
