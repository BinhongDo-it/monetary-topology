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
enter the tier through the opening's stretch, paying everything it holds, which
covers a third of the cost at ``s = 3``. Resale after the opening requires
payment in full, which the median agent meets only at ``rho = 1 / s``. It is a definition and not a fitted
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
    max_units: int | None = None,
) -> tuple[A3Model, np.ndarray]:
    """``rho`` from the opening state onward, and the model it came from.

    Index ``0`` is ``rho_opening`` and index ``t + 1`` is after round ``t``, so
    a crossing index read off this array is counted from the origin §8.3 names
    as the default. One model is built, read, and then run, rather than two
    constructed separately: the opening value and the series have to be about
    the same object.

    ``max_units`` is passed through to ``_config`` and ``None`` takes the
    registered value, so every existing caller is unchanged.
    """
    model = build(seed, rho, gain, eta, max_units)
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

    Kept, but it is survival and not entry. With no cap on units per agent the
    production layer is sold out, or within one node of it, within three
    hundred rounds at every reachability tried, so this number cannot order the
    grid. A5-1 and A5-2 are measured on ``entry_participation`` instead, which
    was the intent. **That is a reading of the uncapped market and not of the
    mechanism**: with one unit per agent the entrants are still holding at the
    end, and ``who_stays`` prints both.
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


#: Opening allocations read around ``rho = 1`` beside the registered grid.
#: A5-1 and A5-2 say where entry is highest and where units start going
#: unsold, and those sentences are computed from the seeds the run uses. They
#: were fixed strings once, carried over from a five-seed reading into a
#: twelve-seed record. Nothing is scored on this grid.
OPENING_FINE_GRID = (0.9, 1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5)


def holdings_now(model: A3Model) -> dict[str, float]:
    """Who holds the stock, read off the unit matrix as it stands.

    Means the same on a model that has been built and on one that has been
    run, for the reason ``median_production_claims`` does: the state now.

    ``cells_per_unit`` is the number of positive ``(node, tier)`` holdings over
    the number of units held. Resale draws once per positive holding and offers
    one unit from it (``A3Model._offers``), so ``turnover * cells_per_unit`` is
    the expected share of held units offered in a round from this state. It is
    one where every holding is a single unit and falls as units pile up in the
    same hands.
    """
    layer1 = model.a3.network.spec.layer1_size
    units = model.units
    production = units[layer1:].sum(axis=1)
    held = float(units.sum())
    if held <= 0.0:
        raise ValueError("nobody holds a unit, so there is no holding to read")
    return {
        "holding_share": float((production > 0).mean()),
        "production_holders": float((production > 0).sum()),
        "production_units": float(production.sum()),
        "financial_units": float(units[:layer1].sum()),
        "unowned": float(sum(model.supply)) - held,
        "largest_holding": float(units.max()),
        "cells_per_unit": float((units > 0).sum()) / held,
    }


def seed_means(rows: list[dict[str, float]]) -> dict[str, float | None]:
    """``holdings_now`` over seeds: means, and four things a mean would hide.

    ``units_per_production_holder`` is pooled, production-layer units over
    production-layer holders summed across the seeds, so a seed in which nobody
    got in is not given a ratio; it is ``None`` when nobody got in anywhere.
    ``seeds_with_unowned`` counts the seeds, of ``seeds``, in which part of the
    stock has no owner. ``largest_holding`` is the largest over the seeds and
    ``cells_per_unit_min`` the smallest, because both are about the most
    concentrated history and its mean says nothing about that one.
    """
    out: dict[str, float | None] = {
        k: float(np.mean([r[k] for r in rows])) for k in rows[0]
    }
    holders = sum(r["production_holders"] for r in rows)
    out["units_per_production_holder"] = (
        float(sum(r["production_units"] for r in rows) / holders)
        if holders
        else None
    )
    out["seeds"] = float(len(rows))
    out["seeds_with_unowned"] = float(sum(r["unowned"] > 0 for r in rows))
    out["largest_holding"] = float(max(r["largest_holding"] for r in rows))
    out["cells_per_unit_min"] = float(min(r["cells_per_unit"] for r in rows))
    return out


