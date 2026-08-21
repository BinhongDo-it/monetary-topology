"""B17 gate zero: count the states and the realised transitions between them.

Pure counting on data already on disk. No download, no sampling, no null model.
The output is the state list and the transition matrix, printed as objects
rather than summarised, because a Betti number without the graph under it
cannot be read.

`b1 = E - V + C` on the undirected graph of realised transitions. Three
variants are reported and they answer different questions:

    full        every state including the absorbing terminals
    no-terminal terminals dropped; a loan that leaves never returns, so a
                terminal cannot carry a loop the framework can price
    recurrent   states that lie on at least one directed cycle
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data" / "processed" / "fannie_core" / "v1"


def load(q: str, name: str, dtype):
    return np.fromfile(CORE / q / f"row_{name}.bin", dtype=dtype)


def enumerate_fields(q: str) -> None:
    man = json.loads((CORE / q / "manifest.json").read_text(encoding="utf-8"))
    print(f"--- {q}   n_loans={man['n_loans']:,}   n_rows={man['n_rows']:,}")
    for name in ("delinq", "mod_flag", "zero_bal", "assist"):
        a = load(q, name, np.uint8)
        v, c = np.unique(a, return_counts=True)
        order = np.argsort(-c)
        shown = ", ".join(
            "%s:%s%s" % (int(v[i]), f"{int(c[i]):,}",
                         " (sentinel)" if int(v[i]) == 255 else "")
            for i in order[:14]
        )
        extra = "" if len(v) <= 14 else f"  ... {len(v) - 14} more values"
        print(f"    {name:<9} {len(v):>3} distinct   {shown}{extra}")


if __name__ == "__main__":
    for q in sys.argv[1:] or ["2002Q1"]:
        enumerate_fields(q)


# --------------------------------------------------------------------------
# The transition graph.
#
# A state is (delinquency depth, modified yes/no). The depth is the raw field:
# no bucketing, because bucketing is a choice and gate zero is a count.
#
# `b1 = E - V + C` is reported against a floor on the edge count rather than at
# one threshold. A single mis-keyed row can invent an edge and an invented edge
# can invent a loop, so the number that matters is where the curve flattens,
# not the number at any one floor. No floor is registered here and none is used
# to decide anything: the curve is the output.

SENT = 255


def states(q: str):
    d = load(q, "delinq", np.uint8).astype(np.int32)
    m = load(q, "mod_flag", np.uint8)
    ok = (d != SENT) & (m != SENT)
    s = d * 2 + (m == 89)          # 89 is ASCII 'Y'
    s[~ok] = -1
    return s


def transitions(q: str):
    s = states(q)
    start = np.fromfile(CORE / q / "loan_row_start.bin", dtype=np.uint64)
    first = np.zeros(s.size, dtype=bool)
    first[start.astype(np.int64)] = True          # row i begins a new loan
    a, b = s[:-1], s[1:]
    keep = (~first[1:]) & (a >= 0) & (b >= 0) & (a != b)
    return a[keep], b[keep]


def betti(edges: set[tuple[int, int]], nodes: set[int]) -> tuple[int, int, int, int]:
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    comps = len({find(n) for n in nodes})
    V, E = len(nodes), len(edges)
    return V, E, comps, E - V + comps


def report(q: str) -> None:
    a, b = transitions(q)
    key = a.astype(np.int64) * 10000 + b.astype(np.int64)
    uk, cnt = np.unique(key, return_counts=True)
    ua, ub = (uk // 10000).astype(int), (uk % 10000).astype(int)
    print(f"\n--- {q}: {len(a):,} within-loan state changes, "
          f"{len(uk):,} distinct directed transitions")
    print("    floor   V     E(undirected)  components   b1 = E - V + C")
    for floor in (1, 2, 5, 10, 50, 100, 500, 1000, 5000, 10000):
        sel = cnt >= floor
        und = {(min(int(x), int(y)), max(int(x), int(y)))
               for x, y in zip(ua[sel], ub[sel])}
        nodes = {n for e in und for n in e}
        if not nodes:
            break
        V, E, C, b1 = betti(und, nodes)
        print(f"    {floor:>6}  {V:>4}      {E:>6}        {C:>4}        {b1:>6}")


# --------------------------------------------------------------------------
# The same count on the rulebook graph rather than the raw field.
#
# `docs/b8_fannie_slice.md` section 2.1 fixes three servicing states and claims
# a triangle, so `b1(G) = 3 - 3 + 1 = 1`. That graph is read off the servicer's
# rulebook rather than off the data, which is the whole reason it is a
# structure and not a choice. This function asks the narrower question the
# rulebook cannot answer on its own: are all three edges realised, and how
# often.

def rulebook(q: str) -> None:
    d = load(q, "delinq", np.uint8).astype(np.int32)
    m = load(q, "mod_flag", np.uint8)
    ok = (d != SENT) & (m != SENT)
    s = np.full(d.size, -1, dtype=np.int8)
    s[ok & (m == 89)] = 2                       # modified
    s[ok & (m != 89) & (d == 0)] = 0            # current
    s[ok & (m != 89) & (d > 0)] = 1             # delinquent
    start = np.fromfile(CORE / q / "loan_row_start.bin", dtype=np.uint64)
    first = np.zeros(s.size, dtype=bool)
    first[start.astype(np.int64)] = True
    a, b = s[:-1], s[1:]
    keep = (~first[1:]) & (a >= 0) & (b >= 0) & (a != b)
    a, b = a[keep], b[keep]
    name = {0: "current", 1: "delinquent", 2: "modified"}
    print(f"\n--- {q} rulebook graph: {len(a):,} state changes")
    seen = set()
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            n = int(np.count_nonzero((a == i) & (b == j)))
            print(f"    {name[i]:>10} -> {name[j]:<10} {n:>10,}"
                  + ("" if n else "   **never happens**"))
            if n:
                seen.add((min(i, j), max(i, j)))
    V, E, C, b1 = betti(seen, {0, 1, 2})
    print(f"    undirected V={V} E={E} C={C}   b1 = {b1}")
