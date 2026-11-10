"""B136: adding a channel, on the price side (B103 to B105) and on the money
side (A45), is one rank-one update.

B103's Theorem 41 moves the potentials by ``w D / (1 + w R) L^+ b`` when a
relation is added, with ``R`` the effective resistance. A45 takes the
derivative of the stationary split of money as ``Z (dB) pi``. On A45's map,
adding or removing one spending route changes the block by exactly one outer
product ``u v'``: rank at most one, and rank one unless a factor is zero (a
payer the wage step leaves with nothing has ``v = 0``, and its route changes
nothing). So the money side has an exact finite step of the same shape, with
the chain's fundamental matrix ``Z`` in place of ``L^+``.

**Theorem 44.** ``B`` with ``l B = l``, eigenvalue one simple, ``B pi = pi``,
``l pi = 1``, ``Z = (I - B + pi l)^-1``, and an action ``B -> B + u v'`` with
``l u = 0``.

1. ``pi' = pi + (v'pi) / (1 - v'Z u) * Z u``. The first-order term is A45's.
2. For a rerouting at ``k`` of its destination mix ``r`` towards ``j``,
   ``(Z (e_j - r))_i = pi_i (m(r -> i) - m(j -> i))``, ``m`` the mean first
   passage time, on an irreducible nonnegative chain: every stationary share
   positive and every passage time finite. On a reducible chain a transient
   node has share zero and an infinite passage time, the right side has no
   value there, and the move is read from ``Z`` by part 1.
3. On the random walk of a weighted undirected graph,
   ``m(a -> b) + m(b -> a) = vol R_ab`` and
   ``m(a -> b) = 1/2 sum_x d_x (R_ab + R_bx - R_ax)``, ``R`` B103's resistance.
4. On an irreducible nonnegative chain, if ``g`` is a gate of a set ``S``
   (every way into ``S`` from outside passes ``g``) and ``j`` and the support
   of ``r`` lie outside ``S``, every node of ``S`` moves by the same relative
   amount as ``g``.
5. ``1 - v'Z u = det(I - B' + pi l) / det(I - B + pi l)``. For one column
   changed on an irreducible chain it never vanishes: every closed class of the
   new chain holds ``k``. A rerouting that closes a set holding ``k`` sends all
   of the stationary split into it. Singularity takes a change on both sides,
   as when a relation between two parts is removed both ways.

Parts 1, 2, 3 and 5's first clause are Sherman and Morrison (1950), Kemeny and
Snell (1960), Chandra et al. (1989) and Tetali (1991), and the matrix
determinant lemma; they are cited. Block one checks the implementation of all
five on synthetic chains and on B103's own graphs. Block two reads A45's
carriers.

Run from the repository root with the project's virtual environment:

    python experiments/b136_channel_bridge.py --selftest
    python experiments/b136_channel_bridge.py --run --no-write
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

#: B103's generator, incidence and fit, imported rather than restated.
import b103_time_reachability as B103  # noqa: E402

CLOSED = True
RECORD = ROOT / "results" / "b136_channel_bridge.json"
SEED = 136
TOL = 1e-9

SIZES = (5, 8, 12, 20, 32, 45, 60)
CHAINS = 200
GRAPH_SIZES = (8, 16, 32)
GRAPHS_PER_SIZE = 30
GATES = 60


# --------------------------------------------------------------------------
# chains


def random_chain(rng, n: int) -> np.ndarray:
    """A nonnegative column-stochastic chain: column ``x`` is where a unit at
    ``x`` goes. Two to five random destinations and a cycle ``x -> x+1`` keep
    it irreducible."""
    B = np.zeros((n, n))
    for x in range(n):
        k = int(rng.integers(2, min(5, n - 1) + 1))
        to = rng.choice(n, size=k, replace=False)
        B[to, x] += rng.uniform(0.1, 1.0, size=k)
        B[(x + 1) % n, x] += rng.uniform(0.1, 1.0)
    return B / B.sum(axis=0, keepdims=True)


def stationary(B: np.ndarray) -> np.ndarray:
    n = B.shape[0]
    lhs = np.vstack([B - np.eye(n), np.ones((1, n))])
    rhs = np.zeros(n + 1)
    rhs[-1] = 1.0
    return np.linalg.lstsq(lhs, rhs, rcond=None)[0]


def fundamental(B: np.ndarray, pi: np.ndarray, fault: str | None = None
                ) -> np.ndarray:
    n = B.shape[0]
    if fault == "pinv":
        return np.linalg.pinv(np.eye(n) - B)
    return np.linalg.inv(np.eye(n) - B + np.outer(pi, np.ones(n)))


def exact_update(B, pi, Z, u, v, fault: str | None = None) -> np.ndarray:
    zu = Z @ u
    scale = float(v @ pi)
    if fault == "wrong_scalar":
        scale = float(pi[int(np.argmax(u))])
    denom = 1.0 - float(v @ zu)
    if fault == "no_denominator":
        denom = 1.0
    return pi + scale / denom * zu


def reroute(B: np.ndarray, k: int, j: int, delta: float):
    """Move ``delta`` of ``k``'s outflow to ``j``: ``u = delta (e_j - r)``,
    ``v = e_k``."""
    n = B.shape[0]
    r = B[:, k].copy()
    u = delta * (np.eye(n)[j] - r)
    v = np.eye(n)[k]
    return u, v, r


def hitting(B: np.ndarray, i: int, fault: str | None = None) -> np.ndarray:
    """Mean first passage times ``m(x -> i)`` for every ``x``, ``m(i -> i) = 0``,
    solved on their own: ``P(x -> y) = B[y, x]``."""
    n = B.shape[0]
    P = B if fault == "transpose" else B.T
    idx = [x for x in range(n) if x != i]
    m = np.zeros(n)
    m[idx] = np.linalg.solve(np.eye(n - 1) - P[np.ix_(idx, idx)],
                             np.ones(n - 1))
    if fault == "return_time":
        pi = stationary(B)
        m[i] = 1.0 / pi[i]
    return m


def passage_matrix(B, fault=None) -> np.ndarray:
    """``M[x, i] = m(x -> i)``."""
    return np.column_stack([hitting(B, i, fault) for i in range(B.shape[0])])


# --------------------------------------------------------------------------
# B136-1, B136-2: the exact step and the first-passage form


def chain_rows(seed=SEED, count=CHAINS, fault=None) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(count):
        n = SIZES[c % len(SIZES)]
        B = random_chain(rng, n)
        pi = stationary(B)
        Z = fundamental(B, pi, fault if fault == "pinv" else None)
        k, j = int(rng.integers(n)), int(rng.integers(n))
        while j == k:
            j = int(rng.integers(n))
        delta = 1.0 if c % 5 == 0 else float(rng.uniform(0.02, 1.0))
        u, v, r = reroute(B, k, j, delta)
        B2 = B + np.outer(u, v)
        pi2 = stationary(B2)
        step = exact_update(B, pi, Z, u, v,
                            fault if fault in ("no_denominator",
                                               "wrong_scalar") else None)
        z = Z @ (np.eye(n)[j] - r)
        M = passage_matrix(B, fault if fault in ("return_time", "transpose")
                           else None)
        passage = pi * (r @ M - M[j])
        det_ratio = (np.linalg.det(np.eye(n) - B2 + np.outer(pi, np.ones(n)))
                     / np.linalg.det(np.eye(n) - B + np.outer(pi, np.ones(n))))
        denom = 1.0 - float(v @ Z @ u)
        if fault == "plus_denominator":
            denom = 1.0 + float(v @ Z @ u)
        rows.append({"n": n, "k": k, "j": j, "delta": delta,
                     "step_gap": float(np.abs(step - pi2).max()),
                     "passage_gap": float(np.abs(z - passage).max()),
                     "det_gap": abs(denom - det_ratio),
                     "denom": denom, "floor": float(np.abs(B2 @ pi2 - pi2).max())})
    return rows


def reducible_example(fault: str | None = None) -> dict:
    """The scope of parts 1 and 2 on two nodes. ``B = [[1, 1/2], [0, 1/2]]`` is
    nonnegative and reducible with eigenvalue one simple: node 1 is transient,
    ``pi = (1, 0)``. A quarter of node 0's outflow sent to node 1 gives
    ``pi' = (2/3, 1/3)`` and denominator ``3/2``. The exact step returns it.
    The first-passage form has no value at node 1: ``m(0 -> 1)`` is infinite
    (the passage system is singular) and ``pi_1`` is zero."""
    B = np.array([[1.0, 0.5], [0.0, 0.5]])
    pi = stationary(B)
    Z = fundamental(B, pi, fault if fault == "pinv" else None)
    u, v, _ = reroute(B, 0, 1, 0.25)
    step = exact_update(B, pi, Z, u, v,
                        fault if fault in ("no_denominator", "wrong_scalar")
                        else None)
    pi2 = stationary(B + np.outer(u, v))
    return {"pi": [float(x) for x in pi], "pi_new": [float(x) for x in pi2],
            "step_gap": float(np.abs(step - pi2).max()),
            "known_gap": max(float(np.abs(pi2 - np.array([2.0 / 3.0, 1.0 / 3.0])).max()),
                             float(np.abs(pi - np.array([1.0, 0.0])).max())),
            "denom": 1.0 - float(v @ Z @ u),
            # the system for m(0 -> 1) is (1 - P(0 -> 0)) m = 1
            "passage_system": float(1.0 - B[0, 0])}


def _worst(values) -> float:
    """The largest of the values. A missing or non-finite one counts as
    infinite, so it fails a bound wherever it sits in the list."""
    values = list(values)
    if not values:
        return math.inf
    return max(float(x) if x is not None and math.isfinite(x) else math.inf
               for x in values)


def criterion_step(rows, example=None) -> dict:
    worst = _worst(r["step_gap"] for r in rows)
    ex = reducible_example() if example is None else example
    ex_ok = (ex["step_gap"] <= TOL and ex["known_gap"] <= TOL
             and abs(ex["denom"] - 1.5) <= TOL and ex["passage_system"] == 0.0)
    return {"name": "B136-1  the exact finite step: pi' = pi + (v'pi)/(1 - v'Zu) Zu "
                    "against the re-solved stationary vector",
            "kind": "instrument", "passed": bool(worst <= TOL and ex_ok),
            "detail": (f"{len(rows)} chains of {SIZES[0]} to {SIZES[-1]} nodes, "
                       f"one in five rerouted whole, largest node gap "
                       f"{worst:.1e} (tolerance {TOL:g}); on the reducible two-node "
                       f"chain, where node 1 is transient and the first-passage "
                       f"form has no value, the step gives "
                       f"({ex['pi_new'][0]:.4f}, {ex['pi_new'][1]:.4f}), gap "
                       f"{max(ex['step_gap'], ex['known_gap']):.1e}, denominator "
                       f"{ex['denom']:.4f}")}


def criterion_passage(rows) -> dict:
    worst = _worst(r["passage_gap"] for r in rows)
    return {"name": "B136-2  the first-passage form on irreducible chains: "
                    "(Z(e_j - r))_i = pi_i (m(r->i) - m(j->i)), passage times "
                    "solved on their own",
            "kind": "instrument", "passed": bool(worst <= TOL),
            "detail": (f"{len(rows)} chains, largest gap {worst:.1e} "
                       f"(tolerance {TOL:g})")}


# --------------------------------------------------------------------------
# B136-3: the reversible limit on B103's graphs


def graph_rows(seed=SEED, fault=None) -> list[dict]:
    rng = np.random.default_rng(seed + 1)
    rows = []
    for n in GRAPH_SIZES:
        for _ in range(GRAPHS_PER_SIZE):
            edges, und = B103.random_connected(rng, n, 3.0 / n)
            w = np.exp(rng.normal(0.0, 1.0, len(edges)))
            W = np.zeros((n, n))
            for (a, b), we in zip(edges, w):
                W[a, b] += we
                W[b, a] += we
            d = W.sum(axis=0)
            walk = W / d[None, :]
            _, _, L, Lp = B103.fit(n, edges,
                                   np.ones(len(edges)) if fault == "unweighted"
                                   else w, np.zeros(len(edges)))
            R = np.array([[float(B103.unit(n, a, b) @ Lp @ B103.unit(n, a, b))
                           for b in range(n)] for a in range(n)])
            M = passage_matrix(walk)
            vol = float(w.sum()) if fault == "vol_edges" else float(d.sum())
            commute = float(np.abs(M + M.T - vol * R).max())
            T = np.zeros((n, n))
            for a in range(n):
                for b in range(n):
                    T[a, b] = 0.5 * float(np.sum(d * (R[a, b] + R[b] - R[a])))
            tet = float(np.abs(M - T).max())
            # the rerouting's direction written in resistances
            pi = stationary(walk)
            Z = fundamental(walk, pi)
            k = int(rng.integers(n))
            j = int(rng.integers(n))
            while j == k:
                j = int(rng.integers(n))
            r = walk[:, k]
            z = Z @ (np.eye(n)[j] - r)
            in_R = pi * (r @ T - T[j])
            scale = max(1.0, float(np.abs(M).max()))
            rows.append({"n": n, "commute_gap": commute / scale,
                         "tetali_gap": tet / scale,
                         "direction_gap": float(np.abs(z - in_R).max()),
                         "reversible_gap": float(np.abs(walk * pi[None, :]
                                                        - (walk * pi[None, :]).T
                                                        ).max())})
    return rows


def criterion_reversible(rows) -> dict:
    worst = max(max(r["commute_gap"], r["tetali_gap"], r["direction_gap"])
                for r in rows)
    return {"name": "B136-3  the reversible limit: on B103's weighted graphs, "
                    "commute time is vol times B103's resistance, Tetali's form "
                    "holds, and the rerouting's direction is written in resistances",
            "kind": "instrument", "passed": bool(worst <= TOL),
            "detail": (f"{len(rows)} graphs of {GRAPH_SIZES[0]} to "
                       f"{GRAPH_SIZES[-1]} nodes, largest gap {worst:.1e} "
                       f"relative to the largest passage time "
                       f"(tolerance {TOL:g})")}


# --------------------------------------------------------------------------
# B136-4: the gate


def gated_chain(rng, n_out: int, n_set: int, back_door: bool) -> tuple:
    """Outside nodes route among the outside and the gate; the gate routes to
    the outside and into the set; the set routes anywhere. With
    ``back_door`` one outside node also routes into the set directly."""
    n = n_out + 1 + n_set
    g = n_out
    out = list(range(n_out))
    S = list(range(n_out + 1, n))
    B = np.zeros((n, n))
    for x in out:
        to = rng.choice(out + [g], size=min(3, n_out), replace=False)
        B[to, x] += rng.uniform(0.1, 1.0, size=to.size)
        B[(x + 1) % (n_out + 1), x] += rng.uniform(0.1, 1.0)
    B[rng.choice(out, size=2, replace=False), g] += rng.uniform(0.1, 1.0, 2)
    B[S[0], g] += rng.uniform(0.1, 1.0)
    for a, x in enumerate(S):
        to = rng.choice(S + out + [g], size=3, replace=False)
        B[to, x] += rng.uniform(0.1, 1.0, size=3)
        B[S[(a + 1) % n_set] if a + 1 < n_set else out[0], x] += rng.uniform(0.1, 1.0)
    door = None
    if back_door:
        door = out[int(rng.integers(n_out))]
        B[S[-1], door] += rng.uniform(0.5, 1.0)
    return B / B.sum(axis=0, keepdims=True), g, out, S, door


def gate_rows(seed=SEED, count=GATES) -> list[dict]:
    rng = np.random.default_rng(seed + 2)
    rows = []
    for c in range(count):
        back = c % 2 == 1
        B, g, out, S, door = gated_chain(rng, int(rng.integers(6, 20)),
                                         int(rng.integers(3, 9)), back)
        pi = stationary(B)
        Z = fundamental(B, pi)
        k = int(rng.choice(out)) if door is None else door
        choices = [x for x in out if x != k]
        j = int(rng.choice(choices))
        r = B[:, k]
        if door is None and np.any(r[S] > 0):
            raise AssertionError("an outside node routes into the set")
        rel = (Z @ (np.eye(B.shape[0])[j] - r)) / pi
        group = rel[S + [g]]
        rows.append({"back_door": back,
                     "spread": float(group.max() - group.min()),
                     "scale": max(1.0, float(np.abs(group).max()))})
    return rows


def criterion_gate(rows, spread_gate=TOL, spread_door=1e-6) -> dict:
    gated = [r["spread"] / r["scale"] for r in rows if not r["back_door"]]
    doors = [r["spread"] / r["scale"] for r in rows if r["back_door"]]
    ok = (bool(gated) and bool(doors) and max(gated) <= spread_gate
          and min(doors) > spread_door)
    return {"name": "B136-4  behind a gate every node moves by the gate's relative "
                    "amount, and a back door breaks it",
            "kind": "instrument", "passed": bool(ok),
            "detail": (f"{len(gated)} gated chains, largest relative spread "
                       f"{max(gated):.1e} (bound {spread_gate:g}); {len(doors)} "
                       f"with a back door, least spread {min(doors):.1e} "
                       f"(must exceed {spread_door:g})")}


# --------------------------------------------------------------------------
# B136-5: the denominator


def closing_rows(seed=SEED, count=40) -> list[dict]:
    """A set ``T`` whose only way out is one route of ``k``; rerouting that
    route into ``T`` closes it. And the two-sided case: two parts joined by
    one relation each way, both removed."""
    rng = np.random.default_rng(seed + 3)
    rows = []
    for c in range(count):
        nt, no = int(rng.integers(3, 10)), int(rng.integers(3, 10))
        n = nt + no
        T = list(range(nt))
        O = list(range(nt, n))
        B = np.zeros((n, n))
        for part in (T, O):
            for a, x in enumerate(part):
                to = rng.choice(part, size=min(3, len(part)), replace=False)
                B[to, x] += rng.uniform(0.1, 1.0, size=to.size)
                B[part[(a + 1) % len(part)], x] += rng.uniform(0.1, 1.0)
        k = T[-1]
        exit_to = O[0]
        B[exit_to, k] += rng.uniform(0.5, 1.0)
        entry_from = O[-1]
        B[T[0], entry_from] += rng.uniform(0.5, 1.0)
        B = B / B.sum(axis=0, keepdims=True)
        pi = stationary(B)
        Z = fundamental(B, pi)
        # one side: k's route out goes to T[0] instead
        share = B[exit_to, k]
        u = share * (np.eye(n)[T[0]] - np.eye(n)[exit_to])
        v = np.eye(n)[k]
        denom = 1.0 - float(v @ Z @ u)
        pi2 = exact_update(B, pi, Z, u, v)
        # both sides: also O's route into T goes back into O
        B2 = B + np.outer(u, v)
        s2 = B2[T[0], entry_from]
        B3 = B2.copy()
        B3[T[0], entry_from] -= s2
        B3[O[0], entry_from] += s2
        smin = float(np.linalg.svd(np.eye(n) - B3 + np.outer(pi, np.ones(n)),
                                   compute_uv=False).min())
        rows.append({"denom": denom,
                     "outside_after": float(np.abs(pi2[O]).max()),
                     "two_sided_smin": smin})
    return rows


def criterion_denominator(chain, closing) -> dict:
    det_worst = max(r["det_gap"] for r in chain)
    least = min(abs(r["denom"]) for r in closing)
    outside = max(r["outside_after"] for r in closing)
    two = max(r["two_sided_smin"] for r in closing)
    ok = (det_worst <= TOL and least > 1e-6 and outside <= 1e-12
          and two <= 1e-12)
    return {"name": "B136-5  the denominator is the determinant ratio; one column "
                    "changed never makes it vanish, a rerouting that closes a set "
                    "sends the whole split into it, and a change on both sides is "
                    "singular",
            "kind": "instrument", "passed": bool(ok),
            "detail": (f"determinant ratio on {len(chain)} chains, largest gap "
                       f"{det_worst:.1e}; {len(closing)} closing reroutes, least "
                       f"|denominator| {least:.2e}, largest share left outside "
                       f"{outside:.1e}; removed both ways, largest least singular "
                       f"value {two:.1e}")}



# --------------------------------------------------------------------------
# block two: A45's carriers


def _a45():
    """A45's builder, parts and derivative, imported on first use so that
    block one runs without A44's and A41's modules."""
    import a45_duration_levers as A45
    return A45


ADD_PER_PAIR = 5
CUT_PER_PAIR = 3
SOURCE_CLASSES = ("l1", "mid", "earners")
DEST_CLASSES = ("l1", "mid", "earners", "unreached")
EDGE_VARIANTS = ("upward out-degree 4", "f2i 10", "f2i 60")
TOL_RANK = 1e-12


class Carrier:
    """One of A45's default carriers, with what the rank-one factors need."""

    def __init__(self, parts, fault: str | None = None) -> None:
        A45 = _a45()
        self.A45 = A45
        self.parts = parts
        self.fault = fault
        self.builder = A45.FieldBuilder()
        self.ell = A45.mass_functional(parts)
        self.block = self.builder.block(parts)
        self.pi = A45.stationary(self.block, self.ell)
        m = self.block.shape[0]
        self.Z = np.linalg.inv(np.eye(m) - self.block + np.outer(self.pi, self.ell))
        self.live = np.asarray(parts.live)
        self.pos = {int(node): k for k, node in enumerate(self.live[:-1])}
        # the wage-and-bill step: the builder with nothing spent, so the
        # spending step is the identity
        self.step = self.builder.matrix(parts, pbar=np.zeros(parts.n))[:parts.n, :]
        self.q = A45.spend_rates(parts, parts.pbar)
        self.routes = A45.routes_of(parts)
        self.classes = A45.block_positions(parts)

    def factors(self, k: int, route0_new: np.ndarray):
        """``u`` and ``v`` of the change to node ``k``'s routes, from the parts."""
        n = self.parts.n
        new = route0_new[k] * self.parts.alive
        s = new.sum()
        r_new = new / s if self.fault != "no_renormalize" else new
        du = self.q[k] * (r_new - self.routes[k])
        u = np.zeros(self.live.size)
        u[:-1] = du[self.live[:-1]]
        if self.fault == "unit_v":
            v = np.zeros(self.live.size)
            v[self.pos[k]] = 1.0
        else:
            v = self.step[k, self.live]
        return u, v

    def rebuilt(self, route0_new: np.ndarray) -> np.ndarray:
        import dataclasses
        return self.builder.block(dataclasses.replace(self.parts, route0=route0_new))

    def shares(self, vec: np.ndarray) -> dict:
        return self.A45.class_sums(self.parts, vec, floor=True)


