"""B124: Theorem 46 checked on generated transport problems.

Statement and proof in docs/b124_transport_dual.md. Levels set by an allocation are the dual
of a transport problem. The checks read, on random connected bipartite graphs with supplies
and demands in general position:

  K1  the routes with flow form a spanning tree, carry their terms exactly, and the routes
      without flow hold the inequality;
  K2  a new route with D >= 0 moves nothing, and one with D < 0 carries flow and moves its
      pair's relative level by the whole of D;
  K3  a small change of term on a route in use moves exactly the pairs that route separates;
  K4  a least-squares fit on the tree of used routes reproduces the levels exactly, while
      Theorem 41's share on the same tree lies strictly between 0 and 1.

Run:  python experiments/b124_transport_dual.py [--selftest] [--trials N] [--seed S]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b124_transport_dual.json"
TOL = 1e-7


def random_problem(rng, nz, nj, extra):
    """Connected bipartite graph: a random spanning tree plus `extra` random edges.
    Supplies and demands are the row and column sums of a positive flow drawn on every edge,
    so the problem is feasible and its data are in general position."""
    order = [("z", 0), ("j", 0)] + rng.permutation(
        [("z", i) for i in range(1, nz)] + [("j", i) for i in range(1, nj)]).tolist()
    order = [(a, int(b)) for a, b in order]
    edges = {(0, 0)}
    placed = {"z": [0], "j": [0]}
    for side, i in order[2:]:
        other = "j" if side == "z" else "z"
        k = placed[other][int(rng.integers(len(placed[other])))]
        edges.add((i, k) if side == "z" else (k, i))
        placed[side].append(i)
    for _ in range(extra):
        edges.add((int(rng.integers(nz)), int(rng.integers(nj))))
    edges = sorted(edges)
    x0 = {e: float(rng.uniform(0.2, 2.0)) for e in edges}
    s = np.array([sum(v for (z, _), v in x0.items() if z == i) for i in range(nz)])
    d = np.array([sum(v for (_, j), v in x0.items() if j == i) for i in range(nj)])
    c = {e: float(rng.uniform(0.0, 10.0)) for e in edges}
    return {"nz": nz, "nj": nj, "edges": edges, "c": c, "s": s, "d": d}


def connected(nz, nj, edges):
    adj = {("z", i): set() for i in range(nz)} | {("j", i): set() for i in range(nj)}
    for z, j in edges:
        adj[("z", z)].add(("j", j))
        adj[("j", j)].add(("z", z))
    start = ("z", 0)
    seen, stack = {start}, [start]
    while stack:
        for v in adj[stack.pop()]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == nz + nj


def solve(p):
    """Return flows {edge: x} and levels phi as (phi_z, phi_j), phi_z[0] fixed at 0."""
    E = p["edges"]
    nz, nj = p["nz"], p["nj"]
    A = np.zeros((nz + nj, len(E)))
    for k, (z, j) in enumerate(E):
        A[z, k] = 1.0
        A[nz + j, k] = 1.0
    b = np.concatenate([p["s"], p["d"]])
    cost = np.array([p["c"][e] for e in E])
    res = linprog(cost, A_eq=A, b_eq=b, bounds=(0, None), method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    y = res.eqlin.marginals
    phi_z = -y[:nz]
    phi_j = y[nz:]
    shift = phi_z[0]
    return dict(zip(E, res.x)), phi_z - shift, phi_j - shift, float(res.fun)


def is_tree(nz, nj, edges):
    return len(edges) == nz + nj - 1 and connected(nz, nj, edges)


def k1(p, x, pz, pj):
    used = [e for e in p["edges"] if x[e] > TOL]
    tight = max(abs(pj[j] - pz[z] - p["c"][(z, j)]) for z, j in used)
    slack = min(p["c"][(z, j)] - (pj[j] - pz[z]) for z, j in p["edges"])
    return {"tree": is_tree(p["nz"], p["nj"], used), "max_tight_error": tight,
            "min_slack": slack, "ok": is_tree(p["nz"], p["nj"], used) and tight < TOL and slack > -TOL}


def non_edge(p, rng):
    E = set(p["edges"])
    cand = [(z, j) for z in range(p["nz"]) for j in range(p["nj"]) if (z, j) not in E]
    return cand[rng.integers(len(cand))] if cand else None


def k2(p, x, pz, pj, rng):
    e = non_edge(p, rng)
    if e is None:
        return None
    z, j = e
    rel = pj[j] - pz[z]
    c_e = float(rel + rng.uniform(-4.0, 4.0))
    D = c_e - rel
    q = dict(p, edges=sorted(p["edges"] + [e]), c={**p["c"], e: c_e})
    x2, pz2, pj2, _ = solve(q)
    if D >= 0:
        moved = max(np.max(np.abs(pz2 - pz)), np.max(np.abs(pj2 - pj)))
        return {"D": D, "case": "idle", "max_level_move": float(moved), "ok": moved < TOL}
    new_rel = pj2[j] - pz2[z]
    return {"D": D, "case": "enters", "flow": float(x2[e]), "move": float(new_rel - rel),
            "ok": x2[e] > TOL and abs((new_rel - rel) - D) < TOL}


def split_by(p, used, e):
    """Vertices on j's side of tree `used` after removing e."""
    rest = [f for f in used if f != e]
    adj = {}
    for z, j in rest:
        adj.setdefault(("z", z), set()).add(("j", j))
        adj.setdefault(("j", j), set()).add(("z", z))
    start = ("j", e[1])
    seen, stack = {start}, [start]
    while stack:
        for v in adj.get(stack.pop(), ()):
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return seen


