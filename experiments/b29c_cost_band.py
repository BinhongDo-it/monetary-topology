"""B29-3: does a transaction-cost band swallow the defect?

Pre-registered: the criteria are written into this file, the record carries
their text, and every quantity this run produced is reported.

B29's arbitrage was an exact orthogonal projection: every visible cycle closes to
machine zero. Real arbitrage has a cost band. A loop whose discrepancy is smaller
than the round-trip cost is not worth doing, so it is left open.

Model: cycle-by-cycle Kaczmarz with a dead zone tau. For each visible cycle c, if
|c.w| > tau, move w so that |c.w| becomes exactly tau, which is where the trade
stops being profitable. Cycles with |c.w| <= tau are left alone.

    w <- w - ((c.w) - sign(c.w) * tau) / (c.c) * c

One structural fact, true for every tau and worth stating before any number: every
update is a multiple of some c in V, so w moves only inside span(V), and the
component of w orthogonal to span(V) is EXACTLY conserved. The defect this
project cares about lives there. So the cost band cannot destroy the defect. What
it can do is raise the noise floor until the defect is not measurable, and that is
what this arm quantifies.

Reported per tau:
    resid      max |c.w| over visible cycles at the fixed point
    hol        the ring cycle sum
    hol_inv    ((I - P_V) R) . w, exactly conserved, the invariant part of hol
    ratio      |hol| / resid, the distinguishability the design registered

Criteria, fixed in advance:
    ratio > 3   defect measurable above the cost band; the ratio is the signal to
                noise a real reading would have
    ratio < 1   defect swallowed; B29-1 is not runnable at that cost level
    1 to 3      marginal, reported as marginal and not rounded
"""
import numpy as np, math, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from b29_locality import circulant, short_cycles, ring_cycle, arbitrage_fixed_point

CACHE = os.path.join(os.path.dirname(__file__), "..", "results", "b29c_cost_band.json")


def soft_kaczmarz(w, C, tau, max_sweeps=2000, tol=1e-12):
    """Sweep cycles until every visible cycle sits inside the band."""
    w = w.copy()
    norms = (C * C).sum(axis=1)
    for sweep in range(max_sweeps):
        moved = 0.0
        for k in range(C.shape[0]):
            g = float(C[k] @ w)
            if abs(g) > tau:
                step = (g - math.copysign(tau, g)) / norms[k]
                w -= step * C[k]
                moved = max(moved, abs(step))
        if moved < tol:
            return w, sweep + 1
    return w, max_sweeps


def run(n=20, r=2, L=6, seed=0, taus=None):
    E = circulant(n, r)
    C = short_cycles(n, E, L)
    R = ring_cycle(n, E)
    # invariant direction: the part of R orthogonal to span(V)
    R_perp = R - (R - arbitrage_fixed_point(R, C))
    rng = np.random.default_rng(seed)
    w0 = rng.normal(size=len(E))
    init_resid = float(np.max(np.abs(C @ w0)))
    rows = []
    for tau in (taus if taus is not None else
                [0.0, 0.001, 0.01, 0.03, 0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]):
        w, sweeps = soft_kaczmarz(w0, C, tau)
        resid = float(np.max(np.abs(C @ w)))
        hol = float(R @ w)
        hol_inv = float(R_perp @ w)
        rows.append(dict(tau=tau, sweeps=sweeps, resid=resid, hol=hol,
                         hol_inv=hol_inv,
                         ratio=(abs(hol) / resid if resid > 1e-15 else float("inf"))))
    return dict(n=n, r=r, L=L, seed=seed, cycles=int(C.shape[0]),
                init_resid=init_resid, rows=rows)


def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    seeds = (0, 1, 2)
    print("n=20 r=2 L=6, so ceil(n/r)=10 and the defect survives by Theorem 7")
    for seed in seeds:
        key = f"20-2-6-{seed}"
        if key not in cache:
            cache[key] = run(seed=seed)
        d = cache[key]
        if seed == seeds[0]:
            print(f"visible cycles {d['cycles']}, largest cycle sum before arbitrage "
                  f"{d['init_resid']:.3f}\n")
            print(f"{'tau':>7} {'sweeps':>7} {'resid':>10} {'hol':>10} {'hol_inv':>10} "
                  f"{'ratio':>9}  verdict")
        print(f"seed {seed}")
        for rw in d["rows"]:
            v = ("measurable" if rw["ratio"] > 3 else
                 "SWALLOWED" if rw["ratio"] < 1 else "marginal")
            rs = f"{rw['ratio']:9.2f}" if math.isfinite(rw["ratio"]) else "      inf"
            print(f"{rw['tau']:7.3f} {rw['sweeps']:7d} {rw['resid']:10.2e} "
                  f"{rw['hol']:10.4f} {rw['hol_inv']:10.4f} {rs}  {v}")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