def entrants_still_holding(
    opened: list[np.ndarray], models: list[A3Model]
) -> float | None:
    """Of the production-layer nodes that got a unit at the opening, the share
    holding one now. Pooled over seeds; ``None`` when nobody got in.

    ``opened`` is each seed's unit matrix at the opening allocation and
    ``models`` the same seeds after the run. ``holding_share`` cannot say this
    on its own: under a cap of one, a unit that passes from one production node
    to another leaves the share where it was, while the entrant it left is no
    longer a holder.
    """
    entered = stayed = 0
    for units, model in zip(opened, models, strict=True):
        layer1 = model.a3.network.spec.layer1_size
        was = units[layer1:].sum(axis=1) > 0
        now = model.units[layer1:].sum(axis=1) > 0
        entered += int(was.sum())
        stayed += int((was & now).sum())
    return stayed / entered if entered else None


def opening_table(
    seeds: range, rhos: tuple[float, ...], max_units: int | None = None
) -> dict[float, dict[str, float | None]]:
    """``holdings_now`` at the opening allocation, by reachability."""
    return {
        rho: seed_means(
            [holdings_now(build(seed, rho, max_units=max_units)) for seed in seeds]
        )
        for rho in rhos
    }


def rho_components(model: A3Model, tier: int = 0) -> tuple[float, float]:
    """How much of ``rho``'s drift is the price, and how much is the buyers.

    Reachability has a numerator and a denominator and the registered criterion
    named only the numerator. Returns the ratio each has moved by over the run,
    **measured from the series origin**, which is one round after
    ``rho_opening``. That distinction is not cosmetic: round zero alone takes
    the median production-layer agent's claims down by 44.7 to 62.5 percent
    across the twelve seeds at ``rho = 0.5`` (54 to 60 on the first five), so
    the same run reads as a fall from the opening state and can read as a rise
    from the state one round later. A5-8 measures the same quantity from
    ``rho_opening``, and over the six reachabilities of the grid rather than at
    one, so the two numbers differ by origin and by the cells they pool.
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


def sweep(
    seeds: range, ends: dict[float, dict[str, float | None]] | None = None
) -> dict[float, dict[str, float]]:
    """The registered grid. ``ends``, when given, is filled with who holds the
    stock at the end of the same histories, so that reading is taken on the
    models that produced the grid and not on a second set."""
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
        if ends is not None:
            ends[rho] = seed_means([holdings_now(m) for m in models]) | {
                "trades": out[rho]["trades"],
                "entrants_still_holding": entrants_still_holding(
                    [build(seed, rho).units for seed in seeds], models
                ),
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


def crossing_summary(trajectories: list[np.ndarray]) -> dict[str, float]:
    """A5-4's two statistics on a set of trajectories counted from ``rho_opening``."""
    firsts, backs = [], []
    for traj in trajectories:
        first, back = crossing(traj)
        firsts.append(ROUNDS if first is None else first)
        backs.append(back)
    return {
        "seeds": float(len(trajectories)),
        "crossed": float(sum(f < ROUNDS for f in firsts)),
        "median_from_opening": float(np.median(firsts)),
        "back": float(np.mean(backs)),
    }


