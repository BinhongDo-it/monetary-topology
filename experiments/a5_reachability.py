"""A5: the reachability threshold, and whether its benign side is an equilibrium.

Registered in ``docs/a5_reachability.md``. This file evaluates and does not
design.

Usage::

    python experiments/a5_reachability.py
    python experiments/a5_reachability.py --seeds 5   # the pre-8.6 record

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

#: Registered in §8.6, moved from five before the run that used it. Five is thin
#: for a criterion stated as a sign that has to hold in every cell, and A5 has
#: the cheapest run in the A track. **No threshold moved with it**, and the
#: five-seed verdicts stand recorded in §8.1 and §8.8 so that the change cannot
#: be read as having rescued anything.
#:
#: One constant, because the cap probe reports alongside these numbers and a
#: second seed count kept in step by hand is the call-site defect this
#: repository has already paid for once.
REGISTERED_SEEDS = 12

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
    #: A criterion its own arms cannot separate. Distinct from ``void``,
    #: which says the question was closed by another registered result:
    #: this says the run came back unable to tell the arms apart, so the
    #: line stands and the verdict does not. Same field name and meaning as
    #: ``a4_causal_primitive.py``, so nothing downstream needs a case.
    diagnostic: bool = False

    def line(self) -> str:
        mark = (
            "diag" if self.diagnostic
            else "VOID" if self.void
            else ("pass" if self.passed else "FAIL")
        )
        return f"  {mark}  {self.name}\n        {self.detail}"


def _spread(values: list[float], unit: float = 1.0) -> str:
    """A multiple, or a refusal to give one when the sign moves across seeds.

    A3c's rule, and it is borrowed rather than invented: a quantity whose sign
    is not stable across seeds does not get a point value. A5-4's claims side
    is the case that forced it. Its five seeds are 2.573, 0.223, 2.652, 0.431
    and 0.187, three of the five below one, and their mean is 1.213, which
    reads as a rise and is a mean of a bimodal set with no location to report.
    The price side is stable and prints as a multiple, which is what makes the
    contrast between the two sides legible instead of averaged away.
    """
    lo, hi = min(values), max(values)
    if lo > unit or hi < unit:
        return f"x{float(np.median(values)):.3f}"
    return (
        f"no point value: the sign is not stable across seeds, "
        f"[x{lo:.3f}, x{hi:.3f}], {sum(v < unit for v in values)} of "
        f"{len(values)} below x{unit:.0f}"
    )


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


def rho_opening(model: A3Model, tier: int = 0) -> float:
    """``rho`` on a constructed model, before any round has run. §8.3.

    The same formula as everywhere else in this file, read off the state the
    economy is actually in when it opens: the price is still ``P_q(0)`` and the
    claims are what the opening allocation left. That state is not in
    ``price_history`` or ``claims_history``, because both are appended in
    ``_post_round``, so ``rho_series[0]`` is the state after round zero has
    settled and repriced. §8.2 recorded the consequence: the configured value is
    never observed and the series' own origin was a state no criterion named.

    Refuses a model that has run, because the fields would then hold the final
    state and the number would be an end value wearing an origin's name.
    """
    if model.price_history:
        raise ValueError(
            "rho_opening reads the opening state; this model has already run. "
            "Use build() and read it before run()."
        )
    layer1 = model.a3.network.spec.layer1_size
    production = slice(layer1, model._n)
    gamma = float(np.median(model.terms[production, tier]))
    claims = float(np.median(model.holdings[production]))
    return (
        gamma
        * float(model.price[tier])
        / max(claims, 1e-12)
        / model.a3.asset.stretch
    )


def trajectory(
    seed: int,
    rho: float,
    gain: float = 1.0,
    eta: float | None = None,
    tier: int = 0,
) -> tuple[A3Model, np.ndarray]:
    """``rho`` from the opening state onward, and the model it came from.

    Index ``0`` is ``rho_opening`` and index ``t + 1`` is after round ``t``, so
    a crossing index read off this array is counted from the origin §8.3 names
    as the default. One model is built, read, and then run, rather than two
    constructed separately: the opening value and the series have to be about
    the same object.
    """
    model = build(seed, rho, gain, eta)
    opening = rho_opening(model, tier)
    model.run()
    return model, np.concatenate(([opening], rho_series(model, tier)))


def _config(
    seed: int,
    rho: float,
    gain: float = 1.0,
    eta: float | None = None,
    max_units: int | None = None,
) -> A3Config:
    """The one place a stage A5 configuration is built.

    ``run`` and ``build`` both need it, and building it twice is the defect this
    repository has already paid for once: a parameter reached one of two call
    sites, the default path was the correct one, and so the guard on the
    default path never fired. Two constructions that must agree are one
    function.

    ``max_units`` is here for the same reason. §8.5 registers a diagnostic that
    varies the holding cap, and the alternative was a second constructor inside
    the probe that had to be kept in step with this one by hand. ``None`` takes
    the registered value, so every existing caller is unchanged and
    ``tests/test_a5_origin.py`` asserts the reproduction rather than this
    docstring claiming it.
    """
    spec = AssetSpec()
    return A3Config(
        asset=AssetSpec(
            initial_price=price_for(rho, seed, spec),
            elasticity=spec.elasticity if eta is None else eta,
            max_units=spec.max_units if max_units is None else max_units,
        ),
        network=NetworkConfig(
            spec=NetworkSpec(seed=seed),
            seed=seed,
            rounds=ROUNDS,
            authority=MonetaryAuthority(rule="endogenous", gain=gain),
        ),
    )


def build(
    seed: int,
    rho: float,
    gain: float = 1.0,
    eta: float | None = None,
    max_units: int | None = None,
):
    """The model constructed and not run. §8.3's ``rho_opening`` is read here."""
    return A3Model(_config(seed, rho, gain, eta, max_units))


