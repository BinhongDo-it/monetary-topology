"""A43: how many independent cross-graph cycles the pair machinery has. Zero.

A40 read catch-up as a set of scalar gaps and A42 asked which channel carries
them. Neither read a cycle, and the framework's own object is a cycle, so the
question left standing is whether one is available on this machine at all.

It is a count, so it costs nothing and it can veto (D22). For two connected
graphs joined by ``k`` edges,

    b1(joined) = b1(G1) + b1(G2) + (k - 1)

because each edge after the first closes exactly one new cycle. **A25's boundary
is one aggregate clearing balance, so ``k = 1`` and the cross-graph block is
zero.** A single bridge lies in no cycle; there is nothing to read a holonomy
around.

That is not a fault in A25. Its boundary is a clearing system and a clearing
system settles one net figure, which is the thing it was built to be. It does
mean a reading of catch-up as a loop needs a different boundary, and the count
says how much of one: ``k`` edges buy ``k - 1`` independent cycles, so two edges
buy the first. Joining position by position instead, on a shared position set,
is the product graph B79 already has a closed form for: ``G box K2`` has a
square block of ``|V_G| - 1``.

    python experiments/a43_pair_cycle_count.py --selftest
    python experiments/a43_pair_cycle_count.py --run
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from monetary_topology.network import Network, NetworkConfig, NetworkSpec  # noqa: E402

OUT = ROOT / "results" / "a43_pair_cycle_count.json"
SEEDS = (0, 1, 2, 3, 4)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


A25 = _load("a25", ROOT / "experiments" / "a25_boundary.py")


def undirected_edges(adj: np.ndarray) -> set[tuple[int, int]]:
    """The support of the adjacency, as unordered pairs, no self-loops.

    A cycle count is about which positions are joined, not about direction or
    weight, so this reads the support and nothing else.
    """
    r, c = np.nonzero(np.asarray(adj) > 0)
    return {(int(min(a, b)), int(max(a, b))) for a, b in zip(r, c) if a != b}


def components(n: int, edges: set[tuple[int, int]]) -> int:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return len({find(i) for i in range(n)})


def b1(n: int, edges: set[tuple[int, int]]) -> int:
    """|E| - |V| + (number of connected components). Counts isolated vertices."""
    return len(edges) - n + components(n, edges)


def join(adj1, adj2, bridges: list[tuple[int, int]]):
    """Two graphs side by side with ``bridges`` joining them, as one vertex set."""
    n1, n2 = adj1.shape[0], adj2.shape[0]
    e = set(undirected_edges(adj1))
    e |= {(a + n1, b + n1) for a, b in undirected_edges(adj2)}
    e |= {(int(min(a, b + n1)), int(max(a, b + n1))) for a, b in bridges}
    return n1 + n2, e


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    crit, report = [], {}
    rows = []
    for seed in SEEDS:
        g1 = Network(NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=1))
        g2 = Network(NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=1))
        a1, a2 = g1.adjacency, g2.adjacency
        n1 = a1.shape[0]
        e1, e2 = undirected_edges(a1), undirected_edges(a2)
        b_1, b_2 = b1(n1, e1), b1(a2.shape[0], e2)
        row = {"seed": seed, "n": n1, "edges_each": len(e1),
               "b1_each": [b_1, b_2], "joined": {}}
        for k in (0, 1, 2, 3, 5, 10):
            bridges = [(i, i) for i in range(k)]
            n, e = join(a1, a2, bridges)
            row["joined"][str(k)] = {"b1": b1(n, e), "components": components(n, e)}
        row["pairwise"] = {"bridges": n1,
                           "b1": b1(*join(a1, a2, [(i, i) for i in range(n1)]))}
        rows.append(row)
    report["rows"] = rows

    # ---- A43-1 the closed form against the count
    worst = 0
    for r in rows:
        base = r["b1_each"][0] + r["b1_each"][1]
        for k, v in r["joined"].items():
            k = int(k)
            expect = base + max(k - 1, 0)
            worst = max(worst, abs(v["b1"] - expect))
    crit.append(_crit(
        "A43-1  the closed form for a joined pair matches the count",
        "instrument", worst == 0,
        f"b1 = |E| - |V| + components, counted on the joined support by union-find, "
        f"against b1(G1) + b1(G2) + max(k - 1, 0) for k bridges. Five seeds by six "
        f"bridge counts: worst disagreement {worst}. The max is there because at k = 0 "
        f"the two graphs are separate components and no cycle is lost or gained; the "
        f"first bridge joins them and closes nothing."))

    # ---- A43-2 the reading: A25's boundary is one edge, so zero cycles
    k1 = [r["joined"]["1"]["b1"] - (r["b1_each"][0] + r["b1_each"][1]) for r in rows]
    k0 = [r["joined"]["0"]["b1"] - (r["b1_each"][0] + r["b1_each"][1]) for r in rows]
    pair_extra = [r["pairwise"]["b1"] - (r["b1_each"][0] + r["b1_each"][1]) for r in rows]
    n = rows[0]["n"]
    report["cross_graph_block"] = {"k0": k0, "k1": k1, "pairwise": pair_extra,
                                   "nodes_per_graph": n}
    crit.append(_crit(
        "A43-2  the pair machinery carries no cross-graph cycle at all",
        "own_reading", all(x == 0 for x in k1),
        f"A25 settles one net figure between the two sides, so the join is one edge. "
        f"Cross-graph block at one bridge: {k1}, five seeds. A single bridge lies in no "
        f"cycle, so there is no closed path that leaves one graph and returns, and a "
        f"holonomy between the two graphs has no object on this machine. **That is a "
        f"property of what a clearing system is and not a fault**: it settles a net "
        f"figure, which is one number. The count also says the price of changing it: k "
        f"bridges buy k - 1 independent cycles, so two buy the first. Joining position "
        f"by position on the shared {n}-position set buys {pair_extra[0]}, which is "
        f"n - 1 and is B79's square block for a product with K2."))

    # ---- A43-3 what this closes
    crit.append(_crit(
        "A43-3  what this closes and what it opens", "bookkeeping", True,
        "closes: whether A40 and A42 could have read catch-up as a loop and did not. "
        "They could not; there was none to read. Opens: a boundary with more than one "
        "edge, which is a different clearing rule and not a flag on this one. Neither "
        "A40's nor A42's readings change, because neither claimed to read a cycle."))

    record = {"stage": "A43",
              "config": {"seeds": list(SEEDS), "bridge_counts": [0, 1, 2, 3, 5, 10],
                         "carrier": "NetworkSpec default, adjacency support only",
                         "note": "no run is needed: this reads the graph as built"},
              "criteria": crit, "report": report}
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:520]}\n")
    r = rows[0]
    print(f"  seed 0: {r['n']} positions a side, {r['edges_each']} edges, "
          f"b1 each {r['b1_each']}")
    print(f"     {'bridges':>8}  {'b1(joined)':>11}  {'components':>11}  {'cross block':>12}")
    for k, v in r["joined"].items():
        base = r["b1_each"][0] + r["b1_each"][1]
        print(f"     {k:>8}  {v['b1']:>11}  {v['components']:>11}  {v['b1']-base:>12}")
    print(f"     {r['pairwise']['bridges']:>8}  {r['pairwise']['b1']:>11}  "
          f"{1:>11}  {r['pairwise']['b1']-r['b1_each'][0]-r['b1_each'][1]:>12}  "
          f"<- position by position")
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nrecord -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


def selftest():
    """Every branch planted on graphs whose answer is known by hand (11f)."""
    ok = []
    # a triangle: b1 = 3 - 3 + 1 = 1
    tri = {(0, 1), (1, 2), (0, 2)}
    ok.append(b1(3, tri) == 1)
    print(f"  triangle            -> b1 {b1(3, tri)}  (want 1)")
    # a path: b1 = 2 - 3 + 1 = 0
    path = {(0, 1), (1, 2)}
    ok.append(b1(3, path) == 0)
    print(f"  path                -> b1 {b1(3, path)}  (want 0)")
    # two triangles, no bridge: 2 components, b1 = 6 - 6 + 2 = 2
    two = tri | {(3, 4), (4, 5), (3, 5)}
    ok.append(b1(6, two) == 2 and components(6, two) == 2)
    print(f"  two triangles apart -> b1 {b1(6, two)}, components "
          f"{components(6, two)}  (want 2, 2)")
    # one bridge closes nothing
    one = two | {(0, 3)}
    ok.append(b1(6, one) == 2 and components(6, one) == 1)
    print(f"  one bridge          -> b1 {b1(6, one)}, components "
          f"{components(6, one)}  (want 2, 1)")
    # the second bridge closes exactly one
    twob = one | {(1, 4)}
    ok.append(b1(6, twob) == 3)
    print(f"  second bridge       -> b1 {b1(6, twob)}  (want 3)")
    # an isolated vertex must not change b1
    ok.append(b1(7, twob) == 3)
    print(f"  plus a lone vertex  -> b1 {b1(7, twob)}  (want 3, unchanged)")
    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(selftest() if a.selftest else run(write=not a.no_write))