def who_stays(
    seeds: range,
    opening: dict[float, dict[str, float | None]],
    uncapped_end: dict[float, dict[str, float | None]],
) -> dict[str, object]:
    """Holding at the opening and at the end, with no cap and with one unit each.

    Entry is who gets in at the opening allocation. Whether an entrant is still
    holding three hundred rounds later is a second question, and A5-4 and A5-7
    do not answer it: they read the median production agent's claims against
    the stretched opening cost at the current price, and a holder whose claims
    no longer reach it still owns what it holds. This reads
    the unit matrix at both times, on the grid's own histories (``uncapped_end``
    comes from ``sweep``) and on their twins under ``CAP_ONE``, and it reads the
    crossing at A5-4's configured reachability under the cap, price live and
    price frozen, so that the two statements can be put side by side.

    Nothing here is scored. It is the reading the sentence "the cap changes who
    enters" needs before anything is said about who stays.
    """
    capped_open = opening_table(seeds, RHO_GRID, CAP_ONE)
    capped_end: dict[float, dict[str, float | None]] = {}
    live: dict[str, float] = {}
    for rho in RHO_GRID:
        pairs = [trajectory(seed, rho, max_units=CAP_ONE) for seed in seeds]
        capped_end[rho] = seed_means([holdings_now(m) for m, _ in pairs]) | {
            "trades": float(np.mean([sum(m.sales) for m, _ in pairs])),
            "entrants_still_holding": entrants_still_holding(
                [build(seed, rho, max_units=CAP_ONE).units for seed in seeds],
                [m for m, _ in pairs],
            ),
        }
        if rho == A5_4_START:
            live = crossing_summary([t for _, t in pairs])
    frozen = crossing_summary(
        [
            trajectory(seed, A5_4_START, eta=0.0, max_units=CAP_ONE)[1]
            for seed in seeds
        ]
    )
    return {
        "turnover": float(AssetSpec().turnover),
        "uncapped": {
            str(rho): {"open": opening[rho], "end": uncapped_end[rho]}
            for rho in RHO_GRID
        },
        "cap_one": {
            str(rho): {"open": capped_open[rho], "end": capped_end[rho]}
            for rho in RHO_GRID
        },
        "cap_one_crossing": {
            "configured_rho": A5_4_START,
            "live": live,
            "frozen": frozen,
        },
    }


def who_stays_lines(holding: dict[str, object]) -> list[str]:
    """The table ``who_stays`` produced, as printed lines."""
    lines = [
        "  share of production-layer nodes holding a unit, opening -> end "
        f"of run ({ROUNDS} rounds), and in brackets the share of the entrants "
        "still holding",
        "    rho      no cap                           one unit per agent"
        "                units offered per round, end (no cap)",
    ]
    tau = float(holding["turnover"])

    def kept(row: dict[str, float | None]) -> str:
        share = row["entrants_still_holding"]
        return "    n/a" if share is None else f"{share:7.2%}"

    for rho in RHO_GRID:
        free = holding["uncapped"][str(rho)]
        cap = holding["cap_one"][str(rho)]
        lines.append(
            f"    {rho:<6g}   {free['open']['holding_share']:8.4%} -> "
            f"{free['end']['holding_share']:8.4%} [{kept(free['end'])}]   "
            f"{cap['open']['holding_share']:8.4%} -> "
            f"{cap['end']['holding_share']:8.4%} [{kept(cap['end'])}]    "
            f"{tau * free['end']['cells_per_unit']:.2%} of held units "
            f"(least {tau * free['end']['cells_per_unit_min']:.2%}; largest "
            f"holding {free['end']['largest_holding']:.0f})"
        )
    x = holding["cap_one_crossing"]
    for arm in ("live", "frozen"):
        lines.append(
            f"    one unit per agent, configured rho={x['configured_rho']}, price "
            f"{arm}: crossed in {x[arm]['crossed']:.0f}/{x[arm]['seeds']:.0f} "
            f"seeds, median round {x[arm]['median_from_opening']:.0f} from "
            f"rho_opening, {x[arm]['back']:.1%} of later rounds back below one"
        )
    return lines