def channel_list(car: Carrier, rng) -> list[tuple]:
    """(kind, k, j) for new routes and cuts between every source and
    destination class, on trading nodes."""
    parts = car.parts
    route0 = parts.route0
    alive = parts.alive
    lab = parts.labels
    out = []
    for sc in SOURCE_CLASSES:
        srcs = [k for k in np.flatnonzero((lab == sc) & alive & parts.has_out)
                if (route0[k] * alive).sum() > 0]
        for dc in DEST_CLASSES:
            dests = np.flatnonzero((lab == dc) & alive)
            adds = [(k, j) for k in srcs for j in dests
                    if j != k and route0[k, j] == 0]
            cuts = [(k, j) for k in srcs for j in dests
                    if route0[k, j] > 0 and ((route0[k] > 0) & alive).sum() >= 2]
            for pool, kind, count in ((adds, "add", ADD_PER_PAIR),
                                      (cuts, "cut", CUT_PER_PAIR)):
                if pool:
                    pick = rng.choice(len(pool), size=min(count, len(pool)),
                                      replace=False)
                    out += [(kind, int(pool[i][0]), int(pool[i][1])) for i in pick]
    return out


def channel_row(car: Carrier, kind: str, k: int, j: int) -> dict:
    parts = car.parts
    route0_new = parts.route0.copy()
    if kind == "add":
        row_k = parts.route0[k][parts.route0[k] > 0]
        route0_new[k, j] = float(row_k.mean())
    else:
        route0_new[k, j] = 0.0
    u, v = car.factors(k, route0_new)
    new_block = car.rebuilt(route0_new)
    d_block = new_block - car.block
    rank_gap = float(np.abs(d_block - np.outer(u, v)).max())
    # an outer product has rank one unless a factor is zero; then the change
    # is the zero matrix and has no second singular value to compare
    zero = not bool(d_block.any())
    sv = np.linalg.svd(d_block, compute_uv=False)
    zu = car.Z @ u
    denom = 1.0 - float(v @ zu)
    scale = float(v @ car.pi)
    step = car.pi + scale / denom * zu
    resolved = car.A45.stationary(new_block, car.ell)
    first = car.A45.Derivative().of(car.block, np.outer(u, v), car.pi, car.ell)
    before, after = car.shares(car.pi), car.shares(resolved)
    kk, jj = car.pos[k], car.pos[j]
    row = {"seed": parts.seed, "wall": parts.wall, "kind": kind,
           "src": str(parts.labels[k]), "dst": str(parts.labels[j]),
           "rank_gap": rank_gap,
           "zero_change": zero,
           "u_max": float(np.abs(u).max()), "v_max": float(np.abs(v).max()),
           "second_sv": None if zero else float(sv[1] / sv[0]),
           "step_gap": float(np.abs(step - resolved).max()),
           "first_gap": float(np.abs(first - scale * zu).max()),
           "denom": denom,
           "src_rel": (resolved[kk] - car.pi[kk]) / car.pi[kk] if car.pi[kk] > 1e-12
           else float("nan"),
           "dst_move": float(resolved[jj] - car.pi[jj])}
    for c in ("l1", "mid", "earners", "unreached"):
        row[f"d_{c}"] = after[c] - before[c]
    return row


