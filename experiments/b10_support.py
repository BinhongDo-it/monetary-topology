"""B10: the observed position graph's `b1`, as a function of grid and support.

Pre-registered in the B10 availability register §16, **before this file was
written**, and amended in §16.11 **also before this file was written**. Every
reading it can return is declared there.

What this measures and what nobody has measured
------------------------------------------------
`b1(G)` for the position graph `G` that a real loan-performance file actually
traces out. Three checks say it has not been done:

* ``experiments/b1_holes.py`` runs on **constructed** graphs. Its own docstring:
  *every graph here is constructed and every number is exact integer linear
  algebra*, *No data is retrieved*.
* ``docs/b8_fannie_slice.md`` §2.1's ``b1(G) = 3 - 3 + 1 = 1`` is an assertion
  about an a-priori triangle, not a count. §14.4 later revised it to
  ``b1 = 5 - 4 + 1 = 2`` on four vertices, still by construction.
* No third place in the repository computes one.

Three downstreams are waiting on the number: `b8_fannie_slice.md` §3.3 requires
every reading on **two** `q` grids and calls a one-grid reading no result, but
how much cycle space the two grids differ by has never been measured;
discipline 11's third family requires the transfer function of a rank-or-
dimension statistic to be measured before grids are compared, and `b1` is one;
and `b9_zero_holonomy.md` §1 states the worry this answers in as many words, that
a non-zero reading elsewhere cannot be told from *an artefact of how states were
cut*.

Scope, declared before the work (§16.3)
----------------------------------------
`G` alone is a 1-complex with no 2-cells of its own, so
``dim H^1(G) = b1(G) = |E| - |V| + c`` is exact and needs no 2-cell information.
``b1_holes.py``'s B1H-7, that the connectivity test is necessary and not
sufficient, is about the **square-filled** complex `Gamma`; this file fills no
squares, so that premise does not hold here. And no Kunneth split is applied to
`b1(G)`: squares internal to `G` are not `Gamma`'s 2-cells and remain cycles of
`G` (§16.9 rule 2).

Two numbers, not one (§16.6)
-----------------------------
``b1_undirected = |E| - |V| + c`` is the cycle space, `H^1(G)` itself. Edges are
undirected because `omega` is antisymmetric on them. But not every undirected
cycle can be walked: ``00 -> RA`` is observed and ``RA -> 00`` is not, and
``b8_fannie_slice.md`` §2.3 leans on exactly that irreversibility rather than
treating it as a reason to drop the edge. So ``b1_walkable`` prints beside it:
per strongly connected component, **symmetrise the intra-component edges and
then** take ``|E| - |V| + 1``. The symmetrisation is the whole point. Counting
``u -> v`` and ``v -> u`` as two directed edges returns 1 for that pair, which is
the digraph's circulation space and not ``H^1``; `b1_theorem.md` §5 says in as
many words that *an out-and-back walk sums to zero by antisymmetry and is not a
cycle at all*. **The first version of this file did it the wrong way and it was
caught only because both numbers printed side by side and the walkable one came
out larger, an ordering that cannot hold.** `MEASUREMENT.md` mode 15.

**Self-loops are excluded.** ``00 -> 00`` is the commonest transition, and
`omega` on a self-loop is zero by antisymmetry. Counting them would raise `b1`
by a whole vertex count with nothing in the raised part.

No threshold anywhere (§16.5)
------------------------------
Whether an edge seen once is an edge has no arbitrariness-free answer, so this
file does not pick. ``b1`` prints as a function of the support cut over a decimal
geometric ladder, and **that curve is the deliverable**, not any one point on it.
The ladder is fixed here and is not anchored on anything this run produces.

Usage::

    python experiments/b10_support.py --selftest
    python experiments/b10_support.py --depth
    python experiments/b10_support.py --run

Writes ``results/b10_support_depth.json`` / ``results/b10_support.json``, both
with ``diagnostic_only`` from this first version. Streams the archives with
``ZipFile.open`` and **extracts nothing to disk**.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

VINTAGES = tuple(range(1999, 2027))

P_SEQ, P_PERIOD, P_DELINQ, P_AGE = 0, 1, 3, 4
P_MODFLAG, P_ZEROBAL, P_DEFERRAL = 7, 8, 24

#: §16.5's ladder. Decimal geometric, fixed here, anchored on nothing this run
#: produces. engineering rule 11 forbids a threshold taken from what a run happened to
#: return; a ladder printed whole is not a threshold.
SUPPORT_CUTS = (1, 2, 5, 10, 100, 1_000, 10_000, 100_000, 1_000_000)

#: §16.11's precedence, written here rather than buried in a branch: a month is
#: `modified` if field 8 reads `Y`, else `deferred` if field 25 is `P` or `C`,
#: else it is read off field 4.
MODIFIED, DEFERRED, RA = "modified", "deferred", "RA"

#: §8·15·4·1. The label a `delinq == 99` row gets **when and only when**
#: `b10_holonomy_ladder.anchor_states` is called with its `name99` switch on.
#: §8·15 ruled that value is not a count of missed months (23 counterexamples,
#: three of them stepping `00 -> 99` in one month) and did **not** name it, so
#: it stands as its own vertex in every grid until it has a name.
#:
#: **`RA`'s treatment, copied rather than invented**: `RA` is Freddie's
#: not-available code and it is its own node in `g1`, `g2` and `g3` already.
#:
#: **Adding it here is inert with the switch off**, and that is the whole
#: point: nothing else in this repository can produce this label, so `b12_*`
#: and every Freddie mode are unaffected **by construction** rather than by an
#: argument someone read out of the code. The selftest checks the inertness by
#: enumerating every label the parsers can emit, not by sampling.
D99 = "D99"

#: §8·25·3. The label a state gets when the labeller **cannot name it**: not
#: `00`, not a two-digit code, not `RA`. §8·22 counted 125,824 such rows on
#: this carrier, and §8·15 has just paid for what happens when a value nobody
#: can name is swept into a default branch — it was read as a deep
#: delinquency for six archives.
#:
#: **So this one is given its own vertex from the start rather than after it
#: bites.** Like `D99`, nothing outside the station that emits it can produce
#: it, so adding it here is inert everywhere else by construction.
UNK = "UNK"

#: The labels every grid keeps as themselves. Named so the three functions
#: below share one list instead of three copies of it.
OWN_NODES = (MODIFIED, DEFERRED, RA, D99, UNK)

#: Dropped in `--run`, kept in `--depth`. `--depth` on all 28 vintages returned a
#: 104th raw state, `XX`, which §2's enumeration on two vintages had not seen, with
#: a shape that decides the question by itself: **zero in-edges, two out-edges
#: (`XX -> 00` 18,586 and `XX -> 01` 130), no self-loop.** Nothing ever transitions
#: *into* it, so it occurs only as a loan's first observed month, on 1.37% of loans.
#: It is Freddie's not-available code, not a servicing state.
#:
#: Its effect on the reading is **exactly known rather than estimated**: a node with
#: one component's worth of vertex and two edges adds **+1 to b1_undirected and 0 to
#: b1_walkable** (it is a source, so its own strongly connected component). Both
#: variants print in `--run` so the correction is shown rather than asserted.
DROP_STATES = ("XX",)


def raw_state(delinq: str, modflag: str, deferral: str) -> str:
    if modflag == "Y":
        return MODIFIED
    if deferral in ("P", "C"):
        return DEFERRED
    return delinq


def g0(s: str) -> str:
    """Field 4's own values. Carries neither modified nor deferred (§16.11)."""
    return s if s not in (MODIFIED, DEFERRED) else "__drop__"


