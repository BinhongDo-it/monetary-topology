"""B29 chunk 1: can local arbitrage remove a global inconsistency?

Setting. Positions sit on a ring of n. Two positions trade iff their ring
distance is at most r, the interaction range (r=1 nearest neighbour, r=2 one
hop across, r=3 two hops across). A log price ratio lives on each edge, so the
state is a 1-chain w in R^E.

Arbitrage that an agent can actually perform is a cycle the agent can walk, so
it is bounded in length. Let V(L) be the span of every simple cycle of length at
most L. Arbitrage drives w to the orthogonal complement of V(L) inside the cycle
space, and leaves the rest untouched.

Claim under test (Theorem 7, winding form). Define the displacement map
    phi(edge i->j) = signed ring step in (-n/2, n/2],
extended linearly. On a cycle its value is a multiple of n, and winding = phi/n
is an integer. Every edge has |step| <= r, so a cycle of length L has
|phi| <= L*r; if L*r < n its winding is forced to 0. Therefore
    V(L) subset ker(winding)
which has codimension exactly 1 in the cycle space. Local arbitrage of any range
r and any horizon L with L*r < n cannot touch the winding component.

Three things get checked numerically rather than assumed:
  (1) rank(V(L)) against b1 - 1, i.e. is the containment an equality;
  (2) the fixed point of the arbitrage dynamics still has a non-zero sum around
      the ring, so the surviving object is real and not a proof artefact;
  (3) the length at which a non-zero cycle sum first appears equals ceil(n/r).

Cheap: pure linear algebra on graphs of a few dozen nodes. Results cached by
(n, r, L) because none of them change once computed.
"""
import json, os, math, itertools
import numpy as np

CACHE = os.path.join(os.path.dirname(__file__), "..", "results", "b29_locality_cache.json")


# ---------------------------------------------------------------- graph

def circulant(n, r):
    """Edges (i, j) with ring distance <= r, i < j in the listing order."""
    E = []
    for i in range(n):
        for d in range(1, r + 1):
            j = (i + d) % n
            E.append((i, j, d))          # oriented i -> j, ring step +d
    return E


def incidence(n, E):
    B = np.zeros((n, len(E)))
    for k, (i, j, d) in enumerate(E):
        B[i, k] -= 1.0
        B[j, k] += 1.0
    return B


def cycle_space_dim(n, E):
    B = incidence(n, E)
    return len(E) - np.linalg.matrix_rank(B)     # connected, so C = 1


# ------------------------------------------------- short cycle enumeration

def short_cycles(n, E, L):
    """Every simple cycle of length <= L, as vectors in R^E. Deduplicated."""
    idx = {}
    adj = {i: [] for i in range(n)}
    for k, (i, j, d) in enumerate(E):
        idx[(i, j)] = (k, +1.0)
        idx[(j, i)] = (k, -1.0)
        adj[i].append(j)
        adj[j].append(i)

    seen, out = set(), []

    def walk(start, node, path, visited):
        if len(path) >= 3 and start in adj[node]:
            edges = list(zip(path, path[1:])) + [(node, start)]
            key = frozenset(idx[e][0] for e in edges)
            if len(key) == len(edges) and key not in seen:
                seen.add(key)
                v = np.zeros(len(E))
                for e in edges:
                    k, s = idx[e]
                    v[k] += s
                out.append(v)
        if len(path) >= L:
            return
        for nb in adj[node]:
            if nb > start and nb not in visited:      # canonical: min node = start
                walk(start, nb, path + [nb], visited | {nb})

    for s in range(n):
        walk(s, s, [s], {s})
    return np.array(out) if out else np.zeros((0, len(E)))


# ------------------------------------------------------------- winding

def winding_vector(n, E):
    """phi as a covector on R^E; winding of a cycle c is (phi . c) / n."""
    return np.array([float(d) for (_, _, d) in E])


# ------------------------------------------------------ arbitrage dynamics