def carrier_list(seeds=None, walls=None):
    A45 = _a45()
    seeds = A45.SEEDS if seeds is None else seeds
    walls = A45.WALLS if walls is None else walls
    return [A45.parts_of(A45.record_path(s, w)) for s in seeds for w in walls]


def channel_rows(carriers, fault=None, seed=SEED) -> list[dict]:
    rng = np.random.default_rng(seed + 10)
    rows = []
    for parts in carriers:
        car = Carrier(parts, fault)
        for kind, k, j in channel_list(car, rng):
            rows.append(channel_row(car, kind, k, j))
    return rows


def criterion_carrier(rows) -> dict:
    zero = [r for r in rows if r["zero_change"]]
    live = [r for r in rows if not r["zero_change"]]
    rank = _worst(r["rank_gap"] for r in rows)
    sv2 = _worst(r["second_sv"] for r in live)
    step = _worst(r["step_gap"] for r in rows)
    first = _worst(r["first_gap"] for r in rows)
    # a change of nothing has a zero factor; a change of something has none
    factors = (all(r["u_max"] == 0.0 or r["v_max"] == 0.0 for r in zero)
               and all(r["u_max"] > 0.0 and r["v_max"] > 0.0 for r in live))
    ok = (bool(live) and factors and rank <= TOL_RANK and sv2 <= TOL_RANK
          and step <= TOL and first <= TOL_RANK)
    n_add = sum(r["kind"] == "add" for r in rows)
    z_add = sum(r["kind"] == "add" for r in zero)
    return {"name": "B136-6  on A45's map one route added or cut changes the block "
                    "by one outer product u v', v the source's row of the "
                    "wage-and-bill step: rank one, or nothing when a factor is "
                    "zero; the exact step matches the rebuilt map, and its first "
                    "order is A45's derivative",
            "kind": "instrument", "passed": bool(ok),
            "detail": (f"{len(rows)} channels ({n_add} added, {len(rows) - n_add} "
                       f"cut) on {len({(r['seed'], r['wall']) for r in rows})} "
                       f"carriers: change against u v' {rank:.1e}; {len(zero)} "
                       f"change nothing ({z_add} added, {len(zero) - z_add} cut, "
                       f"v zero on {sum(r['v_max'] == 0.0 for r in zero)}); on the "
                       f"other {len(live)} the second singular value over the "
                       f"first is {sv2:.1e} (bound {TOL_RANK:g}); exact step "
                       f"against the re-solve {step:.1e} (tolerance {TOL:g}); first "
                       f"order against A45's derivative {first:.1e}")}