def opening_reading(opening: dict[float, dict[str, float | None]]) -> str:
    """The two rationing regimes at the opening, in this run's own numbers."""
    lo, hi = min(RHO_GRID), max(RHO_GRID)
    order = sorted(opening)
    unsold = [r for r in order if opening[r]["seeds_with_unowned"] > 0]
    if not unsold or unsold[0] == order[0]:
        raise ValueError(
            "the opening reading describes two regimes and needs a point where "
            "every unit sells below a point where some do not"
        )
    first_unsold = unsold[0]
    all_sold = [r for r in order if r < first_unsold]
    fine = sorted(OPENING_FINE_GRID)
    top = max(fine, key=lambda r: opening[r]["holding_share"])
    # Where cheapening raises entry is read off the table and not written in:
    # the lowest point from which entry falls at every step up the grid.
    falling_from = order[-1]
    for lower, upper in reversed(list(pairwise(order))):
        if opening[lower]["holding_share"] > opening[upper]["holding_share"]:
            falling_from = lower
        else:
            break
    band = [r for r in order if all_sold[-1] <= r <= falling_from]
    band_shares = [opening[r]["holding_share"] for r in band]
    return (
        f"Up to rho={all_sold[-1]:g} every unit sells in every seed and "
        f"cheapening lets the head of the descending-claims walk take more "
        f"each: {opening[lo]['units_per_production_holder']:.3f} units per "
        f"production buyer at rho={lo:g} against "
        f"{opening[1.0]['units_per_production_holder']:.3f} at rho=1, with the "
        f"financial layer's take rising from "
        f"{opening[1.0]['financial_units']:.1f} to "
        f"{opening[lo]['financial_units']:.1f} of the hundred. From "
        f"rho={first_unsold:g} units go unsold "
        f"({opening[first_unsold]['seeds_with_unowned']:.0f} of "
        f"{opening[first_unsold]['seeds']:.0f} seeds there), "
        f"{opening[1.25]['unowned']:.1f} at rho=1.25 rising to "
        f"{opening[hi]['unowned']:.1f} at rho={hi:g}. From rho={falling_from:g} "
        f"up, entry falls at every step, so there cheapening admits more; "
        f"from rho={all_sold[-1]:g} to {falling_from:g} it stays between "
        f"{min(band_shares):.1%} and {max(band_shares):.1%}. On the finer "
        f"opening grid entry reads "
        + ", ".join(f"rho={r:g}: {opening[r]['holding_share']:.1%}" for r in fine)
        + f"; the highest is {opening[top]['holding_share']:.1%} at rho={top:g}, "
        f"near rho=1, where the median production agent can just enter through "
        f"the stretch, paying everything it holds."
    )