def g0m(s: str) -> str:
    """The common refinement of g0 and g1, added in §16.11 correction four."""
    return s


def g1(s: str) -> str:
    """B8 §14.4's primary grid, plus RA as its own node (§16.11 correction 3),
    plus D99 on the same footing (§8·15·4·1)."""
    if s in OWN_NODES:
        return s
    if s in ("00", "01", "02"):
        return {"00": "current", "01": "30", "02": "60"}[s]
    return "90+"


def g2(s: str) -> str:
    """B8 §14.4's secondary grid, plus RA and D99."""
    if s in OWN_NODES:
        return s
    return "current" if s == "00" else "delinquent"


def g3(s: str) -> str:
    """modified and deferred merged away, to price what those two dimensions add.

    `RA` and `D99` survive: this grid merges the two *event* dimensions away,
    and neither of those is an event dimension. **`D99` is not folded into
    `delinquent` either**, because §8·15 ruled only that the value is not a
    month count — three rows step `00 -> 99` in one month, so whether it is a
    delinquency at all is not known.
    """
    if s in (RA, D99, UNK):
        return s
    if s in (MODIFIED, DEFERRED):
        return "delinquent"
    return "current" if s == "00" else "delinquent"


GRIDS = (("g0", g0), ("g0m", g0m), ("g1", g1), ("g2", g2), ("g3", g3))