# --------------------------------------------------------------------------
# B136-7: A45's exact column, by Woodbury


def woodbury_split(car: Carrier, weights: np.ndarray, fault=None) -> dict:
    """Every source whose routes the weights change contributes one outer
    product; the exact step is Woodbury's. The number of terms bounds the rank
    of the change from above and need not equal it: the terms can be
    dependent. Both are returned, the rank counted from the singular values of
    the change above ``TOL_RANK``."""
    parts = car.parts
    route0_new = parts.route0 * weights
    changed = [k for k in np.flatnonzero(parts.alive & parts.has_out)
               if not np.array_equal(route0_new[k], parts.route0[k])
               and (route0_new[k] * parts.alive).sum() > 0]
    U = np.column_stack([car.factors(k, route0_new)[0] for k in changed])
    V = np.column_stack([car.factors(k, route0_new)[1] for k in changed])
    ZU = car.Z @ U
    y = V.T @ car.pi
    if fault != "first_order":
        y = np.linalg.solve(np.eye(len(changed)) - V.T @ ZU, y)
    new = car.pi + ZU @ y
    change = car.rebuilt(route0_new) - car.block
    gap = float(np.abs(change - U @ V.T).max())
    # planted: the rank of the new map read in place of the rank of the change
    sv = np.linalg.svd(car.rebuilt(route0_new) if fault == "rank_of_map"
                       else change, compute_uv=False)
    rank = int((sv > TOL_RANK).sum())
    return {"shares": car.shares(new), "factor_count": len(changed),
            "factor_gap": gap, "operator_rank": rank,
            "rank_u": int(np.linalg.matrix_rank(U, tol=TOL_RANK)),
            "rank_v": int(np.linalg.matrix_rank(V, tol=TOL_RANK)),
            "smallest_counted_sv": float(sv[rank - 1]) if 0 < rank <= sv.size else None,
            "largest_dropped_sv": float(sv[rank]) if rank < sv.size else None}