def k3(p, x, pz, pj, rng):
    used = [e for e in p["edges"] if x[e] > TOL]
    e = used[rng.integers(len(used))]
    slack = [p["c"][f] - (pj[f[1]] - pz[f[0]]) for f in p["edges"] if f not in used]
    delta = 0.1 * min(slack) if slack else 0.5
    delta = delta if delta > 0 else 1e-3
    q = dict(p, c={**p["c"], e: p["c"][e] + delta})
    x2, pz2, pj2, _ = solve(q)
    side = split_by(p, used, e)
    lev = {("z", i): v for i, v in enumerate(pz)} | {("j", i): v for i, v in enumerate(pj)}
    lev2 = {("z", i): v for i, v in enumerate(pz2)} | {("j", i): v for i, v in enumerate(pj2)}
    worst = 0.0
    for a in lev:
        for b in lev:
            sep = (a in side) != (b in side)
            want = (delta if b in side else -delta) if sep else 0.0
            got = (lev2[b] - lev2[a]) - (lev[b] - lev[a])
            worst = max(worst, abs(got - want))
    same_tree = sorted(f for f in p["edges"] if x2[f] > TOL) == sorted(used)
    return {"delta": delta, "same_tree": same_tree, "max_error": worst,
            "ok": same_tree and worst < TOL}


def ls_on_tree(p, used, x):
    """Weighted least squares on the used routes, weights = flows. Returns levels and the
    Laplacian pseudo-inverse for Theorem 41's resistance."""
    nz, nj = p["nz"], p["nj"]
    n = nz + nj
    B = np.zeros((len(used), n))
    w = np.array([x[e] for e in used])
    om = np.array([p["c"][e] for e in used])
    for k, (z, j) in enumerate(used):
        B[k, z] = -1.0
        B[k, nz + j] = 1.0
    L = B.T @ (w[:, None] * B)
    Lp = np.linalg.pinv(L)
    phi = Lp @ (B.T @ (w * om))
    return phi - phi[0], Lp


def k4(p, x, pz, pj, rng):
    used = [e for e in p["edges"] if x[e] > TOL]
    phi, Lp = ls_on_tree(p, used, x)
    exact = max(np.max(np.abs(phi[:p["nz"]] - pz)), np.max(np.abs(phi[p["nz"]:] - pj)))
    e = non_edge(p, rng) or used[0]
    b = np.zeros(p["nz"] + p["nj"])
    b[e[0]] -= 1.0
    b[p["nz"] + e[1]] += 1.0
    R = float(b @ Lp @ b)
    w_e = float(np.median([x[f] for f in used]))
    theta = w_e * R / (1.0 + w_e * R)
    return {"ls_equals_dual": exact, "theta_41": theta,
            "ok": exact < TOL and 0.0 < theta < 1.0}