def a5_9(grid: dict[float, dict[str, float]], seeds: range) -> Criterion:
    """A5-1's mechanism, tested by removing the thing it names.

    Registered 2026-08-24, after A5-1 failed and the failure was traced. A5-1
    asks for entry to fall with reachability and it does not: it rises from the
    cheapest point of the grid to a peak near ``rho = 1`` and then collapses.
    The reading put that on there being **no cap on units per agent**: below
    the peak every unit sells, so cheapening does not admit more people, it
    lets the head of the descending-claims walk take more each. The figures are
    in A5-1's detail, computed by ``opening_reading``.

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


def a5_1(
    grid: dict[float, dict[str, float]],
    opening: dict[float, dict[str, float | None]],
) -> Criterion:
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
        "swap over near rho=1. "
        + opening_reading(opening)
        + " **The registered "
        "form assumed price is the only rationing device; there is no per-agent "
        "cap, so cheapness rations by letting the front of the queue buy more "
        "than one.**",
    )


def a5_2(
    grid: dict[float, dict[str, float]],
    opening: dict[float, dict[str, float | None]],
) -> Criterion:
    """Void 2026-08-24: the registered floor was never reachable.

    The criterion asks for entry above 50 percent of the production layer at
    ``rho = 0.5``. **The construction cannot deliver it and the arithmetic is
    one line, available before any run.** There are a hundred units across the
    three tiers and a hundred and eighty production-layer nodes, so entry cannot
    exceed ``100/180``, and that is the bound with every unit going to a
    different production node and none to the financial layer. Reaching 50
    percent needs ninety distinct production holders, which leaves at most ten
    units for the twenty financial-layer nodes. The opening walk is by
    descending claims and those nodes are at its head; what they take at the
    registered low point, and what that leaves the production layer, is
    computed in the detail from the opening allocation.

    **The high half was decidable and is reported**: entry at ``rho = 2`` reads
    against its registered ceiling and that comparison stands.

    The reachable question underneath this one is where entry peaks and what
    rations it on each side. The curve and the two rationing regimes are in
    A5-1's detail, computed by ``opening_reading``.
    """
    spec = AssetSpec()
    low = grid[A5_2_LOW_RHO]["participation"]
    high = grid[A5_2_HIGH_RHO]["participation"]
    production = NetworkSpec().size - NetworkSpec().layer1_size
    stock = sum(spec.units)
    ceiling = stock / production
    take = {r: float(opening[r]["financial_units"]) for r in RHO_GRID}
    least, most = min(take, key=take.get), max(take, key=take.get)
    left = (stock - take[A5_2_LOW_RHO]) / production
    both = sorted(opening)
    top = max(both, key=lambda r: opening[r]["holding_share"])
    return Criterion(
        "A5-2  the threshold sits where the definition puts it",
        False,
        f"**Void: the registered floor of {A5_2_LOW_SHARE:.0%} is above what "
        f"the construction can reach.** {sum(spec.units)} units over "
        f"{production} production-layer nodes bounds entry at {ceiling:.1%}, "
        f"and that bound needs every unit to go to a different production node "
        f"with none to the financial layer, which heads the descending-claims "
        f"walk. At rho={A5_2_LOW_RHO} that layer takes "
        f"{take[A5_2_LOW_RHO]:.1f} of the {stock}, which leaves the production "
        f"layer at most {left:.1%} even at one unit each; across the grid its "
        f"take runs from {take[least]:.1f} at rho={least:g} to "
        f"{take[most]:.1f} at rho={most:g}. Highest entry read anywhere, "
        f"registered and finer opening grid together: "
        f"{opening[top]['holding_share']:.1%} at rho={top:g}. Reported "
        f"either way: at rho={A5_2_LOW_RHO} entry reads {low:.1%}; at "
        f"rho={A5_2_HIGH_RHO} it reads {high:.1%} against its registered "
        f"ceiling of {A5_2_HIGH_SHARE:.0%}, and that half was decidable.",
        void=True,
    )


def a5_3(grid: dict[float, dict[str, float]], a5_4_holds: bool) -> Criterion:
    benign = grid[A5_3_BENIGN]
    hostile = grid[A5_3_HOSTILE]
    rose = benign["share_end"] > benign["share_start"]
    fell = hostile["share_end"] < hostile["share_start"]
    # Void 2026-08-24, **in the configuration where A5-4 holds**. A5-3 needs
    # the benign side to end above where it started; A5-4 asks whether the
    # benign side is an equilibrium at all, and where it reads that it is
    # not, there is no benign end state for the share to rise to. The pair
    # was registered without noticing that, which is the shape
    # `docs/MEASUREMENT.md` failure mode 28 records: a criterion whose other
    # branch the design has already closed.
    #
    # **That is a reading of a configuration and not an identity.** The two
    # read different statistics at different reachabilities: A5-3 the
    # production layer's share of net worth, claims plus units at the market
    # price summed over the layer, at the two ends of the grid; A5-4 the
    # median production agent's claims against the price at one interior
    # point. Neither is the negation of the other, and a configuration in
    # which both fail exists: with the wage bill at four times its registered
    # value the share falls at both ends on seed 0 while the configured
    # rho=0.5 first reaches one at index 162 and is back below it in 97
    # percent of the later rounds. So the void follows A5-4's verdict on the
    # run instead of being written in, and when A5-4 does not hold this
    # criterion is live and scored on its two signs.
    reading = (
        f"net worth share at rho={A5_3_BENIGN}: "
        f"{benign['share_start']:.3f} -> {benign['share_end']:.3f}; at "
        f"rho={A5_3_HOSTILE}: {hostile['share_start']:.3f} -> "
        f"{hostile['share_end']:.3f}. "
    )
    if not a5_4_holds:
        return Criterion(
            "A5-3  the sign of the production layer's trend flips",
            bool(rose and fell),
            reading
            + "A5-4 does not hold on this run, so this criterion is live and "
            "is scored on its two signs: the benign side "
            + ("rises" if rose else "does not rise")
            + " and the hostile side "
            + ("falls" if fell else "does not fall")
            + ".",
        )
    return Criterion(
        "A5-3  the sign of the production layer's trend flips",
        False,
        reading
        + "**Void on this run, because A5-4 holds on it.** A5-4 reads that "
        "the benign side is crossed and not returned to (its own line gives "
        "the count), so in this configuration there is no benign end state "
        "for the share to rise to. That is a reading of the configuration and "
        "not an identity between the two criteria: this one reads the "
        "production layer's share of net worth at the two ends of the grid, "
        f"A5-4 the median production agent's claims against the price at "
        f"rho={A5_4_START}, and a configuration in which both fail has been "
        "read (the wage bill at four times its registered value, seed 0). "
        "The numbers above are the reading. Both regimes fall, which is the "
        "finding rather than a null.",
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


def a5_6(seeds: range, a5_7_holds: bool) -> Criterion:
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
    #
    # 2026-10-24: **the exclusion is a reading of the run, not an identity.**
    # The two read different statistics: this one the largest move against
    # the series' own first point, which carries no level; A5-7 the first
    # index at or above one counted from rho_opening. On this run the frozen
    # series starts below one, so a crossing forces a move far above 1%.
    # With the wage bill at four times its registered value the frozen series
    # drifts by tens of percent and never reaches one, and both fail. So the
    # void follows A5-7's verdict, the way A5-3's follows A5-4's.
    reading = (
        f"largest relative move in rho with the price frozen: {worst:.2%} "
        f"against {A5_6_DRIFT:.0%}. "
    )
    if not a5_7_holds:
        return Criterion(
            "A5-6  freeze the price and the drift disappears",
            worst < A5_6_DRIFT,
            reading
            + "A5-7 does not hold on this run, so this criterion is live and "
            "is scored on its own threshold.",
        )
    return Criterion(
        "A5-6  freeze the price and the drift disappears",
        False,
        reading
        + "**Void on this run, because A5-7 holds on it** (its own line gives "
        "the count). The frozen series starts below one, so a crossing forces "
        "a move far above the threshold, and this number is A5-7's evidence "
        "with the sign of the claim reversed. That is a reading of the "
        "configuration and not an identity: the two read different "
        "statistics, and with the wage bill at four times its registered "
        "value both fail. **The reachable region closes through the "
        "denominator and not through the price**, which A5-8 reads again "
        "over the whole grid.",
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
        f"reachabilities and {len(seeds)} seeds, median cell ratio "
        f"{_spread(ratios)}. Reported without a threshold, the same median "
        f"with the price live is {_spread(live_ratios)}: the two arms are two registered settings of "
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
    ends: dict[float, dict[str, float | None]] = {}
    grid = sweep(seeds, ends)
    opening = opening_table(
        seeds, tuple(sorted(set(RHO_GRID) | set(OPENING_FINE_GRID)))
    )
    holding = who_stays(seeds, opening, ends)
    # One quantity under two names has to be one number. Entry on the grid is
    # read by ``entry_participation`` and again by ``holdings_now`` at the
    # opening; survival by ``participation`` and again by ``holdings_now`` at
    # the end. If either pair parts, one of the two readings has moved.
    for rho in RHO_GRID:
        if opening[rho]["holding_share"] != grid[rho]["participation"]:
            raise AssertionError(f"entry read two ways differs at rho={rho}")
        if ends[rho]["holding_share"] != grid[rho]["survival"]:
            raise AssertionError(f"survival read two ways differs at rho={rho}")

    a5_4_line = a5_4(seeds)
    a5_7_line = a5_7(seeds)
    criteria = [
        a5_1(grid, opening),
        a5_2(grid, opening),
        a5_3(grid, a5_4_line.passed),
        a5_4_line,
        a5_5(seeds),
        a5_6(seeds, a5_7_line.passed),
        a5_7_line,
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

    print("\nwho holds, and who is still holding (printed, not scored)")
    for line in who_stays_lines(holding):
        print(line)

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
                # Added 2026-10-10. The opening allocation behind A5-1's and
                # A5-2's sentences, and who holds at the end with and without
                # the cap. Printed readings; no criterion is scored on them.
                "opening": {str(k): v for k, v in opening.items()},
                "holding": holding,
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
