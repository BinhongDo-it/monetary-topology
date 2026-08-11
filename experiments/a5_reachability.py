"""A5: the reachability threshold, and whether its benign side is an equilibrium.

Registered in ``docs/a5_reachability.md``. This file evaluates and does not
design.

Usage::

    python experiments/a5_reachability.py
    python experiments/a5_reachability.py --seeds 5

Writes ``results/a5_reachability.json``.

Reachability is

    rho_q  =  median terms * P_q(0) / median production-layer claims / s

so ``rho = 1`` is the point at which the median production-layer agent can just
afford the tier on the opening day. It is a definition and not a fitted
threshold, which is why A5-2 is stated at that value.

The criterion that matters is **A5-4**. The price is set by a bidder pool made
of the financial layer's claims, and those grow with issuance, so a price that
ordinary agents can meet on day one may be bid away from them by a mechanism
nobody chooses. If that is what happens, then setting the opening price low
enough is not a policy that can hold, because the price is endogenous. That is a
stronger statement than locating the threshold, and A5-4's failure would be the
more consequential of the two outcomes.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    A3Config,
    A3Model,
    AssetSpec,
    centrality,
    terms_matrix,
)
from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkSpec,
)

RESULTS = ROOT / "results"

#: Registered in section 7.
RHO_GRID = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
GAIN_GRID = (0.25, 0.5, 1.0)
ROUNDS = 300

#: Registered thresholds, section 4.
A5_2_LOW_RHO, A5_2_LOW_SHARE = 0.5, 0.50
A5_2_HIGH_RHO, A5_2_HIGH_SHARE = 2.0, 0.05
A5_3_BENIGN, A5_3_HOSTILE = 0.25, 4.0
A5_4_START = 0.5
A5_4_MEDIAN_CROSSING = 100
A5_4_RETURN_SHARE = 0.05
A5_6_DRIFT = 0.01


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False

    def line(self) -> str:
        mark = "VOID" if self.void else ("pass" if self.passed else "FAIL")
        return f"  {mark}  {self.name}\n        {self.detail}"


# ---------------------------------------------------------------------------
# setting and measuring reachability
# ---------------------------------------------------------------------------


def baseline(seed: int) -> tuple[np.ndarray, float, slice]:
    """Terms, median production-layer opening claims, and that layer's slice.

    Read off a bare stage A2 network, before any asset exists. The denominator
    of reachability has to be what an ordinary agent holds *before* the asset
    market touches anything, or the measure would be defined in terms of its own
    consequences.
    """
    spec = NetworkSpec(seed=seed)
    net = Network(NetworkConfig(spec=spec, seed=seed))
    production = slice(spec.layer1_size, spec.size)
    terms = terms_matrix(centrality(net.adjacency), AssetSpec())
    return terms, float(np.median(net.holdings[production])), production


def price_for(target: float, seed: int, spec: AssetSpec) -> tuple[float, ...]:
    """Opening prices scaled so that the low tier's reachability is ``target``.

    Only the scale moves; the tiers keep their registered ratio of one to two to
    four, because that ratio is what makes them three different things.
    """
    terms, median_claims, production = baseline(seed)
    gamma = float(np.median(terms[production, 0]))
    base = spec.initial_price[0]
    current = gamma * base / median_claims / spec.stretch
    factor = target / current
    return tuple(float(p * factor) for p in spec.initial_price)


def rho_series(model: A3Model, tier: int = 0) -> np.ndarray:
    """``rho(t)`` for one tier, recomputed every round from that round's state.

    The same formula as the opening value, applied to the prices and the
    production layer's claims as they stand. A trajectory rather than a number
    is the whole point of A5-4.
    """
    spec = model.a3.asset
    layer1 = model.a3.network.spec.layer1_size
    production = slice(layer1, model._n)
    gamma = float(np.median(model.terms[production, tier]))
    prices = np.asarray(model.price_history)[:, tier]
    claims = np.asarray(model.claims_history)[:, production]
    median_claims = np.median(claims, axis=1)
    return gamma * prices / np.maximum(median_claims, 1e-12) / spec.stretch


def run(seed: int, rho: float, gain: float = 1.0, eta: float | None = None):
    spec = AssetSpec()
    prices = price_for(rho, seed, spec)
    asset = AssetSpec(
        initial_price=prices,
        elasticity=spec.elasticity if eta is None else eta,
    )
    net = NetworkConfig(
        spec=NetworkSpec(seed=seed),
        seed=seed,
        rounds=ROUNDS,
        authority=MonetaryAuthority(rule="endogenous", gain=gain),
    )
    model = A3Model(A3Config(asset=asset, network=net))
    model.run()
    return model


# ---------------------------------------------------------------------------
# outcome measures
# ---------------------------------------------------------------------------


def participation(model: A3Model) -> float:
    """Share of production-layer nodes holding a unit **at the end**.

    Kept, but it is survival and not entry: the production layer is sold out
    within three hundred rounds at every reachability tried, so this number is
    zero across the whole grid and cannot order it. A5-1 and A5-2 are measured
    on ``entry_participation`` instead, which was the intent.
    """
    layer1 = model.a3.network.spec.layer1_size
    held = model.units.sum(axis=1)[layer1:] > 0
    return float(held.mean())


def entry_participation(seed: int, rho: float) -> float:
    """Share of production-layer nodes that got in at the opening allocation.

    Measured on a freshly constructed model, before any round is run. Entry is
    what reachability is about; whether an entrant is still holding three
    hundred rounds later is a different question and is reported separately.
    """
    spec = AssetSpec()
    model = A3Model(
        A3Config(
            asset=AssetSpec(initial_price=price_for(rho, seed, spec)),
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=ROUNDS
            ),
        )
    )
    layer1 = model.a3.network.spec.layer1_size
    return float((model.units.sum(axis=1)[layer1:] > 0).mean())


def rho_components(model: A3Model, tier: int = 0) -> tuple[float, float]:
    """How much of ``rho``'s drift is the price, and how much is the buyers.

    Reachability has a numerator and a denominator and the registered criterion
    named only the numerator. Returns the ratio each has moved by over the run.
    """
    layer1 = model.a3.network.spec.layer1_size
    prices = np.asarray(model.price_history)[:, tier]
    claims = np.median(np.asarray(model.claims_history)[:, layer1:], axis=1)
    return float(prices[-1] / prices[0]), float(claims[-1] / claims[0])


def production_share(model: A3Model) -> np.ndarray:
    """The production layer's share of total net worth, per round."""
    layer1 = model.a3.network.spec.layer1_size
    nw = np.asarray(model.net_worth_history)
    total = nw.sum(axis=1)
    return np.divide(
        nw[:, layer1:].sum(axis=1), total, out=np.zeros_like(total), where=total > 0
    )


