"""A2e: is there anything for an instanton to tunnel between?

**This is a gate, not a station.** It runs before any dynamical work and decides
whether that work is possible at all. It licenses nothing about any economy and
produces no figure for a manuscript.

A minimum-action method needs two things the A2 carrier is not yet known to have:
two metastable regions at *one* parameter value, and a scalar collective variable
on which they separate. A2c's reading that realised cycle rank sits at ``0.029``
of the potential rank and that one autonomous edge restores it to ``0.783`` is
consistent with two basins and equally consistent with a smooth crossover driven
by the knob. Those are different worlds and only the first has transitions in it.

    Q0  range.      Does a candidate move at all across the sweep? A variable
        pinned against a bound cannot separate anything, and testing it for
        modes is a category error. Range is tested first and the dead are
        struck out before anything else runs.

    Q1  bistability. At a fixed knob value, does the across-seed distribution
        of a live candidate have two modes? Smooth movement of every seed with
        the knob is a crossover and answers no.

    Q2  transitions. Within one run, does the variable leave one level and
        arrive at the other, dwelling at each and crossing quickly? Two basins
        each run falls into once and never leaves are initial-condition
        sensitivity, not metastability.

    Q3  control.    A knob A2d showed does not select the terminal state must
        come back unimodal. If everything looks bimodal the estimator is
        manufacturing peaks and Q1 means nothing.

**Thresholds are fixed here, before any run.** A candidate is live when its
relative spread across the sweep exceeds ``0.02``. Two components are preferred
over one when ``dBIC > 10``, the conventional very-strong cut, and Sarle's
bimodality coefficient exceeds ``5/9``, its uniform-distribution value.

Two rules in this file were bought with a wasted run and are recorded so they are
not re-bought:

**Cache the invariant, derive the rest.** The first version cached computed
candidate values. Changing a candidate definition therefore meant recomputing
every simulation. This version caches what the simulation and the topology
produce and nothing else; every candidate is a cheap function of the cache, so a
new candidate costs zero recompute.

**Magnitudes, not shares.** The first version's Hodge candidates were energy
shares. On this carrier they are useless: across 84 runs ``circulation_ratio``
spanned ``0.9998`` to ``1.0`` with 71 per cent of runs exactly at the ceiling,
``gradient_share`` sat between ``1.3e-06`` and ``3.3e-04``, and
``harmonic_share`` reached ``2.5e-30``. A2c's own note already said why: the
harmonic component's magnitude stays within a factor of 1.65 while its share
falls seven orders, because the denominator grows. Q0 exists so that this class
of error is caught by the script rather than by a person reading a null result.

**Cost.** ``hodge_decomposition`` costs about 40 s per call at this graph size,
209,000 times ``cycle_rank`` at 0.19 ms, and the simulation itself is 0.2 s for
600 rounds. So the Hodge candidates are opt-in behind ``--hodge`` and off by
default, and the default gate over the whole sweep runs in about a minute on one
core. Nothing here benefits from a GPU: small graphs, a discrete agent loop, and
the machine that matters is the CPU.

**If the gate fails, that is the finding and it gets reported.** A failed gate
means the endogenous-transition station does not get built on this carrier,
and raising the seed count does not change that. Its scope and its closure are
in ``docs/a2e_gate.md``.

Usage::

    python experiments/a2e_reaction_coordinate.py
    python experiments/a2e_reaction_coordinate.py --seeds 48
    python experiments/a2e_reaction_coordinate.py --hodge      # slow, opt-in

Writes ``results/a2e_reaction_coordinate.json``. Exits non-zero if any criterion
fails, and a FAIL here is a licit outcome rather than a bug.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monetary_topology.config import MonetaryAuthority, WageChannel
from monetary_topology.network import NetworkConfig, NetworkSpec, run_network
from monetary_topology.topology import (
    cycle_rank,
    hodge_decomposition,
    net_flow_vector,
    realized_adjacency,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CACHE = RESULTS / "cache" / "a2e"

SNAPSHOT_EVERY = 25
DIGITS = 6

EDGE_SWEEP = (0, 1, 2, 3, 4, 6, 8, 12, 20, 30)
CONTROL_SWEEP = (1, 2, 3, 4)

#: Candidates and where each comes from. ``snap`` is read at every snapshot and
#: costs one ``cycle_rank``; ``round`` is read at every round and is free, having
#: been computed by the simulation already. Free ones are preferred because they
#: give 600 points per run instead of 25, and Q2 counts crossings.
FREE_ROUND = ("support_fraction", "total_ratio", "layer2_reached", "realized_support")
CANDIDATES = ("realized_rank_frac", "realized_support_frac") + FREE_ROUND[:2]
HODGE_CANDIDATES = ("gradient_norm", "curl_norm", "harmonic_norm", "divergence_norm")

BURN_IN = 0.5
BIC_CUT = 10.0
SARLE_CUT = 5.0 / 9.0
SPREAD_CUT = 0.02
#: A mixture component holding fewer than this fraction is an outlier, not a
#: mode. Bought with a spurious PASS: on a cell whose 48 values were all 1.0 to
#: six digits, EM split one point off with microscopic variance and returned
#: dBIC 155.9 and separation 26.9 at weights [0.979, 0.021]. Both guards below
#: are stated before the re-run, not tuned until the answer changed.
MIN_WEIGHT = 0.10


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        return f"  [{'PASS' if self.passed else 'FAIL'}] {self.name}\n         {self.detail}"


def r(x: float) -> float:
    return round(float(x), DIGITS)


# ---------------------------------------------------------------------------
# one run, cached
# ---------------------------------------------------------------------------


def _key(seed: int, rounds: int, edges: int, upward: int, hodge: bool) -> str:
    raw = (f"v3|seed={seed}|rounds={rounds}|edges={edges}|upward={upward}"
           f"|snap={SNAPSHOT_EVERY}|hodge={int(hodge)}")
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def simulate(seed: int, rounds: int, edges: int, upward: int, hodge: bool,
             use_cache: bool) -> dict:
    """One run, cached.

    **What is cached is what the simulation and the topology produce, never a
    candidate.** Candidates are cheap functions of this payload and are computed
    on load, so redefining one costs nothing. The first version of this file did
    the opposite and a candidate change meant recomputing everything.
    """
    path = CACHE / f"{_key(seed, rounds, edges, upward, hodge)}.json"
    if use_cache and path.exists():
        return json.loads(path.read_text())

    spec = NetworkSpec(
        seed=seed,
        intermediate_size=30,
        layer2_size=150,
        financial_to_intermediate_edges=edges,
        upward_out_degree=upward,
    )
    h = run_network(
        NetworkConfig(
            spec=spec,
            rounds=rounds,
            seed=seed,
            snapshot_every=SNAPSHOT_EVERY,
            authority=MonetaryAuthority(rule="endogenous"),
            wages=WageChannel(bill=8.0, elasticity=0.0),
        )
    )

    # The potential graph is what the economy permits and never changes: no edge
    # is deleted. A2c takes it from ``h.adjacency`` and so does this, because a
    # denominator read off the flow would be the complete graph.
    out: dict = {
        "potential_rank": max(cycle_rank(h.adjacency), 1),
        "potential_support": int(h.potential_support),
        "node_count": int(h.node_count),
        "snap_round": [],
        "realized_rank": [],
    }
    for k in FREE_ROUND:
        out[k] = [float(v) for v in np.asarray(getattr(h, k), dtype=float)]

    if hodge:
        for k in HODGE_CANDIDATES:
            out[k] = []

    for t in sorted(h.snapshots):
        flow = h.snapshots[t]
        realized = realized_adjacency(flow, h.epsilon_absolute)
        out["snap_round"].append(int(t))
        out["realized_rank"].append(int(cycle_rank(realized)))
        if hodge:
            split = hodge_decomposition(flow, realized)
            g, c, hh = split.energies()
            w = net_flow_vector(flow, realized)
            div = incidence_matrix(realized).T @ w
            # Magnitudes. Shares are what the first version recorded and they
            # are pinned on this carrier; A2c says why.
            out["gradient_norm"].append(float(np.sqrt(g)))
            out["curl_norm"].append(float(np.sqrt(c)))
            out["harmonic_norm"].append(float(np.sqrt(hh)))
            out["divergence_norm"].append(float(np.linalg.norm(div)))

    if use_cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out))
    return out


def series(run: dict, name: str) -> np.ndarray:
    """A candidate as a time series, derived from the cache. Never cached."""
    if name == "realized_rank_frac":
        return np.asarray(run["realized_rank"], float) / float(run["potential_rank"])
    if name == "realized_support_frac":
        return np.asarray(run["realized_support"], float) / max(float(run["potential_support"]), 1.0)
    if name == "layer2_reached":
        return np.asarray(run["layer2_reached"], float) / max(float(run["node_count"]), 1.0)
    return np.asarray(run[name], dtype=float)


def _job(args: tuple) -> tuple[tuple, dict]:
    seed, rounds, edges, upward, hodge, use_cache = args
    return (edges, upward, seed), simulate(seed, rounds, edges, upward, hodge, use_cache)


# ---------------------------------------------------------------------------
# bimodality, dependency free
# ---------------------------------------------------------------------------


def spread(vals: np.ndarray) -> float:
    """Relative spread. A candidate pinned against a bound scores near zero.

    Q0 uses this before any mode test runs. ``circulation_ratio`` in the
    superseded version scored ``1.6e-04`` here and was tested for bimodality
    anyway, which was the error this function exists to prevent.
    """
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return float("nan")
    scale = max(abs(float(v.max())), abs(float(v.min())), 1e-300)
    return float((v.max() - v.min()) / scale)


def sarle(x: np.ndarray) -> float:
    """Sarle's bimodality coefficient, ``(skew^2 + 1) / kurtosis``.

    Exceeds ``5/9`` for the uniform distribution and above. Reported alongside
    the mixture fit because the two fail in different ways and agreeing is
    worth more than either alone.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 4:
        return float("nan")
    m = x.mean()
    s = x.std(ddof=1)
    if s == 0:
        return float("nan")
    z = (x - m) / s
    g1 = float((z**3).mean())
    g2 = float((z**4).mean()) - 3.0
    num = n - 1
    den = (n - 2) * (n - 3)
    corr = 3.0 * num * num / den if den else 1.0
    return float((g1**2 + 1.0) / (g2 + corr))


