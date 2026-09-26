"""B65-6 and B65-7: the known-answer check and the structural checks for the
post-Keynesian station.

The statements are proved in docs/b65_post_keynesian.md. This file checks their
algebra, and the implementation of the objects they use, on graphs built for
the purpose, and runs Model SIM of Godley and Lavoie (2007, chapter 3) as a flow
on the enlarged graph. It reads no data and measures nothing in the world.

  B65-6   Model SIM as a flow, from zero stocks, with the government as the
          outside node. Each period is solved from the model's own seven
          equations and the flow is built from the solution. Kirchhoff's law
          holds at every node of every period. At the outside node, whose
          equation the solution never uses, it reads H_h(t) = H_s(t) at every
          date. The incidence matrix has rank one short of the node count. The
          stationary state reads back Y* = G/theta = 100, YD* = 80, H* = 80.
  B65-7a  Proposition 9.0 and Theorem 9 on random graphs: the incidence matrix
          has rank V - c; a potential pairs to zero with every circulation; the
          pairing of a field with a circulation is bounded by the distance of
          Theorem 5 times the circulation's norm, with equality at the field's
          cycle component; a field is exact exactly when every fundamental
          cycle sums to zero; one unit sent once around a cycle returns the
          exponential of the cycle's sum.
  B65-7b  Lemma 9.1 on random partitions of random connected graphs: the
          projection sends circulations to circulations of the quotient; with
          connected blocks it is onto, its kernel has the dimension of the
          circulations inside the blocks, and the first Betti number splits;
          with blocks allowed to fall apart, the image misses onto by exactly
          the sum over blocks of (components - 1).
  B65-7c  Theorem 10 and Corollary 10.2 on production graphs: the production
          cycle sums to log(1 + mu); with an unbounded producer a directed
          cycle is positive exactly when mu > 0; with every producer bounded
          none is; an entrant paying c per unit of output caps the price at
          unit cost + c; the profits of several producers are the sum over
          their cycles of the cost bill times (exp(cycle sum) - 1).
  B65-7d  Corollary 10.1 on random economies of workers, capitalists, firms,
          the rest of the world and the outside node, over one to four
          periods, with money and bills: Kirchhoff's law at the outside node
          without imposing it; the quotient by sector and date carries a
          circulation; each block's net lending read from its stocks equals
          its surplus on the flows that cross into it; the four sum to zero;
          and Kalecki's profit equation holds period by period, with profits
          read from the firms' income statement.

(NA) in B65-7c is the condition of b4_directed_edges Theorem 4, no directed
cycle with a positive sum, checked by Bellman-Ford on the edges held by the
classes that can walk without a bound on quantity.

Residuals are printed. The record keeps the bound each one was held to, since
their last digits belong to the numerical library.

Run:

    python experiments\\b65_pk_flow_side.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b65_pk_flow_side.json"

SEED = 0
TOL = 1e-12            # identities on flows and fields of order one to a hundred
TOL_CYCLE = 1e-12      # a directed cycle counts as positive only above this sum
TOL_PRICE = 1e-9       # the limit price found by bisection, against its closed form
TOL_STEADY = 1e-9      # SIM's stationary solution, against the book's values
TOL_PATH = 1e-4        # SIM's last simulated period, against the same values
GENERIC_FLOOR = 1e-6   # a generic field must leave some cycle sum above this
IMAGE_TOL = 1e-9       # singular values of a projected orthonormal cycle basis below this are zero
SIM_DIGITS = 6         # SIM's path as written to the record

# Model SIM, Godley and Lavoie (2007), chapter 3: parameters and starting stocks
SIM = {"alpha1": 0.6, "alpha2": 0.4, "theta": 0.2, "W": 1.0, "G": 20.0, "H0": 0.0}
SIM_PERIODS = 100
SIM_STEADY = {"Y": 100.0, "YD": 80.0, "H": 80.0}
SIM_SHOW = (1, 2, 3, 50, 100)
SIM_RANK_AT = (1, 2, 3, 10, 100)
SIM_RATIO_UPTO = 40    # periods over which the gap to the stationary state is read as a ratio

N_GRAPHS = 300
NODES = (4, 30)
EDGE_P = (0.08, 0.5)
PIECES_SHARE = 0.25    # share of graphs drawn in two or three pieces, for the rank count
X_PER_GRAPH = 5
N_PARTITIONS = 300
PART_NODES = (6, 30)
BLOCKS = (2, 6)
N_PRODUCTION = 400
MU_SPAN = 0.5
ENTRY_EVERY = 4        # the limit-price bisection runs on every fourth production draw
BISECTION_STEPS = 60
N_FIRMS = (2, 8)
N_ECONOMIES = 200
CLOSED_SHARE = 0.1
MAX_PERIODS = 4


# ------------------------------------------------------------------- graphs


def incidence(nodes, edges):
    """Rows are nodes, columns edges: +1 at the head, -1 at the tail. The
    transpose is d0, and incidence @ flow is the net inflow at every node."""
    index = {v: k for k, v in enumerate(nodes)}
    B = np.zeros((len(nodes), len(edges)))
    for e, (u, v) in enumerate(edges):
        B[index[v], e] += 1.0
        B[index[u], e] -= 1.0
    return B


def rank_of(M) -> int:
    return int(np.linalg.matrix_rank(M)) if M.size else 0


def net_inflow(edges, flows):
    """Kirchhoff's sum at every node: what flows in less what flows out."""
    out = {}
    for (u, v), x in zip(edges, flows):
        out[v] = out.get(v, 0.0) + float(x)
        out[u] = out.get(u, 0.0) - float(x)
    return out