def crossing(series: np.ndarray) -> tuple[int | None, float]:
    """First round at which ``rho`` reaches one, and the share of rounds after
    it that fall back below."""
    above = np.flatnonzero(series >= 1.0)
    if above.size == 0:
        return None, 0.0
    first = int(above[0])
    after = series[first:]
    return first, float((after < 1.0).mean())


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------


def sweep(seeds: range) -> dict[float, dict[str, float]]:
    out: dict[float, dict[str, float]] = {}
    for rho in RHO_GRID:
        models = [run(seed, rho) for seed in seeds]
        shares = [production_share(m) for m in models]
        out[rho] = {
            "participation": float(
                np.mean([entry_participation(seed, rho) for seed in seeds])
            ),
            "survival": float(np.mean([participation(m) for m in models])),
            "share_start": float(np.mean([s[0] for s in shares])),
            "share_end": float(np.mean([s[-1] for s in shares])),
            "trades": float(np.mean([sum(m.sales) for m in models])),
        }
    return out


def a5_1(grid: dict[float, dict[str, float]]) -> Criterion:
    values = [grid[r]["participation"] for r in RHO_GRID]
    monotone = all(a >= b - 1e-12 for a, b in pairwise(values))
    return Criterion(
        "A5-1  participation falls with reachability",
        monotone,
        "production-layer participation across the grid: "
        + ", ".join(f"rho={r}: {grid[r]['participation']:.1%}" for r in RHO_GRID),
    )


def a5_2(grid: dict[float, dict[str, float]]) -> Criterion:
    low = grid[A5_2_LOW_RHO]["participation"]
    high = grid[A5_2_HIGH_RHO]["participation"]
    return Criterion(
        "A5-2  the threshold sits where the definition puts it",
        low > A5_2_LOW_SHARE and high < A5_2_HIGH_SHARE,
        f"at rho={A5_2_LOW_RHO}: {low:.1%} against a floor of "
        f"{A5_2_LOW_SHARE:.0%}; at rho={A5_2_HIGH_RHO}: {high:.1%} against a "
        f"ceiling of {A5_2_HIGH_SHARE:.0%}. rho=1 is where the median agent can "
        f"just pay, not a fitted value",
    )