def _gauss(x: np.ndarray, mu: float, var: float) -> np.ndarray:
    return np.exp(-0.5 * (x - mu) ** 2 / var) / np.sqrt(2.0 * np.pi * var)


def fit_two(x: np.ndarray, iters: int = 200, restarts: int = 5) -> dict:
    """One-dimensional two-component Gaussian mixture by EM.

    Five restarts because EM is local and one start is a coin flip; not more,
    because the objective is one dimensional and five is already past the point
    where a sixth changes the answer.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    floor = max(np.var(x) * 1e-6, 1e-12)
    best = None
    rng = np.random.default_rng(0)
    for k in range(restarts):
        q = np.quantile(x, [0.25 + 0.1 * k, 0.75 - 0.1 * k])
        mu = np.array([q[0], q[1]], dtype=float) + rng.normal(0, 1e-9, 2)
        var = np.array([np.var(x) + floor] * 2)
        pi = np.array([0.5, 0.5])
        ll = -np.inf
        for _ in range(iters):
            comp = np.stack([pi[j] * _gauss(x, mu[j], var[j]) for j in range(2)])
            tot = comp.sum(axis=0)
            tot = np.where(tot <= 0, 1e-300, tot)
            new_ll = float(np.log(tot).sum())
            resp = comp / tot
            nk = resp.sum(axis=1)
            nk = np.where(nk <= 0, 1e-300, nk)
            pi = nk / n
            mu = (resp * x).sum(axis=1) / nk
            var = np.maximum((resp * (x - mu[:, None]) ** 2).sum(axis=1) / nk, floor)
            if abs(new_ll - ll) < 1e-10:
                ll = new_ll
                break
            ll = new_ll
        if best is None or ll > best["ll"]:
            order = np.argsort(mu)
            best = {
                "ll": ll,
                "mu": mu[order].tolist(),
                "sd": np.sqrt(var[order]).tolist(),
                "pi": pi[order].tolist(),
            }
    return best


def bimodality(x: np.ndarray) -> dict:
    """Two components against one, by BIC, plus Sarle, overlap and two guards.

    **Bimodality is a within-cell question.** Q0's range test pools the whole
    sweep, so a candidate that moves with the knob passes it while being
    constant inside every cell. A cell whose own spread is below ``SPREAD_CUT``
    is not tested: a mixture fitted to a constant is a fit to floating-point
    noise, and it returns spectacular numbers.

    **A component below ``MIN_WEIGHT`` is an outlier.** One point split off with
    a microscopic variance maximises likelihood and means nothing.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    sp = spread(x)
    dead = {"n": int(n), "d_bic": float("nan"), "sarle": float("nan"),
            "overlap": float("nan"), "separation": float("nan"),
            "cell_spread": r(sp) if np.isfinite(sp) else float("nan"),
            "bimodal": False}
    if n < 8 or np.std(x) == 0:
        return dead
    if not np.isfinite(sp) or sp <= SPREAD_CUT:
        dead["skipped"] = "cell spread below cut: constant within the cell"
        return dead

    var1 = max(float(np.var(x)), 1e-300)
    ll1 = float(np.log(_gauss(x, float(x.mean()), var1) + 1e-300).sum())
    bic1 = 2.0 * np.log(n) - 2.0 * ll1

    two = fit_two(x)
    bic2 = 5.0 * np.log(n) - 2.0 * two["ll"]
    d_bic = float(bic1 - bic2)

    mu, sd, pi = two["mu"], two["sd"], two["pi"]
    pooled = float(np.sqrt(0.5 * (sd[0] ** 2 + sd[1] ** 2)))
    separation = float(abs(mu[1] - mu[0]) / pooled) if pooled > 0 else float("inf")
    mid = 0.5 * (mu[0] + mu[1])
    # misclassification of a hard split at the midpoint, under the fitted mixture
    lo = pi[0] * float(1.0 - _cdf(mid, mu[0], sd[0]))
    hi = pi[1] * float(_cdf(mid, mu[1], sd[1]))
    overlap = float(lo + hi)
    sc = sarle(x)
    balanced = min(pi) >= max(MIN_WEIGHT, 3.0 / n)
    return {
        "n": int(n),
        "cell_spread": r(sp),
        "d_bic": r(d_bic),
        "sarle": r(sc),
        "mu": [r(v) for v in mu],
        "sd": [r(v) for v in sd],
        "pi": [r(v) for v in pi],
        "min_weight_ok": bool(balanced),
        "separation": r(separation),
        "overlap": r(overlap),
        "bimodal": bool(d_bic > BIC_CUT and sc > SARLE_CUT and balanced),
    }


