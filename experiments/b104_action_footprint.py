"""B104: how far an action's rewrite of relative prices reaches.

B103 reads the pair an action joins. This station reads every other pair. An action that
joins i and j inside a component moves the nearest potential by kappa * u, where
u = L^+ (e_j - e_i) is the potential of a unit current into j and out of i and
kappa = w_e D / (1 + w_e R) (B103, Theorem 41 (2), checked there on every vertex). Where u
is flat and where it is not is a statement about the blocks of the graph, its maximal
pieces that no single vertex can disconnect.

  B104-1  no relative level moves by more than the joined pair's, and the pairs that move
          by exactly that much are the pairs with one end hanging off i and the other
          hanging off j.
  B104-2  the blocks on the block-cut path between i and j are, together, the block the
          action creates, and every vertex outside it moves with the one vertex of it that it
          hangs from, so no relative level inside a part hanging off that block moves at all.
  B104-3  along that path the joined pair's move is shared among the blocks in proportion
          to each block's own resistance between its two gateways, the vertices it shares
          with its neighbours on the path, and every vertex of a block lies between its two
          gateways, so every pair split by a gateway moves the way the joined pair does.

The moves are read from the two fits, before and after the action. Which pairs attain the
bound, and how the move is shared along the path, are read on u, which does not scale with D.

Paper station: zero data. The projection and the graph helpers are imported from B103.

Run:
    python experiments/b104_action_footprint.py
    python experiments/b104_action_footprint.py --selftest
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys
import time
from collections import deque

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import b103_time_reachability as B103                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b104_action_footprint.json"

SEED = 104
#: Every connected labelled graph on 2 to 6 vertices, every missing edge added once.
MAX_ENUM_N = 6
#: Sparse random connected graphs: a spanning tree plus each other pair with probability
#: EXTRA_SCALE / n, which leaves many cut vertices and long block-cut paths.
SIZES = (16, 32, 64)
GRAPHS_PER_SIZE = 200
ACTIONS_PER_GRAPH = 5
EXTRA_SCALE = 1.5
#: Identities and the bound are compared at this tolerance. What the run reaches is
#: printed; only the tolerance goes into the record, because the last digits belong to
#: the BLAS build.
TOL = 1e-9


def sig(x, digits=6):
    """A float through an explicit format spec, so the record does not carry BLAS digits."""
    return float(f"{x:.{digits}g}")


# ------------------------------------------------- blocks and the path between i and j

def blocks(n, und):
    """Vertex sets of the biconnected components (blocks), by Tarjan's algorithm.

    A bridge is a block of two vertices. `und` holds each edge once, as an unordered pair.
    """
    adj = [[] for _ in range(n)]
    for k, (a, b) in enumerate(und):
        adj[a].append((b, k))
        adj[b].append((a, k))
    disc = [-1] * n
    low = [0] * n
    clock = [0]
    stack, out = [], []

    def visit(v, parent_edge):
        disc[v] = low[v] = clock[0]
        clock[0] += 1
        for (x, k) in adj[v]:
            if k == parent_edge:
                continue
            if disc[x] == -1:
                stack.append(k)
                visit(x, k)
                low[v] = min(low[v], low[x])
                if low[x] >= disc[v]:
                    part = set()
                    while True:
                        e = stack.pop()
                        part.update(und[e])
                        if e == k:
                            break
                    out.append(frozenset(part))
            elif disc[x] < disc[v]:
                stack.append(k)
                low[v] = min(low[v], disc[x])

    for v in range(n):
        if disc[v] == -1:
            visit(v, -1)
    return out


def block_path(n, und, i, j):
    """The blocks on the block-cut tree path from i to j, in order, and their gateways.

    `gates[0]` is i, `gates[-1]` is j, and `gates[k]` is the cut vertex that `blocks[k - 1]`
    and `blocks[k]` share.
    """
    bl = blocks(n, und)
    adj = {}
    for k, part in enumerate(bl):
        for x in part:
            adj.setdefault(("v", x), []).append(("b", k))
            adj.setdefault(("b", k), []).append(("v", x))
    start, goal = ("v", i), ("v", j)
    prev = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            break
        for nxt in adj.get(node, []):
            if nxt not in prev:
                prev[nxt] = node
                queue.append(nxt)
    nodes, node = [], goal
    while node is not None:
        nodes.append(node)
        node = prev[node]
    nodes.reverse()
    return ([bl[x[1]] for x in nodes if x[0] == "b"],
            [x[1] for x in nodes if x[0] == "v"])


def block_resistance(part, und, w, a, c, unweighted=False):
    """Effective resistance between a and c in the block `part`, on its own edges alone.

    Two blocks share at most one vertex, so an edge with both ends in `part` is an edge of
    this block. `unweighted=True` is the self-test's seeded error: every edge conducts one.
    """
    loc = {v: k for k, v in enumerate(sorted(part))}
    edges, ws = [], []
    for k, (x, y) in enumerate(und):
        if x in part and y in part:
            edges.append((loc[x], loc[y]))
            ws.append(1.0 if unweighted else float(w[k]))
    _, _, _, Lp = B103.fit(len(loc), edges, np.array(ws), np.zeros(len(edges)))
    b = B103.unit(len(loc), loc[a], loc[c])
    return float(b @ Lp @ b)


def attachments(n, und, union, i, mutate=None):
    """Each vertex's attachment: itself on the path, else the one path vertex its part meets.

    Returns the attachment of every vertex and the number of off-path parts that meet the
    path in other than exactly one vertex, which a block-cut tree makes zero.
    `mutate="to_i"` is the self-test's seeded error: every off-path vertex attached to i.
    """
    adj = [[] for _ in range(n)]
    for a, b in und:
        adj[a].append(b)
        adj[b].append(a)
    att = {v: v for v in union}
    not_unique = 0
    seen = set(union)
    for v in range(n):
        if v in seen:
            continue
        part, meets, queue = {v}, set(), deque([v])
        seen.add(v)
        while queue:
            x = queue.popleft()
            for y in adj[x]:
                if y in union:
                    meets.add(y)
                elif y not in part:
                    part.add(y)
                    seen.add(y)
                    queue.append(y)
        if len(meets) != 1:
            not_unique += 1
        anchor = i if mutate == "to_i" else min(meets)
        for x in part:
            att[x] = anchor
    return att, not_unique


# ------------------------------------------------- one action

def read_action(n, und, w, om, i, j, we, oe, mutate_eq=None, mutate_att=None,
                mutate_fit=None, mutate_bound=None, mutate_share=None, mutate_between=None,
                mutate_fused=None):
    """Everything B104 reads about one action joining i and j inside a component.

    Seeded errors for the self-test: `mutate_fit="same"` leaves the new edge out of the fit
    after the action, so nothing moves and both bounds hold for no reason;
    `mutate_bound="half"` reads the joined pair's move at half its size, so the bound fails;
    `mutate_share="unweighted"`, `"last_unweighted"` and `"next"` compare each block's drop
    with its resistance at unit weights, the last block's alone at unit weights, and the
    next block's resistance; `mutate_between="first_gates"`
    holds every block between the first block's gateways, and `"lift_inside"` reads every
    vertex strictly inside a block one R above where it is; `mutate_fused="without_edge"`
    looks for the block the action creates in the graph before the action.
    """
    phi0, _, _, Lp0 = B103.fit(n, und, w, om)
    if mutate_fit == "same":
        phi1 = phi0.copy()
    else:
        phi1, _, _, _ = B103.fit(n, und + [(i, j)], np.append(w, we), np.append(om, oe))
    mv = phi1 - phi0
    joined = abs(mv[j] - mv[i])
    b = B103.unit(n, i, j)
    u = Lp0 @ b
    R = float(b @ u)
    bpath, gates = block_path(n, und, i, j)
    union = set().union(*bpath)
    att, not_unique = attachments(n, und, union, i, mutate_att)
    true_att, _ = attachments(n, und, union, i)
    off = [v for v in range(n) if v not in union]

    # B104-1: the bound on the moves, and which pairs attain it, read on u
    excess = float(mv.max() - mv.min() - joined * (0.5 if mutate_bound == "half" else 1.0))
    scale = TOL * max(1.0, R)
    mismatch, gap = 0, np.inf
    for p, q in itertools.combinations(range(n), 2):
        attained = R - abs(u[q] - u[p]) <= scale
        if mutate_eq == "ends_only":
            predicted = {p, q} == {i, j}
        else:
            predicted = {att[p], att[q]} == {i, j}
        mismatch += int(attained != predicted)
        if not predicted:
            gap = min(gap, (R - abs(u[q] - u[p])) / R)

    # B104-2: the path blocks are the block the action creates, and parts off it move with
    # their attachment
    grown = blocks(n, und if mutate_fused == "without_edge" else und + [(i, j)])
    fused = next((x for x in grown if i in x and j in x), None)
    if fused is None:
        fused = next(x for x in grown if i in x)
    fused_mismatch = int(set(fused) != union)
    insulation = max((abs(mv[v] - mv[att[v]]) for v in off), default=0.0)
    path_u = np.sort(u[sorted(union)])
    converse = float(np.min(np.diff(path_u)) / R) if len(path_u) > 1 else np.inf
    classes = {}
    for v in range(n):
        classes[true_att[v]] = classes.get(true_att[v], 0) + 1
    still = sum(c * (c - 1) // 2 for c in classes.values())
    # the converse read from the fits: pairs hanging from different path vertices that the
    # fits read below TOL, and the largest move their potential gaps predict (kappa * du)
    moving, apart_still, apart_still_pred = 0, 0, 0.0
    for p, q in itertools.combinations(range(n), 2):
        read = abs(mv[q] - mv[p])
        moving += int(read > TOL)
        if true_att[p] != true_att[q] and read <= TOL:
            apart_still += 1
            apart_still_pred = max(apart_still_pred, joined * abs(u[q] - u[p]) / R)

    # B104-3: the move shared along the path by each block's own resistance, read on u
    own = [block_resistance(part, und, w, gates[k], gates[k + 1],
                            unweighted=(mutate_share == "unweighted"
                                        or (mutate_share == "last_unweighted"
                                            and 2 <= len(bpath) == k + 1)))
           for k, part in enumerate(bpath)]
    if mutate_share == "next":
        own = own[1:] + own[:1]
    drop = max(abs((u[gates[k + 1]] - u[gates[k]]) - own[k]) / R for k in range(len(bpath)))
    between, margin = 0.0, np.inf
    for k, part in enumerate(bpath):
        lo, hi = (gates[0], gates[1]) if mutate_between == "first_gates" else (gates[k],
                                                                              gates[k + 1])
        for v in part:
            uv = u[v] + (R if mutate_between == "lift_inside"
                         and v not in (gates[k], gates[k + 1]) else 0.0)
            between = max(between, (u[lo] - uv) / R, (uv - u[hi]) / R)
            if v not in (gates[k], gates[k + 1]):
                margin = min(margin, (u[v] - u[gates[k]]) / R, (u[gates[k + 1]] - u[v]) / R)
    return {"n": n, "R": R, "joined": joined, "excess": excess, "mismatch": mismatch, "gap": gap,
            "insulation": float(insulation), "not_unique": not_unique, "converse": converse,
            "fused_mismatch": fused_mismatch,
            "off": len(off), "union": len(union), "pairs": n * (n - 1) // 2, "still": still,
            "moved_float": moving, "apart_still": apart_still,
            "apart_still_pred": apart_still_pred,
            "chain_drop": float(drop),
            "chain_between": float(between), "chain_margin": float(margin),
            "blocks_on_path": len(bpath), "bridges_on_path": sum(1 for x in bpath if len(x) == 2),
            "chain_exercised": len(bpath) >= 2 and any(len(x) >= 3 for x in bpath),
            "hanging_at_ends": sum(1 for v in off if true_att[v] in (i, j)) > 0,
            "off_not_i": any(true_att[v] != i and abs(u[true_att[v]] - u[i]) > scale
                             for v in off)}


def enumerate_actions(rng, max_n, **mutate):
    rows = []
    for n in range(2, max_n + 1):
        pairs = list(itertools.combinations(range(n), 2))
        for code in range(1 << len(pairs)):
            und = [pairs[k] for k in range(len(pairs)) if code >> k & 1]
            if B103.components(n, und) != 1:
                continue
            w = np.exp(rng.normal(0.0, 1.0, len(und)))
            om = rng.normal(0.0, 1.0, len(und))
            present = set(und)
            for (a, b) in pairs:
                if (a, b) in present:
                    continue
                i, j = (a, b) if rng.random() < 0.5 else (b, a)
                we = float(np.exp(rng.normal(0.0, 1.0)))
                oe = float(rng.normal(0.0, 1.0))
                rows.append(read_action(n, und, w, om, i, j, we, oe, **mutate))
    return rows


def random_actions(rng, sizes, per_size, actions, **mutate):
    rows = []
    for n in sizes:
        for _ in range(per_size):
            while True:
                _, und = B103.random_connected(rng, n, EXTRA_SCALE / n)
                present = set(und)
                missing = [p for p in itertools.combinations(range(n), 2) if p not in present]
                if len(missing) >= actions:
                    break
            w = np.exp(rng.normal(0.0, 1.0, len(und)))
            om = rng.normal(0.0, 1.0, len(und))
            for k in rng.choice(len(missing), actions, replace=False):
                a, b = missing[int(k)]
                i, j = (a, b) if rng.random() < 0.5 else (b, a)
                we = float(np.exp(rng.normal(0.0, 1.0)))
                oe = float(rng.normal(0.0, 1.0))
                rows.append(read_action(n, und, w, om, i, j, we, oe, **mutate))
    return rows


def judge_bound(rows):
    worst = max(r["excess"] for r in rows)
    mismatch = sum(r["mismatch"] for r in rows)
    exercised = any(r["hanging_at_ends"] for r in rows) and any(r["joined"] > TOL for r in rows)
    return bool(rows) and worst <= TOL and mismatch == 0 and exercised, worst, mismatch


def judge_insulation(rows):
    worst = max(r["insulation"] for r in rows)
    not_unique = sum(r["not_unique"] for r in rows)
    fused = sum(r["fused_mismatch"] for r in rows)
    exercised = sum(r["off"] for r in rows) > 0 and any(r["joined"] > TOL for r in rows)
    ok = bool(rows) and worst <= TOL and not_unique == 0 and fused == 0 and exercised
    return ok, worst, not_unique, fused


def judge_chain(rows):
    drop = max(r["chain_drop"] for r in rows)
    between = max(r["chain_between"] for r in rows)
    exercised = any(r["chain_exercised"] for r in rows)
    return bool(rows) and max(drop, between) <= TOL and exercised, drop, between


def summary(rows):
    pairs = sum(r["pairs"] for r in rows)
    still = sum(r["still"] for r in rows)
    return {"actions": len(rows), "pairs": pairs, "vertices": sum(r["n"] for r in rows),
            "actions_leaving_vertices_outside_the_block_they_create":
                sum(int(r["off"] > 0) for r in rows),
            "pairs_hanging_together": still,
            "share_of_pairs_hanging_together": sig(still / pairs, 4),
            "off_path_vertices": sum(r["off"] for r in rows),
            "actions_with_parts_hanging_off_an_end": sum(int(r["hanging_at_ends"]) for r in rows),
            "smallest_relative_gap_below_the_bound": sig(min(r["gap"] for r in rows), 3),
            "smallest_relative_potential_gap_between_path_vertices":
                sig(min(r["converse"] for r in rows), 3),
            "pairs_read_moving_above_the_tolerance": sum(r["moved_float"] for r in rows),
            "pairs_hanging_apart_read_below_it": sum(r["apart_still"] for r in rows),
            "largest_move_predicted_for_those":
                sig(max(r["apart_still_pred"] for r in rows), 3)
                if any(r["apart_still"] for r in rows) else None,
            "actions_whose_path_crosses_two_blocks_or_more":
                sum(int(r["blocks_on_path"] >= 2) for r in rows),
            "most_blocks_on_one_path": max(r["blocks_on_path"] for r in rows),
            "blocks_on_paths": sum(r["blocks_on_path"] for r in rows),
            "single_edge_blocks_on_paths": sum(r["bridges_on_path"] for r in rows),
            "smallest_relative_margin_inside_a_block":
                sig(min(r["chain_margin"] for r in rows), 3)
                if min(r["chain_margin"] for r in rows) < np.inf else None}


# ------------------------------------------------- self-test

def selftest() -> int:
    """Every criterion passes on a clean fixture and fails on a planted error (rule 11f)."""
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    # the block-cut machinery on a graph small enough to read: a path 0-1-2 with 3 hanging
    # off 1 and 4 hanging off 3, joined across 0 and 2
    und = [(0, 1), (1, 2), (1, 3), (3, 4)]
    union = set().union(*block_path(5, und, 0, 2)[0])
    att, not_unique = attachments(5, und, union, 0)
    expect(union == {0, 1, 2} and att[3] == 1 and att[4] == 1 and not_unique == 0,
           "block-cut path or attachments wrong on the hand fixture")
    expect(len(blocks(5, und)) == 4, "blocks wrong on the hand fixture")
    bp, gt = block_path(5, und, 0, 2)
    expect([sorted(x) for x in bp] == [[0, 1], [1, 2]] and gt == [0, 1, 2],
           "block path or its gateways wrong on the hand fixture")
    expect(attachments(5, und, {0, 2}, 0)[1] == 1,
           "a part meeting a wrong path in two vertices is not counted")
    bowtie = [(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (2, 4)]
    expect(sorted(len(b) for b in blocks(5, bowtie)) == [3, 3],
           "blocks do not split a bowtie at its cut vertex")

    # a pair one millionth of R below the bound: a path 0-1-2 whose first edge is a million
    # times stronger, joined across 0 and 2; the pair (1, 2) must not count as attaining
    near = read_action(3, [(0, 1), (1, 2)], np.array([1e6, 1.0]), np.zeros(2), 0, 2, 1.0, 1.0)
    expect(near["gap"] < 1e-5, "seed not planted: no pair sits just below the bound")
    expect(near["mismatch"] == 0, "the attaining set is misread where a pair sits one millionth below the bound")

    clean = enumerate_actions(np.random.default_rng(11), 4)
    expect(judge_bound(clean)[0], "B104-1 fails on a clean fixture")
    expect(judge_insulation(clean)[0], "B104-2 fails on a clean fixture")
    expect(any(r["hanging_at_ends"] for r in clean),
           "seed not planted: no action has a part hanging off an end")
    expect(not judge_bound(enumerate_actions(np.random.default_rng(11), 4,
                                             mutate_eq="ends_only"))[0],
           "B104-1 passes with the attaining pairs taken as the joined pair alone")
    expect(any(r["off_not_i"] for r in clean),
           "seed not planted: every off-path vertex already sits at i's potential")
    expect(not judge_insulation(enumerate_actions(np.random.default_rng(11), 4,
                                                  mutate_att="to_i"))[0],
           "B104-2 passes with every off-path vertex attached to i")
    expect(not judge_insulation(clean + [dict(clean[0], not_unique=1)])[0],
           "B104-2 passes with a part off the path meeting it in two vertices")
    expect(any(r["joined"] > TOL for r in clean),
           "seed not planted: no action moves the pair it joins")
    expect(not judge_bound(enumerate_actions(np.random.default_rng(11), 4,
                                             mutate_bound="half"))[0],
           "B104-1 passes with the joined pair's move read at half its size")
    still = enumerate_actions(np.random.default_rng(11), 4, mutate_fit="same")
    expect(not judge_bound(still)[0], "B104-1 passes when the action is left out of the fit")
    expect(not judge_insulation(still)[0], "B104-2 passes when the action is left out of the fit")
    expect(not judge_insulation(enumerate_actions(np.random.default_rng(11), 4,
                                                  mutate_fused="without_edge"))[0],
           "B104-2 passes with the block the action creates looked for before the action")

    expect(judge_chain(clean)[0], "B104-3 fails on a clean fixture")
    expect(any(r["chain_exercised"] for r in clean),
           "seed not planted: no path crosses two blocks one of which holds a cycle")
    expect(any(r["chain_margin"] < np.inf for r in clean),
           "seed not planted: no block on a path has a vertex other than its gateways")
    for kw, what in ((dict(mutate_share="unweighted"), "every edge of a block conducting one"),
                     (dict(mutate_share="last_unweighted"), "the last block alone on a path "
                                                            "read at unit weights"),
                     (dict(mutate_share="next"), "each block's drop read against the next "
                                                 "block's resistance"),
                     (dict(mutate_between="first_gates"), "every block held between the first "
                                                          "block's gateways"),
                     (dict(mutate_between="lift_inside"), "the vertices inside a block read "
                                                          "one R above where they are")):
        expect(not judge_chain(enumerate_actions(np.random.default_rng(11), 4, **kw))[0],
               f"B104-3 passes with {what}")

    for f in fails:
        print(f"SELFTEST FAIL  {f}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


# ------------------------------------------------- the run

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    t0 = time.perf_counter()
    enum = enumerate_actions(np.random.default_rng(a.seed + 0), MAX_ENUM_N)
    rand = random_actions(np.random.default_rng(a.seed + 1), SIZES, GRAPHS_PER_SIZE,
                          ACTIONS_PER_GRAPH)
    criteria, report = [], {}

    ok1e, worst1e, mis1e = judge_bound(enum)
    ok1r, worst1r, mis1r = judge_bound(rand)
    ok2e, worst2e, nu2e, fu2e = judge_insulation(enum)
    ok2r, worst2r, nu2r, fu2r = judge_insulation(rand)
    ok3e, drop3e, bet3e = judge_chain(enum)
    ok3r, drop3r, bet3r = judge_chain(rand)
    se, sr = summary(enum), summary(rand)
    print(f"enumeration: {se['actions']} actions, {se['pairs']} pairs; random: "
          f"{sr['actions']} actions, {sr['pairs']} pairs")
    print(f"B104-1  worst excess over the joined pair's move: enumeration {worst1e:.2e}, "
          f"random {worst1r:.2e}; attaining pairs mismatched {mis1e} and {mis1r}")
    print(f"B104-2  worst move relative to the attachment: enumeration {worst2e:.2e}, "
          f"random {worst2r:.2e}; attachments not unique {nu2e} and {nu2r}; block the action "
          f"creates differing from the path blocks {fu2e} and {fu2r}")
    print(f"B104-3  worst drop across a block against its own resistance, share of R: "
          f"enumeration {drop3e:.2e}, random {drop3r:.2e}; worst reach outside a block's "
          f"gateways {bet3e:.2e} and {bet3r:.2e}")
    print(f"pairs the fits read moving by more than {TOL:.0e}: enumeration "
          f"{se['pairs_read_moving_above_the_tolerance']} of {se['pairs']}, the attachment "
          f"classes let {se['pairs'] - se['pairs_hanging_together']} move; random "
          f"{sr['pairs_read_moving_above_the_tolerance']} of {sr['pairs']}, classes let "
          f"{sr['pairs'] - sr['pairs_hanging_together']} move")
    print(f"pairs hanging apart that the fits read below {TOL:.0e}: enumeration "
          f"{se['pairs_hanging_apart_read_below_it']}, random "
          f"{sr['pairs_hanging_apart_read_below_it']}; largest move their potential gaps "
          f"predict: enumeration {se['largest_move_predicted_for_those']}, random "
          f"{sr['largest_move_predicted_for_those']}")
    preds = [x["largest_move_predicted_for_those"] for x in (se, sr)
             if x["largest_move_predicted_for_those"] is not None]
    if preds:
        tail = (f". Read from the fits, {se['pairs_hanging_apart_read_below_it']} and "
                f"{sr['pairs_hanging_apart_read_below_it']} pairs hang from different vertices "
                f"of that block yet move by less than {TOL:.0e}; the move their potential gaps "
                f"predict is at most {max(preds):.3g}")
    else:
        tail = (f". Read from the fits, every pair hanging from different vertices of that block moves "
                f"by more than {TOL:.0e}")

    criteria.append({
        "name": "B104-1", "kind": "own_reading", "passed": bool(ok1e and ok1r),
        "statement": "no relative level moves by more than the joined pair's, and the pairs "
                     "that move by exactly that much are those with one end hanging off i and "
                     "the other hanging off j",
        "detail": (f"every connected labelled graph on 2 to {MAX_ENUM_N} vertices with every "
                   f"missing edge added once ({se['actions']} actions, {se['pairs']} pairs), and "
                   f"{sr['actions']} actions on sparse random connected graphs of "
                   f"{', '.join(map(str, SIZES))} vertices ({sr['pairs']} pairs). The largest "
                   f"move of any pair, read from the fits before and after, exceeds the joined "
                   f"pair's by no more than {TOL:.0e} on every action. The pairs whose potential "
                   f"difference under a unit current from j to i equals R are exactly those "
                   f"with one end attached at i and the other at j, mismatches {mis1e} and "
                   f"{mis1r}; {se['actions_with_parts_hanging_off_an_end']} and "
                   f"{sr['actions_with_parts_hanging_off_an_end']} actions have a part hanging "
                   f"off an end, so the attaining set is more than the joined pair. Outside that "
                   f"set the closest pair stays below the bound by a share "
                   f"{min(se['smallest_relative_gap_below_the_bound'], sr['smallest_relative_gap_below_the_bound']):.3g} of R")})
    criteria.append({
        "name": "B104-2", "kind": "own_reading", "passed": bool(ok2e and ok2r),
        "statement": "the blocks on the block-cut path between i and j are together the block "
                     "the action creates, and every vertex outside it moves with the one vertex "
                     "of it that it hangs from",
        "detail": (f"the same actions: on every one, the block of the graph after the action "
                   f"that holds the new edge has exactly the vertices of the blocks on the path "
                   f"(mismatches {fu2e} and {fu2r}). {se['off_path_vertices']} and "
                   f"{sr['off_path_vertices']} vertices lie outside it; each part outside meets "
                   f"it in exactly one vertex (exceptions {nu2e} and {nu2r}), and every vertex "
                   f"outside moves with that vertex to within {TOL:.0e}. So "
                   f"{se['pairs_hanging_together']} of {se['pairs']} pairs in the enumeration and "
                   f"{sr['pairs_hanging_together']} of {sr['pairs']} on the random graphs cannot "
                   f"move under the action they face. The converse is printed and not judged: "
                   f"distinct vertices of that block differ in potential by at least a share "
                   f"{min(se['smallest_relative_potential_gap_between_path_vertices'], sr['smallest_relative_potential_gap_between_path_vertices']):.3g} "
                   f"of R here, which holds for weights off a set of measure zero and not for "
                   f"every weight{tail}")})
    margins = [x["smallest_relative_margin_inside_a_block"] for x in (se, sr)
               if x["smallest_relative_margin_inside_a_block"] is not None]
    criteria.append({
        "name": "B104-3", "kind": "own_reading", "passed": bool(ok3e and ok3r),
        "statement": "along the path the joined pair's move is shared among the blocks in "
                     "proportion to each block's own resistance between its two gateways, "
                     "and every vertex of a block lies between its gateways, so every pair "
                     "split by a gateway moves the way the joined pair does",
        "detail": (f"the same actions: the path crosses two blocks or more on "
                   f"{se['actions_whose_path_crosses_two_blocks_or_more']} and "
                   f"{sr['actions_whose_path_crosses_two_blocks_or_more']} of them, at most "
                   f"{se['most_blocks_on_one_path']} and {sr['most_blocks_on_one_path']} "
                   f"blocks, and {se['single_edge_blocks_on_paths']} of "
                   f"{se['blocks_on_paths']} and {sr['single_edge_blocks_on_paths']} of "
                   f"{sr['blocks_on_paths']} blocks on the paths are a single edge. On every "
                   f"block the potential under a unit current rises from the gateway toward i "
                   f"to the gateway toward j by the block's own resistance, computed on its "
                   f"edges alone, to within {TOL:.0e} of R, and no vertex of a block lies "
                   f"outside its gateways by more than {TOL:.0e} of R"
                   + (f". Inside a block the closest vertex stays clear of both gateways by a "
                      f"share {min(margins):.3g} of R" if margins else ""))})
    report["enumeration"] = se
    report["random_sparse"] = sr
    report["compared_below"] = f"{TOL:.0e}"

    print(f"(run took {time.perf_counter() - t0:.1f} s; not written to the record)")
    for c in criteria:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['detail'][:160]}")

    rec = {"stage": "B104",
           "config": {"seed": a.seed, "max_enum_n": MAX_ENUM_N, "sizes": list(SIZES),
                      "graphs_per_size": GRAPHS_PER_SIZE, "actions_per_graph": ACTIONS_PER_GRAPH,
                      "extra_scale": EXTRA_SCALE, "tol": f"{TOL:.0e}",
                      "imports": ["b103_time_reachability"]},
           "criteria": criteria, "report": report}
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