def known_rows(fault=None, seeds=None) -> list[dict]:
    A45 = _a45()
    import json
    rec = json.loads((ROOT / "results" / "a45_duration_levers.json")
                     .read_text(encoding="utf-8"))
    want = {(r["variant"], r["seed"]): r for r in rec["variants"]
            if r["variant"] in EDGE_VARIANTS}
    moves = dict(A45.VARIANT_LEVERS)
    rows = []
    for seed in (A45.SEEDS if seeds is None else seeds):
        car = Carrier(A45.parts_of(A45.record_path(seed, 0.0)))
        for name in EDGE_VARIANTS:
            kw = A45.moved_kwargs(car.parts, moves[name])
            w = woodbury_split(car, kw["weights"], fault)
            split = w["shares"]
            r = want[(name, seed)]
            rows.append({"variant": name, "seed": seed,
                         **{k: w[k] for k in ("factor_count", "operator_rank",
                                              "rank_u", "rank_v", "factor_gap",
                                              "smallest_counted_sv",
                                              "largest_dropped_sv")},
                         "gap": max(abs(split[c] - r[f"exact_{c}"])
                                    for c in ("l1", "mid", "earners")),
                         "l1": split["l1"], "record_l1": r["exact_l1"],
                         "first_l1": r["first_l1"]})
    return rows


def criterion_known(rows) -> dict:
    gap = _worst(r["gap"] for r in rows)
    fgap = _worst(r["factor_gap"] for r in rows)
    ranks = bool(rows) and all(0 < r["operator_rank"] <= r["factor_count"]
                               for r in rows)
    ok = bool(rows) and gap <= TOL and fgap <= TOL_RANK and ranks
    span = {}
    for r in rows:
        span.setdefault(r["variant"], []).append(r)
    by = "; ".join(f"{name}: {min(x['factor_count'] for x in rs)}"
                   + (f" to {max(x['factor_count'] for x in rs)}"
                      if len({x['factor_count'] for x in rs}) > 1 else "")
                   + f" terms, rank {min(x['operator_rank'] for x in rs)}"
                   + (f" to {max(x['operator_rank'] for x in rs)}"
                      if len({x['operator_rank'] for x in rs}) > 1 else "")
                   for name, rs in span.items())
    return {"name": "B136-7  A45's exact column for its three edge-lever variants, "
                    "rebuilt as a Woodbury step from one outer-product term per "
                    "source whose routes the lever changes; the change's rank is "
                    "at most the number of terms",
            "kind": "known_answer", "passed": bool(ok),
            "detail": (f"{len(rows)} rows ({len(span)} variants, "
                       f"{len({r['seed'] for r in rows})} seeds); {by} (singular "
                       f"values above {TOL_RANK:g} counted); factors against the "
                       f"change {fgap:.1e}; class shares against A45's recorded "
                       f"exact column, largest gap {gap:.1e} (tolerance {TOL:g}, "
                       f"the record carries ten places)")}


# --------------------------------------------------------------------------
# B136-8: the readings


def one_way_share(F: np.ndarray) -> tuple[float, float, int]:
    """Off the diagonal of a flow ``F[y, x]``: the share of all flow with no
    matching flow back, the share of node pairs carrying flow one way only,
    and the number of pairs carrying any."""
    F = F.copy()
    np.fill_diagonal(F, 0.0)
    iu = np.triu_indices_from(F, k=1)
    a, b = F[iu], F.T[iu]
    tot = a + b
    live = tot > 1e-15
    return (float(np.abs(a - b)[live].sum() / tot[live].sum()),
            float(((a > 1e-15) ^ (b > 1e-15))[live].mean()), int(live.sum()))