def _cdf(t: float, mu: float, sd: float) -> float:
    if sd <= 0:
        return 1.0 if t >= mu else 0.0
    from math import erf, sqrt
    return 0.5 * (1.0 + erf((t - mu) / (sd * sqrt(2.0))))


# ---------------------------------------------------------------------------
# within-run switching
# ---------------------------------------------------------------------------


def crossings(series: np.ndarray, lo: float, hi: float) -> dict:
    """Dwell and transit against two bands.

    A crossing is a move from inside the low band to inside the high band, or
    the reverse, with whatever happens in between counted as transit. Time in
    transit is the quantity that separates a metastable pair from a drift: a
    pair dwells and crosses quickly, a drift spends its life in the middle.
    """
    s = np.asarray(series, dtype=float)
    state = np.where(s <= lo, -1, np.where(s >= hi, 1, 0))
    seen = state[state != 0]
    n_cross = int(np.sum(seen[1:] != seen[:-1])) if seen.size > 1 else 0
    total = int(s.size)
    return {
        "crossings": n_cross,
        "frac_low": r(float(np.mean(state == -1))) if total else float("nan"),
        "frac_high": r(float(np.mean(state == 1))) if total else float("nan"),
        "frac_transit": r(float(np.mean(state == 0))) if total else float("nan"),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def terminal(run: dict, name: str) -> float:
    """Post burn-in mean of a candidate on one run."""
    v = series(run, name)
    k = max(int(len(v) * BURN_IN), 1)
    tail = v[k:]
    tail = tail[np.isfinite(tail)]
    return float(np.mean(tail)) if tail.size else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=48)
    ap.add_argument("--rounds", type=int, default=600)
    ap.add_argument("--workers", type=int, default=max(os.cpu_count() or 2, 2))
    ap.add_argument("--hodge", action="store_true",
                    help="also compute Hodge magnitudes: ~40 s per snapshot, opt-in")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    use_cache = not args.no_cache
    cands = list(CANDIDATES) + (list(HODGE_CANDIDATES) if args.hodge else [])

    seeds = list(range(args.seeds))
    jobs = [(s_, args.rounds, e, 2, args.hodge, use_cache) for e in EDGE_SWEEP for s_ in seeds]
    jobs += [(s_, args.rounds, 0, u, args.hodge, use_cache)
             for u in CONTROL_SWEEP if u != 2 for s_ in seeds]

    print(f"a2e: {len(jobs)} runs, {args.workers} workers, "
          f"hodge {'on' if args.hodge else 'off'}, cache {'on' if use_cache else 'off'}")
    store: dict[tuple, dict] = {}
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for key, run in ex.map(_job, jobs):
            store[key] = run
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)
    # ``upward=2`` is omitted from the control jobs because the edge sweep
    # already holds ``(edges=0, upward=2)``; the control loop reads it from
    # there rather than simulating it twice.

    report: dict = {"config": vars(args), "range": {}, "sweep": {}, "control": {}, "switching": {}}
    crit: list[Criterion] = []

    crit.append(Criterion(
        "A2e-1  every run completed",
        len(store) >= len(EDGE_SWEEP) * len(seeds),
        f"{len(store)} cells held, {len(jobs)} jobs dispatched"))

    # ---- Q0: which candidates move at all ----
    live, dead = [], []
    for c in cands:
        vals = np.array([terminal(store[(e, 2, s_)], c) for e in EDGE_SWEEP for s_ in seeds])
        sp = spread(vals)
        row = {"spread": r(sp), "min": r(float(np.nanmin(vals))), "max": r(float(np.nanmax(vals))),
               "live": bool(sp > SPREAD_CUT)}
        report["range"][c] = row
        (live if row["live"] else dead).append(c)
    crit.append(Criterion(
        "A2e-0  at least one candidate has range across the sweep",
        bool(live),
        f"live {live}; struck out for spread<={SPREAD_CUT}: "
        f"{[(c, report['range'][c]['spread']) for c in dead] or 'none'}"))

    # ---- Q1 / bistability, live candidates only ----
    best = {"cand": None, "edges": None, "d_bic": -np.inf}
    for e in EDGE_SWEEP:
        cell = {}
        for c in live:
            vals = np.array([terminal(store[(e, 2, s_)], c) for s_ in seeds])
            bm = bimodality(vals)
            cell[c] = bm
            if bm["bimodal"] and bm["d_bic"] > best["d_bic"]:
                best = {"cand": c, "edges": e, "d_bic": bm["d_bic"], "fit": bm}
        report["sweep"][str(e)] = cell
    crit.append(Criterion(
        "A2e-2  bistability at a fixed knob value",
        best["cand"] is not None,
        (f"best {best['cand']} at edges={best['edges']}, dBIC {best['d_bic']}, "
         f"separation {best['fit']['separation']}, overlap {best['fit']['overlap']}, "
         f"weights {best['fit']['pi']}")
        if best["cand"] else
        f"no cell cleared dBIC>{BIC_CUT} and Sarle>{r(SARLE_CUT)} on {len(live)} live "
        f"candidate(s); a crossover, not two basins"))

    # ---- Q3 control ----
    ctrl = []
    for u in CONTROL_SWEEP:
        cell = {}
        for c in live:
            vals = np.array([terminal(store[(0, u, s_)], c) for s_ in seeds])
            bm = bimodality(vals)
            cell[c] = bm
            if bm["bimodal"]:
                ctrl.append((u, c, bm["d_bic"]))
        report["control"][str(u)] = cell
    crit.append(Criterion(
        "A2e-4  the flat control knob returns unimodal",
        not ctrl,
        "no control cell bimodal" if not ctrl
        else f"{len(ctrl)} control cells bimodal: {ctrl[:4]} — estimator artefact suspected"))

    # ---- Q2 within-run switching ----
    if best["cand"]:
        c, e, fit = best["cand"], best["edges"], best["fit"]
        lo, hi = fit["mu"][0] + fit["sd"][0], fit["mu"][1] - fit["sd"][1]
        rows = {}
        for s_ in seeds:
            v = series(store[(e, 2, s_)], c)
            k = max(int(len(v) * BURN_IN), 1)
            rows[str(s_)] = crossings(v[k:], lo, hi)
        report["switching"] = {"candidate": c, "edges": e, "lo": r(lo), "hi": r(hi),
                               "points_per_run": int(len(series(store[(e, 2, seeds[0])], c))),
                               "runs": rows}
        tot = sum(x["crossings"] for x in rows.values())
        movers = sum(1 for x in rows.values() if x["crossings"] > 0)
        transit = float(np.mean([x["frac_transit"] for x in rows.values()]))
        crit.append(Criterion(
            "A2e-3  within-run transitions, not just two basins",
            tot > 0,
            f"{tot} crossings across {movers}/{len(seeds)} runs, mean time in transit {r(transit)}"
            if tot else
            "0 crossings in every run: two basins reached once and never left. "
            "That is initial-condition sensitivity, and there is no transition to time"))
    else:
        crit.append(Criterion(
            "A2e-3  within-run transitions, not just two basins",
            False, "not evaluated: A2e-2 found no pair to cross between"))

    report["criteria"] = [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in crit]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "a2e_reaction_coordinate.json").write_text(json.dumps(report, indent=2))

    print()
    for c in crit:
        print(c.line())
    ok = all(c.passed for c in crit)
    print()
    print("GATE OPEN: the endogenous-transition station is buildable here" if ok
          else "GATE CLOSED: report this and do not build the station")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