def arbitrage_fixed_point(w, C, tol=1e-10):
    """Project w off the span of the visible cycles C (rows).

    QR is wrong here: the short-cycle family is always rank deficient, and a
    reduced QR of a rank-deficient matrix returns columns that span more than
    the column space, so the projection removes directions no arbitrage can
    reach. The basis is taken from the SVD with a rank cut instead.
    """
    if C.shape[0] == 0:
        return w.copy()
    U, s, _ = np.linalg.svd(C.T, full_matrices=False)
    k = int((s > tol * max(1.0, s[0])).sum())
    Q = U[:, :k]
    return w - Q @ (Q.T @ w)


def ring_cycle(n, E):
    v = np.zeros(len(E))
    for k, (i, j, d) in enumerate(E):
        if d == 1:
            v[k] = 1.0
    return v


# ------------------------------------------------------------------ run

def run(n, r, L, seed=0):
    E = circulant(n, r)
    b1 = cycle_space_dim(n, E)
    C = short_cycles(n, E, L)
    rank_V = np.linalg.matrix_rank(C) if C.shape[0] else 0
    phi = winding_vector(n, E)
    max_wind = float(np.max(np.abs(C @ phi))) / n if C.shape[0] else 0.0

    rng = np.random.default_rng(seed)
    w = rng.normal(size=len(E))
    w_star = arbitrage_fixed_point(w, C)

    R = ring_cycle(n, E)
    resid_visible = float(np.max(np.abs(C @ w_star))) if C.shape[0] else 0.0
    ring_sum = float(R @ w_star)

    return dict(n=n, r=r, L=L, edges=len(E), b1=int(b1), n_short_cycles=int(C.shape[0]),
                rank_visible=int(rank_V), gap=int(b1 - rank_V),
                max_winding_of_short_cycle=max_wind,
                max_visible_cycle_sum_at_fixed_point=resid_visible,
                ring_cycle_sum_at_fixed_point=ring_sum,
                min_winding_cycle_length=math.ceil(n / r))


def first_nonzero_length(n, r, L_arb, seed=0, L_probe=None):
    """After arbitrage with horizon L_arb, at what cycle length does a non-zero
    sum first appear? Probes cycles by length."""
    E = circulant(n, r)
    C = short_cycles(n, E, L_arb)
    rng = np.random.default_rng(seed)
    w_star = arbitrage_fixed_point(rng.normal(size=len(E)), C)
    L_probe = L_probe or (math.ceil(n / r) + 1)
    rows = []
    for L in range(3, L_probe + 1):
        P = short_cycles(n, E, L)
        if P.shape[0] == 0:
            rows.append((L, 0, 0.0)); continue
        lens = np.abs(P).sum(axis=1)
        sel = P[np.isclose(lens, L)]
        m = float(np.max(np.abs(sel @ w_star))) if sel.shape[0] else 0.0
        rows.append((L, int(sel.shape[0]), m))
    return rows


def main():
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE))

    print("part 1: does local arbitrage exhaust the cycle space?")
    print(f"{'n':>4} {'r':>3} {'L':>3} {'E':>5} {'b1':>5} {'#cyc':>6} {'rank V':>7} "
          f"{'gap':>4} {'maxwind':>8} {'visible resid':>14} {'ring sum':>10}")
    # Kept to sizes that enumerate in seconds. Degree grows as 2r and the walk
    # depth is L, so (n, r, L) with 2r above 8 and L above 6 is not worth the
    # wait and adds no configuration the threshold is not already read at.
    for n, r, L in [(12,1,8),(12,2,4),(12,2,5),(12,2,6),(12,3,3),(12,3,4),
                    (16,2,4),(16,2,6),(16,2,8),(16,3,4),(16,3,5),(16,3,6),
                    (20,2,6),(20,2,10),(20,4,4),(20,4,5)]:
        key = f"{n}-{r}-{L}"
        if key not in cache:
            cache[key] = run(n, r, L)
        d = cache[key]
        print(f"{d['n']:>4} {d['r']:>3} {d['L']:>3} {d['edges']:>5} {d['b1']:>5} "
              f"{d['n_short_cycles']:>6} {d['rank_visible']:>7} {d['gap']:>4} "
              f"{d['max_winding_of_short_cycle']:>8.3f} "
              f"{d['max_visible_cycle_sum_at_fixed_point']:>14.2e} "
              f"{d['ring_cycle_sum_at_fixed_point']:>10.4f}")

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w"), indent=1, sort_keys=True)

    print()
    print("part 2: at what cycle length does inconsistency become visible?")
    for n, r, L_arb in [(16,2,6),(20,4,4)]:
        need = math.ceil(n / r)
        print(f"  n={n} r={r} arbitrage horizon L={L_arb}; ceil(n/r) = {need}")
        for L, cnt, m in first_nonzero_length(n, r, L_arb, L_probe=need + 1):
            flag = "  <-- first non-zero" if m > 1e-8 and L >= need else ""
            print(f"    cycles of length {L:>3}: n={cnt:>6}  max |sum| = {m:.3e}{flag}")