def reversibility(car: Carrier) -> dict:
    """Detailed balance on the holdings block ``H``, the spending state left
    out, under two weights.

    ``one_way``, ``one_sided``: the flow ``H diag(h)``, ``h`` the holdings part
    of the whole map's stationary vector. With the bill column
    ``H h + b z = h``, so ``h`` is not ``H``'s own stationary vector; this is
    the holdings block's flow in the stationary state of the whole round, and
    ``whole_map_balance_gap`` is ``max |H h - h|``.

    ``one_way_own``, ``one_sided_own``: the flow ``H diag(h_H)``, ``h_H`` the
    stationary vector of ``H`` itself (``H`` is nonnegative with unit column
    sums). This is the reversibility of the holdings chain on its own.

    ``one_way`` is zero for a reversible chain and one when every flow runs
    one way."""
    H = car.block[:-1, :-1]
    h = car.pi[:-1]
    own = car.A45.stationary(H, np.ones(H.shape[0]))
    ow, os_, pairs = one_way_share(H * h[None, :])
    ow2, os2, _ = one_way_share(H * own[None, :])
    return {"seed": car.parts.seed, "wall": car.parts.wall,
            "one_way": ow, "one_sided": os_, "pairs": pairs,
            "one_way_own": ow2, "one_sided_own": os2,
            "whole_map_balance_gap": float(np.abs(H @ h - h).max()),
            "own_residual": float(np.abs(H @ own - own).max())}


def criterion_readings(rows, carriers_seen, rev=None) -> dict:
    keys = ("denom", "d_l1", "d_mid", "d_earners", "d_unreached", "dst_move")
    finite = all(np.isfinite(r[k]) for r in rows for k in keys)
    pairs = {(r["src"], r["dst"], r["kind"]) for r in rows}
    rev = [] if rev is None else rev
    rev_keys = ("one_way", "one_sided", "one_way_own", "one_sided_own",
                "whole_map_balance_gap")
    rev_ok = (len(rev) == carriers_seen
              and all(np.isfinite(r[k]) for r in rev for k in rev_keys)
              and _worst(r["own_residual"] for r in rev) <= TOL)
    ok = (bool(rows) and finite and carriers_seen > 0 and len(pairs) >= 12
          and rev_ok)
    return {"name": "B136-8  channel readings printed on every carrier: class "
                    "shares moved, the denominator, the source's own relative "
                    "move, the destination's move, and how far the carrier's "
                    "holdings block is from reversible, under the whole map's "
                    "stationary vector and under its own",
            "kind": "own_reading", "passed": bool(ok),
            "detail": (f"{len(rows)} channel rows over {len(pairs)} "
                       f"(source, destination, kind) cells on {carriers_seen} "
                       f"carriers, {'all finite' if finite else 'NaN present'}; "
                       f"reversibility read on {len(rev)} carriers"
                       + (f", the block's own stationary vector solved to "
                          f"{_worst(r['own_residual'] for r in rev):.1e}"
                          if rev else ""))}


def print_readings(rows, rev) -> None:
    ow = [r["one_way"] for r in rev]
    os_ = [r["one_sided"] for r in rev]
    print(f"\nthe carriers' holdings blocks, weights from the whole map's "
          f"stationary vector: share of flow with no flow back {min(ow):.4f} to "
          f"{max(ow):.4f} (median {np.median(ow):.4f}); node pairs with flow one "
          f"way only {min(os_):.3f} to {max(os_):.3f} (median {np.median(os_):.3f})")
    ow2 = [r["one_way_own"] for r in rev]
    os2 = [r["one_sided_own"] for r in rev]
    gap = [r["whole_map_balance_gap"] for r in rev]
    print(f"the same blocks under their own stationary vector: {min(ow2):.4f} to "
          f"{max(ow2):.4f} (median {np.median(ow2):.4f}); one way only "
          f"{min(os2):.3f} to {max(os2):.3f}; largest difference between the two "
          f"weights {max(abs(a - b) for a, b in zip(ow, ow2)):.4f}; |H h - h| "
          f"under the whole map's vector {min(gap):.2e} to {max(gap):.2e}")
    zero = [r for r in rows if r["zero_change"]]
    print(f"\nchannels that change nothing: {len(zero)} "
          f"({sum(r['kind'] == 'add' for r in zero)} added, "
          f"{sum(r['kind'] == 'cut' for r in zero)} cut), v zero on "
          f"{sum(r['v_max'] == 0.0 for r in zero)}, u zero on "
          f"{sum(r['u_max'] == 0.0 for r in zero)}; sources "
          f"{sorted({r['src'] for r in zero})}")
    print("\nR1  class shares moved per channel, medians [min, max], by source, "
          "destination and kind")
    cells = {}
    for r in rows:
        cells.setdefault((r["kind"], r["src"], r["dst"]), []).append(r)
    for key in sorted(cells):
        rs = cells[key]
        def span(k):
            vals = [r[k] for r in rs]
            return (f"{np.median(vals):+.5f} [{min(vals):+.5f}, "
                    f"{max(vals):+.5f}]")
        print(f"  {key[0]:3s} {key[1]:8s}->{key[2]:9s} n {len(rs):3d}"
              f"  l1 {span('d_l1')}  mid {span('d_mid')}"
              f"  earn {span('d_earners')}")
    print("\nR2  denominators, the source's own relative move, and the "
          "destination node's move")
    for kind in ("add", "cut"):
        rs = [r for r in rows if r["kind"] == kind]
        d = np.array([r["denom"] for r in rs])
        src = np.array([r["src_rel"] for r in rs])
        src = src[np.isfinite(src)]
        dst = np.array([r["dst_move"] for r in rs])
        print(f"  {kind}: {len(rs)} channels, denominator {d.min():.3f} to "
              f"{d.max():.3f} (median {np.median(d):.3f}), above one "
              f"{int((d > 1).sum())}; source share rose {int((src > 0).sum())},"
              f" fell {int((src < 0).sum())}; destination node rose "
              f"{int((dst > 1e-15).sum())}, fell {int((dst < -1e-15).sum())}")
    print("\nR3  channels whose own destination class lost share (added routes)")
    lost = [r for r in rows if r["kind"] == "add" and r["dst"] != "unreached"
            and r[f"d_{r['dst']}"] < -1e-12]
    print(f"  {len(lost)} of {sum(r['kind'] == 'add' for r in rows)}")
    for r in lost[:8]:
        print(f"    seed {r['seed']} wall {r['wall']} {r['src']} -> {r['dst']}:"
              f" destination class {r['d_' + r['dst']]:+.2e}, destination node "
              f"{r['dst_move']:+.2e}, denominator {r['denom']:.4f}")


def block_two(fault=None, quick=False):
    carriers = carrier_list(seeds=(0,) if quick else None,
                            walls=(0.0,) if quick else None)
    rows = channel_rows(carriers, fault)
    known = known_rows(fault if fault in ("first_order", "rank_of_map")
                       else None, seeds=(0,) if quick else None)
    rev = [reversibility(Carrier(p)) for p in carriers]
    crit = [criterion_carrier(rows), criterion_known(known),
            criterion_readings(rows, len(carriers), rev)]
    return crit, rows, known, rev


# --------------------------------------------------------------------------
# the record