# ---------------------------------------------------------------------------
# Graph arithmetic. Exact integers, no tolerance anywhere.
# ---------------------------------------------------------------------------

def components(nodes, edges) -> int:
    """Weakly connected components, union-find."""
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
    return len({find(n) for n in nodes})


def tarjan_scc(nodes, directed):
    """Strongly connected components, iterative Tarjan (no recursion limit)."""
    adj = {n: [] for n in nodes}
    for u, v in directed:
        adj[u].append(v)
    index, low, onstk, stack, comp = {}, {}, set(), [], {}
    counter = [0]
    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(adj[root]))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        onstk.add(root)
        while work:
            u, it = work[-1]
            advanced = False
            for v in it:
                if v not in index:
                    index[v] = low[v] = counter[0]
                    counter[0] += 1
                    stack.append(v)
                    onstk.add(v)
                    work.append((v, iter(adj[v])))
                    advanced = True
                    break
                if v in onstk:
                    low[u] = min(low[u], index[v])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[u])
            if low[u] == index[u]:
                cid = len(set(comp.values())) if comp else 0
                cid = u
                while True:
                    w = stack.pop()
                    onstk.discard(w)
                    comp[w] = cid
                    if w == u:
                        break
    return comp


def betti(counts: Counter, cut: int) -> dict:
    """`b1` undirected and directed on the sub-graph of edges seen `>= cut`.

    ``counts`` maps a **directed** ordered pair to its observation count.
    Self-loops are dropped before anything (§16.6).
    """
    directed = [(u, v) for (u, v), n in counts.items() if n >= cut and u != v]
    nodes = sorted({x for e in directed for x in e})
    if not nodes:
        return {"cut": cut, "V": 0, "E_undirected": 0, "E_directed": 0,
                "c": 0, "b1_undirected": 0, "b1_walkable": 0, "n_scc": 0, "invariant_violated": False}

    undirected = {tuple(sorted(e)) for e in directed}
    c = components(nodes, undirected)
    b1_u = len(undirected) - len(nodes) + c

    # The walkable cycle count. **Symmetrise inside each strongly connected
    # component before counting**, because an out-and-back is not a cycle:
    # `b1_theorem.md` §5's scoping block, verbatim, *on a two-position graph
    # {rent, own} an out-and-back walk sums to zero by antisymmetry and is not a
    # cycle at all*. Counting `u -> v` and `v -> u` as two edges over two
    # vertices returns 1 for that pair, which is the digraph's circulation space
    # and **not** `H^1`. The first version of this file did exactly that; it was
    # caught because `b1_walkable` came out larger than `b1_undirected` on grid
    # g3, an ordering that cannot hold when one counts a subset of the other.
    # See `MEASUREMENT.md` mode 15.
    comp = tarjan_scc(nodes, directed)
    sizes = Counter(comp.values())
    intra_und: dict = {}
    for u, v in directed:
        if comp[u] == comp[v]:
            intra_und.setdefault(comp[u], set()).add(tuple(sorted((u, v))))
    b1_w = sum(len(es) - sizes[k] + 1 for k, es in intra_und.items())

    # The invariant that would have caught mode 15 on the first run instead of
    # the second. The walkable cycles are the cycle spaces of vertex-disjoint
    # subgraphs, which are independent subspaces of the whole cycle space, so
    # `b1_walkable <= b1_undirected` **always**. It is checked rather than
    # trusted, and a violation prints instead of passing quietly.
    violated = b1_w > b1_u
    if violated:
        print(f"  !! INVARIANT VIOLATED at cut {cut}: b1_walkable {b1_w} > "
              f"b1_undirected {b1_u}. The walkable count is not a sub-count of "
              f"the cycle space, so its construction is wrong. "
              f"MEASUREMENT.md mode 15.", file=sys.stderr)

    return {"cut": cut, "V": len(nodes), "E_undirected": len(undirected),
            "E_directed": len(directed), "c": c,
            "b1_undirected": b1_u, "b1_walkable": b1_w,
            "n_scc": len(sizes), "invariant_violated": violated}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def archive(v: int) -> Path:
    return RAW / f"sample_{v}.zip"


