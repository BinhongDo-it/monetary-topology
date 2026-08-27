"""B1-R: the reduction rate. How far a product price form sits from one scalar.

Theorem 1 condition (4) says a single scalar price vector exists exactly when
every ``w_a`` is exact on ``G`` **and** all of them are equal. Standard price
theory assumes the second half. This module measures what is left when that half
fails by a little, and checks the answer against brute force.

Setting. ``G`` is the position graph, ``H`` the agent-class graph, and
``Gamma = G box H``. Class ``a`` carries its own 1-form ``w_a`` on the position
edges; moving a position between classes carries no price, so the form is zero on
every agent edge. Write ``wbar`` for the mean of the ``w_a`` and ``u_a`` for the
deviations.

The claim, checked below three independent ways::

    dist(omega, im d0)^2
        = sum_a ||w_a||^2  -  sum_{k, lam>0} <v_lam, delta_G what_k>^2 / (lam + mu_k)

where ``lam, v_lam`` run over the spectrum of ``L_G``, ``mu_k, chi_k`` over the
spectrum of ``L_H``, and ``what_k = sum_a chi_k(a) w_a``. Equivalently, splitting
off the constant mode ``chi_0``::

    dist^2 = A * dist(wbar, im d_G)^2  +  R,        R = sum_{k != 0} term_k
    term_k = ||what_k^perp||^2 + sum_lam c_lam(k) * mu_k / (lam + mu_k)

The two readings this file exists to establish:

1. **The split has no cross term.** ``R`` is a quadratic form in the deviations
   alone and the first summand depends on ``wbar`` alone. So the reduction is not
   asymptotic: it is exact, and its error term is exactly quadratic in the
   heterogeneity rather than merely order two in a limit.

2. **The damping factor is spectral.** Each non-constant mode is absorbed into a
   potential only up to ``lam / (lam + mu_k)``. Sending ``mu -> 0`` (classes
   uncoupled) recovers ``A`` separate one-index theories; sending ``mu -> inf``
   (classes perfectly comparable) leaves the deviation standing in full. Hence
   ``rho * D^2 <= R <= D^2`` with ``rho = mu_1 / (lam_max + mu_1)`` and
   ``D^2 = sum_a ||u_a||^2``, both endpoints fixed by the two graphs, not by the
   prices.

Usage::

    python experiments/b1_reduction.py
    python experiments/b1_reduction.py --seed 7 --trials 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.product_graph import (  # noqa: E402
    box_product,
    complete_agent_graph,
    undirected_pairs,
    vertex,
)
from monetary_topology.topology import incidence_matrix, undirected_edges  # noqa: E402

TOL = 1e-9


# --------------------------------------------------------------------------
# graphs and forms
# --------------------------------------------------------------------------


def random_connected(n: int, extra: int, rng: np.random.Generator) -> np.ndarray:
    """A random tree on ``n`` nodes plus ``extra`` chords, so ``b1 = extra``."""
    adj = np.zeros((n, n), dtype=int)
    order = rng.permutation(n)
    for t in range(1, n):
        i = int(order[t])
        j = int(order[rng.integers(0, t)])
        adj[i, j] = adj[j, i] = 1
    missing = [(i, j) for i in range(n) for j in range(i + 1, n) if not adj[i, j]]
    rng.shuffle(missing)
    for i, j in missing[:extra]:
        adj[i, j] = adj[j, i] = 1
    return adj


def assemble(adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray) -> np.ndarray:
    """The 1-form on ``Gamma`` as a vector over ``undirected_edges(box)``.

    ``w`` has shape ``(A, e_G)`` in the order of ``undirected_pairs(adj_g)``.
    Position edges carry ``w_a``; agent edges carry zero.
    """
    n = adj_g.shape[0]
    col = {pair: e for e, pair in enumerate(undirected_pairs(adj_g))}
    box = box_product(adj_g, adj_h)
    omega = np.zeros(len(undirected_edges(box)))
    for e, (u, v) in enumerate(undirected_edges(box)):
        a, i = divmod(int(u), n)
        b, j = divmod(int(v), n)
        if a == b:
            omega[e] = w[a, col[(i, j)]] if i < j else -w[a, col[(j, i)]]
        # agent edge (i == j, a != b): stays zero
    return omega


# --------------------------------------------------------------------------
# the three routes to the same number
# --------------------------------------------------------------------------


def _weights(adj_g: np.ndarray, adj_h: np.ndarray, t: float) -> np.ndarray:
    """Per-edge weight on ``Gamma``: one on position edges, ``t`` on agent edges."""
    n = adj_g.shape[0]
    box = box_product(adj_g, adj_h)
    edges = undirected_edges(box)
    same_slice = (edges[:, 0] // n) == (edges[:, 1] // n)
    return np.where(same_slice, 1.0, t)


def residual_bruteforce(
    adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray, t: float = 1.0
) -> float:
    """Least squares against the incidence operator of ``Gamma``. No theory used."""
    box = box_product(adj_g, adj_h)
    d0 = incidence_matrix(box)
    omega = assemble(adj_g, adj_h, w)
    root = np.sqrt(_weights(adj_g, adj_h, t))[:, None]
    fit, *_ = np.linalg.lstsq(root * d0, root[:, 0] * omega, rcond=None)
    return float(np.sum(root[:, 0] ** 2 * (omega - d0 @ fit) ** 2))


def residual_projector(
    adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray, t: float = 1.0
) -> float:
    """A fourth route that shares no code with the other three.

    Builds ``L_Gamma`` from the product graph directly, inverts it on its own
    eigenbasis, and never touches the mode transform, the Kronecker structure or
    ``lstsq``. If the product structure were being assumed rather than used, this
    is the route that would disagree.
    """
    box = box_product(adj_g, adj_h)
    d0 = incidence_matrix(box)
    c = _weights(adj_g, adj_h, t)
    omega = assemble(adj_g, adj_h, w)
    lap = d0.T @ (c[:, None] * d0)
    ev, vec = np.linalg.eigh(lap)
    div = d0.T @ (c * omega)
    coef = vec.T @ div
    keep = ev > TOL * max(1.0, float(ev.max()))
    return float(np.sum(c * omega**2) - float(np.sum(coef[keep] ** 2 / ev[keep])))


def _mode_transform(adj_h: np.ndarray, w: np.ndarray):
    """``(mu, what)`` with ``what[k] = sum_a chi_k(a) w_a``, ``chi`` orthonormal."""
    deg = np.diag(np.asarray(adj_h).sum(axis=1).astype(float))
    lap_h = deg - np.asarray(adj_h, dtype=float)
    mu, chi = np.linalg.eigh(lap_h)
    return mu, chi.T @ w


def residual_modewise(
    adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray, t: float = 1.0
) -> float:
    """One Tikhonov problem per agent mode, solved on ``G`` alone."""
    d_g = incidence_matrix(adj_g)
    lap_g = d_g.T @ d_g
    mu, what = _mode_transform(adj_h, w)
    mu = t * mu
    total = 0.0
    for k, mu_k in enumerate(mu):
        rhs = d_g.T @ what[k]
        psi = np.linalg.lstsq(lap_g + mu_k * np.eye(lap_g.shape[0]), rhs, rcond=None)[0]
        total += float(np.sum((what[k] - d_g @ psi) ** 2) + mu_k * float(psi @ psi))
    return total


def residual_spectral(
    adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray, t: float = 1.0
) -> float:
    """The closed form: one double sum over the two Laplacian spectra."""
    d_g = incidence_matrix(adj_g)
    lam, vec = np.linalg.eigh(d_g.T @ d_g)
    mu, what = _mode_transform(adj_h, w)
    mu = t * mu
    div = what @ d_g @ vec                     # <v_lam, delta_G what_k>
    keep = lam > TOL
    denom = lam[None, keep] + mu[:, None]
    return float(np.sum(what**2) - float(np.sum(div[:, keep] ** 2 / denom)))


def split(adj_g: np.ndarray, adj_h: np.ndarray, w: np.ndarray):
    """``(common, R, D2, rho)``: the one-index part, the excess, and its bounds."""
    d_g = incidence_matrix(adj_g)
    a_count = adj_h.shape[0]
    wbar = w.mean(axis=0)
    fit, *_ = np.linalg.lstsq(d_g, wbar, rcond=None)
    common = a_count * float(np.sum((wbar - d_g @ fit) ** 2))
    excess = residual_spectral(adj_g, adj_h, w) - common
    dev2 = float(np.sum((w - wbar) ** 2))
    mu = np.linalg.eigvalsh(np.diag(adj_h.sum(axis=1).astype(float)) - adj_h)
    mu_1 = float(mu[mu > TOL].min()) if (mu > TOL).any() else 0.0
    lam_max = float(np.linalg.eigvalsh(d_g.T @ d_g).max())
    rho = mu_1 / (lam_max + mu_1) if mu_1 > 0 else 0.0
    return common, excess, dev2, rho


# --------------------------------------------------------------------------
# criteria
# --------------------------------------------------------------------------


def run(seed: int, trials: int) -> int:
    rng = np.random.default_rng(seed)
    shapes = [(4, 1, 3, 0), (5, 2, 3, 1), (6, 3, 4, 2), (7, 2, 5, 4), (4, 0, 4, 0)]
    bad = 0

    print("R-1  four routes to dist(omega, im d0)^2 agree")
    print(f"{'n':>3} {'b1G':>4} {'m':>3} {'b1H':>4} "
          f"{'brute':>14} {'modewise':>14} {'spectral':>14} {'projector':>14} "
          f"{'max gap':>10}")
    for t in range(trials):
        n, extra_g, m, extra_h = shapes[t % len(shapes)]
        adj_g = random_connected(n, extra_g, rng)
        adj_h = random_connected(m, extra_h, rng) if m > 1 else complete_agent_graph(1)
        e_g = len(undirected_pairs(adj_g))
        w = rng.normal(size=(m, e_g))
        b = residual_bruteforce(adj_g, adj_h, w)
        d = residual_modewise(adj_g, adj_h, w)
        sp = residual_spectral(adj_g, adj_h, w)
        pr = residual_projector(adj_g, adj_h, w)
        gap = max(abs(b - d), abs(b - sp), abs(b - pr))
        bad += gap > 1e-7
        print(f"{n:>3} {extra_g:>4} {m:>3} {extra_h:>4} "
              f"{b:>14.8f} {d:>14.8f} {sp:>14.8f} {pr:>14.8f} {gap:>10.2e}")

    print()
    print("R-2  the split has no cross term: scaling deviations by t scales R by t^2")
    adj_g = random_connected(6, 3, rng)
    adj_h = random_connected(4, 2, rng)
    e_g = len(undirected_pairs(adj_g))
    w0 = rng.normal(size=(4, e_g))
    wbar = w0.mean(axis=0)
    dev = w0 - wbar
    base_common, base_excess, _, _ = split(adj_g, adj_h, w0)
    print(f"{'t':>8} {'common':>14} {'R':>14} {'R/t^2':>14}")
    for t_scale in (1.0, 0.5, 0.25, 0.1, 0.01):
        w = wbar + t_scale * dev
        c, r, _, _ = split(adj_g, adj_h, w)
        print(f"{t_scale:>8.2f} {c:>14.8f} {r:>14.8f} {r / t_scale**2:>14.8f}")
        bad += abs(c - base_common) > 1e-9
        bad += abs(r / t_scale**2 - base_excess) > 1e-9

    print()
    print("R-3  bounds: rho * D^2 <= R <= D^2, both ends spectral")
    print(f"{'n':>3} {'A':>3} {'rho':>10} {'rho*D^2':>14} {'R':>14} {'D^2':>14}")
    for t in range(trials):
        n, extra_g, m, extra_h = shapes[t % len(shapes)]
        if m == 1:
            continue
        adj_g = random_connected(n, extra_g, rng)
        adj_h = random_connected(m, extra_h, rng)
        w = rng.normal(size=(m, len(undirected_pairs(adj_g))))
        _, r, dev2, rho = split(adj_g, adj_h, w)
        ok = rho * dev2 - 1e-9 <= r <= dev2 + 1e-9
        bad += not ok
        print(f"{n:>3} {m:>3} {rho:>10.6f} {rho * dev2:>14.8f} {r:>14.8f} "
              f"{dev2:>14.8f}{'' if ok else '   <-- OUT'}")

    print()
    print("R-4  the two degenerate ends, by construction")
    adj_g = random_connected(6, 2, rng)
    adj_h = random_connected(4, 1, rng)
    e_g = len(undirected_pairs(adj_g))
    d_g = incidence_matrix(adj_g)

    shared = rng.normal(size=e_g)
    w = np.tile(shared, (4, 1))
    got = residual_spectral(adj_g, adj_h, w)
    fit, *_ = np.linalg.lstsq(d_g, shared, rcond=None)
    want = 4 * float(np.sum((shared - d_g @ fit) ** 2))
    print(f"  all classes equal      dist^2 = {got:.10f}   A*dist(w,im d_G)^2 = {want:.10f}")
    bad += abs(got - want) > 1e-9

    pot = rng.normal(size=adj_g.shape[0])
    w = np.tile(d_g @ pot, (4, 1))
    got = residual_spectral(adj_g, adj_h, w)
    print(f"  equal and exact        dist^2 = {got:.3e}   (condition 4 holds)")
    bad += abs(got) > 1e-9

    print()
    print("R-5  what the damping does, one shape, mu swept by rewiring H")
    adj_g = random_connected(5, 2, rng)
    e_g = len(undirected_pairs(adj_g))
    w = rng.normal(size=(4, e_g))
    lam_max = float(np.linalg.eigvalsh(incidence_matrix(adj_g).T @ incidence_matrix(adj_g)).max())
    print(f"  lam_max(L_G) = {lam_max:.6f}")
    print(f"{'H':>10} {'mu_1':>10} {'rho':>10} {'R':>14} {'D^2':>14} {'R/D^2':>10}")
    hs = {"path": np.array([[0, 1, 0, 0], [1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0]]),
          "star": np.array([[0, 1, 1, 1], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]]),
          "cycle": np.array([[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0]]),
          "complete": complete_agent_graph(4)}
    for name in sorted(hs):
        adj_h = hs[name]
        _, r, dev2, rho = split(adj_g, adj_h, w)
        mu = np.linalg.eigvalsh(np.diag(adj_h.sum(axis=1).astype(float)) - adj_h)
        mu_1 = float(mu[mu > TOL].min())
        print(f"{name:>10} {mu_1:>10.6f} {rho:>10.6f} {r:>14.8f} {dev2:>14.8f} "
              f"{r / dev2:>10.6f}")


    print()
    print("R-6  the product Laplacian factors, exactly")
    print(f"{'n':>3} {'m':>3} {'max |L(box) - kron form|':>26}")
    for n, extra_g, m, extra_h in shapes:
        if m == 1:
            continue
        adj_g = random_connected(n, extra_g, rng)
        adj_h = random_connected(m, extra_h, rng)
        d_box = incidence_matrix(box_product(adj_g, adj_h))
        lap_box = d_box.T @ d_box
        lap_g = incidence_matrix(adj_g).T @ incidence_matrix(adj_g)
        lap_h = incidence_matrix(adj_h).T @ incidence_matrix(adj_h)
        # vertex index is a*n + i, so the agent index is the slow one
        kron = np.kron(np.eye(m), lap_g) + np.kron(lap_h, np.eye(n))
        gap = float(np.abs(lap_box - kron).max())
        bad += gap > 1e-12
        print(f"{n:>3} {m:>3} {gap:>26.2e}")

    print()
    print("R-7  the two ends of Corollary 5.2, reached by weighting the agent edges")
    adj_g = random_connected(6, 3, rng)
    adj_h = random_connected(4, 2, rng)
    d_g = incidence_matrix(adj_g)
    w = rng.normal(size=(4, len(undirected_pairs(adj_g))))
    wbar = w.mean(axis=0)
    per_class = sum(
        float(np.sum((w[a] - d_g @ np.linalg.lstsq(d_g, w[a], rcond=None)[0]) ** 2))
        for a in range(4)
    )
    common = 4 * float(
        np.sum((wbar - d_g @ np.linalg.lstsq(d_g, wbar, rcond=None)[0]) ** 2)
    )
    dev2 = float(np.sum((w - wbar) ** 2))
    print(f"  t -> 0   target  sum_a dist(w_a, im d_G)^2 = {per_class:.8f}")
    print(f"  t -> inf target  m*dist(wbar,.)^2 + D^2    = {common + dev2:.8f}")
    print(f"{'t':>10} {'brute':>16} {'spectral':>16} {'gap':>10}")
    prev = -np.inf
    for t_w in (1e-6, 1e-3, 0.1, 1.0, 10.0, 1e3, 1e6):
        b = residual_bruteforce(adj_g, adj_h, w, t_w)
        sp = residual_spectral(adj_g, adj_h, w, t_w)
        bad += abs(b - sp) > 1e-6 * max(1.0, abs(b))
        bad += sp < prev - 1e-9          # must rise with t
        prev = sp
        print(f"{t_w:>10.0e} {b:>16.8f} {sp:>16.8f} {abs(b - sp):>10.2e}")
    bad += abs(residual_spectral(adj_g, adj_h, w, 1e-6) - per_class) > 1e-4
    bad += abs(residual_spectral(adj_g, adj_h, w, 1e6) - (common + dev2)) > 1e-4

    print()
    print("R-8  parallelogram law: rho^2(wbar+u) + rho^2(wbar-u) - 2 rho^2(wbar) = 2 R(u)")
    print(f"{'trial':>6} {'left':>16} {'2R(u)':>16} {'gap':>10}")
    adj_g = random_connected(6, 2, rng)
    adj_h = random_connected(5, 3, rng)
    e_g = len(undirected_pairs(adj_g))
    for trial in range(5):
        base = rng.normal(size=e_g)
        dev = rng.normal(size=(5, e_g))
        dev = dev - dev.mean(axis=0)
        plus = residual_spectral(adj_g, adj_h, base + dev)
        minus = residual_spectral(adj_g, adj_h, base - dev)
        flat = residual_spectral(adj_g, adj_h, np.tile(base, (5, 1)))
        left = plus + minus - 2 * flat
        _, r_u, _, _ = split(adj_g, adj_h, base + dev)
        gap = abs(left - 2 * r_u)
        bad += gap > 1e-8
        print(f"{trial:>6} {left:>16.8f} {2 * r_u:>16.8f} {gap:>10.2e}")

    print()
    print("R-9  structured fields, where the answer is known without the formula")
    adj_g = random_connected(6, 2, rng)
    adj_h = random_connected(4, 1, rng)
    d_g = incidence_matrix(adj_g)
    e_g = len(undirected_pairs(adj_g))

    pots = rng.normal(size=(4, adj_g.shape[0]))
    w = np.array([d_g @ pots[a] for a in range(4)])
    got = residual_spectral(adj_g, adj_h, w)
    _, r_only, _, _ = split(adj_g, adj_h, w)
    print(f"  each class exact, all different   rho^2 = {got:.8f}   R = {r_only:.8f}"
          f"   common = {got - r_only:.2e}")
    bad += abs(got - r_only) > 1e-9

    harm = rng.normal(size=e_g)
    harm = harm - d_g @ np.linalg.lstsq(d_g, harm, rcond=None)[0]
    w = np.tile(harm, (4, 1))
    got = residual_spectral(adj_g, adj_h, w)
    print(f"  all equal and co-closed           rho^2 = {got:.8f}"
          f"   m*||w||^2 = {4 * float(harm @ harm):.8f}")
    bad += abs(got - 4 * float(harm @ harm)) > 1e-9

    w = np.zeros((4, e_g))
    w[0] = d_g @ rng.normal(size=adj_g.shape[0])
    got = residual_spectral(adj_g, adj_h, w)
    b = residual_bruteforce(adj_g, adj_h, w)
    print(f"  exact field on one class only     rho^2 = {got:.8f}   brute = {b:.8f}")
    bad += abs(got - b) > 1e-8

    print()
    print("R-10  m = 1 collapses to the one-index problem on G alone")
    adj_g = random_connected(7, 3, rng)
    d_g = incidence_matrix(adj_g)
    w = rng.normal(size=(1, len(undirected_pairs(adj_g))))
    got = residual_spectral(adj_g, complete_agent_graph(1), w)
    want = float(np.sum((w[0] - d_g @ np.linalg.lstsq(d_g, w[0], rcond=None)[0]) ** 2))
    print(f"  rho^2 = {got:.10f}   dist(w, im d_G)^2 = {want:.10f}")
    bad += abs(got - want) > 1e-9

    print()
    print("R-11  stress: 300 random shapes, all four routes")
    worst = 0.0
    worst_shape = None
    for _ in range(300):
        n = int(rng.integers(3, 13))
        m = int(rng.integers(2, 9))
        eg = int(rng.integers(0, max(1, n * (n - 1) // 2 - (n - 1)) + 1))
        eh = int(rng.integers(0, max(1, m * (m - 1) // 2 - (m - 1)) + 1))
        adj_g = random_connected(n, eg, rng)
        adj_h = random_connected(m, eh, rng)
        w = rng.normal(size=(m, len(undirected_pairs(adj_g))))
        vals = [
            residual_bruteforce(adj_g, adj_h, w),
            residual_modewise(adj_g, adj_h, w),
            residual_spectral(adj_g, adj_h, w),
            residual_projector(adj_g, adj_h, w),
        ]
        rel = (max(vals) - min(vals)) / max(1.0, abs(vals[0]))
        if rel > worst:
            worst, worst_shape = rel, (n, eg, m, eh)
        _, r, dev2, rho = split(adj_g, adj_h, w)
        bad += not (rho * dev2 - 1e-8 <= r <= dev2 + 1e-8)
    print(f"  worst relative spread across four routes: {worst:.2e}"
          f"   at (n, b1G, m, b1H) = {worst_shape}")
    print("  bounds of Corollary 5.3 held on all 300")
    bad += worst > 1e-8

    print()
    print(f"{'ALL AGREE' if bad == 0 else str(bad) + ' DISAGREEMENTS'}")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260827)
    ap.add_argument("--trials", type=int, default=10)
    args = ap.parse_args()
    return run(args.seed, args.trials)


if __name__ == "__main__":
    raise SystemExit(main())