def run(trials, seed):
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(trials):
        nz, nj = int(rng.integers(3, 8)), int(rng.integers(3, 8))
        p = random_problem(rng, nz, nj, extra=int(rng.integers(2, 2 * (nz + nj))))
        x, pz, pj, _ = solve(p)
        rows.append({"trial": t, "nz": nz, "nj": nj, "edges": len(p["edges"]),
                     "k1": k1(p, x, pz, pj), "k2": k2(p, x, pz, pj, rng),
                     "k3": k3(p, x, pz, pj, rng), "k4": k4(p, x, pz, pj, rng)})
    return rows


def criteria(rows):
    k2s = [r["k2"] for r in rows if r["k2"] is not None]
    cases = {c: sum(1 for k in k2s if k["case"] == c) for c in ("idle", "enters")}
    thetas = [r["k4"]["theta_41"] for r in rows]
    return [
        {"name": "B124-T1", "kind": "own_reading",
         "statement": "Used routes form a spanning tree, carry their terms exactly, unused routes hold the inequality",
         "passed": all(r["k1"]["ok"] for r in rows),
         "detail": f"{sum(r['k1']['ok'] for r in rows)} of {len(rows)}; worst tight error "
                   f"{max(r['k1']['max_tight_error'] for r in rows):.1e}"},
        {"name": "B124-T2", "kind": "own_reading",
         "statement": "A new route with D >= 0 moves nothing; with D < 0 it carries flow and moves its pair by all of D",
         "passed": bool(k2s) and all(k["ok"] for k in k2s) and cases["idle"] > 0 and cases["enters"] > 0,
         "detail": f"{sum(k['ok'] for k in k2s)} of {len(k2s)}; idle {cases['idle']}, enters {cases['enters']}"},
        {"name": "B124-T3", "kind": "own_reading",
         "statement": "A small term change on a used route moves exactly the pairs it separates",
         "passed": all(r["k3"]["ok"] for r in rows),
         "detail": f"{sum(r['k3']['ok'] for r in rows)} of {len(rows)}; worst "
                   f"{max(r['k3']['max_error'] for r in rows):.1e}"},
        {"name": "B124-T4", "kind": "own_reading",
         "statement": "Least squares on the used tree equals the dual; Theorem 41's share there lies in (0, 1)",
         "passed": all(r["k4"]["ok"] for r in rows),
         "detail": f"{sum(r['k4']['ok'] for r in rows)} of {len(rows)}; theta range "
                   f"{min(thetas):.3f} to {max(thetas):.3f}"},
    ]


def selftest(seed):
    rng = np.random.default_rng(seed)
    p = random_problem(rng, 4, 5, extra=6)
    x, pz, pj, _ = solve(p)
    assert k1(p, x, pz, pj)["ok"]
    bad = pj.copy()
    bad[0] += 0.5
    assert not k1(p, x, pz, bad)["ok"], "K1 did not flip on shifted levels"
    r = {"k1": {"ok": True, "max_tight_error": 0.0}, "k2": {"case": "enters", "ok": False, "D": -1.0},
         "k3": {"ok": True, "max_error": 0.0}, "k4": {"ok": True, "theta_41": 0.5}}
    good = dict(r, k2={"case": "idle", "ok": True, "D": 1.0})
    cr = criteria([r, good])
    assert not cr[1]["passed"], "T2 did not flip on a failed entering case"
    cr = criteria([good, good])
    assert not cr[1]["passed"], "T2 did not flip when no entering case was drawn"
    r4 = dict(good, k4={"ok": False, "theta_41": 1.0})
    assert not criteria([r4, dict(r4, k2={'case': 'enters', 'ok': True, 'D': -1.0})])[3]["passed"], \
        "T4 did not flip"
    print("selftest: 4/4 seeds flip their flag")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261026)
    a = ap.parse_args()
    if a.selftest:
        selftest(a.seed)
        return 0
    rows = run(a.trials, a.seed)
    crit = criteria(rows)
    for c in crit:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['statement']}  ({c['detail']})")
    rec = {"stage": "B124-T", "config": {"trials": a.trials, "seed": a.seed, "tol": TOL},
           "doc": "docs/b124_transport_dual.md", "criteria": crit,
           "trials": [{"trial": r["trial"], "nz": r["nz"], "nj": r["nj"], "edges": r["edges"],
                       "k2_case": r["k2"]["case"] if r["k2"] else None,
                       "k2_D": round(r["k2"]["D"], 6) if r["k2"] else None,
                       "theta_41": round(r["k4"]["theta_41"], 6)} for r in rows]}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