def n_components(nodes, edges) -> int:
    parent = {v: v for v in nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    return len({find(v) for v in nodes})


def fundamental_cycles(n, edges):
    """One signed indicator vector per edge outside a breadth-first spanning
    forest of the graph on nodes 0..n-1: +1 where the cycle runs along an
    edge, -1 where it runs against it."""
    adj = [[] for _ in range(n)]
    for e, (u, v) in enumerate(edges):
        adj[u].append((v, e))
        adj[v].append((u, e))
    depth, parent, pedge, tree = [-1] * n, [-1] * n, [-1] * n, set()
    for root in range(n):
        if depth[root] >= 0:
            continue
        depth[root] = 0
        queue = [root]
        for a in queue:
            for b, e in adj[a]:
                if depth[b] < 0:
                    depth[b], parent[b], pedge[b] = depth[a] + 1, a, e
                    tree.add(e)
                    queue.append(b)
    cycles = []
    for e, (u, v) in enumerate(edges):
        if e in tree:
            continue
        z = np.zeros(len(edges))
        z[e] = 1.0                        # along e, from u to v; then back from v to u in the tree
        a, b, up, down = v, u, [], []
        while depth[a] > depth[b]:
            up.append(a)
            a = parent[a]
        while depth[b] > depth[a]:
            down.append(b)
            b = parent[b]
        while a != b:
            up.append(a)
            a = parent[a]
            down.append(b)
            b = parent[b]
        for c in up:                      # a step from c to its parent
            z[pedge[c]] += 1.0 if edges[pedge[c]][0] == c else -1.0
        for c in down:                    # a step from a parent down to c
            z[pedge[c]] += 1.0 if edges[pedge[c]][1] == c else -1.0
        cycles.append(z)
    return cycles


def cycle_space(B):
    """Columns: an orthonormal basis of the kernel of the incidence matrix."""
    if B.shape[1] == 0:
        return np.zeros((0, 0))
    _, s, vt = np.linalg.svd(B, full_matrices=True)
    cut = s.max() * max(B.shape) * np.finfo(float).eps if s.size else 0.0
    return vt[int((s > cut).sum()):].T


def distance(B, omega):
    """Theorem 5's distance from omega to the fields with a potential, and the
    residual of the least-squares fit, which is omega's cycle component."""
    psi, *_ = np.linalg.lstsq(B.T, omega, rcond=None)
    comp = omega - B.T @ psi
    return float(np.linalg.norm(comp)), comp


def random_graph(rng, n, p, pieces=1):
    """A random simple graph on nodes 0..n-1, connected within each of
    `pieces` parts: a random spanning tree per part, then each further pair
    inside a part with probability p, every edge oriented at random."""
    order = [int(a) for a in rng.permutation(n)]
    parts = [order[k::pieces] for k in range(pieces)]
    pairs = set()
    for part in parts:
        for i in range(1, len(part)):
            j = int(rng.integers(0, i))
            pairs.add((min(part[i], part[j]), max(part[i], part[j])))
        for i in range(len(part)):
            for j in range(i + 1, len(part)):
                if rng.random() < p:
                    pairs.add((min(part[i], part[j]), max(part[i], part[j])))
    return [(a, b) if rng.random() < 0.5 else (b, a) for a, b in sorted(pairs)]


def positive_cycle(edges) -> bool:
    """True iff some directed cycle has a sum above TOL_CYCLE: Bellman-Ford on
    the negated weights from a virtual source at every node."""
    index = {}
    for u, v, _ in edges:
        index.setdefault(u, len(index))
        index.setdefault(v, len(index))
    dist = [0.0] * len(index)
    arcs = [(index[u], index[v], -w) for u, v, w in edges]
    for _ in range(len(index) + 1):
        changed = False
        for u, v, c in arcs:
            if dist[u] + c < dist[v] - TOL_CYCLE:
                dist[v] = dist[u] + c
                changed = True
        if not changed:
            return False
    return True


# -------------------------------------------------------------- B65-6: SIM


def sim_path():
    """Model SIM period by period, from its own seven equations (3.1 to 3.11
    with the supplies set equal to the demands). Unknowns: Y, N, T, YD, C,
    the change in the households' money dHh and the change in the money the
    government has issued dHs. The equation H_h = H_s is not among them."""
    a1, a2, th, W, G = (SIM[k] for k in ("alpha1", "alpha2", "theta", "W", "G"))
    A = np.array([[0.0, -W, 1.0, 1.0, 0.0, 0.0, 0.0],        # YD = W N - T
                  [0.0, -th * W, 1.0, 0.0, 0.0, 0.0, 0.0],   # T = theta W N
                  [0.0, 0.0, 0.0, -a1, 1.0, 0.0, 0.0],       # C = alpha1 YD + alpha2 Hh(-1)
                  [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],       # dHs = G - T
                  [0.0, 0.0, 0.0, -1.0, 1.0, 1.0, 0.0],      # dHh = YD - C
                  [1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0],      # Y = C + G
                  [-1.0, W, 0.0, 0.0, 0.0, 0.0, 0.0]])       # N = Y / W
    path, hh, hs = [], SIM["H0"], SIM["H0"]
    for t in range(1, SIM_PERIODS + 1):
        b = np.array([0.0, 0.0, a2 * hh, G, 0.0, G, 0.0])
        Y, N, T, YD, C, dhh, dhs = (float(v) for v in np.linalg.solve(A, b))
        hh, hs = hh + dhh, hs + dhs
        path.append({"t": t, "Y": Y, "N": N, "T": T, "YD": YD, "C": C,
                     "dHh": dhh, "dHs": dhs, "Hh": hh, "Hs": hs})
    return path


def sim_graph(path, horizon):
    """The flow of the first `horizon` periods on Gamma. Classes: households h
    and firms f, with the government as the outside node O. Positions: money
    m, hours L, goods Q. Money flows one way on an agent edge and goods or
    hours the other way, at p = W = 1 per unit; the firms' production edge
    L -> Q carries the wage bill, which the goods sell for, since output per
    hour is W and the price is 1. The households' money is carried on the time
    edge and leaves to O at the last date; hours enter from O and goods used
    up leave to it."""
    W, G = SIM["W"], SIM["G"]
    edges, flows = [], []

    def add(u, v, x):
        edges.append((u, v))
        flows.append(x)

    add("O", ("h", "m", 0), SIM["H0"])
    carried = SIM["H0"]
    for row in path[:horizon]:
        t, wage = row["t"], W * row["N"]
        add(("h", "m", t - 1), ("h", "m", t), carried)   # the households' money, carried
        add(("f", "m", t), ("h", "m", t), wage)          # wages
        add(("h", "m", t), ("f", "m", t), row["C"])      # consumption, paid
        add("O", ("f", "m", t), G)                       # government spending, paid
        add(("h", "m", t), "O", row["T"])                # taxes
        add("O", ("h", "L", t), wage)                    # hours supplied, at the wage
        add(("h", "L", t), ("f", "L", t), wage)          # hours sold
        add(("f", "L", t), ("f", "Q", t), wage)          # production
        add(("f", "Q", t), ("h", "Q", t), row["C"])      # goods bought by households
        add(("f", "Q", t), "O", G)                       # goods bought by the government
        add(("h", "Q", t), "O", row["C"])                # goods used up
        carried = row["Hh"]
    add(("h", "m", horizon), "O", carried)               # the households' money at the last date
    return edges, np.array(flows)


def sim_stationary():
    """The same equations with dHh = dHs = 0: seven equations in Y, N, T, YD,
    C and H. Their rank is six, one of them implied by the rest."""
    a1, a2, th, W, G = (SIM[k] for k in ("alpha1", "alpha2", "theta", "W", "G"))
    A = np.array([[0.0, -W, 1.0, 1.0, 0.0, 0.0],        # YD = W N - T
                  [0.0, -th * W, 1.0, 0.0, 0.0, 0.0],   # T = theta W N
                  [0.0, 0.0, 0.0, -a1, 1.0, -a2],       # C = alpha1 YD + alpha2 H
                  [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],       # 0 = G - T
                  [0.0, 0.0, 0.0, -1.0, 1.0, 0.0],      # 0 = YD - C
                  [1.0, 0.0, 0.0, 0.0, -1.0, 0.0],      # Y = C + G
                  [-1.0, W, 0.0, 0.0, 0.0, 0.0]])       # N = Y / W
    b = np.array([0.0, 0.0, 0.0, G, 0.0, G, 0.0])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    names = ("Y", "N", "T", "YD", "C", "H")
    return ({k: float(v) for k, v in zip(names, sol)}, rank_of(A),
            float(np.abs(A @ sol - b).max()))


def check_sim():
    path = sim_path()
    # Kirchhoff at every node of the full run, the outside node included
    edges, flows = sim_graph(path, SIM_PERIODS)
    inflow = net_inflow(edges, flows)
    worst_inside = max(abs(v) for k, v in inflow.items() if k != "O")
    # the outside node, on the run cut at every date
    worst_outside, worst_row = 0.0, 0.0
    for h in range(1, SIM_PERIODS + 1):
        e_h, x_h = sim_graph(path, h)
        worst_outside = max(worst_outside, abs(net_inflow(e_h, x_h)["O"]))
        worst_row = max(worst_row, abs(path[h - 1]["Hh"] - path[h - 1]["Hs"]))
    # rank of the incidence matrix, one short of the node count
    ranks = {}
    for h in SIM_RANK_AT:
        e_h, _ = sim_graph(path, h)
        nodes = sorted({v for pair in e_h for v in pair}, key=repr)
        ranks[h] = (len(nodes), rank_of(incidence(nodes, e_h)), n_components(nodes, e_h))
    rank_ok = all(r == n - 1 and c == 1 for n, r, c in ranks.values())
    # the stationary state, solved and simulated
    stat, stat_rank, stat_resid = sim_stationary()
    last = path[-1]
    gap_stat = max(abs(stat["Y"] - SIM_STEADY["Y"]), abs(stat["YD"] - SIM_STEADY["YD"]),
                   abs(stat["H"] - SIM_STEADY["H"]))
    gap_path = max(abs(last["Y"] - SIM_STEADY["Y"]), abs(last["YD"] - SIM_STEADY["YD"]),
                   abs(last["Hh"] - SIM_STEADY["H"]))
    a1, a2, th = SIM["alpha1"], SIM["alpha2"], SIM["theta"]
    factor = 1.0 - a2 * th / (1.0 - a1 * (1.0 - th))
    ratios = [(SIM_STEADY["H"] - path[t]["Hh"]) / (SIM_STEADY["H"] - path[t - 1]["Hh"])
              for t in range(1, SIM_RATIO_UPTO)]
    ratio_gap = max(abs(r - factor) for r in ratios)
    # the firms' production cycle: buy an hour at W, make W units, sell each at 1
    W = SIM["W"]
    cycle_sum = -math.log(W) + math.log(W) + math.log(1.0)

    ok = (worst_inside < TOL and worst_outside < TOL and worst_row < TOL and rank_ok
          and stat_rank == 6 and stat_resid < TOL_STEADY and gap_stat < TOL_STEADY
          and gap_path < TOL_PATH)
    shown = {str(t): {k: round(path[t - 1][k], SIM_DIGITS)
                      for k in ("Y", "T", "YD", "C", "dHh", "Hh", "Hs")} for t in SIM_SHOW}
    rank_txt = ", ".join("%d nodes and rank %d at %d period%s" % (n, r, h, "" if h == 1 else "s")
                         for h, (n, r, c) in ranks.items())
    detail = ("%d periods from zero stocks, G = %g, theta = %g, alpha1 = %g, alpha2 = %g, W = %g, "
              "each solved from the seven equations of the model and written as a flow on "
              "households, firms and the outside node, over money, hours and goods. Kirchhoff's "
              "law holds within %g at every node of every period. At the outside node, whose "
              "equation no step of the solution uses, it holds within %g on the run cut at each "
              "of the %d dates, and H_h(t) - H_s(t), the two stocks carried by the two budget "
              "constraints separately, stays within %g. The graph is connected and its incidence "
              "matrix has rank one short of its node count: %s. The stationary equations have "
              "rank 6 in 7 and solve to Y = %g, YD = %g, H = %g within %g; the last period lies "
              "within %g of them. The firms' production cycle sums to zero"
              % (SIM_PERIODS, SIM["G"], th, a1, a2, W, TOL, TOL, SIM_PERIODS, TOL, rank_txt,
                 SIM_STEADY["Y"], SIM_STEADY["YD"], SIM_STEADY["H"], TOL_STEADY, TOL_PATH))
    printed = ["Kirchhoff, worst over the %d-period run: %.3e at the nodes inside, "
               "%.3e at the outside node on the cut runs; worst |H_h - H_s| %.3e"
               % (SIM_PERIODS, worst_inside, worst_outside, worst_row),
               "stationary solution: " + ", ".join("%s = %.9f" % kv for kv in stat.items())
               + "; rank %d in 7, residual %.3e" % (stat_rank, stat_resid),
               "last period against the book's values: largest gap %.3e" % gap_path,
               "the gap to H* shrinks by %.9f each period (closed form "
               "1 - alpha2 theta / (1 - alpha1 (1 - theta))); the ratio over periods 1 to %d "
               "departs from it by at most %.3e" % (factor, SIM_RATIO_UPTO - 1, ratio_gap),
               "production cycle of the firms: %.3e" % cycle_sum,
               "   t        Y        T       YD        C      dHh       Hh       Hs"]
    for t in SIM_SHOW:
        r = path[t - 1]
        printed.append("%4d %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f"
                       % (t, r["Y"], r["T"], r["YD"], r["C"], r["dHh"], r["Hh"], r["Hs"]))
    report = {"periods": SIM_PERIODS, "kirchhoff_below": TOL,
              "outside_node_below": TOL, "balance_sheet_row_below": TOL,
              "ranks": {str(h): {"nodes": n, "rank": r, "components": c}
                        for h, (n, r, c) in ranks.items()},
              "stationary": {k: round(v, SIM_DIGITS) for k, v in stat.items()},
              "stationary_rank": stat_rank, "stationary_within": TOL_STEADY,
              "last_period_within": TOL_PATH,
              "convergence_factor": round(factor, 12),
              "ratio_matches_factor_below_1e-9": bool(ratio_gap < 1e-9),
              "production_cycle_sum": round(cycle_sum, 12),
              "path": shown}
    return ok, detail, report, printed


# ----------------------------------------------- B65-7a: Proposition 9.0, Theorem 9


def check_a(rng):
    n_graphs = n_pieces = rank_ok = count_ok = with_cycles = 0
    worst = dict.fromkeys(("basis", "potential", "two_distances", "equality", "exact_sums",
                           "exact_distance", "shifted_distance", "multiplier"), 0.0)
    excess = -math.inf          # |<omega, x>| - distance * ||x||, largest over all draws
    generic_sum = generic_dist = math.inf
    for _ in range(N_GRAPHS):
        n = int(rng.integers(NODES[0], NODES[1] + 1))
        pieces = int(rng.integers(2, 4)) if rng.random() < PIECES_SHARE else 1
        edges = random_graph(rng, n, float(rng.uniform(*EDGE_P)), pieces)
        nodes = list(range(n))
        B = incidence(nodes, edges)
        c, r = n_components(nodes, edges), rank_of(B)
        cycles = fundamental_cycles(n, edges)
        n_graphs += 1
        n_pieces += c > 1
        rank_ok += r == n - c
        count_ok += len(cycles) == len(edges) - n + c == len(edges) - r
        if not cycles:
            continue
        with_cycles += 1
        Z = np.array(cycles).T
        worst["basis"] = max(worst["basis"], float(np.abs(B @ Z).max()))
        omega, psi = rng.normal(0, 1, len(edges)), rng.normal(0, 1, n)
        dist, comp = distance(B, omega)
        Q = cycle_space(B)
        worst["two_distances"] = max(worst["two_distances"],
                                     abs(dist - float(np.linalg.norm(Q @ (Q.T @ omega)))))
        for _ in range(X_PER_GRAPH):
            x = Z @ rng.normal(0, 1, Z.shape[1])
            worst["potential"] = max(worst["potential"], abs(float((B.T @ psi) @ x)))
            excess = max(excess, abs(float(omega @ x)) - dist * float(np.linalg.norm(x)))
        worst["equality"] = max(worst["equality"],
                                abs(float(omega @ comp) - dist * float(np.linalg.norm(comp))))
        exact = B.T @ psi
        worst["exact_sums"] = max(worst["exact_sums"], float(np.abs(Z.T @ exact).max()))
        worst["exact_distance"] = max(worst["exact_distance"], distance(B, exact)[0])
        z = Z @ rng.normal(0, 1, Z.shape[1])
        worst["shifted_distance"] = max(worst["shifted_distance"],
                                        abs(distance(B, exact + z)[0] - float(np.linalg.norm(z))))
        generic_sum = min(generic_sum, float(np.abs(Z.T @ omega).max()))
        generic_dist = min(generic_dist, dist)
        for zc in cycles:
            product = 1.0
            for e in np.nonzero(zc)[0]:
                product *= math.exp(zc[e] * omega[e])
            total = math.exp(float(zc @ omega))
            worst["multiplier"] = max(worst["multiplier"], abs(product - total) / total)
    ok = (rank_ok == n_graphs and count_ok == n_graphs and all(v < TOL for v in worst.values())
          and excess <= TOL and generic_sum > GENERIC_FLOOR and generic_dist > GENERIC_FLOOR)
    detail = ("%d random graphs of %d to %d nodes, %d of them in two or three pieces. The "
              "incidence matrix has rank V - c in %d of %d, and the fundamental cycles number "
              "E - V + c = E - rank in %d of %d. On the %d graphs with a cycle, %d random "
              "circulations: every fundamental cycle is a circulation; a random potential pairs "
              "to zero with every circulation; the distance of Theorem 5, once by least squares "
              "and once by projection on the cycle space, agrees; |<omega, x>| never exceeds "
              "the distance times ||x||, and the field's cycle component attains it; an exact "
              "field has every fundamental cycle sum and its distance at zero, and adding a "
              "circulation z moves the distance to ||z||; a generic field leaves some fundamental "
              "cycle sum and its distance above %g on every graph; one unit sent around each "
              "fundamental cycle, rate by rate, returns exp of the cycle's sum. Identities "
              "within %g"
              % (n_graphs, NODES[0], NODES[1], n_pieces, rank_ok, n_graphs, count_ok, n_graphs,
                 with_cycles, with_cycles * X_PER_GRAPH, GENERIC_FLOOR, TOL))
    printed = ["worst residuals: " + ", ".join("%s %.3e" % kv for kv in worst.items()),
               "largest |<omega, x>| - distance ||x||: %.3e (no larger than zero is the bound)"
               % excess,
               "generic field, smallest over graphs of the largest |cycle sum|: %.4f; "
               "smallest distance: %.4f" % (generic_sum, generic_dist)]
    report = {"graphs": n_graphs, "in_pieces": n_pieces, "rank_is_V_minus_c": rank_ok,
              "cycle_count_matches": count_ok, "graphs_with_cycles": with_cycles,
              "circulations": with_cycles * X_PER_GRAPH, "identities_below": TOL,
              "generic_above": GENERIC_FLOOR}
    return ok, detail, report, printed


# ------------------------------------------------------------ B65-7b: Lemma 9.1


def grow_blocks(rng, n, edges, k):
    """A random partition into k blocks, each inducing a connected subgraph:
    k random seeds, then each node in turn joins a block it has an edge to."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    label = [-1] * n
    for b, s in enumerate(rng.choice(n, size=k, replace=False)):
        label[int(s)] = b
    while min(label) < 0:
        frontier = sorted({v for u in range(n) if label[u] >= 0 for v in adj[u] if label[v] < 0})
        v = frontier[int(rng.integers(0, len(frontier)))]
        owners = sorted({label[u] for u in adj[v] if label[u] >= 0})
        label[v] = owners[int(rng.integers(0, len(owners)))]
    return label


def scatter_blocks(rng, n, k):
    """A random partition into k non-empty blocks, with no condition on them."""
    label = [0] * n
    for i, v in enumerate(int(a) for a in rng.permutation(n)):
        label[v] = i if i < k else int(rng.integers(0, k))
    return label


def quotient_counts(n, edges, label, k):
    nodes = list(range(n))
    B = incidence(nodes, edges)
    b1 = len(edges) - rank_of(B)
    out = [e for e, (u, v) in enumerate(edges) if label[u] != label[v]]
    qedges = [(label[edges[e][0]], label[edges[e][1]]) for e in out]
    Bq = incidence(list(range(k)), qedges)
    b1_q = len(qedges) - rank_of(Bq)
    inside = deficit = 0
    for blk in range(k):
        members = [v for v in nodes if label[v] == blk]
        inner = [(u, v) for (u, v) in edges if label[u] == blk and label[v] == blk]
        inside += len(inner) - rank_of(incidence(members, inner))
        deficit += n_components(members, inner) - 1
    Q = cycle_space(B)
    image = Q[out, :] if Q.size else np.zeros((len(out), 0))
    into = float(np.abs(Bq @ image).max()) if image.size else 0.0
    # The columns of Q are orthonormal, so the singular values of the image lie in [0, 1]; an
    # absolute cut is the right one here, since an image that should vanish has all of its
    # singular values at rounding level, the largest included.
    sv = np.linalg.svd(image, compute_uv=False) if image.size else np.zeros(0)
    rank_image = int((sv > IMAGE_TOL).sum())
    return {"b1": b1, "b1_quotient": b1_q, "b1_inside": inside, "image": rank_image,
            "kernel": b1 - rank_image, "deficit": deficit, "into": into,
            "largest_zero": float(sv[sv <= IMAGE_TOL].max()) if (sv <= IMAGE_TOL).any() else 0.0,
            "smallest_nonzero": float(sv[sv > IMAGE_TOL].min()) if (sv > IMAGE_TOL).any() else 1.0}


def check_b(rng):
    conn = {"n": 0, "onto": 0, "kernel": 0, "split": 0}
    scat = {"n": 0, "short_by_deficit": 0, "kernel": 0, "with_deficit": 0}
    worst_into, largest_zero, smallest_nonzero = 0.0, 0.0, 1.0
    for _ in range(N_PARTITIONS):
        n = int(rng.integers(PART_NODES[0], PART_NODES[1] + 1))
        edges = random_graph(rng, n, float(rng.uniform(*EDGE_P)))
        k = int(rng.integers(BLOCKS[0], min(BLOCKS[1], n - 1) + 1))
        q = quotient_counts(n, edges, grow_blocks(rng, n, edges, k), k)
        worst_into = max(worst_into, q["into"])
        largest_zero = max(largest_zero, q["largest_zero"])
        smallest_nonzero = min(smallest_nonzero, q["smallest_nonzero"])
        conn["n"] += 1
        conn["onto"] += q["image"] == q["b1_quotient"] and q["deficit"] == 0
        conn["kernel"] += q["kernel"] == q["b1_inside"]
        conn["split"] += q["b1"] == q["b1_quotient"] + q["b1_inside"]
        q = quotient_counts(n, edges, scatter_blocks(rng, n, k), k)
        worst_into = max(worst_into, q["into"])
        largest_zero = max(largest_zero, q["largest_zero"])
        smallest_nonzero = min(smallest_nonzero, q["smallest_nonzero"])
        scat["n"] += 1
        scat["short_by_deficit"] += q["b1_quotient"] - q["image"] == q["deficit"]
        scat["kernel"] += q["kernel"] == q["b1_inside"]
        scat["with_deficit"] += q["deficit"] > 0
    ok = (worst_into < TOL and conn["onto"] == conn["kernel"] == conn["split"] == conn["n"]
          and scat["short_by_deficit"] == scat["kernel"] == scat["n"])
    detail = ("%d random connected graphs of %d to %d nodes, each partitioned twice into %d to "
              "%d blocks. The projection keeps only the edges between blocks and sends every "
              "circulation to a circulation of the quotient, within %g, in all %d partitions. "
              "Blocks grown connected: the projection is onto in %d of %d, its kernel has the "
              "dimension of the circulations inside the blocks in %d of %d, and "
              "b1(Gamma) = b1(quotient) + sum of b1(blocks) in %d of %d. Blocks drawn with no "
              "condition, %d of them with a block in pieces: the kernel is still the "
              "circulations inside the blocks in %d of %d, and the image misses onto by exactly "
              "the sum over blocks of (components - 1) in %d of %d"
              % (N_PARTITIONS, PART_NODES[0], PART_NODES[1], BLOCKS[0], BLOCKS[1], TOL,
                 conn["n"] + scat["n"], conn["onto"], conn["n"], conn["kernel"], conn["n"],
                 conn["split"], conn["n"], scat["with_deficit"], scat["kernel"], scat["n"],
                 scat["short_by_deficit"], scat["n"]))
    printed = ["worst |quotient Kirchhoff| of a projected circulation: %.3e" % worst_into,
               "singular values of the projected cycle basis, over all partitions: largest "
               "counted as zero %.3e, smallest counted as nonzero %.3e, cut at %g"
               % (largest_zero, smallest_nonzero, IMAGE_TOL)]
    report = {"graphs": N_PARTITIONS, "connected_blocks": conn, "unconditioned_blocks": scat,
              "into_below": TOL, "rank_cut": IMAGE_TOL}
    return ok, detail, report, printed


# ------------------------------------------- B65-7c: Theorem 10, Corollary 10.2


def production_graph(classes, w_in, tech, price, walkers, entry=None):
    """Edges at money M, the input L and goods Q. The input is labour hours at
    the wage w_in with tech hours per unit of output, or one bundle of prime
    inputs at its unit cost w_in with tech = 1. Market edges run both ways at
    the posted prices for every class, agent edges between classes at par.
    Each class in `walkers` holds the production edge L -> Q, which does not
    run backward; `entry` maps a class to its cost per unit of output, paid on
    its production edge. A class that produces under a bound on quantity is
    left out of `walkers`: its production edge is not a walk without bound."""
    entry = entry or {}
    edges = []
    for a in classes:
        edges += [((a, "M"), (a, "L"), -math.log(w_in)), ((a, "L"), (a, "M"), math.log(w_in)),
                  ((a, "M"), (a, "Q"), -math.log(price)), ((a, "Q"), (a, "M"), math.log(price))]
        if a in walkers:
            cost = entry.get(a, 0.0)
            edges.append(((a, "L"), (a, "Q"), -math.log(tech) - math.log1p(cost / (w_in * tech))))
    for a in classes:
        for b in classes:
            if a != b:
                edges += [((a, i), (b, i), 0.0) for i in ("M", "L", "Q")]
    return edges


def cycle_sum(edges, a):
    """The sum of the production cycle (a, M) -> (a, L) -> (a, Q) -> (a, M)."""
    w = {(u, v): x for u, v, x in edges}
    return w[((a, "M"), (a, "L"))] + w[((a, "L"), (a, "Q"))] + w[((a, "Q"), (a, "M"))]


def limit_price(classes, w_in, tech, walkers, entry):
    """The largest price at which no directed cycle is positive, by bisection."""
    cap = w_in * tech + max(entry.values())
    lo, hi = 0.5 * w_in * tech, 2.0 * cap
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        if positive_cycle(production_graph(classes, w_in, tech, mid, walkers, entry)):
            hi = mid
        else:
            lo = mid
    return lo


def check_c(rng):
    n = dict.fromkeys(("draws", "labour", "bundle", "free_entry", "all_bounded",
                       "bounded_plus_entrant", "entry_draws", "entry_cap", "entry_zero_cost"), 0)
    worst_sum = worst_price = worst_profit = 0.0
    first_order_example = None
    for k in range(N_PRODUCTION):
        mu = 0.0 if k == 0 else float(rng.uniform(-MU_SPAN, MU_SPAN))
        if k % 2 == 0:
            w_in, tech = float(rng.uniform(0.5, 2.0)), float(rng.uniform(0.2, 2.0))
            n["labour"] += 1
        else:
            w_in = (float(rng.uniform(0.5, 2.0)) * float(rng.uniform(0.2, 2.0))
                    + float(rng.uniform(0.1, 1.0)) * float(rng.uniform(0.1, 1.0)))
            tech = 1.0
            n["bundle"] += 1
        price = (1.0 + mu) * w_in * tech
        producers = ["F%d" % j for j in range(int(rng.integers(1, 4)))]
        households = ["H%d" % j for j in range(int(rng.integers(1, 3)))]
        classes = producers + households
        n["draws"] += 1
        g = production_graph(classes, w_in, tech, price, producers)
        worst_sum = max(worst_sum, abs(cycle_sum(g, producers[0]) - math.log1p(mu)))
        n["free_entry"] += positive_cycle(g) == (mu > 0)
        n["all_bounded"] += not positive_cycle(production_graph(classes, w_in, tech, price, []))
        n["bounded_plus_entrant"] += positive_cycle(
            production_graph(classes + ["E"], w_in, tech, price, ["E"])) == (mu > 0)
        if k % ENTRY_EVERY == 0:
            cost = 0.0 if k == 0 else float(rng.uniform(0.0, 1.0)) * w_in * tech
            p_star = limit_price(classes + ["E"], w_in, tech, ["E"], {"E": cost})
            worst_price = max(worst_price, abs(p_star - (w_in * tech + cost)))
            n["entry_draws"] += 1
            n["entry_cap"] += abs(p_star - (w_in * tech + cost)) < TOL_PRICE
            n["entry_zero_cost"] += cost == 0.0 and abs(p_star - w_in * tech) < TOL_PRICE
        # Corollary 10.2 with several producers, each with its own cost and markup
        firms = int(rng.integers(N_FIRMS[0], N_FIRMS[1] + 1))
        u = rng.uniform(0.5, 2.0, firms)
        q = rng.uniform(0.5, 10.0, firms)
        m = rng.uniform(-0.3, 0.8, firms)
        p = (1.0 + m) * u
        sums = np.log(p) - np.log(u)
        exact = float(((p - u) * q).sum())
        via_cycles = float((u * q * np.expm1(sums)).sum())
        worst_profit = max(worst_profit, abs(exact - via_cycles) / max(1.0, abs(exact)))
        if first_order_example is None:
            first_order_example = (exact, via_cycles, float((u * q * sums).sum()))
    ok = (worst_sum < TOL and n["free_entry"] == n["draws"] and n["all_bounded"] == n["draws"]
          and n["bounded_plus_entrant"] == n["draws"] and n["entry_cap"] == n["entry_draws"]
          and n["entry_zero_cost"] == 1 and worst_profit < TOL)
    detail = ("%d production draws, %d with labour hours as the input and %d with a bundle of "
              "prime inputs at its unit cost, the first at mu = 0 exactly, the rest with mu "
              "uniform in [-%g, %g]. The production cycle sums to log(1 + mu) within %g. All "
              "producers unbounded: a directed cycle is positive exactly when mu > 0 in %d of "
              "%d. All producers bounded: no directed cycle is positive in %d of %d. Bounded "
              "producers and one unbounded entrant: positive exactly when mu > 0 in %d of %d. "
              "An entrant paying c per unit of output, on %d draws, the first with c = 0: the "
              "largest price with no positive cycle is unit cost + c within %g in %d of %d. "
              "Profits of 2 to 8 producers with their own costs and markups equal the sum over "
              "their cycles of cost bill times (exp(sum) - 1), within %g relative, on every draw"
              % (n["draws"], n["labour"], n["bundle"], MU_SPAN, MU_SPAN, TOL, n["free_entry"],
                 n["draws"], n["all_bounded"], n["draws"], n["bounded_plus_entrant"], n["draws"],
                 n["entry_draws"], TOL_PRICE, n["entry_cap"], n["entry_draws"], TOL))
    printed = ["worst cycle-sum error %.3e; worst limit-price error %.3e; worst profit error %.3e"
               % (worst_sum, worst_price, worst_profit),
               "first multi-producer draw: profits %.6f, through the cycles %.6f, first order "
               "(cost bill times cycle sum) %.6f" % first_order_example]
    report = {"counts": n, "cycle_sum_below": TOL, "limit_price_below": TOL_PRICE,
              "profits_below": TOL}
    return ok, detail, report, printed


# -------------------------------------------------------- B65-7d: Corollary 10.1

BLOCK = {"w": "W", "k": "K", "f": "K", "r": "R"}   # capitalists and their firms are one block


def random_economy(rng, closed):
    """Workers w, capitalists k, firms f and the rest of the world r, holding
    money m and bills b, with the government as the outside node O, over one
    to `MAX_PERIODS` periods. Each flow is (period, kind, payer, payee,
    instrument, amount). A closed economy has no government, no trade with
    the rest of the world, and workers who spend what they earn."""
    size = {"w": int(rng.integers(2, 6)), "k": int(rng.integers(1, 4)),
            "f": int(rng.integers(2, 5)), "r": int(rng.integers(1, 3))}
    agents = [(s, j) for s in ("w", "k", "f", "r") for j in range(size[s])]
    periods = int(rng.integers(1, MAX_PERIODS + 1))
    stock0 = {(a, i): float(rng.uniform(0.0, 1.0)) for a in agents for i in ("m", "b")}
    flows = []

    def pick(s):
        return "O" if s == "O" else (s, int(rng.integers(0, size[s])))

    def draw(t, kind, payer_s, payee_s, instrument="m"):
        for _ in range(int(rng.integers(1, 5))):
            payer, payee = pick(payer_s), pick(payee_s)
            amount = float(rng.uniform(0.0, 1.0))
            if payer != payee:
                flows.append((t, kind, payer, payee, instrument, amount))

    for t in range(1, periods + 1):
        draw(t, "wage", "f", "w")
        if closed:
            wages = sum(x for (tt, kd, _, _, _, x) in flows if tt == t and kd == "wage")
            raw = rng.uniform(0.1, 1.0, int(rng.integers(1, 5)))
            for x in raw * (wages / raw.sum()):
                flows.append((t, "cons_w", pick("w"), pick("f"), "m", float(x)))
        else:
            draw(t, "cons_w", "w", "f")
        draw(t, "cons_k", "k", "f")
        draw(t, "inv", "f", "f")
        draw(t, "div", "f", "k")
        for s in ("w", "k", "r"):
            draw(t, "transfer", s, s)
        for _ in range(int(rng.integers(0, 4))):          # bills traded between private agents
            seller = pick(agents[int(rng.integers(0, len(agents)))][0])
            buyer = pick(agents[int(rng.integers(0, len(agents)))][0])
            amount = float(rng.uniform(0.0, 1.0))
            if seller != buyer:
                flows.append((t, "trade_bill", seller, buyer, "b", amount))
                flows.append((t, "trade_pay", buyer, seller, "m", amount))
        if closed:
            continue
        draw(t, "gov", "O", "f")
        draw(t, "tax_w", "w", "O")
        draw(t, "tax_k", "f", "O")
        draw(t, "tax_k", "k", "O")
        draw(t, "exp", "r", "f")
        draw(t, "imp", "f", "r")
        for _ in range(int(rng.integers(0, 4))):          # bills bought from the outside node
            buyer = pick(agents[int(rng.integers(0, len(agents)))][0])
            amount = float(rng.uniform(0.0, 1.0))
            flows.append((t, "issue_pay", buyer, "O", "m", amount))
            flows.append((t, "issue_bill", "O", buyer, "b", amount))
    return agents, periods, stock0, flows


def economy_graph(stock0, flows, horizon):
    """The flow of the first `horizon` periods. Node (a, i, t) receives the
    stock carried from t - 1 and the period's flows in instrument i, and
    carries the rest to t + 1; the stocks enter from O at date 0 and leave
    to it at the last date. The stocks are what Kirchhoff's law at the
    private nodes leaves; the law at O is not imposed."""
    stocks = {0: dict(stock0)}
    for t in range(1, horizon + 1):
        cur = dict(stocks[t - 1])
        for (tt, _, payer, payee, inst, x) in flows:
            if tt == t:
                if payer != "O":
                    cur[(payer, inst)] -= x
                if payee != "O":
                    cur[(payee, inst)] += x
        stocks[t] = cur

    def node(p, i, t):
        return "O" if p == "O" else (p, i, t)

    edges, xs = [], []
    for (a, i), s0 in stock0.items():
        edges.append(("O", (a, i, 0)))
        xs.append(s0)
    for t in range(1, horizon + 1):
        for (a, i) in stock0:
            edges.append(((a, i, t - 1), (a, i, t)))
            xs.append(stocks[t - 1][(a, i)])
        for (tt, _, payer, payee, inst, x) in flows:
            if tt == t:
                edges.append((node(payer, inst, t), node(payee, inst, t)))
                xs.append(x)
    for (a, i) in stock0:
        edges.append(((a, i, horizon), "O"))
        xs.append(stocks[horizon][(a, i)])
    return edges, xs, stocks


def label_of(v):
    return "O" if v == "O" else (BLOCK[v[0][0]], v[2])


def check_d(rng):
    n_econ = n_closed = n_periods = 0
    worst = dict.fromkeys(("inside", "outside", "quotient", "workers", "rest", "capitalists",
                           "sum", "kalecki", "closed"), 0.0)
    for k in range(N_ECONOMIES):
        closed = k < N_ECONOMIES * CLOSED_SHARE
        agents, periods, stock0, flows = random_economy(rng, closed)
        n_econ += 1
        n_closed += closed
        for h in range(1, periods + 1):                    # the law at O, on the run cut at each date
            e_h, x_h, _ = economy_graph(stock0, flows, h)
            worst["outside"] = max(worst["outside"], abs(net_inflow(e_h, x_h).get("O", 0.0)))
        edges, xs, stocks = economy_graph(stock0, flows, periods)
        inflow = net_inflow(edges, xs)
        worst["inside"] = max(worst["inside"], max(abs(v) for kk, v in inflow.items() if kk != "O"))
        q_edges = [(label_of(u), label_of(v)) for (u, v) in edges if label_of(u) != label_of(v)]
        q_flows = [x for (u, v), x in zip(edges, xs) if label_of(u) != label_of(v)]
        worst["quotient"] = max(worst["quotient"],
                                max(abs(v) for v in net_inflow(q_edges, q_flows).values()))
        for t in range(1, periods + 1):
            n_periods += 1
            tot = {}
            for (tt, kind, payer, payee, inst, x) in flows:
                if tt == t:
                    tot[kind] = tot.get(kind, 0.0) + x
            g = tot.get
            wages, c_w, c_k, inv = g("wage", 0.0), g("cons_w", 0.0), g("cons_k", 0.0), g("inv", 0.0)
            gov, tax_w, tax_k = g("gov", 0.0), g("tax_w", 0.0), g("tax_k", 0.0)
            exports, imports = g("exp", 0.0), g("imp", 0.0)
            taxes = tax_w + tax_k
            profits = (c_w + c_k + inv + gov + exports) - wages - imports - tax_k
            lending = {b: sum(stocks[t][(a, i)] - stocks[t - 1][(a, i)]
                              for a in agents for i in ("m", "b") if BLOCK[a[0]] == b)
                       for b in ("W", "K", "R")}
            s_w = lending["W"]
            worst["workers"] = max(worst["workers"], abs(s_w - (wages - c_w - tax_w)))
            worst["rest"] = max(worst["rest"], abs(lending["R"] - (imports - exports)))
            worst["capitalists"] = max(worst["capitalists"],
                                       abs(lending["K"] - (profits - c_k - inv)))
            worst["sum"] = max(worst["sum"], abs(sum(lending.values()) + (taxes - gov)))
            rhs = c_k + inv + (gov - taxes) + (exports - imports) - s_w
            worst["kalecki"] = max(worst["kalecki"], abs(profits - rhs))
            if closed:
                worst["closed"] = max(worst["closed"], abs(profits - (c_k + inv)))
    ok = all(v < TOL for v in worst.values())
    detail = ("%d random economies, %d of them closed with workers spending what they earn, "
              "%d periods in all, with workers, capitalists, firms and the rest of the world "
              "holding money and bills and the government as the outside node. Kirchhoff's law "
              "holds at every private node by construction and, without being imposed, at the "
              "outside node on the run cut at every date. The quotient by block and date "
              "carries a circulation. Period by period, each block's net lending read from its "
              "stocks equals its surplus on the flows that cross into it: S_w for workers, "
              "M - X for the rest of the world, P - C_k - I for capitalists with their firms, "
              "with P read from the firms' income statement; with T - G for the government the "
              "four sum to zero; P = C_k + I + (G - T) + (X - M) - S_w; and in the closed "
              "economies P = C_k + I. All within %g"
              % (n_econ, n_closed, n_periods, TOL))
    printed = ["worst residuals: " + ", ".join("%s %.3e" % kv for kv in worst.items())]
    report = {"economies": n_econ, "closed": n_closed, "periods": n_periods,
              "identities_below": TOL}
    return ok, detail, report, printed


# ---------------------------------------------------------------------- main


def main():
    rng = np.random.default_rng(SEED)
    results = [
        ("B65-6", "known_answer",
         "Model SIM written as a flow on Gamma: Kirchhoff's law every period, the redundant "
         "equation at the outside node, and the stationary state", check_sim()),
        ("B65-7a", "instrument",
         "Proposition 9.0 and Theorem 9 on random graphs", check_a(rng)),
        ("B65-7b", "instrument",
         "Lemma 9.1 on random partitions", check_b(rng)),
        ("B65-7c", "instrument",
         "Theorem 10 and Corollary 10.2 on production graphs", check_c(rng)),
        ("B65-7d", "instrument",
         "Corollary 10.1 on random economies, period by period", check_d(rng)),
    ]
    mapping = {"B65-6": "read back -> PASS; not read back -> FAIL, and the code is fixed first",
               "B65-7": "every check holds -> PASS; any check fails -> FAIL, and the code is fixed"}
    print("=" * 78)
    print("B65-6 and B65-7: known answer and structural checks for docs/b65_post_keynesian.md")
    print("=" * 78)
    for name, text in mapping.items():
        print("  states to verdicts, %s: %s" % (name, text))
    criteria, report = [], {}
    for name, kind, statement, (ok, detail, rep, printed) in results:
        print("\n%s  %s  [%s]\n  %s\n  %s" % (name, "PASS" if ok else "FAIL", kind, statement,
                                             detail))
        for line in printed:
            print("    " + line)
        criteria.append({"name": name, "kind": kind, "passed": bool(ok),
                         "statement": statement, "detail": detail})
        report[name] = rep
    rec = {
        "stage": "B65",
        "config": {
            "seed": SEED, "tol": TOL, "tol_cycle": TOL_CYCLE, "tol_price": TOL_PRICE,
            "tol_steady": TOL_STEADY, "tol_path": TOL_PATH, "generic_floor": GENERIC_FLOOR,
            "image_tol": IMAGE_TOL,
            "sim": SIM, "sim_periods": SIM_PERIODS, "sim_steady": SIM_STEADY,
            "sim_rank_at": list(SIM_RANK_AT), "sim_show": list(SIM_SHOW),
            "sim_ratio_upto": SIM_RATIO_UPTO, "sim_digits": SIM_DIGITS,
            "n_graphs": N_GRAPHS, "nodes": list(NODES), "edge_p": list(EDGE_P),
            "pieces_share": PIECES_SHARE, "x_per_graph": X_PER_GRAPH,
            "n_partitions": N_PARTITIONS, "part_nodes": list(PART_NODES),
            "blocks": list(BLOCKS), "n_production": N_PRODUCTION, "mu_span": MU_SPAN,
            "entry_every": ENTRY_EVERY, "bisection_steps": BISECTION_STEPS,
            "n_firms": list(N_FIRMS), "n_economies": N_ECONOMIES,
            "closed_share": CLOSED_SHARE, "max_periods": MAX_PERIODS,
        },
        "mapping": mapping,
        "criteria": criteria,
        "report": report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    passed = all(c["passed"] for c in criteria)
    print("\n  all five pass: %s\n  record: results/%s" % (passed, OUT.name))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
