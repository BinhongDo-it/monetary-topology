"""A3: the asset channel, executed against its seven registered criteria.

Registered in ``docs/a3_asset_channel.md``. This file evaluates and does not
design: every threshold it compares against is written there, and where a
criterion cannot be evaluated it reports **void** rather than a number.

Usage::

    python experiments/a3_asset_channel.py
    python experiments/a3_asset_channel.py --seeds 5
    python experiments/a3_asset_channel.py --rent-sweep   # §9.11, frozen price

``--sweep``, the §4 robustness grid, was advertised here before it existed and
still does not exist. §9.10 records that as a breach of a registered promise
rather than as a todo, so the flag is not listed as available until it is.

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
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monetary_topology.asset import (  # noqa: E402
    CLOSED,
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
    """
    traders = np.flatnonzero(model.cycles > 0)
    if traders.size < 2:
        return np.array([], dtype=int), np.array([], dtype=int)
    gamma = model.terms[traders, 0]
    order = traders[np.argsort(gamma)]
    half = max(1, order.size // 3)
    return order[:half], order[-half:]   # (better terms, worse terms)


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


def a3_5(seeds: range) -> Criterion:
    """Opening a tier changes two things at once, so both are reported.

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
        for seed in seeds:
            m = run(seed, open_tiers=open_tiers, elasticity=eta)
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


def _holders_at_shock(seed: int) -> tuple[np.ndarray, np.ndarray]:
    """``(holders, non-holders)`` as of the shock round.

    The population is read **at the moment of the shock** rather than at the
    end, because the criterion asks whether a transfer lands on someone who has
    a stock, and that is a fact about the recipient when the transfer arrives.
    """
    at_shock = run(seed, rounds=A3_6_SHOCK_ROUND)
    held = at_shock.units.sum(axis=1) > 0
    return np.flatnonzero(held), np.flatnonzero(~held)


def _shock_survival(seed: int, target: int, base: A3Model | None = None) -> float:
    """What is left, after ``A3_6_HORIZON`` rounds, of a transfer to ``target``."""
    base = base if base is not None else run(seed)
    shocked = A3Model(
        A3Config(
            asset=AssetSpec(),
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=300
            ),
        )
    )
    original = shocked._pre_round

    def hook(t: int, _m=shocked, _i=target, _pre=original) -> None:
        _pre(t)
        if t == A3_6_SHOCK_ROUND:
            gift = _m.holdings.sum() * 0.10
            _m.holdings -= gift / _m._n
            _m.holdings[_i] += gift

    shocked._pre_round = hook  # type: ignore[method-assign]
    shocked.run()

    a = np.asarray(base.net_worth_history)[:, target]
    b = np.asarray(shocked.net_worth_history)[:, target]
    dev = np.abs(b - a)
    start = float(dev[A3_6_SHOCK_ROUND])
    return float(dev[A3_6_SHOCK_ROUND + A3_6_HORIZON] / start) if start > 0 else 0.0


def a3_6(seeds: range) -> Criterion:
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
        base = run(seed)
        holders, others = _holders_at_shock(seed)
        sizes.append(holders.size)
        downstairs.append(int(base._is_production[holders].sum()))
        if holders.size:
            v = [_shock_survival(seed, int(i), base) for i in holders]
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
        "--rent-sweep",
        action="store_true",
        help="§9.11's frozen-price rent arm. Costs one run per rate per seed",
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

    sweep = None
    if args.rent_sweep:
        print("\n  rent sweep at a frozen price (elasticity = 0)")
        sweep = rent_sweep(seeds, args.rounds)
        print(
            f"    zero calibration: "
            f"{'ok' if sweep['zero_calibration_ok'] else 'BROKEN'};"
            f" dropped from the paired population: "
            f"{sweep['dropped_from_paired_population']}"
        )
        for rate in RENT_RATES:
            row = sweep["per_rate"][f"{rate:g}"]
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
                "rent_sweep": sweep,
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