def _rv(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return float(f"{x:.10g}") if math.isfinite(x) else None
    return x


def _within(value: float, tol: float):
    """A residue inside its tolerance is written as the tolerance, since its
    last digits belong to the machine; outside it, as the value."""
    return _rv(tol) if abs(value) <= tol else _rv(value)


def build_record(crit, chain, graphs, gates, closing, rows, known, rev) -> dict:
    ex = reducible_example()
    rec = {
        "stage": "B136",
        "config": {
            "seed": SEED, "tolerance": TOL, "rank_tolerance": TOL_RANK,
            "chains": {"count": CHAINS, "sizes": list(SIZES),
                       "shape": ("nonnegative column-stochastic, two to five "
                                 "random destinations per node and a cycle "
                                 "x -> x+1; one reroute in five moves the whole "
                                 "of the source's outflow")},
            "graphs": {"sizes": list(GRAPH_SIZES), "per_size": GRAPHS_PER_SIZE,
                       "generator": "b103_time_reachability.random_connected, "
                                    "extra 3/n, weights exp(N(0,1))"},
            "gates": GATES,
            "closing": ("a set whose only way out is one route of k; that "
                        "route turned back into the set; both ways: the "
                        "outside's route in turned back as well"),
            "carriers": ("a45_duration_levers.parts_of(record_path(seed, wall)),"
                         " every seed and wall, FieldBuilder main entry"),
            "channels": {"sources": list(SOURCE_CLASSES),
                         "destinations": list(DEST_CLASSES),
                         "added_per_pair": ADD_PER_PAIR,
                         "cut_per_pair": CUT_PER_PAIR,
                         "new_route_weight": "mean of the source's route weights"},
            "known_answer": {"record": "a45_duration_levers.json, variants",
                             "variants": list(EDGE_VARIANTS)},
        },
        "criteria": [{k: c[k] for k in ("name", "kind", "passed", "detail")}
                     for c in crit],
        "reducible_example": {
            "chain": "B = [[1, 1/2], [0, 1/2]], columns are where a unit goes",
            "action": "a quarter of node 0's outflow to node 1",
            # the stated values; the solved ones agree to the gap written below
            "stationary_before": [1.0, 0.0],
            "stationary_after": [_rv(2.0 / 3.0), _rv(1.0 / 3.0)],
            "denominator": 1.5,
            "gap_to_stated_values": _within(max(ex["step_gap"], ex["known_gap"],
                                                abs(ex["denom"] - 1.5)), TOL),
            "passage_0_to_1": "infinite: the passage system is 0 * m = 1"},
        "chains": [{"n": r["n"], "k": r["k"], "j": r["j"],
                    "delta": _rv(r["delta"]), "denominator": _rv(r["denom"]),
                    "step_gap": _within(r["step_gap"], TOL),
                    "passage_gap": _within(r["passage_gap"], TOL),
                    "det_gap": _within(r["det_gap"], TOL)} for r in chain],
        "graphs": [{"n": r["n"],
                    "commute_gap": _within(r["commute_gap"], TOL),
                    "tetali_gap": _within(r["tetali_gap"], TOL),
                    "direction_gap": _within(r["direction_gap"], TOL)}
                   for r in graphs],
        "gates": [{"back_door": r["back_door"],
                   "relative_spread": (_rv(r["spread"] / r["scale"])
                                       if r["back_door"] else
                                       _within(r["spread"] / r["scale"], TOL))}
                  for r in gates],
        "closing": [{"denominator": _rv(r["denom"]),
                     "outside_after": _within(r["outside_after"], 1e-12),
                     "two_sided_least_singular_value":
                         _within(r["two_sided_smin"], 1e-12)} for r in closing],
        "channels": [{"seed": r["seed"], "wall": _rv(r["wall"]),
                      "kind": r["kind"], "source": r["src"],
                      "destination": r["dst"],
                      "denominator": _rv(r["denom"]),
                      "source_relative": _rv(r["src_rel"]),
                      "destination_node": _rv(r["dst_move"]),
                      **{f"class_{c}": _rv(r[f"d_{c}"])
                         for c in ("l1", "mid", "earners", "unreached")},
                      "rank_gap": _within(r["rank_gap"], TOL_RANK),
                      "zero_change": bool(r["zero_change"]),
                      "wage_row_zero": bool(r["v_max"] == 0.0),
                      "second_singular": (None if r["zero_change"] else
                                          _within(r["second_sv"], TOL_RANK)),
                      "step_gap": _within(r["step_gap"], TOL)} for r in rows],
        "known": [{"variant": r["variant"], "seed": r["seed"],
                   "factor_count": r["factor_count"],
                   "operator_rank": r["operator_rank"],
                   "rank_u": r["rank_u"], "rank_v": r["rank_v"],
                   "smallest_counted_singular": _rv(r["smallest_counted_sv"]),
                   "largest_dropped_singular": (
                       None if r["largest_dropped_sv"] is None
                       else _within(r["largest_dropped_sv"], TOL_RANK)),
                   "l1": _rv(r["l1"]),
                   "record_exact_l1": _rv(r["record_l1"]),
                   "record_first_l1": _rv(r["first_l1"]),
                   "gap": _within(r["gap"], TOL)} for r in known],
        "reversibility": [{k: (_within(v, TOL) if k == "own_residual" else _rv(v))
                           for k, v in r.items()} for r in rev],
    }
    if not CLOSED:
        rec["diagnostic_only"] = True
        rec["diagnostic_reason"] = ("Station not closed: the readings are not "
                                    "yet written into RESULTS.md.")
    return rec


def write_record(rec: dict) -> None:
    text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    RECORD.write_text(text, encoding="utf-8", newline="\n")
    print(f"\nwrote {RECORD.name}")

# --------------------------------------------------------------------------
# the block


def block_one(fault: str | None = None, quick: bool = False) -> tuple:
    count = 40 if quick else CHAINS
    chain = chain_rows(count=count, fault=fault)
    graphs = graph_rows(fault=fault) if not quick else graph_rows(fault=fault)[:12]
    gates = gate_rows(count=20 if quick else GATES)
    closing = closing_rows(count=12 if quick else 40)
    crit = [criterion_step(chain, reducible_example(fault)),
            criterion_passage(chain),
            criterion_reversible(graphs), criterion_gate(gates),
            criterion_denominator(chain, closing)]
    return crit, chain, graphs, gates, closing


def selftest(block2: bool = False) -> bool:
    ok = True
    crit, *_ = block_one(quick=True)
    print("  clean  " + "  ".join(f"{c['name'][:6]} {c['passed']}" for c in crit))
    ok &= all(c["passed"] for c in crit)
    plan = (("no_denominator", 0), ("wrong_scalar", 0), ("pinv", 0),
            ("return_time", 1), ("transpose", 1),
            ("vol_edges", 2), ("unweighted", 2),
            ("plus_denominator", 4))
    for fault, idx in plan:
        crit, *_ = block_one(fault=fault, quick=True)
        c = crit[idx]
        print(f"  fault {fault:16s} {c['name'][:6]} fails: {not c['passed']}"
              f"  {c['detail'][:110]}")
        ok &= not c["passed"]
    # the gate criterion's own negative: judge the back-door chains as gated
    gates = gate_rows(count=20)
    swapped = [dict(r, back_door=not r["back_door"]) for r in gates]
    c = criterion_gate(swapped)
    print(f"  fault {'door_as_gate':16s} {c['name'][:6]} fails: {not c['passed']}")
    ok &= not c["passed"]
    # the reducible example alone: clean chains, the step without its denominator
    clean_chain = chain_rows(count=40)
    c = criterion_step(clean_chain, reducible_example("no_denominator"))
    print(f"  fault {'example_only':16s} {c['name'][:6]} fails: {not c['passed']}")
    ok &= not c["passed"]
    # a non-finite gap fails wherever it sits
    for where in (0, len(clean_chain) - 1):
        bad = [dict(r) for r in clean_chain]
        bad[where]["step_gap"] = float("nan")
        c = criterion_step(bad)
        print(f"  fault {'nan at ' + str(where):16s} {c['name'][:6]} fails: "
              f"{not c['passed']}")
        ok &= not c["passed"]
    if not block2:
        return bool(ok)
    crit, rows, known, rev = block_two(quick=True)
    print("  clean  " + "  ".join(f"{c['name'][:6]} {c['passed']}" for c in crit))
    ok &= all(c["passed"] for c in crit)
    for fault, idx in (("unit_v", 0), ("no_renormalize", 0), ("first_order", 1),
                       ("rank_of_map", 1)):
        crit, *_ = block_two(fault=fault, quick=True)
        c = crit[idx]
        print(f"  fault {fault:16s} {c['name'][:6]} fails: {not c['passed']}"
              f"  {c['detail'][:120]}")
        ok &= not c["passed"]
    c = criterion_readings([], 1, rev)
    print(f"  fault {'no_rows':16s} {c['name'][:6]} fails: {not c['passed']}")
    ok &= not c["passed"]
    c = criterion_readings(rows, len(rev), rev[:-1] if len(rev) > 1 else [])
    print(f"  fault {'a carrier unread':16s} {c['name'][:6]} fails: {not c['passed']}")
    ok &= not c["passed"]
    c = criterion_readings(rows, len(rev), [dict(rev[0], own_residual=1e-3)] + rev[1:])
    print(f"  fault {'own vector off':16s} {c['name'][:6]} fails: {not c['passed']}")
    ok &= not c["passed"]
    # B136-6: the zero changes and the order of the rows
    zero = [r for r in rows if r["zero_change"]]
    live = [r for r in rows if not r["zero_change"]]
    print(f"  the quick sample holds {len(zero)} zero changes and {len(live)} others")
    ok &= bool(zero) and bool(live)
    if zero and live:
        for name, order in (("zero first", zero + live), ("zero last", live + zero)):
            c = criterion_carrier(order)
            print(f"  order {name:16s} {c['name'][:6]} passes: {c['passed']}")
            ok &= c["passed"]
        for name, where in (("nan first", 0), ("nan last", len(live) - 1)):
            bad = [dict(r) for r in live]
            bad[where]["second_sv"] = float("nan")
            for order_name, order in (("zero first", zero + bad), ("zero last", bad + zero)):
                c = criterion_carrier(order)
                print(f"  fault {name + ', ' + order_name:22s} {c['name'][:6]} fails: "
                      f"{not c['passed']}")
                ok &= not c["passed"]
        bad = [dict(zero[0], zero_change=False)] + zero[1:] + live
        c = criterion_carrier(bad)
        print(f"  fault {'zero read as rank one':22s} {c['name'][:6]} fails: {not c['passed']}")
        ok &= not c["passed"]
        bad = zero + [dict(live[0], zero_change=True, second_sv=None)] + live[1:]
        c = criterion_carrier(bad)
        print(f"  fault {'rank one read as zero':22s} {c['name'][:6]} fails: {not c['passed']}")
        ok &= not c["passed"]
    return bool(ok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--block", type=int, choices=(1, 2), default=1)
    a = ap.parse_args(argv)
    if a.selftest:
        t0 = time.perf_counter()
        ok = selftest(block2=a.block >= 2)
        print(f"selftest {'passed' if ok else 'FAILED'} "
              f"({time.perf_counter() - t0:.1f} s)")
        return 0 if ok else 1
    if a.run:
        if a.block == 1 and not a.no_write:
            print("block one does not write; pass --no-write")
            return 2
        t0 = time.perf_counter()
        crit, chain, graphs, gates, closing = block_one()
        for c in crit:
            print(f"{c['name']}\n    [{c['kind']}] "
                  f"{'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
        floor = max(r["floor"] for r in chain)
        print(f"\nre-solve residual |B'pi' - pi'| largest {floor:.1e}")
        rg = [r["reversible_gap"] for r in graphs]
        print(f"B103 graphs' walks: detailed-balance gap largest {max(rg):.1e}")
        dens = np.array([r["denom"] for r in chain])
        print(f"denominators on the rerouted chains: {dens.min():.3f} to "
              f"{dens.max():.3f}, median {np.median(dens):.3f}")
        print(f"closing reroutes: denominators {min(r['denom'] for r in closing):.3f}"
              f" to {max(r['denom'] for r in closing):.3f}")
        print(f"\n{time.perf_counter() - t0:.1f} s")
        if a.block == 1:
            return 0 if all(c["passed"] for c in crit) else 1
        t1 = time.perf_counter()
        crit2, rows, known, rev = block_two()
        print()
        for c in crit2:
            print(f"{c['name']}\n    [{c['kind']}] "
                  f"{'PASS' if c['passed'] else 'FAIL'}: {c['detail']}")
        print("\nB136-7 rows: variant, seed, outer-product terms, rank of the "
              "change (of U, of V), smallest singular value counted / largest "
              "dropped, l1 by Woodbury / recorded exact / recorded first order")
        for r in known:
            dropped = r["largest_dropped_sv"]
            print(f"  {r['variant']:20s} seed {r['seed']} terms "
                  f"{r['factor_count']:3d} rank {r['operator_rank']:3d} "
                  f"({r['rank_u']:3d}, {r['rank_v']:3d})  "
                  f"{r['smallest_counted_sv']:.4f} / "
                  f"{'none' if dropped is None else format(dropped, '.1e')}"
                  f"  {r['l1']:.6f} / {r['record_l1']:.6f} / {r['first_l1']:.6f}")
        print_readings(rows, rev)
        print(f"\nblock two {time.perf_counter() - t1:.1f} s")
        if not a.no_write:
            write_record(build_record(crit + crit2, chain, graphs, gates,
                                      closing, rows, known, rev))
        return 0 if all(c["passed"] for c in crit + crit2) else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