# ---------------------------------------------------------------------------
# Part 3: the seam, and the same construction on a torus.
# ---------------------------------------------------------------------------

def seam_demo(n=20, r=2, L=6, seed=7):
    """Show that every local check passes while the ring fails to close."""
    E = circulant(n, r)
    C = short_cycles(n, E, L)
    rng = np.random.default_rng(seed)
    w = arbitrage_fixed_point(rng.normal(size=len(E)), C)

    step = {}
    for k, (i, j, d) in enumerate(E):
        step[(i, j)] = w[k]
        step[(j, i)] = -w[k]

    phi = [0.0]
    for i in range(n - 1):
        phi.append(phi[-1] + step[(i, i + 1)])
    seam = phi[-1] + step[(n - 1, 0)] - phi[0]

    worst = 0.0
    for i in range(n):
        for j in range(n):
            if min((i - j) % n, (j - i) % n) <= 2 * r:
                vals = [step[(i, m)] + step[(m, j)]
                        for m in range(n) if (i, m) in step and (m, j) in step]
                if (i, j) in step:
                    vals.append(step[(i, j)])
                if len(vals) > 1:
                    worst = max(worst, max(vals) - min(vals))

    return dict(visible_cycle_residual=float(np.max(np.abs(C @ w))),
                worst_local_route_disagreement=worst,
                ring_discrepancy=seam,
                ring_cycle_sum=float(ring_cycle(n, E) @ w))


def torus(nx, ny):
    V = [(x, y) for x in range(nx) for y in range(ny)]
    idx = {v: i for i, v in enumerate(V)}
    Eg = []
    for (x, y) in V:
        Eg.append((idx[(x, y)], idx[((x + 1) % nx, y)], 0))
        Eg.append((idx[(x, y)], idx[(x, (y + 1) % ny)], 0))
    return len(V), Eg


def torus_table(shapes=((4, 4), (5, 4), (5, 5), (6, 5)), L=4):
    rows = []
    for nx, ny in shapes:
        V, Eg = torus(nx, ny)
        b1 = cycle_space_dim(V, Eg)
        Cs = short_cycles(V, Eg, L)
        rk = int(np.linalg.matrix_rank(Cs)) if Cs.shape[0] else 0
        rows.append(dict(nx=nx, ny=ny, V=V, E=len(Eg), b1=int(b1),
                         cycles=int(Cs.shape[0]), rank_visible=rk, gap=int(b1) - rk))
    return rows


def part3():
    d = seam_demo()
    print()
    print("part 3a: the seam, ring of 20, range 2, horizon 6")
    for k, v in d.items():
        print(f"    {k:38} {v: .6e}")
    print()
    print("part 3b: torus, nearest neighbour, horizon 4")
    print(f"    {'nx':>3} {'ny':>3} {'V':>4} {'E':>4} {'b1':>4} {'cycles':>7} "
          f"{'rank V':>7} {'gap':>4}")
    for row in torus_table():
        print(f"    {row['nx']:>3} {row['ny']:>3} {row['V']:>4} {row['E']:>4} "
              f"{row['b1']:>4} {row['cycles']:>7} {row['rank_visible']:>7} {row['gap']:>4}")


if __name__ == "__main__":
    main()
    part3()
