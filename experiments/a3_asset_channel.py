"""A3: the asset channel, executed against its seven registered criteria.

Registered in ``docs/a3_asset_channel.md``. This file evaluates and does not
design: every threshold it compares against is written there, and where a
criterion cannot be evaluated it reports **void** rather than a number.

Usage::

    python experiments/a3_asset_channel.py
    python experiments/a3_asset_channel.py --seeds 5
    python experiments/a3_asset_channel.py --rent-sweep   # frozen-price rent arm
    python experiments/a3_asset_channel.py --sweep        # §4's robustness grid

``--sweep`` is §4's robustness grid, one parameter at a time off the registered
point. It was advertised here for a long time before it existed, and §6.5
records that as a breach of a registered promise rather than as a todo. Three
section numbers in this docstring were stale after the document was rewritten:
the grid is §4 and not §7, the breach is recorded in §6.5 and not §9.10, and
the rent arm is §6.2b and not §9.11. The stale numbers are corrected here
rather than in the document, which is not rewritten.

Writes ``results/a3_asset_channel.json``.

The criterion that matters is **A3-4**, and its whole force is that the two
numbers it compares are produced by code that shares nothing. The simulated
exponent comes from ``asset.py`` running an economy with prices, circulation, a
wage bill, issuance, supply limits and turnover in it. The loop sum comes from
``product_graph.py`` given nothing but a terms matrix and two price vectors.
Neither module imports the other, ``main`` asserts it, and the price is expected
to fall out of the second by itself rather than being divided out.

A3-2 is a floor, not evidence. It compares owners against non-owners, which is
a gap produced by owning rather than by the terms of owning, and it can be three
orders of magnitude wide while the loop sum is exactly zero. The comparison that
carries A3-3 and A3-4 is the **terms pair**: agents who all own and all trade,
differing only in what they are charged.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    CLOSED,
    SWEEP_CELLS,
    A3Config,
    A3Model,
    AssetSpec,
)
from monetary_topology.network import (  # noqa: E402
    NetworkConfig,
    NetworkSpec,
    run_network,
)
from monetary_topology.product_graph import (  # noqa: E402
    Cochain,
    cochain_from_field,
    squares,
    tier_field,
    tier_positions,
)

RESULTS = ROOT / "results"

#: Registered in §4. A fixed count either side of the allocation boundary,
#: replacing a decile that would have been one node.
BOUNDARY = 5

#: Registered thresholds, §4. Named here so a reader can see them together and
#: check them against the document rather than hunting through the code.
A3_2_FLOOR = 2.0
A3_4_TOLERANCE = 0.20
#: A3-5 was registered as ``low > 1.5 > high`` on a **ratio** of group net
#: worths. Rent drives the denominator of that ratio toward zero, so once
#: ``rent_rate`` was switched on the number moved for a reason that has nothing
#: to do with the gate: A3-2's ratio went 3.2 -> 9.1 on the rent switch alone.
#: The quantity is now a **difference of growth multiples**, each node measured
#: against its own opening claims, which no arm can move. The old threshold does
#: not survive the change of scale and is void; the new one is a split at half
#: the gates-shut gap. **Registered after seeing that the ratio was
#: contaminated, and before seeing any number on the new scale.**
A3_5_OPEN_VOID = 1.5
A3_5_SPLIT = 0.5
A3_6_SURVIVAL = 0.50
A3_6_HORIZON = 40
A3_6_SHOCK_ROUND = 150

WINDOWS = ((0, 100), (100, 200), (200, 300))

#: The registered run. ``WINDOWS`` already assumes three hundred rounds, so a
#: shorter run silently empties two of the three windows and A3-7 reads as a
#: failure that is really an empty measurement.
REGISTERED_SEEDS = 5
REGISTERED_ROUNDS = 300


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    void: bool = False
    #: Printed, never counted. A quantity worth reading that cannot decide
    #: anything: a floor, or an identity. Keeping these in the pass count made
    #: five passes look like five findings when two of them were one identity
    #: read twice. See ``docs/a3_asset_channel.md`` §5.1.
    diagnostic: bool = False

    def line(self) -> str:
        if self.diagnostic:
            mark = "diag"
        elif self.void:
            mark = "VOID"
        else:
            mark = "pass" if self.passed else "FAIL"
        return f"  {mark}  {self.name}\n        {self.detail}"


# ---------------------------------------------------------------------------
# running
# ---------------------------------------------------------------------------


def run(seed: int, rounds: int = 300, **asset_kw) -> A3Model:
    spec = AssetSpec(**asset_kw)
    model = A3Model(
        A3Config(
            asset=spec,
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )
    model.run()
    return model


def entry_pair(model: A3Model) -> tuple[np.ndarray, np.ndarray]:
    """The five entrants nearest the boundary from below, and the five
    non-entrants nearest it from above.

    The boundary is the opening allocation's, so the ranking is by claims at
    ``t = 0``, which is the ranking the allocation itself walked.
    """
    order = np.argsort(-model._claims_0, kind="stable")
    held = model.units.sum(axis=1) > 0
    entrants = [i for i in order if held[i]]
    outside = [i for i in order if not held[i]]
    return (
        np.array(entrants[-BOUNDARY:], dtype=int),
        np.array(outside[:BOUNDARY], dtype=int),
    )


def terms_pair(model: A3Model) -> tuple[np.ndarray, np.ndarray]:
    """Among agents who actually completed cycles, the best and worst terms.

    Both groups own and both trade; the only difference between them is
    ``gamma``. An agent with no completed cycle carries no evidence about the
    loop sum however far its net worth has moved, so it is excluded here even
    though it owns.

    **The width of the two groups is ``centrality_bins`` and used to be a
    hardcoded three.** Sorting by ``gamma`` is sorting by centrality:
    ``γ = γ̄(1 + κ(1 − c))`` is strictly monotone decreasing in ``c``, so the
    two orders are the same order and the field's name describes this cut. At
    ``centrality_bins = 3``, its default, ``width`` is ``order.size // 3`` and
    every number this function has ever produced is reproduced exactly.

    A bin count low enough to make the two groups overlap returns the empty
    pair, which A3-4 reads as void. Comparing a set against itself would give a
    holonomy of zero and a relative error of zero, so the criterion would score
    a perfect pass on a comparison that does not exist. Unreachable at any bin
    count of two or more, which is every value the grid uses.
    """
    traders = np.flatnonzero(model.cycles > 0)
    if traders.size < 2:
        return np.array([], dtype=int), np.array([], dtype=int)
    gamma = model.terms[traders, 0]
    order = traders[np.argsort(gamma)]
    width = max(1, order.size // max(1, model.a3.asset.centrality_bins))
    if 2 * width > order.size:
        return np.array([], dtype=int), np.array([], dtype=int)
    return order[:width], order[-width:]   # (better terms, worse terms)


def ratio_series(
    model: A3Model, better: np.ndarray, worse: np.ndarray
) -> np.ndarray:
    """Mean net worth of the better-termed group over the worse-termed one."""
    nw = np.asarray(model.net_worth_history)
    top = nw[:, better].mean(axis=1)
    bottom = nw[:, worse].mean(axis=1)
    return np.divide(top, bottom, out=np.ones_like(top), where=bottom > 0)


# ---------------------------------------------------------------------------
# the loop sum, from the product graph and nothing else
# ---------------------------------------------------------------------------


def loop_sum_from_graph(
    model: A3Model,
    better: np.ndarray,
    worse: np.ndarray,
    adjusted: dict[tuple[int, int], list[float]] | None = None,
):
    """``delta`` for the terms pair, computed on ``Gamma`` from terms alone.

    The two groups are collapsed to two agent classes by taking each group's
    mean terms, the field is built on the cash-and-tiers star, and the holonomy
    is read off the squares. Returns ``(delta, holonomy, price_free)``, where
    ``price_free`` is the largest discrepancy between the holonomy computed at
    the realised prices and at a deliberately unrelated pair of price vectors.
    It should be zero, and it is measured rather than asserted.
    """
    spec = model.a3.asset

    def collapse(group: np.ndarray) -> np.ndarray:
        """One agent class from a group of nodes.

        The **geometric** mean of the terms, weighted by how many trades each
        node actually made. The four-cycle is stated in logs, so an arithmetic
        mean of ``gamma`` is not the class's representative: the log of a mean
        is not the mean of a log, and using it left a thirty percent gap in
        A3-4 that had nothing to do with the mechanism. Weighting by trades is
        the same requirement from the other side, since the simulated number is
        a mean over trades and not over nodes.
        """
        members = group.tolist()
        weights = np.ones(len(members))
        if adjusted is not None:
            counts = {i: 0 for i in members}
            for (node, _tier), values in adjusted.items():
                if node in counts:
                    counts[node] += len(values)
            weights = np.array([max(counts[i], 0) for i in members], dtype=float)
            if weights.sum() <= 0:
                weights = np.ones(len(members))
        logs = np.log(model.terms[group])
        return np.exp(np.average(logs, axis=0, weights=weights))

    gamma = np.vstack([collapse(better), collapse(worse)])
    entry = np.asarray(spec.initial_price, dtype=float)
    exit_ = np.asarray(model.price, dtype=float)

    adj = tier_positions(spec.tiers)
    walks = squares(adj, 2)
    chain: Cochain = cochain_from_field(adj, tier_field(gamma, entry, exit_), 2)
    holonomy = float(np.mean([chain.sum_over(w) for w in walks]))

    unrelated = cochain_from_field(
        adj,
        tier_field(gamma, entry * 13.0 + 7.0, exit_ * 0.31 + 2.0),
        2,
    )
    price_free = max(
        abs(chain.sum_over(w) - unrelated.sum_over(w)) for w in walks
    )
    return holonomy / spec.holding_period, holonomy, float(price_free)


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------


def a3_1(seeds: range) -> Criterion:
    worst = 0.0
    for seed in seeds:
        cfg = NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed, rounds=300)
        base = run_network(cfg)
        got = A3Model(A3Config(asset=CLOSED, network=cfg)).run()
        for name in ("holdings", "effective_support", "total_volume", "issuance"):
            a = np.asarray(getattr(base, name))
            b = np.asarray(getattr(got, name))
            worst = max(worst, float(np.abs(a - b).max()))
    return Criterion(
        "A3-1  the closed channel reproduces A2 bitwise",
        worst == 0.0,
        f"largest absolute difference over {len(seeds)} seeds and four series: "
        f"{worst:.3e}. Not a tolerance: anything but zero is a different model",
    )


def a3_2(models: list[A3Model]) -> Criterion:
    ratios = []
    for m in models:
        inside, outside = entry_pair(m)
        nw = m.net_worth()
        below = float(nw[outside].mean())
        ratios.append(float(nw[inside].mean()) / below if below > 0 else np.inf)
    mean = float(np.mean(ratios))
    return Criterion(
        "A3-2  a gap opens between agents who started level",
        mean > A3_2_FLOOR,
        f"entry pair, {BOUNDARY} either side of the allocation boundary: mean "
        f"net worth ratio {mean:.1f} against a floor of {A3_2_FLOOR}. **A floor "
        f"and not a criterion**, demoted in §5.1: this is owning against not "
        f"owning, which is a gap produced by owning rather than by the terms of "
        f"owning, and it can be orders of magnitude wide while the loop sum is "
        f"exactly zero",
        diagnostic=True,
    )


def adjusted_trades(model: A3Model) -> dict[tuple[int, int], list[float]]:
    """Cell-adjusted realised return of each resale round trip, per node.

    The four-cycle is stated at a **fixed** entry and a **fixed** exit, so a
    realised return has to have the window taken out of it before it can be
    compared against a holonomy. The window's contribution is
    ``log(P_q(exit) / P_q(entry))``, and what is left is

        return - cell effect  =  log(reference price at entry / price paid)

    which the four-cycle predicts is exactly ``-log(gamma)``. Measuring the
    realised return without this adjustment reverses the sign of the effect: the
    badly-termed agents trade less often, each of their trades spans a longer
    window, prices rise, and the holding period pays them more than the terms
    cost them.

    Opening-allocation entries are excluded. A stretched entrant pays what it
    has rather than ``gamma * P``, so the identity does not hold there by
    construction, and including those trades would be measuring the stretch.
    """
    out: dict[tuple[int, int], list[float]] = {}
    for node, tier, entry_round, _exit, paid, _recv, reference in model.trades:
        if entry_round == 0:
            continue
        key = (int(node), int(tier))
        out.setdefault(key, []).append(float(np.log(reference / paid)))
    return out


def a3_3(models: list[A3Model]) -> Criterion:
    """The adjusted return per trade must be the same on every trade a node
    makes, which is what makes the gap compound rather than level off.

    A constant per-trade increment in logs is a geometric gap in levels: after
    ``N`` round trips the ratio is ``(gamma_w / gamma_b) ** N``. A decaying
    increment would be a leak that exhausts itself, which is the reading the
    framework denies.
    """
    worst, checked = 0.0, 0
    for m in models:
        for _key, series in adjusted_trades(m).items():
            if len(series) < 4:
                continue
            checked += 1
            half = len(series) // 2
            early, late = np.mean(series[:half]), np.mean(series[half:])
            scale = max(abs(early), 1e-12)
            worst = max(worst, abs(late - early) / scale)
    if not checked:
        return Criterion(
            "A3-3  the gap compounds rather than levelling off", False,
            "void: no node completed four resale round trips", void=True,
        )
    return Criterion(
        "A3-3  the gap compounds rather than levelling off",
        worst < 0.05,
        f"largest drift between a node's first and second half of trades, over "
        f"{checked} nodes with four or more: {worst:.2e}. **An assertion and "
        f"not a criterion**, demoted in §5.1: `adjusted return = -log gamma` "
        f"holds by construction, so this is a machine-precision reading of an "
        f"identity and belongs in the test suite. It is printed because a "
        f"non-zero value here would mean the identity had been broken",
        diagnostic=True,
    )


def a3_4(models: list[A3Model]) -> Criterion:
    """The registered form fitted an exponent against time. That had no
    measurement validity and was replaced; see section 9.6.

    What is compared now is a per-transaction quantity against a
    per-transaction quantity. The simulated side is the mean cell-adjusted
    return of each group, read off the trade ledger. The graph side is the
    holonomy of the four-cycle, computed by ``product_graph`` from the terms
    matrix alone. Neither sees the other.
    """
    rows = []
    for m in models:
        better, worse = terms_pair(m)
        if better.size == 0:
            continue
        adjusted = adjusted_trades(m)
        rb = [r for (i, _q), v in adjusted.items() if i in set(better.tolist())
              for r in v]
        rw = [r for (i, _q), v in adjusted.items() if i in set(worse.tolist())
              for r in v]
        if not rb or not rw:
            continue
        _, holonomy, price_free = loop_sum_from_graph(
            m, better, worse, adjusted
        )
        rows.append((float(np.mean(rb) - np.mean(rw)), holonomy, price_free))
    if not rows:
        return Criterion(
            "A3-4  the realised terms differential is the loop sum", False,
            "void: no terms pair completed a resale round trip", void=True,
        )
    observed = float(np.mean([r[0] for r in rows]))
    holonomy = float(np.mean([r[1] for r in rows]))
    price_free = max(r[2] for r in rows)
    rel = abs(observed - holonomy) / abs(holonomy) if holonomy else np.inf
    return Criterion(
        "A3-4  the realised terms differential is the loop sum",
        rel < A3_4_TOLERANCE,
        f"mean cell-adjusted return, better group minus worse: {observed:+.5f} "
        f"against a holonomy of {holonomy:+.5f} from the product graph, "
        f"relative error {rel:.2%} against {A3_4_TOLERANCE:.0%}. Price "
        f"cancellation observed, not assumed: largest holonomy shift under "
        f"unrelated prices {price_free:.2e}",
    )


def a3_5(seeds: range, **asset_kw) -> Criterion:
    """Opening a tier changes two things at once, so both are reported.

    **The sweep does not reach this criterion along the elasticity axis, and it
    is dropped here rather than left to the caller.** Section 4 registers `eta`
    as swept, and this criterion sweeps it itself: the verdict is taken on the
    price-frozen arm and the price-responsive arm is reported beside it,
    because the difference between them is the finding. A cell that varied
    `eta` would overwrite the two values the comparison is made of, so it would
    not be testing this criterion's robustness, it would be replacing the
    criterion. Section 6.5's record says which axes reach which criteria.

    ``open_tiers`` removes the gate, and the gate is also what defines the
    bidder pool, so admitting everyone to a tier both lets them in and floods
    the price with their claims. The first version measured only the combined
    effect, which answers "what happens when access is widened" and not the
    registered question, "is exclusion from the high tier what binds".

    The verdict is taken on the **price-frozen** arm, where opening a tier is a
    gate change and nothing else. The price-responsive arm is reported beside
    it because the difference between them is itself the finding.
    """

    def measure(
        open_tiers: tuple[int, ...], eta: float
    ) -> tuple[float, float]:
        """``(difference, ratio)`` between the two sides of the boundary.

        The **difference** is the verdict quantity. Each node's terminal net
        worth is divided by **its own opening claims**, which is a pre-treatment
        number no arm can move, and the two group means are then subtracted. The
        ratio is kept beside it only so the change of scale is auditable against
        the runs recorded before it.
        """
        diffs, ratios = [], []
        others = {k: v for k, v in asset_kw.items() if k != "elasticity"}
        for seed in seeds:
            m = run(seed, open_tiers=open_tiers, elasticity=eta, **others)
            inside, outside = entry_pair(m)
            nw = m.net_worth()
            base = np.maximum(m._claims_0, 1e-12)
            grown = nw / base
            diffs.append(float(grown[inside].mean() - grown[outside].mean()))
            below = float(nw[outside].mean())
            ratios.append(
                float(nw[inside].mean()) / below if below > 0 else np.inf
            )
        return float(np.mean(diffs)), float(np.mean(ratios))

    shut_d, shut_r = measure((), 0.0)
    low_d, low_r = measure((0,), 0.0)
    high_d, high_r = measure((2,), 0.0)
    _, low_live_r = measure((0,), 1.0)
    _, high_live_r = measure((2,), 1.0)
    split = A3_5_SPLIT * shut_d
    return Criterion(
        "A3-5  the gate binds at the high tier, not at ownership",
        bool(low_d > split > high_d),
        f"price frozen, so opening a tier is a gate change and nothing else. "
        f"Gap as a difference of growth multiples, each node against its own "
        f"opening claims: gates shut {shut_d:+.2f}, low tier open {low_d:+.2f}, "
        f"high tier open {high_d:+.2f}, against the registered split at "
        f"{A3_5_SPLIT:.0%} of shut, {split:+.2f}. Ratios for continuity with "
        f"the runs recorded before the rescale: shut {shut_r:.2f}, low "
        f"{low_r:.2f}, high {high_r:.2f} frozen; low {low_live_r:.2f}, high "
        f"{high_live_r:.2f} with the price free. VOID per §6.3: opening the "
        f"high tier is a bitwise no-op, because open_tiers never reaches "
        f"resale, the high tier allocates fully at the opening, and no "
        f"production-layer node can reach it even at the soft gate. At the high "
        f"tier the exclusion is a price wall and not a hole, so there is "
        f"nothing there for a gate criterion to measure",
        # Void, not failed. §6.3: the high-tier arm is a bitwise no-op for three
        # independent reasons, so the criterion cannot be evaluated, and a
        # recorded failure would be a claim about the gate that the run does not
        # make. The numbers are still printed; only the verdict is withheld.
        void=True,
    )


def _holders_at_shock(
    seed: int, **asset_kw
) -> tuple[np.ndarray, np.ndarray]:
    """``(holders, non-holders)`` as of the shock round.

    The population is read **at the moment of the shock** rather than at the
    end, because the criterion asks whether a transfer lands on someone who has
    a stock, and that is a fact about the recipient when the transfer arrives.
    """
    at_shock = run(seed, rounds=A3_6_SHOCK_ROUND, **asset_kw)
    held = at_shock.units.sum(axis=1) > 0
    return np.flatnonzero(held), np.flatnonzero(~held)


def _shock_survival(
    seed: int, target: int, base: A3Model | None = None, **asset_kw
) -> float:
    """What is left, after ``A3_6_HORIZON`` rounds, of a transfer to ``target``.

    Behaviour unchanged. The body moved into ``_shock_trace`` so that §16.1's
    profile can also see the deviation **at** the shock round, which is what
    tells "the transfer was recaptured" apart from "the transfer left no trace
    to measure". Those are different events and A3-6's ratio reports both as
    ``0.0``. Verified identical by re-running A3-6 and comparing its detail
    string character for character.
    """
    return _shock_trace(seed, target, base, **asset_kw)[0]


#: Horizons the §16.1 profile reads the same shock at. The registered forty is
#: one of them, so the criterion's own number is visible in the row. All five
#: come out of **one** model run per node: the deviation series is already
#: there and reading it at five points costs nothing, which is the only reason
#: the horizon question is answerable without a second sweep. The last is
#: bounded by the history's length, since the shock lands at round 150 of 300.
PROFILE_HORIZONS = (10, 20, 40, 80, 149)


def _shock_trace(
    seed: int,
    target: int,
    base: A3Model | None = None,
    *,
    shock_round: int = A3_6_SHOCK_ROUND,
    **asset_kw,
) -> tuple[float, float, dict[str, float]]:
    """``(retention, deviation at the shock round, retention by horizon)``.

    One model run. The third element exists because "does the step depend on
    how long you wait" is a question about the same series, not about a
    different experiment.

    ``shock_round`` defaults to the registered value, so A3-6's own path never
    passes it and cannot be moved by it. It is keyword-only and separate from
    ``asset_kw`` because it is not an ``AssetSpec`` field: it is *when* the
    transfer lands, and §16.1's whole difficulty turns out to live there.
    """
    base = base if base is not None else run(seed, **asset_kw)
    shocked = A3Model(
        A3Config(
            asset=AssetSpec(**asset_kw),
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=300
            ),
        )
    )
    original = shocked._pre_round

    def hook(t: int, _m=shocked, _i=target, _pre=original,
             _r=shock_round) -> None:
        _pre(t)
        if t == _r:
            gift = _m.holdings.sum() * 0.10
            _m.holdings -= gift / _m._n
            _m.holdings[_i] += gift

    shocked._pre_round = hook  # type: ignore[method-assign]
    shocked.run()

    a = np.asarray(base.net_worth_history)[:, target]
    b = np.asarray(shocked.net_worth_history)[:, target]
    dev = np.abs(b - a)
    start = float(dev[shock_round])
    end = float(dev[min(shock_round + A3_6_HORIZON, dev.size - 1)])
    by_h = {}
    for h in PROFILE_HORIZONS:
        at = min(shock_round + h, dev.size - 1)
        by_h[str(h)] = float(dev[at] / start) if start > 0 else 0.0
    return (end / start if start > 0 else 0.0), start, by_h


def a3_6(seeds: range, **asset_kw) -> Criterion:
    """Does a stock exist, and for whom? A4's precondition, and only that.

    **Rewritten. The domain was wrong and the obvious repair is forbidden.**

    As first registered the criterion shocked the **median node** and required
    half the transfer to survive forty rounds. The framework's own claim is that
    the median node cannot hold a stock, so the criterion demanded the model
    contradict its thesis before A4 could start. It measured `0.0%`.

    The tempting repair is to shock the **richest** node instead, which measures
    `62.2%` and passes. That repair is refused twice over. It is picking the arm
    that passes after seeing that it passes, which the earlier version of this
    docstring already named as the move this repository exists to avoid. And a
    single richest node is not "the population that holds a stock": swapping one
    single-node measurement for another and calling it a population is §11.10's
    error — a quantile taken on a handful of units — moved to a new place.

    **The domain is now the set that actually holds a unit when the transfer
    arrives**, read at the shock round rather than at the end, and the statistic
    is the **median over that set**, which is a legitimate statistic on fifteen
    to eighteen nodes in a way that a decile on ten never was.

    **The threshold is carried over and that is disclosed rather than hidden.**
    `A3_6_SURVIVAL` was registered against the median-node version, which
    failed, and it is being applied to a new domain by an author who has
    already seen the richest node's number. It is kept because lowering it would
    be worse, not because carrying it is clean.

    The non-holder arm is reported beside it. **That contrast is the finding,
    and it is worth more than the verdict**: a one-off transfer to a node with
    no asset is recaptured within a generation, while the same transfer to a
    holder is not. That is the redistribution-futility result, and it is what
    A6 goes on to price.
    """
    holder, nonholder, sizes, downstairs, every = [], [], [], [], []
    for seed in seeds:
        base = run(seed, **asset_kw)
        holders, others = _holders_at_shock(seed, **asset_kw)
        sizes.append(holders.size)
        downstairs.append(int(base._is_production[holders].sum()))
        if holders.size:
            v = [
                _shock_survival(seed, int(i), base, **asset_kw)
                for i in holders
            ]
            every.extend(v)
            holder.append(float(np.median(v)))
        if others.size:
            pick = others[others.size // 2]
            nonholder.append(_shock_survival(seed, int(pick), base))
    if not holder:
        return Criterion(
            "A3-6  a stock exists, and A4's domain is exactly who holds it",
            False,
            "void: nobody holds a unit at the shock round, so there is no "
            "population for A4 to run on at all",
            void=True,
        )
    med = float(np.mean(holder))
    non = float(np.mean(nonholder)) if nonholder else 0.0
    n = float(np.mean(sizes))
    prod = float(np.mean(downstairs))
    return Criterion(
        "A3-6  a stock exists, and A4's domain is exactly who holds it",
        med > A3_6_SURVIVAL,
        f"median holder retains {med:.1%} of the transfer after "
        f"{A3_6_HORIZON} rounds against {A3_6_SURVIVAL:.0%} required, and "
        f"**{float(np.mean(np.asarray(every) > A3_6_SURVIVAL)):.0%} of "
        f"{len(every)} holders clear the threshold**; a "
        f"non-holder retains {non:.1%}, against 0.00% on the A2 carrier. "
        f"**The holding population is {n:.1f} nodes of 200, of which "
        f"{prod:.1f} are in the production layer.** So A4's domain is "
        f"{n:.1f} nodes and they are upstairs, which is a constraint on A4 and "
        f"not a licence: four competitors that act on wealth, measured where "
        f"the wealth is, describe stratification *within* that set and not the "
        f"economy's. Threshold carried over from the median-node version, "
        f"disclosed in the docstring",
    )


def a3_7(models: list[A3Model]) -> Criterion:
    """Same sign in every window, measured on trades rather than on a series.

    A trade belongs to the window its sale falls in. A wedge that shows up in
    one window only is a single repricing rather than a per-period term.
    """
    per_window = []
    for m in models:
        better, worse = terms_pair(m)
        if better.size == 0:
            continue
        good, bad = set(better.tolist()), set(worse.tolist())
        signs = []
        for lo, hi in WINDOWS:
            rb, rw = [], []
            for node, _q, t0, t1, paid, _recv, ref in m.trades:
                if t0 == 0 or not (lo <= t1 < hi):
                    continue
                value = float(np.log(ref / paid))
                if node in good:
                    rb.append(value)
                elif node in bad:
                    rw.append(value)
            signs.append(bool(rb and rw and np.mean(rb) > np.mean(rw)))
        per_window.append(signs)
    if not per_window:
        return Criterion(
            "A3-7  non-overlapping windows agree in sign", False,
            "void: no terms pair to measure a window on", void=True,
        )
    rates = np.mean(per_window, axis=0)
    return Criterion(
        "A3-7  non-overlapping windows agree in sign",
        bool(np.all(np.array(per_window).all(axis=1))),
        "better terms beat worse in "
        + ", ".join(
            f"[{a},{b}): {p:.0%}"
            for (a, b), p in zip(WINDOWS, rates, strict=True)
        )
        + " of seeds. One window only would be a repricing",
    )


# ---------------------------------------------------------------------------
# the rent sweep, at a frozen price
# ---------------------------------------------------------------------------

#: §9.11. Rent moves three things at once -- the transfer itself, the price
#: path, and the composition of the landlord set -- and only the first is the
#: mechanism. ``elasticity = 0`` freezes the second. The third is then no longer
#: an artefact of the treatment: with the price fixed, a node that fails to buy
#: because rent took its claims failed for the reason under test, and the
#: transition matrix reported below is the evidence that it happens rarely
#: enough for the paired population to stay put.
def _state(c: Criterion) -> str:
    """The four states a criterion can be in, as one word.

    A verdict is not the only thing that can change. A criterion that was void
    and is now evaluable, or that was a diagnostic and is now decidable, has
    moved, and the sweep is asking whether anything moved.
    """
    if c.diagnostic:
        return "diag"
    if c.void:
        return "void"
    return "pass" if c.passed else "FAIL"


def sweep(
    seeds: range, rounds: int, cells: tuple[tuple[str, dict], ...],
    baseline: dict[str, str], baseline_details: dict[str, str],
    progress: bool = True,
) -> dict:
    """Section 4's robustness grid. Every live criterion at every cell.

    **A3-1 is excluded, and by construction rather than by choice.** It asks
    whether the closed channel reproduces stage A2 bitwise, and the closed
    channel is built from the module-level ``CLOSED`` spec, which no asset
    parameter reaches. Its verdict cannot move, so running it once per cell
    would measure nothing and would hide that fact behind a passing row.

    The verdict is that **no live criterion changes state at any cell**.
    Failures and voids count: A3-5 is void and A3-6 fails at the registered
    point, and either of those becoming a pass is as much a finding as a pass
    becoming a failure.

    **A cell whose details are identical to the registered point is flagged
    ``inert`` rather than counted as a pass.** A3-1 is excluded above by an
    argument made in advance; the same defect can exist in a parameter nobody
    argued about, and then the grid reports a knob that reaches no code as
    evidence of robustness. Every ``detail`` string carries an explicit format
    spec, so equality across all six of them is a bit-level statement that this
    cell changed nothing the criteria can see. It is reported and not gated:
    inertness is a fact about coverage, not a failure of the run.
    """
    out: dict[str, dict] = {}
    for axis, kw in cells:
        key = " ".join(f"{k}={v}" for k, v in sorted(kw.items()))
        started = time.time()
        models = [run(seed, rounds=rounds, **kw) for seed in seeds]
        deviations = sorted({d for m in models for d in m.deviations})
        criteria = [
            a3_2(models), a3_3(models), a3_4(models),
            a3_5(seeds, **kw), a3_6(seeds, **kw), a3_7(models),
        ]
        states = {c.name: _state(c) for c in criteria}
        moved = {
            name: f"{baseline[name]} -> {state}"
            for name, state in states.items()
            if name in baseline and baseline[name] != state
        }
        details = {c.name: c.detail for c in criteria}
        inert = all(
            details[name] == baseline_details[name]
            for name in details
            if name in baseline_details
        )
        out[key] = {
            "axis": axis,
            "parameters": kw,
            "states": states,
            "moved": moved,
            # True means every criterion's detail came out character-identical
            # to the registered point: this parameter reaches nothing the
            # criteria can see, so the cell is not evidence of robustness.
            "inert": inert,
            # A cell that trips a registered design tie is not a measurement
            # of anything, whether or not a criterion moved in it. Recorded
            # here so that a violated tie cannot again be something visible
            # only in stderr while the digest reports a clean row.
            "deviations": deviations,
            "details": details,
        }
        if progress:
            flag = "  ** DESIGN DEVIATION" if deviations else ""
            short = ", ".join(
                f"{name.split()[0]} {change}" for name, change in moved.items()
            )
            print(f"    {key:34s} "
                  + ("no state change" if not moved else f"MOVED: {short}")
                  + flag
                  + f"   {time.time() - started:5.1f}s", flush=True)
            if inert:
                print("        ** AXIS INERT: every criterion detail is "
                      "identical to the registered point, so this cell is not "
                      "evidence of robustness", flush=True)
    return {
        "baseline": baseline,
        "cells": out,
        "excluded": {
            "A3-1": "the closed channel reaches no asset parameter, so its "
                    "verdict is invariant by construction",
            "A3-5 on the eta axis": "the criterion sweeps eta itself and the "
                                    "comparison is between its two values",
        },
        "one_at_a_time": True,
        "interactions_not_tested": True,
        "cells_with_deviations": [
            k for k, c in out.items() if c["deviations"]
        ],
        # Named rather than counted. An inert cell costs the same to run as a
        # live one and looks identical in a pass count, which is how a grid
        # ends up reporting coverage it does not have.
        "cells_inert": [k for k, c in out.items() if c["inert"]],
        "live_cells": sum(1 for c in out.values() if not c["inert"]),
        # Both are required. A cell that tripped a design tie is not clean
        # even if nothing moved in it, because what it measured is not the
        # parameter it was varying.
        "passed": (
            not any(c["moved"] for c in out.values())
            and not any(c["deviations"] for c in out.values())
        ),
    }


def retention_profile(
    seeds: range, *, shock_round: int = A3_6_SHOCK_ROUND, **asset_kw
) -> dict:
    """`PROJECT_PLAN` §16.1 step one: retention at every node, not two of them.

    **This registers nothing and decides nothing.** A3-6 keeps its threshold,
    its domain and its verdict; nothing here is read into that criterion. It
    exists because §16.1 makes a claim about a *shape*, that a one-off transfer
    is retained in a step on whether the recipient holds an asset rather than
    along a gradient in wealth, and the evidence for that shape was **two
    points**: one holder statistic and one non-holder statistic. Two points
    cannot tell a step from a steep monotone gradient, and the step is the whole
    of what §16.1 wants to take to external data. So the profile is run first,
    internally, and it is allowed to come out either way.

    Every node in the population is shocked separately, which is one full model
    run each. The ordering is by ``holdings`` at the shock round, which is the
    closest quantity this model has to the income gradient the external
    literature is ranked on. The same profile is reported against **opening**
    claims as well, a pre-treatment quantity no arm can move, so a reader can
    see whether the shape depends on which of the two orderings is used.

    **The sharp comparison is the boundary pair**: the poorest node that holds a
    unit against the richest node that does not. Under a gradient the richer
    non-holder retains more; under a step the poorer holder does. That
    comparison needs no threshold and no distributional assumption, which is why
    it is reported first.

    Nodes whose deviation at the shock round is zero are counted separately
    rather than recorded as retaining nothing. "The transfer left no trace to
    measure" and "the transfer was recaptured" are different events, and
    folding the first into the second would manufacture the step this is
    supposed to be testing for.
    """
    rows: list[dict] = []
    for seed in seeds:
        base = run(seed, **asset_kw)
        at_shock = run(seed, rounds=shock_round, **asset_kw)
        wealth = np.asarray(at_shock.holdings, dtype=float)
        net = np.asarray(at_shock.net_worth(), dtype=float)
        held = at_shock.units.sum(axis=1) > 0
        opening = np.asarray(base._claims_0, dtype=float)
        for i in range(base._n):
            keep, start, by_h = _shock_trace(
                seed, int(i), base, shock_round=shock_round, **asset_kw
            )
            rows.append(
                {
                    "seed": int(seed),
                    "node": int(i),
                    "shock_round": int(shock_round),
                    "holder": bool(held[i]),
                    "production": bool(base._is_production[i]),
                    "retention_by_horizon": by_h,
                    "wealth_at_shock": float(wealth[i]),
                    # Claims alone exclude the value of the units a holder
                    # owns, which is the quantity closest to the liquid
                    # resources the external literature ranks on. Net worth
                    # includes them and is reported beside it, because a
                    # reading of this profile that depends on which of the two
                    # is used is a reading about the choice.
                    "net_worth_at_shock": float(net[i]),
                    "opening_claims": float(opening[i]),
                    "retention": float(keep),
                    "shock_footprint": float(start),
                }
            )
        print(f"    seed {seed}: {base._n} nodes shocked, "
              f"{int(held.sum())} of them holders", flush=True)
    return summarise_profile(rows)


def summarise_profile(rows: list[dict]) -> dict:
    """Read the profile without deciding anything from it.

    Four descriptions, none of which needs a threshold.

    **The boundary pair**, per seed: the poorest holder against the richest
    non-holder. This is the whole gradient-or-step question in two numbers, and
    it is the one comparison where the two hypotheses predict opposite signs.

    **Retention by wealth decile, holders and non-holders separately.** A
    gradient shows retention climbing across the deciles *within* the
    non-holders; a step shows it flat and low across all of them.

    **The largest adjacent jump** in the rank-ordered retention curve, with its
    location, next to the location of the holding boundary. If the curve's one
    big discontinuity sits somewhere else entirely, the step is not the step
    §16.1 describes.

    **Overlap**, in both directions: the share of non-holders retaining more
    than the median holder, and the share of holders retaining less than the
    median non-holder. Two separated populations overlap in neither direction.
    """
    seeds = sorted({r["seed"] for r in rows})

    def boundary_pair(key: str) -> list[dict]:
        out = []
        for s in seeds:
            block = [r for r in rows if r["seed"] == s]
            hold = [r for r in block if r["holder"]]
            free = [r for r in block if not r["holder"]]
            if not hold or not free:
                continue
            poorest = min(hold, key=lambda r: r[key])
            richest = max(free, key=lambda r: r[key])
            # The pair separates the two hypotheses **only** when the holder is
            # the poorer of the two. When the poorest holder is still richer
            # than every non-holder, both hypotheses predict the same sign and
            # the cell says nothing; calling it a step there would be reading a
            # confirmation out of a comparison that could not have come out the
            # other way.
            discriminating = poorest[key] < richest[key]
            out.append(
                {
                    "seed": s,
                    "poorest_holder_wealth": poorest[key],
                    "poorest_holder_retention": poorest["retention"],
                    "richest_nonholder_wealth": richest[key],
                    "richest_nonholder_retention": richest["retention"],
                    "discriminating": bool(discriminating),
                    "step": bool(
                        discriminating
                        and poorest["retention"] > richest["retention"]
                    ),
                }
            )
        return out

    boundary = boundary_pair("wealth_at_shock")

    def deciles(key: str) -> list[dict]:
        out = []
        for d in range(10):
            block = []
            for s in seeds:
                per = sorted(
                    (r for r in rows if r["seed"] == s), key=lambda r: r[key]
                )
                lo = d * len(per) // 10
                hi = (d + 1) * len(per) // 10
                block.extend(per[lo:hi])
            hold = [r["retention"] for r in block if r["holder"]]
            free = [r["retention"] for r in block if not r["holder"]]
            out.append(
                {
                    "decile": d + 1,
                    "n_holders": len(hold),
                    "n_nonholders": len(free),
                    "holder_median": float(np.median(hold)) if hold else None,
                    "nonholder_median": float(np.median(free)) if free else None,
                }
            )
        return out

    jumps = []
    for s in seeds:
        per = sorted(
            (r for r in rows if r["seed"] == s), key=lambda r: r["wealth_at_shock"]
        )
        keep = np.array([r["retention"] for r in per])
        flags = np.array([r["holder"] for r in per])
        steps = np.abs(np.diff(keep))
        at = int(np.argmax(steps)) if steps.size else 0
        first_holder = int(np.argmax(flags)) if flags.any() else -1
        jumps.append(
            {
                "seed": s,
                "largest_adjacent_jump": float(steps[at]) if steps.size else 0.0,
                "at_rank": at + 1,
                "of_ranks": len(per),
                "first_holder_at_rank": first_holder + 1,
                # A holding boundary that is not a single crossing means the
                # ranking and the holding status disagree, which is itself a
                # finding about the shape and is reported rather than smoothed.
                "holder_block_is_contiguous": bool(
                    flags.any() and flags[first_holder:].all()
                ),
            }
        )

    def within_group(holder: bool, key: str = "wealth_at_shock") -> dict:
        """Does retention still climb with wealth **inside** one group?

        This is the test the deciles cannot do. Holding and top-decile wealth
        turn out to be nearly collinear in this model, so a table of deciles
        compares two things that barely vary independently. Inside a group the
        holding status is constant by construction, so any remaining
        relationship with wealth is gradient and nothing else. Spearman, on
        ranks, because retention spans four orders of magnitude and a
        correlation on levels would be a correlation with the top few nodes.
        """
        block = [r for r in rows if r["holder"] is holder]
        if len(block) < 3:
            return {"n": len(block), "spearman": None}
        w = np.argsort(np.argsort([r[key] for r in block]))
        k = np.argsort(np.argsort([r["retention"] for r in block]))
        w = w - w.mean()
        k = k - k.mean()
        denom = float(np.sqrt((w * w).sum() * (k * k).sum()))
        return {
            "n": len(block),
            "spearman": float((w * k).sum() / denom) if denom > 0 else None,
        }

    def layer_groups() -> list[dict]:
        """Three groups, not two, because the two-group split is confounded.

        A3-6 and the two-point picture compare **holders** against
        **non-holders**. In this model every holder is a financial-layer node
        and no production-layer node ever holds, so that comparison also swaps
        the layer, and the layer carries two things of its own that have
        nothing to do with owning an asset: ``_collect_rent`` bills only
        ``_is_production`` nodes, and ``_prior_owner_weights`` routes the
        opening proceeds and the unsold residual to the financial layer.

        So the split is the full two by two, layer against holding, and the two
        cells that answer §16.1 are the **production-layer** pair: same layer,
        same rent liability, same everything the construction assigns, and the
        asset is the only thing that differs. That cell is **empty at the
        registered shock round of 150**, because the production layer holds
        nothing by then. It is populated at an early shock round, which is why
        ``--profile-shock-round`` exists.
        """
        spec = {
            "financial_layer_with_asset": (
                lambda r: r["holder"] and not r["production"]
            ),
            "financial_layer_no_asset": (
                lambda r: not r["holder"] and not r["production"]
            ),
            "production_layer_with_asset": (
                lambda r: r["holder"] and r["production"]
            ),
            "production_layer_no_asset": (
                lambda r: not r["holder"] and r["production"]
            ),
        }
        out = []
        for name, pick in spec.items():
            block = [r for r in rows if pick(r)]
            if not block:
                out.append({"group": name, "n": 0})
                continue
            keep = np.array([r["retention"] for r in block])
            out.append(
                {
                    "group": name,
                    "n": len(block),
                    "median": float(np.median(keep)),
                    "mean": float(keep.mean()),
                    "p25": float(np.percentile(keep, 25)),
                    "p75": float(np.percentile(keep, 75)),
                    "median_wealth": float(
                        np.median([r["wealth_at_shock"] for r in block])
                    ),
                    "by_horizon": {
                        str(h): float(
                            np.median(
                                [r["retention_by_horizon"][str(h)] for r in block]
                            )
                        )
                        for h in PROFILE_HORIZONS
                    },
                }
            )
        return out

    hold_all = [r["retention"] for r in rows if r["holder"]]
    free_all = [r["retention"] for r in rows if not r["holder"]]
    med_h = float(np.median(hold_all)) if hold_all else 0.0
    med_f = float(np.median(free_all)) if free_all else 0.0
    traceless = [r for r in rows if r["shock_footprint"] <= 0.0]
    grew = [r for r in rows if r["retention"] > 1.0]
    holder_ranks = []
    for s in seeds:
        per = sorted(
            (r for r in rows if r["seed"] == s), key=lambda r: r["wealth_at_shock"]
        )
        idx = [i + 1 for i, r in enumerate(per) if r["holder"]]
        if idx:
            holder_ranks.append(
                {"seed": s, "lowest": min(idx), "highest": max(idx),
                 "of": len(per)}
            )
    return {
        "diagnostic_only": (
            "registers nothing and feeds no criterion; PROJECT_PLAN 16.1 "
            "step one"
        ),
        "shock_round": int(rows[0].get("shock_round", A3_6_SHOCK_ROUND)),
        "horizon": A3_6_HORIZON,
        "n_rows": len(rows),
        "boundary_pair": boundary,
        # The same pair under two other orderings. If the reading depends on
        # which one is used, the reading is about the ordering.
        "boundary_pair_by_net_worth": boundary_pair("net_worth_at_shock"),
        "boundary_pair_by_opening_claims": boundary_pair("opening_claims"),
        "by_layer_group": layer_groups(),
        "horizons": list(PROFILE_HORIZONS),
        "by_wealth_decile": deciles("wealth_at_shock"),
        "by_opening_claims_decile": deciles("opening_claims"),
        "largest_jump": jumps,
        "holder_median": med_h,
        "nonholder_median": med_f,
        "nonholders_above_holder_median": float(
            np.mean([r > med_h for r in free_all]) if free_all else 0.0
        ),
        "holders_below_nonholder_median": float(
            np.mean([r < med_f for r in hold_all]) if hold_all else 0.0
        ),
        "n_holders": len(hold_all),
        "n_nonholders": len(free_all),
        # Counted, never folded into a retention of zero.
        "n_no_measurable_shock": len(traceless),
        # A retention above one means the deviation was larger forty rounds
        # after the transfer than at the moment it landed. Reported because a
        # profile that calls that "retention" without saying so is describing
        # amplification in the vocabulary of survival.
        "n_retention_above_one": len(grew),
        "gradient_within_holders": within_group(True),
        "gradient_within_nonholders": within_group(False),
        "gradient_within_holders_net_worth": within_group(
            True, "net_worth_at_shock"
        ),
        "gradient_within_nonholders_net_worth": within_group(
            False, "net_worth_at_shock"
        ),
        "holder_wealth_ranks": holder_ranks,
        "rows": rows,
    }


RENT_RATES = (0.0, 0.002, 0.005, 0.01, 0.02, 0.05)


def _holding_mask(model: A3Model) -> np.ndarray:
    return model.units.sum(axis=1) > 0


def _transition(base: A3Model, arm: A3Model) -> tuple[int, int, int, int]:
    """``(both, base only, arm only, neither)`` over production-layer nodes."""
    prod = base._is_production
    b, a = _holding_mask(base)[prod], _holding_mask(arm)[prod]
    return (
        int((b & a).sum()),
        int((b & ~a).sum()),
        int((~b & a).sum()),
        int((~b & ~a).sum()),
    )


def rent_sweep(seeds: range, rounds: int) -> dict:
    """The pure transfer, isolated, paired by node, at a frozen price.

    §9.11 delivered ``rent_rate`` as a switch and then forbade reporting any
    number from it until the price path was frozen too, because a median near
    zero is extremely sensitive to a price path the treatment also moved. This
    is that arm.

    Three rules from ``MEASUREMENT.md`` are load-bearing here and each one is
    answered in the output rather than in a comment:

    * **Rule 4, one thing at a time.** ``elasticity = 0`` throughout, so the
      only live channel is the transfer.
    * **Rule 5, population.** Every node is compared against *itself* in the
      baseline arm. The measured set is the intersection of the never-holders
      across all rates, and the number of nodes that had to be dropped to form
      that intersection is reported. If it is not zero the comparison is
      composition-contaminated and the reader can see so.
    * **Rule 1, time quantifier.** The claim is that holding *continuously*
      takes from non-holding, so the flow is reported per round as well as
      cumulatively, and both are normalised by total claims.

    The zero calibration is checklist item 7. ``rent_rate = 0`` is run as a
    **separate model** from the baseline rather than being aliased to it, so the
    row at rate zero compares two independent executions of the same
    configuration and must come out bitwise identical. Aliasing it to the
    baseline would have made that row a tautology and tested nothing.
    """
    per_rate: dict[str, dict] = {}
    dropped_total = 0
    for seed in seeds:
        base = run(seed, rounds=rounds, rent_rate=0.0, elasticity=0.0)
        arms = {
            r: run(seed, rounds=rounds, rent_rate=r, elasticity=0.0)
            for r in RENT_RATES
        }
        prod = base._is_production
        never = prod & ~_holding_mask(base)
        for r in RENT_RATES:
            never = never & ~_holding_mask(arms[r])
        dropped_total += int((prod & ~_holding_mask(base)).sum() - never.sum())

        claims_0 = np.maximum(base._claims_0, 1e-12)
        nw_base = base.net_worth()
        holders = prod & _holding_mask(base)
        #: Receipts go out in proportion to units held, and the financial layer
        #: holds most of the units, so the destination of the transfer is not
        #: the production-layer landlord. Both are reported: a channel whose
        #: nominal beneficiaries also lose is a different claim from a channel
        #: that moves resources up, and the two are told apart here.
        upstairs = ~prod & _holding_mask(base)
        total_claims = float(base._claims_0.sum())

        for r in RENT_RATES:
            arm = arms[r]
            delta = (arm.net_worth() - nw_base) / claims_0
            rents = np.asarray(arm.rent_history, dtype=float)
            row = per_rate.setdefault(
                f"{r:g}",
                {
                    "renter_delta_median": [],
                    "renter_delta_worst": [],
                    "landlord_delta_median": [],
                    "landlord_n": [],
                    "financial_delta_median": [],
                    "financial_n": [],
                    "rent_per_round_share": [],
                    "rent_cumulative_share": [],
                    "transition": [],
                    "renters": [],
                },
            )
            row["renter_delta_median"].append(float(np.median(delta[never])))
            row["renter_delta_worst"].append(float(delta[never].min()))
            row["landlord_delta_median"].append(
                float(np.median(delta[holders])) if holders.any() else 0.0
            )
            row["landlord_n"].append(int(holders.sum()))
            row["financial_delta_median"].append(
                float(np.median(delta[upstairs])) if upstairs.any() else 0.0
            )
            row["financial_n"].append(int(upstairs.sum()))
            row["rent_per_round_share"].append(
                float(rents.mean() / total_claims) if rents.size else 0.0
            )
            row["rent_cumulative_share"].append(
                float(arm.rent_collected / total_claims)
            )
            row["transition"].append(list(_transition(base, arm)))
            row["renters"].append(int(never.sum()))

    summary = {
        rate: {
            k: (v if k == "transition" else float(np.mean(v)))
            for k, v in row.items()
        }
        for rate, row in per_rate.items()
    }
    zero = summary["0"]
    return {
        "elasticity": 0.0,
        "rates": list(RENT_RATES),
        "dropped_from_paired_population": dropped_total,
        "zero_calibration_ok": zero["renter_delta_median"] == 0.0
        and zero["landlord_delta_median"] == 0.0,
        "per_rate": summary,
    }


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[-1] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add((node.module or "").split(".")[-1])
            out |= {a.name for a in node.names}
    return out


def assert_no_shared_code() -> None:
    """A3-4's force is that the two numbers come from unrelated code.

    Imports only, read from the syntax tree. A first version matched the module
    name anywhere in the text and fired on a docstring that merely says where
    the loop sum lives, which is the same class of error as checking lint with a
    regex: a mention is not a dependency.
    """
    src = ROOT / "src" / "monetary_topology"
    if "product_graph" in _imported_modules(src / "asset.py"):
        raise AssertionError("asset.py imports product_graph: A3-4 is circular")
    if "asset" in _imported_modules(src / "product_graph.py"):
        raise AssertionError("product_graph.py imports asset: A3-4 is circular")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument(
        "--sweep",
        action="store_true",
        help="section 4's robustness grid, one parameter at a time. "
             "Costs one full criteria evaluation per cell",
    )
    ap.add_argument(
        "--sweep-max",
        type=int,
        default=0,
        help="run only the first N sweep cells. For measuring the cost "
             "before committing to the whole grid; 0 runs all of them",
    )
    ap.add_argument(
        "--rent-sweep",
        action="store_true",
        help="the frozen-price rent arm. Costs one run per rate per seed",
    )
    ap.add_argument(
        "--retention-profile",
        action="store_true",
        help="PROJECT_PLAN 16.1 step one: retention at every node rank rather "
             "than at two points. Diagnostic, registers nothing. Costs one "
             "model run per node per seed",
    )
    ap.add_argument(
        "--profile-shock-round",
        type=int,
        default=A3_6_SHOCK_ROUND,
        help="when the transfer lands, for the profile only. A3-6 keeps its "
             "registered 150 whatever this is set to. At 150 the production "
             "layer holds nothing, so holding and layer are the same variable "
             "and 16.1's question cannot be asked; early rounds have a real "
             "population of production-layer holders to compare against",
    )
    ap.add_argument(
        "--profile-arm",
        choices=("registered", "open-frozen", "open-free"),
        default="registered",
        help="which arm to profile. `registered` cannot separate holding from "
             "wealth, because holding IS clearing a wealth gate there. The "
             "two `open` arms admit the low tier regardless of claims, which "
             "is the only switch in the model that breaks that identity; "
             "`open-frozen` also holds the price still, which is the arm A3-5 "
             "takes its own verdict on",
    )
    args = ap.parse_args()
    seeds = range(args.seeds)

    assert_no_shared_code()
    print("A3: the asset channel\n")
    print(f"  running {args.seeds} seeds at the registered parameters")
    models = [run(seed, rounds=args.rounds) for seed in seeds]
    deviations = sorted({d for m in models for d in m.deviations})

    criteria = [
        a3_1(seeds),
        a3_2(models),
        a3_3(models),
        a3_4(models),
        a3_5(seeds),
        a3_6(seeds),
        a3_7(models),
    ]

    grid = None
    if args.sweep:
        cells = SWEEP_CELLS[: args.sweep_max] if args.sweep_max else SWEEP_CELLS
        print(f"\n  section 4 robustness grid, {len(cells)} of "
              f"{len(SWEEP_CELLS)} cells, one parameter at a time")
        # Criterion names carry their claim after the tag, so the tag is
        # matched on its prefix. Comparing against the bare "A3-1" silently
        # matched nothing, which is the shape of defect this sweep exists
        # to catch in the model.
        baseline = {
            c.name: _state(c)
            for c in criteria
            if not c.name.startswith("A3-1 ")
        }
        baseline_details = {
            c.name: c.detail
            for c in criteria
            if not c.name.startswith("A3-1 ")
        }
        grid = sweep(seeds, args.rounds, cells, baseline, baseline_details)
        headline = (
            "no criterion changed state"
            if grid["passed"]
            else "A CRITERION CHANGED STATE"
        )
        print(f"    {headline} across {len(cells)} cells. A3-1 is excluded by "
              f"construction and the eta axis does not reach A3-5")
        print(f"    {grid['live_cells']} of {len(cells)} cells varied "
              f"something a criterion can see; the rest are named in the "
              f"result file and are not evidence of anything")

    sweep_result = None
    if args.rent_sweep:
        print("\n  rent sweep at a frozen price (elasticity = 0)")
        sweep_result = rent_sweep(seeds, args.rounds)
        print(
            f"    zero calibration: "
            f"{'ok' if sweep_result['zero_calibration_ok'] else 'BROKEN'};"
            f" dropped from the paired population: "
            f"{sweep['dropped_from_paired_population']}"
        )
        for rate in RENT_RATES:
            row = sweep_result["per_rate"][f"{rate:g}"]
            print(
                f"    rent={rate:<6g} renter {row['renter_delta_median']:+.4f} "
                f"(worst {row['renter_delta_worst']:+.4f})  landlord "
                f"{row['landlord_delta_median']:+.4f} (n={row['landlord_n']:.1f})"
                f"  L1 {row['financial_delta_median']:+.4f} "
                f"(n={row['financial_n']:.1f})  flow/round "
                f"{row['rent_per_round_share']:.2e}  cumulative "
                f"{row['rent_cumulative_share']:.4f}"
            )
        print(
            "    renter and landlord figures are paired net worth changes "
            "against the same node in the rent-free arm, each divided by that "
            "node's own opening claims. `n` is the size of the group the "
            "median is taken over, printed because §11.10's error was a "
            "quantile on ten units and the production-layer landlord set here "
            "is routinely empty"
        )

    if args.retention_profile:
        print("\n  PROJECT_PLAN §16.1 step one: retention at every node rank")
        print("  Diagnostic. It registers nothing, feeds no criterion, and is "
              "allowed to\n  come out either way. Until it is read, \"the model "
              "predicts a step\" rests\n  on two points, which cannot tell a "
              "step from a steep gradient.")
        # No `--rounds`: the shock machinery is pinned to the registered three
        # hundred rounds internally, exactly as A3-6 runs it, so the profile
        # describes the criterion's own configuration and not a nearby one.
        #
        # `open_tiers = (0,)` is the low tier. §6.3 records that opening the
        # **high** tier is a bitwise no-op, so it is not offered here: an arm
        # that changes nothing would answer the question by not asking it.
        arm_kw = {
            "registered": {},
            "open-frozen": {"open_tiers": (0,), "elasticity": 0.0},
            "open-free": {"open_tiers": (0,)},
        }[args.profile_arm]
        print(f"    arm: {args.profile_arm}"
              + (f", {arm_kw}" if arm_kw else ", the registered parameters"))
        profile = retention_profile(
            seeds, shock_round=args.profile_shock_round, **arm_kw
        )
        profile["arm"] = args.profile_arm
        profile["arm_parameters"] = {k: list(v) if isinstance(v, tuple) else v
                                     for k, v in arm_kw.items()}
        print(f"\n    shock at round {profile['shock_round']}, measured "
              f"{profile['horizon']} rounds later, {profile['n_rows']} nodes "
              f"shocked one at a time")
        print(f"    holders {profile['n_holders']}, non-holders "
              f"{profile['n_nonholders']}, no measurable shock "
              f"{profile['n_no_measurable_shock']}")

        print("\n    layer against holding, the full two by two. Holding and "
              "layer are separate\n    questions and the two-point picture "
              "answers only their product; rent is billed\n    to "
              "`_is_production` nodes and the opening proceeds are routed to "
              "the financial\n    layer, so swapping the layer swaps those too.")
        print("      group                          n   median     mean      "
              "p25      p75   median wealth")
        for g in profile["by_layer_group"]:
            if not g["n"]:
                print(f"      {g['group']:<28s} {0:>4d}   EMPTY at this shock "
                      f"round")
                continue
            print(f"      {g['group']:<28s} {g['n']:>4d} {g['median']:8.2%} "
                  f"{g['mean']:8.2%} {g['p25']:8.2%} {g['p75']:8.2%} "
                  f"{g['median_wealth']:14.3f}")
        print("      The two production-layer rows are the comparison that "
              "answers §16.1: same\n      layer, same rent liability, only the "
              "asset differs.")

        print("\n    the same three groups at five horizons, median retention "
              "(the registered one is 40):")
        head = "".join(f"{h:>10d}" for h in profile["horizons"])
        print(f"      {'group':<28s}{head}")
        for g in profile["by_layer_group"]:
            if not g["n"]:
                continue
            cells = "".join(
                f"{g['by_horizon'][str(h)]:9.2%} " for h in profile["horizons"]
            )
            print(f"      {g['group']:<28s}{cells}")

        print("\n    the boundary pair, the one comparison where the two "
              "hypotheses disagree in sign:")
        print("      seed   poorest holder            richest non-holder"
              "        reads as")
        for b in profile["boundary_pair"]:
            if not b["discriminating"]:
                verdict = "says nothing: the holder is the richer of the two"
            else:
                verdict = "step" if b["step"] else "GRADIENT"
            print(f"      {b['seed']:<6d} "
                  f"w={b['poorest_holder_wealth']:9.3f} "
                  f"keeps {b['poorest_holder_retention']:7.2%}   "
                  f"w={b['richest_nonholder_wealth']:9.3f} "
                  f"keeps {b['richest_nonholder_retention']:7.2%}   "
                  f"{verdict}")
        n_disc = sum(b["discriminating"] for b in profile["boundary_pair"])
        print(f"      {n_disc} of {len(profile['boundary_pair'])} seeds put a "
              f"non-holder above a holder in wealth, which is the only "
              f"arrangement\n      in which this pair can come out either way")
        for label, key in (
            ("net worth at the shock round", "boundary_pair_by_net_worth"),
            ("opening claims", "boundary_pair_by_opening_claims"),
        ):
            pairs = profile[key]
            d = sum(b["discriminating"] for b in pairs)
            st = sum(b["step"] for b in pairs)
            print(f"      ordered instead by {label}: {d} of {len(pairs)} "
                  f"seeds discriminate, {st} of those read as a step")

        print("\n    retention by wealth decile at the shock round, median "
              "within each group:")
        print("      decile   holders  median      non-holders  median")
        for d in profile["by_wealth_decile"]:
            hm = "  n/a  " if d["holder_median"] is None else \
                f"{d['holder_median']:7.2%}"
            fm = "  n/a  " if d["nonholder_median"] is None else \
                f"{d['nonholder_median']:7.2%}"
            print(f"      {d['decile']:<8d} {d['n_holders']:>7d}  {hm}      "
                  f"{d['n_nonholders']:>10d}  {fm}")

        print("\n    largest adjacent jump in the rank-ordered curve, against "
              "where holding starts:")
        for j in profile["largest_jump"]:
            print(f"      seed {j['seed']}: jump {j['largest_adjacent_jump']:.2%}"
                  f" at rank {j['at_rank']}/{j['of_ranks']}, first holder at "
                  f"rank {j['first_holder_at_rank']}, holders contiguous "
                  f"{j['holder_block_is_contiguous']}")

        print(f"\n    overlap: {profile['nonholders_above_holder_median']:.1%} "
              f"of non-holders retain more than the median holder "
              f"({profile['holder_median']:.2%}); "
              f"{profile['holders_below_nonholder_median']:.1%} of holders "
              f"retain less than the median non-holder "
              f"({profile['nonholder_median']:.2%})")
        print("    Two separated populations overlap in neither direction. "
              "This is reported\n    and not scored: no threshold is "
              "registered for any of it.")

        gh = profile["gradient_within_holders"]
        gf = profile["gradient_within_nonholders"]
        rho_h = "n/a" if gh["spearman"] is None else f"{gh['spearman']:+.3f}"
        rho_f = "n/a" if gf["spearman"] is None else f"{gf['spearman']:+.3f}"
        print("\n    inside each group, where holding is constant and only "
              "wealth varies:")
        print(f"      holders     n={gh['n']:<4d} "
              f"Spearman(retention, wealth) = {rho_h}")
        print(f"      non-holders n={gf['n']:<4d} "
              f"Spearman(retention, wealth) = {rho_f}")
        gh2 = profile["gradient_within_holders_net_worth"]
        gf2 = profile["gradient_within_nonholders_net_worth"]
        r2h = "n/a" if gh2["spearman"] is None else f"{gh2['spearman']:+.3f}"
        r2f = "n/a" if gf2["spearman"] is None else f"{gf2['spearman']:+.3f}"
        print(f"      the same against net worth instead: holders {r2h}, "
              f"non-holders {r2f}")
        print("      A step predicts these near zero; a gradient predicts them "
              "strongly positive.\n      This is the test the deciles cannot "
              "do, because holding and top-decile\n      wealth are nearly "
              "collinear here:")
        for h in profile["holder_wealth_ranks"]:
            print(f"        seed {h['seed']}: holders occupy wealth ranks "
                  f"{h['lowest']} to {h['highest']} of {h['of']}")
        print(f"\n    {profile['n_retention_above_one']} of "
              f"{profile['n_rows']} nodes end with a larger deviation than "
              f"they started with, which is amplification and not retention")

        RESULTS.mkdir(parents=True, exist_ok=True)
        default_run = (
            args.profile_arm == "registered"
            and args.profile_shock_round == A3_6_SHOCK_ROUND
        )
        pf = RESULTS / (
            "a3_retention_profile.json"
            if default_run
            else f"a3_retention_profile.{args.profile_arm}"
                 f".shock{args.profile_shock_round}.json"
        )
        pf.write_text(
            json.dumps({"stage": "A3 §16.1 step one", "seeds": args.seeds,
                        **profile}, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\n    wrote {pf.relative_to(ROOT)}, kept out of "
              f"a3_asset_channel.json so a diagnostic cannot reach a criterion")

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    live = [c for c in criteria if not (c.void or c.diagnostic)]
    n_pass = sum(c.passed for c in live)
    n_void = sum(c.void for c in criteria)
    n_diag = sum(c.diagnostic for c in criteria)
    print(f"\n  {n_pass}/{len(live)} live criteria passed, {n_void} void, "
          f"{n_diag} diagnostic")
    print("  A3-8, the load-bearing intervention, is evaluated separately in "
          "experiments/a3c_load_bearing.py")
    if deviations:
        print("\n  DEVIATIONS -- no headline number may be taken from this run:")
        for d in deviations:
            print(f"    {d}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    #: Only a run at the registered parameters may claim the registered
    #: filename. A hand-off once lost the stored 5-seed result by running
    #: two seeds for a hundred and twenty rounds to check that a new code path
    #: executed; nothing warned it, because the writer did not care what it had
    #: been asked to run. Off-parameter runs land under their own name.
    registered = args.seeds == REGISTERED_SEEDS and args.rounds == REGISTERED_ROUNDS
    out = RESULTS / (
        "a3_asset_channel.json"
        if registered
        else f"a3_asset_channel.offparam_{args.seeds}x{args.rounds}.json"
    )
    if not registered:
        print(
            f"\n  off-parameter run ({args.seeds} seeds, {args.rounds} rounds "
            f"against the registered {REGISTERED_SEEDS}x{REGISTERED_ROUNDS}): "
            f"writing beside the registered result, not over it"
        )
    # A plain run must not delete a stored grid. Without this, running this
    # file with no flags after a --sweep run writes `"sweep": null` over the
    # only record that §6.5's registered commitment was met, and nothing says
    # so. Carried forward with a flag on it instead, because presenting an old
    # grid as this run's output would be the opposite error.
    def carried(key: str, produced):
        if produced is not None or not out.exists():
            return produced
        try:
            prior = json.loads(out.read_text(encoding="utf-8")).get(key)
        except (OSError, json.JSONDecodeError):
            return None
        if prior is None:
            return None
        print(f"\n  carrying forward the stored `{key}` left by an earlier "
              f"run, marked in the file as being from one. This run did not "
              f"produce it")
        return {**prior, "from_an_earlier_run": True}

    grid = carried("sweep", grid)
    sweep_result = carried("rent_sweep", sweep_result)

    out.write_text(
        json.dumps(
            {
                "stage": "A3",
                "seeds": args.seeds,
                "rounds": args.rounds,
                # The seven criteria run at the registered defaults. Recorded
                # here because the stored result and the registered value have
                # already drifted apart once, silently.
                "registered_rent_rate": AssetSpec().rent_rate,
                "deviations": deviations,
                "rent_sweep": sweep_result,
                "sweep": grid,
                "market": {
                    "sales": [int(sum(m.sales)) for m in models],
                    "traders": [int((m.cycles > 0).sum()) for m in models],
                    "max_cycles": [int(m.cycles.max()) for m in models],
                },
                "criteria": [
                    {
                        "name": c.name,
                        "passed": bool(c.passed),
                        "void": bool(c.void),
                        "diagnostic": bool(c.diagnostic),
                        "detail": c.detail,
                    }
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(live) else 1


if __name__ == "__main__":
    raise SystemExit(main())