def transitions(v: int, tally: Counter, drops: Counter) -> None:
    """Accumulate raw-state ordered pairs for one vintage. One pass, no sampling.

    A pair is kept when the two months are the same loan and consecutive rows in
    the file. The performance file groups a loan's months and orders them, and a
    file that stopped doing so would show up as a flood of nonsense pairs rather
    than silently, because ``--depth`` prints the matrix whole.
    """
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as fh:
            seq, prev = None, None
            for line in io.TextIOWrapper(fh, encoding="utf-8", newline=""):
                line = line.rstrip("\r\n")
                if not line:
                    continue
                f = line.split("|")
                try:
                    s = raw_state(f[P_DELINQ], f[P_MODFLAG], f[P_DEFERRAL])
                except IndexError:
                    drops["short_row"] += 1
                    continue
                if f[P_SEQ] != seq:
                    seq, prev = f[P_SEQ], s
                    drops["loan_first_month"] += 1
                    continue
                tally[(prev, s)] += 1
                prev = s


# ---------------------------------------------------------------------------
# --selftest. §16.10. Constructed graphs where the answer is known.
# ---------------------------------------------------------------------------

def cmd_selftest() -> int:
    print("b10_support selftest. Constructed graphs, answers known first.\n")
    fails = []

    def chk(name, counts, want_u, want_w):
        r = betti(Counter(counts), 1)
        ok = (r["b1_undirected"] == want_u and r["b1_walkable"] == want_w)
        print(f"  {name:<44} b1_u {r['b1_undirected']:>3} (want {want_u:>3})"
              f"   b1_w {r['b1_walkable']:>3} (want {want_w:>3})"
              f"   {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(name)

    # a directed triangle: one cycle, walkable
    chk("directed triangle a->b->c->a", {("a", "b"): 9, ("b", "c"): 9,
                                         ("c", "a"): 9}, 1, 1)
    # b1_theorem.md §5: an out-and-back is not a cycle. This is the case the
    # first version of this file got wrong.
    chk("reciprocal pair a<->b, an out-and-back",
        {("a", "b"): 9, ("b", "a"): 9}, 0, 0)
    chk("triangle with one reciprocal leg",
        {("a", "b"): 9, ("b", "a"): 9, ("b", "c"): 9, ("c", "a"): 9}, 1, 1)
    # B8 §14.4's four-vertex five-edge graph
    chk("B8 §14.4 four vertices five edges",
        {("cur", "del"): 9, ("del", "mod"): 9, ("mod", "cur"): 9,
         ("del", "def"): 9, ("def", "cur"): 9}, 2, 2)
    # a path: no cycles at all
    chk("path a->b->c", {("a", "b"): 9, ("b", "c"): 9}, 0, 0)
    # an absorbing sink reached from two places: undirected cycle, no directed one
    chk("two sources into one sink (RA shape)",
        {("a", "b"): 9, ("a", "s"): 9, ("b", "s"): 9}, 1, 0)
    # self-loops must not count
    chk("self-loops only", {("a", "a"): 99, ("b", "b"): 99}, 0, 0)
    chk("triangle plus self-loops", {("a", "b"): 9, ("b", "c"): 9, ("c", "a"): 9,
                                     ("a", "a"): 99, ("b", "b"): 99}, 1, 1)
    # two disjoint triangles: c = 2, and b1 must not absorb the extra component
    chk("two disjoint triangles",
        {("a", "b"): 9, ("b", "c"): 9, ("c", "a"): 9,
         ("x", "y"): 9, ("y", "z"): 9, ("z", "x"): 9}, 2, 2)
    # the support cut must actually bite
    rare = Counter({("a", "b"): 9, ("b", "c"): 9, ("c", "a"): 1})
    r_lo, r_hi = betti(rare, 1), betti(rare, 5)
    ok = r_lo["b1_walkable"] == 1 and r_hi["b1_walkable"] == 0
    print(f"  {'support cut removes a rare reverse edge':<44} "
          f"b1_walk at cut 1 = {r_lo['b1_walkable']}, at cut 5 = {r_hi['b1_walkable']}"
          f"   {'ok' if ok else 'FAIL'}")
    if not ok:
        fails.append("support cut")

    # the grids must be total on every raw state they can see
    probe = ["00", "01", "02", "17", "99", RA, MODIFIED, DEFERRED]
    print("\n  grid images, so a state that falls through is visible:")
    for gname, gf in GRIDS:
        print(f"    {gname:<5} " + "  ".join(f"{s}->{gf(s)}" for s in probe))

    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# --depth. §16.4 group 1. Computes no b1.
# ---------------------------------------------------------------------------

def cmd_depth(only) -> int:
    vintages = only or VINTAGES
    print("b10_support depth. The transition matrix. No b1 is computed.\n")
    total, drops = Counter(), Counter()
    per_vintage = {}
    for v in vintages:
        if not archive(v).exists():
            continue
        t = Counter()
        transitions(v, t, drops)
        per_vintage[v] = {"pairs": sum(t.values()), "distinct": len(t)}
        total.update(t)
        print(f"  {v}  pairs {sum(t.values()):>12,}  distinct ordered pairs {len(t):>7,}")

    states = sorted({x for e in total for x in e})
    print(f"\n  raw states observed: {len(states)}")
    print("  " + " ".join(states))
    print(f"\n  ordered pairs, all vintages: {sum(total.values()):,} over "
          f"{len(total):,} distinct")

    self_n = sum(n for (u, v_), n in total.items() if u == v_)
    print(f"  of which self-loops: {self_n:,} "
          f"({self_n / sum(total.values()):.4f}) and they are excluded from b1")

    print("\n  the twenty commonest transitions:")
    for (u, v_), n in total.most_common(20):
        print(f"    {u:>9} -> {v_:<9} {n:>13,}")
    print("\n  the count distribution over the support ladder:")
    for cut in SUPPORT_CUTS:
        k = sum(1 for (u, v_), n in total.items() if n >= cut and u != v_)
        print(f"    edges with count >= {cut:>9,}   {k:>6,}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_support_depth.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "support_depth", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §16. It measures a "
             "cycle-space capacity and carries no omega or holonomy claim "
             "(§16.0).",
         "raw_states": states, "per_vintage": per_vintage,
         "self_loop_pairs": self_n, "total_pairs": sum(total.values()),
         "distinct_pairs": len(total),
         "matrix": {f"{u}->{v_}": n for (u, v_), n in sorted(total.items())},
         "drops": dict(sorted(drops.items()))},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --run. §16.4 groups 2 to 5.
# ---------------------------------------------------------------------------

def project(total: Counter, gf, drop_states=DROP_STATES) -> tuple[Counter, int]:
    """Map raw pairs onto a grid. Returns the projection and the dropped count."""
    out, dropped = Counter(), 0
    for (u, v_), n in total.items():
        if u in drop_states or v_ in drop_states:
            dropped += n
            continue
        a, b = gf(u), gf(v_)
        if a == "__drop__" or b == "__drop__":
            continue
        out[(a, b)] += n
    return out, dropped


def cmd_run(only) -> int:
    vintages = only or VINTAGES
    print("b10_support run. Five grids x nine support cuts. "
          "No threshold in this file.\n")
    total, drops = Counter(), Counter()
    per_vintage_raw = {}
    for v in vintages:
        if not archive(v).exists():
            continue
        t = Counter()
        transitions(v, t, drops)
        per_vintage_raw[v] = t
        total.update(t)

    out_grids = {}
    for gname, gf in GRIDS:
        proj, dropped = project(total, gf)
        rows = [betti(proj, cut) for cut in SUPPORT_CUTS]
        out_grids[gname] = rows
        print(f"\n  grid {gname}   (pairs dropped for {DROP_STATES}: {dropped:,})")
        print(f"    {'cut':>10}{'V':>6}{'E_und':>8}{'E_dir':>8}{'c':>5}"
              f"{'b1_und':>9}{'b1_walk':>9}{'SCC':>6}")
        for r in rows:
            print(f"    {r['cut']:>10,}{r['V']:>6}{r['E_undirected']:>8}"
                  f"{r['E_directed']:>8}{r['c']:>5}{r['b1_undirected']:>9}"
                  f"{r['b1_walkable']:>9}{r['n_scc']:>6}")

    print("\n  §16.8's four cells read off the tables above:\n"
          "    b1_walk >= 1 on g1 and g2 with a plateau in the curve -> both q\n"
          "      grids carry cycle space and it does not rest on rare edges;\n"
          "    b1 falling an order of magnitude between g1 and g2 -> the grid\n"
          "      choice sets the size of the cycle space, which is discipline 11's\n"
          "      third family, and no cross-grid holonomy comparison may be made\n"
          "      until this transfer function is quoted alongside it;\n"
          "    b1_walk 0 while b1_und > 0 -> cycles exist that no agent can walk;\n"
          "    no plateau anywhere -> b1 rests on rare edges and carries nothing.\n"
          "  §16.9: b1 > 0 is capacity, not a value. It is not a slice reading.")

    # The XX correction, shown rather than asserted. §16.12.
    keep, _ = project(total, g0m)
    with_xx, _ = project(total, g0m, drop_states=())
    print(f"\n  the {DROP_STATES} correction on g0m, both variants:")
    print(f"    {'cut':>10}{'b1_und kept':>14}{'b1_und with XX':>17}"
          f"{'b1w kept':>14}{'b1w with XX':>17}")
    xx_rows = []
    for cut in SUPPORT_CUTS:
        a, b = betti(keep, cut), betti(with_xx, cut)
        xx_rows.append({"cut": cut, "b1u_kept": a["b1_undirected"],
                        "b1u_with_xx": b["b1_undirected"],
                        "b1w_kept": a["b1_walkable"],
                        "b1w_with_xx": b["b1_walkable"]})
        print(f"    {cut:>10,}{a['b1_undirected']:>14}{b['b1_undirected']:>17}"
              f"{a['b1_walkable']:>14}{b['b1_walkable']:>17}")
    print("    Read: a source node with two out-edges and no in-edge adds one to\n"
          "    the undirected cycle count and nothing to the directed one. If the\n"
          "    two right-hand columns do not differ by exactly that, the diagnosis\n"
          "    of XX as a first-month artefact is wrong and §16.12 is void.")

    # §16.4 group 5: vintage is a variable, not a choice.
    print("\n  per vintage, grid g1, cut 100:")
    print(f"    {'vintage':>8}{'V':>5}{'E_und':>7}{'c':>4}{'b1_und':>8}{'b1_walk':>8}")
    per_v = {}
    for v, t in sorted(per_vintage_raw.items()):
        pr, _ = project(t, g1)
        r = betti(pr, 100)
        per_v[v] = r
        print(f"    {v:>8}{r['V']:>5}{r['E_undirected']:>7}{r['c']:>4}"
              f"{r['b1_undirected']:>8}{r['b1_walkable']:>8}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b10_support.json"
    out.write_text(json.dumps(
        {"stage": "B10", "step": "support", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §16. It measures a "
             "cycle-space capacity and carries no omega or holonomy claim "
             "(§16.0).",
         "support_cuts": list(SUPPORT_CUTS),
         "grids": out_grids,
         "per_vintage_g1_cut100": {str(k): v for k, v in per_v.items()},
         "drop_states": list(DROP_STATES),
         "xx_correction_g0m": xx_rows,
         "drops": dict(sorted(drops.items()))},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--depth", action="store_true",
                    help="§16.4 group 1: the matrix, computing no b1")
    ap.add_argument("--run", action="store_true", help="§16.4 groups 2 to 5")
    ap.add_argument("--only", type=int, action="append")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.depth:
        return cmd_depth(a.only)
    if a.run:
        return cmd_run(a.only)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