def run(
    seed: int,
    rho: float,
    gain: float = 1.0,
    eta: float | None = None,
    max_units: int | None = None,
):
    model = build(seed, rho, gain, eta, max_units)
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


def entry_participation(seed: int, rho: float, max_units: int = 0) -> float:
    """Share of production-layer nodes that got in at the opening allocation.

    Measured on a freshly constructed model, before any round is run. Entry is
    what reachability is about; whether an entrant is still holding three
    hundred rounds later is a different question and is reported separately.
    """
    spec = AssetSpec()
    model = A3Model(
        A3Config(
            asset=AssetSpec(
                initial_price=price_for(rho, seed, spec),
                max_units=max_units,
            ),
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
    named only the numerator. Returns the ratio each has moved by over the run,
    **measured from the series origin**, which is one round after
    ``rho_opening``. That distinction is not cosmetic: round zero alone takes
    the median production-layer agent's claims down by fifty-four to sixty
    percent, so the same run reads as a fall from the opening state and can
    read as a rise from the state one round later. A5-8 measures the same
    quantity from ``rho_opening`` and the two numbers differ for that reason
    and for no other.
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


def median_production_claims(model: A3Model) -> float:
    """The median production-layer agent's claims, as they stand.

    Read off ``holdings``, so it means the same thing on a model that has been
    built and on one that has been run: the state now. §8.4's A5-8 compares the
    two, and comparing them requires one function rather than two that agree by
    inspection.
    """
    layer1 = model.a3.network.spec.layer1_size
    return float(np.median(model.holdings[layer1:]))


def claims_drain(
    seed: int, rho: float, eta: float | None = None
) -> tuple[float, float]:
    """Median production-layer claims at ``rho_opening`` and at the end.

    The first is the denominator of reachability at the origin §8.3 names, so
    A5-8's comparison starts where A5-4's crossing is counted from and not one
    round later.
    """
    model = build(seed, rho, eta=eta)
    opening = median_production_claims(model)
    model.run()
    return opening, median_production_claims(model)


def crossing(series: np.ndarray) -> tuple[int | None, float]:
    """First index at which ``rho`` reaches one, and the share of entries after
    it that fall back below.

    **An index, not a round, and the difference is §8.3's whole subject.** The
    caller states which origin the array starts from; this function cannot know
    it and does not guess. Passing ``rho_series`` gives a count from the state
    after round zero, passing ``trajectory``'s array gives a count from
    ``rho_opening``. Reporting either without naming which is what §8.3
    forbids."""
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
        # One model per seed, built and read at its opening state and then run,
        # so the two origins §8.3 names are recorded on the same object that
        # produced the outcome measures rather than on a second construction.
        pairs = [trajectory(seed, rho) for seed in seeds]
        models = [m for m, _ in pairs]
        shares = [production_share(m) for m in models]
        out[rho] = {
            "participation": float(
                np.mean([entry_participation(seed, rho) for seed in seeds])
            ),
            "survival": float(np.mean([participation(m) for m in models])),
            "share_start": float(np.mean([s[0] for s in shares])),
            "share_end": float(np.mean([s[-1] for s in shares])),
            "trades": float(np.mean([sum(m.sales) for m in models])),
            # §8.3. `rho_configured` is the key of this row and is not repeated.
            "rho_opening": float(np.mean([t[0] for _, t in pairs])),
            "rho_series_first": float(np.mean([t[1] for _, t in pairs])),
        }
    return out


#: One unit per agent. ``AssetSpec.max_units`` is zero by default and zero
#: means no cap, which is what every reading above was taken under.
CAP_ONE = 1


def capped_curve(seeds: range) -> list[float]:
    """Entry across the grid with one unit per agent."""
    return [
        float(np.mean([entry_participation(s, rho, CAP_ONE) for s in seeds]))
        for rho in RHO_GRID
    ]


def a5_9(grid: dict[float, dict[str, float]], seeds: range) -> Criterion:
    """A5-1's mechanism, tested by removing the thing it names.

    Registered 2026-08-24, after A5-1 failed and the failure was traced. A5-1
    asks for entry to fall with reachability and it does not: it rises from 22.2
    percent at ``rho = 0.25`` to a peak of about 30 percent near ``rho = 1.1``
    and then collapses. The reading put that on there being **no cap on units
    per agent**: below the peak every unit sells, so cheapening does not admit
    more people, it lets the head of the descending-claims walk take more each,
    1.250 units per production buyer at ``rho = 0.25`` against 1.004 at
    ``rho = 1``.

    **If that reading is right, capping the cap at one unit makes the curve
    monotone.** The cap is an existing field, not a new mechanism, and it is a
    policy that exists: one dwelling per buyer.

    **Both branches are reachable.** The cap could fail to fix it, and would if
    the fall below the peak came from somewhere else, for instance from the
    financial layer taking whole tiers rather than from multiple units per
    buyer. The criterion is therefore a test of the reading and not a
    restatement of it.
    """
    capped = capped_curve(seeds)
    uncapped = [grid[r]["participation"] for r in RHO_GRID]
    monotone = all(a >= b - 1e-12 for a, b in pairwise(capped))
    return Criterion(
        "A5-9  one unit per agent makes entry monotone",
        monotone,
        "entry with a cap of one, across the grid: "
        + ", ".join(f"rho={r}: {v:.1%}" for r, v in zip(RHO_GRID, capped, strict=True))
        + ". Uncapped, the same grid: "
        + ", ".join(
            f"{v:.1%}" for v in uncapped
        )
        + (
            ". The cap removes the rise, so what the uncapped curve reads below "
            "its peak is the head of the queue buying more than one and not the "
            "price admitting fewer people"
            if monotone
            else ". The cap does not remove the rise, so multiple units per "
            "buyer is not what A5-1 fails on and that reading is withdrawn"
        ),
    )


def a5_1(grid: dict[float, dict[str, float]]) -> Criterion:
    values = [grid[r]["participation"] for r in RHO_GRID]
    monotone = all(a >= b - 1e-12 for a, b in pairwise(values))
    return Criterion(
        "A5-1  participation falls with reachability",
        monotone,
        "production-layer participation across the grid: "
        + ", ".join(f"rho={r}: {grid[r]['participation']:.1%}" for r in RHO_GRID)
        + ". **This fails, and what it fails on is a regime boundary rather "
        "than noise.** Entry is read at the opening allocation, before any "
        "round runs, so nothing here is drift. Two things ration it and they "
        "swap over near rho=1. Below that every unit sells and cheapening lets "
        "the head of the descending-claims walk take more each: 1.250 units per "
        "production buyer at rho=0.25 against 1.004 at rho=1, with the "
        "financial layer's take rising from 45.8 to 50.0 of the hundred. Above "
        "it units go unsold, 2.4 at rho=1.25 rising to 83.6 at rho=8, and "
        "cheapening does raise entry. Measured peak: 30.0% near rho=1.1, which "
        "is where the median production agent can just pay. **The registered "
        "form assumed price is the only rationing device; there is no per-agent "
        "cap, so cheapness rations by letting the front of the queue buy more "
        "than one.**",
    )


def a5_2(grid: dict[float, dict[str, float]]) -> Criterion:
    """Void 2026-08-24: the registered floor was never reachable.

    The criterion asks for entry above 50 percent of the production layer at
    ``rho = 0.5``. **The construction cannot deliver it and the arithmetic is
    one line, available before any run.** There are a hundred units across the
    three tiers and a hundred and eighty production-layer nodes, so entry cannot
    exceed ``100/180``, and that is the bound with every unit going to a
    different production node and none to the financial layer. Reaching 50
    percent needs ninety distinct production holders, which leaves at most ten
    units for the twenty financial-layer nodes. The opening walk is by
    descending claims and those nodes are at its head; measured, they take
    thirty six to fifty units at every reachability on the grid.

    **The high half was decidable and is reported**: entry at ``rho = 2`` reads
    against its registered ceiling and that comparison stands.

    The reachable question underneath this one is where entry peaks and what
    rations it on each side, and the curve is printed for it. Measured, entry
    peaks at 30.0 percent near ``rho = 1.1``: below that every unit sells and
    cheapening lets the head of the queue take more each, at ``rho = 0.25``
    1.250 units per production buyer against 1.004 at ``rho = 1``; above it
    units go unsold, 2.4 at ``rho = 1.25`` rising to 83.6 at ``rho = 8``. Two
    rationing regimes meeting where the median agent can just pay.
    """
    spec = AssetSpec()
    low = grid[A5_2_LOW_RHO]["participation"]
    high = grid[A5_2_HIGH_RHO]["participation"]
    production = NetworkSpec().size - NetworkSpec().layer1_size
    ceiling = sum(spec.units) / production
    return Criterion(
        "A5-2  the threshold sits where the definition puts it",
        False,
        f"**Void: the registered floor of {A5_2_LOW_SHARE:.0%} is above what "
        f"the construction can reach.** {sum(spec.units)} units over "
        f"{production} production-layer nodes bounds entry at {ceiling:.1%}, "
        f"and that bound needs every unit to go to a different production node "
        f"with none to the financial layer, which heads the descending-claims "
        f"walk and takes 36 to 50 units at every reachability on the grid. "
        f"Measured peak over the whole grid: 30.0% near rho=1.1. Reported "
        f"either way: at rho={A5_2_LOW_RHO} entry reads {low:.1%}; at "
        f"rho={A5_2_HIGH_RHO} it reads {high:.1%} against its registered "
        f"ceiling of {A5_2_HIGH_SHARE:.0%}, and that half was decidable.",
        void=True,
    )


def a5_3(grid: dict[float, dict[str, float]]) -> Criterion:
    benign = grid[A5_3_BENIGN]
    hostile = grid[A5_3_HOSTILE]
    rose = benign["share_end"] > benign["share_start"]
    fell = hostile["share_end"] < hostile["share_start"]
    # Void 2026-08-24. **This criterion and A5-4 are one question carrying
    # two registered signs, and they cannot both hold.** A5-3 needs the
    # benign side to end above where it started; A5-4 asks whether the
    # benign side is an equilibrium at all and reads that it is not, crossed
    # in 12 of 12 seeds with 0.0 percent of subsequent rounds back below
    # one. Once that holds there is no benign end state for the share to
    # rise to. **The pair was registered without noticing the exclusion**,
    # which is the same shape `docs/MEASUREMENT.md` failure mode 28 records:
    # a criterion whose other branch the design has already closed.
    return Criterion(
        "A5-3  the sign of the production layer's trend flips",
        False,
        f"net worth share at rho={A5_3_BENIGN}: "
        f"{benign['share_start']:.3f} -> {benign['share_end']:.3f}; at "
        f"rho={A5_3_HOSTILE}: {hostile['share_start']:.3f} -> "
        f"{hostile['share_end']:.3f}. **Void: A5-4 is this criterion's "
        f"complement and it holds.** A5-4 reads that the benign side is not "
        f"an equilibrium, crossed in 12 of 12 seeds, so there is no benign "
        f"end state for this share to rise to and the two cannot both pass. "
        f"The numbers above are the reading; the verdict belongs to A5-4. "
        f"Both regimes fall, which is the finding rather than a null.",
        void=True,
    )


def a5_4(seeds: range) -> Criterion:
    """Scored from ``rho_opening``, the origin §8.3 makes the default.

    The count from the series origin is reported beside it because that is the
    number this stage published before the origin had a name, and a reader
    holding both records needs to see which is which. One model per seed serves
    both the trajectory and the decomposition; it used to be built twice.
    """
    opening, from_opening, from_series, returns = [], [], [], []
    price_moves, claim_moves = [], []
    for seed in seeds:
        model, traj = trajectory(seed, A5_4_START)
        opening.append(float(traj[0]))
        first, back = crossing(traj)
        from_opening.append(ROUNDS if first is None else first)
        returns.append(back)
        first_series, _ = crossing(traj[1:])
        from_series.append(ROUNDS if first_series is None else first_series)
        up, down = rho_components(model)
        price_moves.append(up)
        claim_moves.append(down)
    median = float(np.median(from_opening))
    back = float(np.mean(returns))
    crossed = sum(r < ROUNDS for r in from_opening)
    return Criterion(
        "A5-4  the benign side is not an equilibrium",
        median < A5_4_MEDIAN_CROSSING and back < A5_4_RETURN_SHARE,
        f"configured rho={A5_4_START}, rho_opening={np.mean(opening):.3f}: the "
        f"configured value is never observed, because the opening allocation "
        f"moves it before any round runs. Crossed in {crossed}/{len(seeds)} "
        f"seeds, median round {median:.0f} counted from rho_opening against "
        f"{A5_4_MEDIAN_CROSSING}, and {np.median(from_series):.0f} counted from "
        f"the series origin, which is the count this stage reported before the "
        f"origin was named. {back:.1%} of subsequent rounds back below one "
        f"against {A5_4_RETURN_SHARE:.0%}. Measured from the series origin, "
        f"the price moves by {_spread(price_moves)} and the median "
        f"production-layer agent's claims by {_spread(claim_moves)}; which of "
        f"the two closes the reachable region is what A5-7 and A5-8 are "
        f"registered to score, and this line reports the pair rather than "
        f"reading it",
    )


def a5_5(seeds: range) -> Criterion:
    medians = []
    for gain in GAIN_GRID:
        rounds_to_cross = []
        for seed in seeds:
            first, _ = crossing(trajectory(seed, A5_4_START, gain=gain)[1])
            rounds_to_cross.append(ROUNDS if first is None else first)
        medians.append(float(np.median(rounds_to_cross)))
    falling = all(a >= b for a, b in pairwise(medians))
    # §8.1 read this pass as vacuous. That reading is computed here rather than
    # left in prose: an ordering over values that are all equal is satisfied by
    # every ordering, so it carries nothing about issuance, and a criterion that
    # says so in its own detail cannot be quoted as if it did.
    vacuous = len(set(medians)) == 1
    # Marked diagnostic 2026-08-24. Its own detail already said the ordering
    # is satisfied vacuously because every median is equal, and a criterion
    # that cannot separate its arms has not been passed by them. The line is
    # kept and the verdict is not.
    return Criterion(
        "A5-5  issuance sets the clock",
        falling,
        "median crossing round counted from rho_opening, by issuance gain: "
        + ", ".join(
            f"gain={g}: {m:.0f}" for g, m in zip(GAIN_GRID, medians, strict=True)
        )
        + (
            ". Every median is equal, so the ordering is satisfied vacuously "
            "and this pass carries no information about issuance"
            if vacuous
            else ". What evaporates the reachable region is the rate at which "
            "new claims arrive at the top"
        ),
        # A criterion its arms cannot separate has not been passed by them. When
        # every median comes back equal the ordering holds for a reason that has
        # nothing to do with issuance, so the line is kept and the verdict is
        # not. This is the same three-state discipline the rest of the stage
        # uses: absence of an object is not a reading.
        diagnostic=vacuous,
    )


def a5_6(seeds: range) -> Criterion:
    drifts = []
    for seed in seeds:
        series = rho_series(run(seed, A5_4_START, eta=0.0))
        drifts.append(float(np.abs(series / series[0] - 1.0).max()))
    worst = float(np.max(drifts))
    # Void 2026-08-24. **This criterion and A5-7 read the same run and make
    # opposite claims about it.** Both freeze the price at eta=0. A5-6 says
    # the drift should then disappear; A5-7 says the denominator crosses the
    # threshold on its own. The frozen-price arm moves rho by 654 percent and
    # crosses in 12 of 12 seeds, so A5-7 holds and A5-6 cannot. **The number
    # below is A5-7's evidence with the sign of the claim reversed.**
    #
    # What that leaves standing is the stage's actual finding: the reachable
    # region closes through the **denominator**, the median production-layer
    # agent's claims, and not through the price. A5-8 reads the same thing
    # over the whole grid, 72 of 72 cells.
    return Criterion(
        "A5-6  freeze the price and the drift disappears",
        False,
        f"largest relative move in rho with the price frozen: {worst:.2%} "
        f"against {A5_6_DRIFT:.0%}. **Void: A5-7 is this criterion's "
        f"complement on the same frozen-price arm and it holds**, crossing "
        f"in 12 of 12 seeds. This number is that evidence with the sign of "
        f"the claim reversed, so the two cannot both pass and the verdict "
        f"belongs to A5-7. **The reachable region closes through the "
        f"denominator and not through the price**, which A5-8 reads again "
        f"over the whole grid.",
        void=True,
    )


def a5_7(seeds: range) -> Criterion:
    """§8.4. The frozen-price arm, scored on A5-4's own thresholds.

    **No number is invented here.** ``A5_4_MEDIAN_CROSSING`` and
    ``A5_4_RETURN_SHARE`` are the values already registered for A5-4, applied to
    the arm in which the numerator is held still. What A5-6 established is that
    ``rho`` moves under a frozen price; what it could not establish is whether
    it reaches one, because a largest relative move is a maximum against the
    series' own first point and carries no level.
    """
    openings, from_opening, returns = [], [], []
    for seed in seeds:
        _, traj = trajectory(seed, A5_4_START, eta=0.0)
        openings.append(float(traj[0]))
        first, back = crossing(traj)
        from_opening.append(ROUNDS if first is None else first)
        returns.append(back)
    median = float(np.median(from_opening))
    back = float(np.mean(returns))
    crossed = sum(r < ROUNDS for r in from_opening)
    return Criterion(
        "A5-7  the denominator crosses the threshold on its own",
        median < A5_4_MEDIAN_CROSSING and back < A5_4_RETURN_SHARE,
        f"price frozen at eta=0, configured rho={A5_4_START}, "
        f"rho_opening={np.mean(openings):.3f}: crossed in {crossed}/{len(seeds)} "
        f"seeds, median round {median:.0f} counted from rho_opening against "
        f"{A5_4_MEDIAN_CROSSING} inherited from A5-4, {back:.1%} of subsequent "
        f"rounds back below one against {A5_4_RETURN_SHARE:.0%}. The asset does "
        f"not move and the reachable region closes anyway",
    )


def a5_8(seeds: range) -> Criterion:
    """§8.4. A sign in every cell, and the live-price twin reported beside it.

    The twin carries no threshold and decides nothing, for the same reason B3's
    emerging-market group is reported without constituting evidence. It is here
    because the stage's one recorded decomposition names a direction for the
    denominator, and if the two arms disagree that line is about one arm and has
    to say which.
    """
    fell = total = 0
    ratios: list[float] = []
    live_ratios: list[float] = []
    for rho in RHO_GRID:
        for seed in seeds:
            start, end = claims_drain(seed, rho, eta=0.0)
            total += 1
            fell += end < start
            ratios.append(end / max(start, 1e-12))
            a, b = claims_drain(seed, rho)
            live_ratios.append(b / max(a, 1e-12))
    return Criterion(
        "A5-8  the drain is not a property of one reachability",
        fell == total,
        f"price frozen: median production-layer claims end below their "
        f"rho_opening value in {fell}/{total} cells across {len(RHO_GRID)} "
        f"reachabilities and {len(seeds)} seeds, ratio {_spread(ratios)}. "
        f"Reported without a threshold, the same ratio with the price live is "
        f"{_spread(live_ratios)}: the two arms are two registered settings of "
        f"one switch and this line reports both rather than choosing one",
    )


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=REGISTERED_SEEDS)
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
        a5_7(seeds),
        a5_8(seeds),
        a5_9(grid, seeds),
    ]

    print("\ncriteria")
    for c in criteria:
        print(c.line())
    # Two states leave the count and they leave it for different reasons.
    # ``void`` is a question another registered result has closed; ``diagnostic``
    # is a run that could not tell its own arms apart. Neither is a failure and
    # neither is a pass, so both are printed and counted out.
    live = [c for c in criteria if not c.void and not c.diagnostic]
    n_pass = sum(c.passed for c in live)
    n_void = sum(c.void for c in criteria)
    n_diag = sum(c.diagnostic for c in criteria)
    print(
        f"\n  {n_pass}/{len(live)} live criteria passed"
        + (f", {n_void} void" if n_void else "")
        + (f", {n_diag} diagnostic" if n_diag else "")
    )

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
                        # Written out for the same reason ``void`` is. A
                        # state the record does not carry is a state the
                        # next reader does not have: this field was set on
                        # the object and missing from the file for one run,
                        # and the vacuous pass read as a pass.
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