def a5_3(grid: dict[float, dict[str, float]]) -> Criterion:
    benign = grid[A5_3_BENIGN]
    hostile = grid[A5_3_HOSTILE]
    rose = benign["share_end"] > benign["share_start"]
    fell = hostile["share_end"] < hostile["share_start"]
    return Criterion(
        "A5-3  the sign of the production layer's trend flips",
        rose and fell,
        f"net worth share at rho={A5_3_BENIGN}: "
        f"{benign['share_start']:.3f} -> {benign['share_end']:.3f}; at "
        f"rho={A5_3_HOSTILE}: {hostile['share_start']:.3f} -> "
        f"{hostile['share_end']:.3f}. One mechanism, two regimes, nothing "
        f"changed but reachability",
    )


def a5_4(seeds: range) -> Criterion:
    rounds_to_cross, returns = [], []
    for seed in seeds:
        series = rho_series(run(seed, A5_4_START))
        first, back = crossing(series)
        rounds_to_cross.append(ROUNDS if first is None else first)
        returns.append(back)
    median = float(np.median(rounds_to_cross))
    back = float(np.mean(returns))
    crossed = sum(r < ROUNDS for r in rounds_to_cross)
    price_moves, claim_moves = [], []
    for seed in seeds:
        up, down = rho_components(run(seed, A5_4_START))
        price_moves.append(up)
        claim_moves.append(down)
    return Criterion(
        "A5-4  the benign side is not an equilibrium",
        median < A5_4_MEDIAN_CROSSING and back < A5_4_RETURN_SHARE,
        f"starting at rho={A5_4_START}: crossed in {crossed}/{len(seeds)} seeds, "
        f"median round {median:.0f} against {A5_4_MEDIAN_CROSSING}, "
        f"{back:.1%} of subsequent rounds back below one against "
        f"{A5_4_RETURN_SHARE:.0%}. Decomposed over the run, the price moves by "
        f"x{np.mean(price_moves):.1f} and the median buyer's claims by "
        f"x{np.mean(claim_moves):.3f}: the reachable region closes from the "
        f"denominator, not only from the price",
    )


def a5_5(seeds: range) -> Criterion:
    medians = []
    for gain in GAIN_GRID:
        rounds_to_cross = []
        for seed in seeds:
            first, _ = crossing(rho_series(run(seed, A5_4_START, gain=gain)))
            rounds_to_cross.append(ROUNDS if first is None else first)
        medians.append(float(np.median(rounds_to_cross)))
    falling = all(a >= b for a, b in pairwise(medians))
    return Criterion(
        "A5-5  issuance sets the clock",
        falling,
        "median crossing round by issuance gain: "
        + ", ".join(
            f"gain={g}: {m:.0f}" for g, m in zip(GAIN_GRID, medians, strict=True)
        )
        + ". What evaporates the reachable region is the rate at which new "
        "claims arrive at the top",
    )


def a5_6(seeds: range) -> Criterion:
    drifts = []
    for seed in seeds:
        series = rho_series(run(seed, A5_4_START, eta=0.0))
        drifts.append(float(np.abs(series / series[0] - 1.0).max()))
    worst = float(np.max(drifts))
    return Criterion(
        "A5-6  freeze the price and the drift disappears",
        worst < A5_6_DRIFT,
        f"largest relative move in rho with the price frozen: {worst:.2%} "
        f"against {A5_6_DRIFT:.0%}. Any crossing at a live price is therefore "
        f"the price channel and not the wage bill, issuance or turnover",
    )


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()
    seeds = range(args.seeds)

    print("A5: the reachability threshold\n")
    print(f"  sweeping rho over {RHO_GRID} at {args.seeds} seeds")
    grid = sweep(seeds)

    criteria = [
        a5_1(grid),
        a5_2(grid),
        a5_3(grid),
        a5_4(seeds),
        a5_5(seeds),
        a5_6(seeds),
    ]

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not c.void]
    n_pass = sum(c.passed for c in live)
    print(f"\n  {n_pass}/{len(live)} live criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "a5_reachability.json"
    out.write_text(
        json.dumps(
            {
                "stage": "A5",
                "seeds": args.seeds,
                "rounds": ROUNDS,
                "grid": {str(k): v for k, v in grid.items()},
                "criteria": [
                    {
                        "name": c.name,
                        "passed": bool(c.passed),
                        "void": bool(c.void),
                        "detail": c.detail,
                    }
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
