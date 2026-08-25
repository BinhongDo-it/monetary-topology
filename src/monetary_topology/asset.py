"""A3: the asset channel. Opening allocation, the gate, and pricing.

What is here and what is not
----------------------------
Carried: the full parameter surface of ``docs/a3_asset_channel.md`` §8, the unit
ledger, the terms function, the acquisition gate, the opening allocation, the
pricing rule, and the net worth measure.

Carried as well: turnover under both registered arms, the resale market, and the
cycle counter. The channel is complete.

A configuration that switches turnover off and leaves forced sales off still
runs, and says so through ``DesignDeviation`` and ``A3Model.deviations``. That
is not a partial implementation but a genuine control: with nothing changing
hands the cash-tier-cash cycle is walked zero times, so criteria A3-3, A3-4 and
A3-7 have no realisation to be evaluated against and any divergence the run
shows is revaluation alone.

What this module does establish on its own is A3-1: with ``tiers = 0`` there is
no asset layer and the run is stage A2 to the last bit. That is the same
discipline as ``elasticity = 0``, ``intermediate_size = 0`` and ``min_size = 0``
elsewhere in the repository, and it is worth having by itself, because
everything the later chunks add is interpretable only if the base did not move
underneath them.

Terms, not prices
-----------------
The piece the whole stage turns on, and the reason A3-4 is a test rather than a
restatement.

Class ``a`` acquiring a unit of tier ``q`` pays ``γ_{a,q} · P_q(t)``; every
holder sells at the market price. Over a holding period ``T`` the weight on the
edge from cash into the tier is

    w_a(cash → q) = log( P_q(t+T) / (γ_{a,q} · P_q(t)) )

so the four-cycle ``(a,cash) → (a,q) → (b,q) → (b,cash)`` sums to

    w_a − w_b = log( γ_{b,q} / γ_{a,q} )

and **the price cancels**. The holonomy is the terms differential alone,
independent of the price path. That is what makes A3-4 a test rather than a
restatement: the simulation contains price dynamics, claim circulation, a wage
bill, issuance, supply constraints and turnover, none of which appear in that
expression, and the prediction is that they leave it intact.

``γ`` also sets the gate: a node may acquire tier ``q`` only if its claims cover
``γ_{i,q} · P_q(t)``. Worse terms mean both paying more and being shut out
sooner as prices rise, which is the framework's distinction between a hole and a
high price expressed as one parameter rather than two.

What is assumed, and what only looks assumed
-------------------------------------------
That centrality sets bargaining position reads like a free assumption and mostly
is not one. It is the Cantillon effect on a graph: new money enters at a point,
and whoever is nearest that point transacts on the old price level before it
adjusts. The structure predates this stage — stage A2 injects at
``argmax(in_degree)`` over the financial layer, so the injection point *is* the
most central node by construction, and A2's whole subject is reachability from
it. A3 restates the same fact one level down, at the terms rather than at the
flow.

So the **direction** — higher centrality, better terms — follows from the
injection rule together with the graph. What is chosen, and therefore what a
critic should aim at, is the **functional form** ``γ = γ̄ (1 + κ (1 − c))`` and
the value of ``κ``, which is swept end to end so that no result lives at one
value of it. Section 3.3 of the pre-registration records why the remaining
assumption is not demoted to a derivation here.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from .network import Network, NetworkConfig, NetworkHistory

#: Which units are offered back to the market each round.
TURNOVER_ARMS: tuple[str, ...] = ("exogenous", "forced")

#: What entering short of the price costs the entrant.
STRETCH_COSTS: tuple[str, ...] = ("uncounted", "counted")

#: ``docs/a3b_initial_construction.md`` §3. Three sourced points on one axis:
#: how strongly opening ownership tracks opening claims. Not three unrelated
#: modes, and the ownership *rate* is explicitly not the axis (§3.4).
CONSTRUCTIONS: tuple[str, ...] = ("auction", "occupancy", "continuous")

#: Where the opening sale's proceeds go. ``"equal"`` splits across all nodes and
#: is what the code did before A3b; ``"seller"`` pays whoever held the unit.
PROCEEDS: tuple[str, ...] = ("equal", "seller")

#: Who the rent bill is assessed on. ``layer`` keys the payer set on the layer
#: index fixed at construction, which is what every result before 2026-08-13
#: was produced under and remains the default so those results reproduce
#: bitwise. ``holding`` keys it on the measured magnitude, so the two sides of
#: the instrument are keyed on the same kind of thing.
#:
#: `MEASUREMENT.md` §8 lists the payer side of this instrument as a membership
#: error and its checklist item 9 asks, of any number, whether it is keyed on a
#: set fixed at construction time and whether the other side of a two-sided
#: instrument is keyed on the same kind of thing. Here it is not: the receipt
#: side is already ``held > 0``, computed every round from the measured units,
#: while the payer side carries ``& _is_production``. So a financial-layer node
#: holding nothing pays no rent and a production-layer node holding nothing
#: pays every round, and neither fact is about renting.
#:
#: This switch does not make layer endogenous and is not an argument for doing
#: so. Layer as position, meaning who has which edges, is the framework's own
#: object and is untouched. What moves is a **liability**, and the real thing it
#: stands for is assessed on whether you hold, which the model already measures.
RENT_BASES: tuple[str, ...] = ("layer", "holding")


class DesignDeviation(UserWarning):
    """The configuration runs, but departs from the registered design.

    Two kinds of refusal are worth keeping apart. A configuration that is
    *incoherent* -- units that do not match the tier count, a negative
    elasticity -- raises, because there is nothing to run. A configuration that
    is coherent but departs from what was registered runs and warns, because
    debugging a mechanism routinely means holding it in states the final design
    does not contain, and a stage that refuses those states is a stage that
    cannot be debugged.

    The warning is not decoration. Anything reported out of a run that raised it
    has to say so, which is why ``A3Model.deviations`` keeps the list rather
    than relying on whoever was watching stderr.
    """


@dataclass(frozen=True)
class AssetSpec:
    """The asset channel's parameters. Values are those registered in §8.

    The defaults are the pre-registered values and
    ``test_defaults_match_the_pre_registration`` asserts it. That test exists so
    that a later edit which quietly moves a default in order to make A3-4 pass
    fails the suite rather than passing unremarked.
    """

    #: Tiers. ``0`` removes the asset layer entirely and is the A3-1 control.
    tiers: int = 3

    #: Units available in each tier, low to high.
    units: tuple[int, ...] = (60, 30, 10)

    #: ``P_q(0)``. Reference price of each tier at ``t = 0``, low to high.
    #:
    #: Absent from the pre-registration's §8 table, which is a gap rather than a
    #: freedom: the price path has to start somewhere. Added before any run and
    #: recorded in §9.1. The registered values put the asset stock at
    #: ``60·0.5 + 30·1 + 10·2 = 80``, or eighty percent of the opening claim
    #: stock of one hundred, and give the tiers a price ratio of ``1 : 2 : 4``,
    #: which is what makes them three different things rather than three names
    #: for one.
    initial_price: tuple[float, ...] = (0.5, 1.0, 2.0)

    #: ``η``. Price elasticity to the bidder pool's claims. Zero freezes prices
    #: while leaving the asset in place, which is the control separating
    #: revaluation from ownership as such.
    elasticity: float = 1.0

    #: ``γ̄_q``. Base acquisition terms by tier, low to high. Close to one
    #: because a terms premium is a premium and not a multiple: the whole of the
    #: loop sum comes from ``terms_spread``.
    base_terms: tuple[float, ...] = (1.00, 1.05, 1.15)

    #: ``κ``. How far terms spread across centrality. The most central node pays
    #: ``γ̄_q`` and the most peripheral pays ``(1 + κ) γ̄_q``. Zero makes terms
    #: uniform, which sets the loop sum to zero by construction and makes A3-4
    #: vacuous; the pre-registration records that a pass there is a null.
    terms_spread: float = 1.0

    #: ``τ``. Share of held units returning to the market each round for reasons
    #: unrelated to price. Set at the observed turnover of the US housing stock,
    #: roughly three to five percent a year, with a round read as a year.
    turnover: float = 0.04

    #: ``φ``. A node holding claims below this share of its round-zero claims
    #: must sell one unit. Arm F only.
    forced_sale_floor: float = 0.10

    #: How many bins the trader population is cut into before two of them are
    #: compared. Swept, for the same reason B2 sweeps its band and its minimum
    #: cell size: a result that lives in the binning is a result about the
    #: binning.
    #:
    #: **This field existed for a long time and was read by nothing.** It was
    #: declared, validated against ``< 1``, documented as feeding the loop sum,
    #: and no line in the repository ever looked at it. Two models differing
    #: only in it were bit-identical in ``terms``, ``units``, ``cycles``,
    #: ``centrality``, ``uncounted_cost`` and ``net_worth``. The §6.5 grid duly
    #: swept it across ``2`` and ``8``, reported "no state change" both times,
    #: and that clean row was worth nothing: an axis that reaches no code cannot
    #: move a verdict, and a grid that counts it as robustness is claiming
    #: coverage it does not have.
    #:
    #: **The default moved from 4 to 3, and 3 is not a preference.** Both call
    #: sites cut the population into thirds with a hardcoded ``// 3``, so 3 is
    #: the value at which the wired parameter reproduces every stored A3 result
    #: bit for bit. Leaving the declared ``4`` in place would have silently
    #: changed every number in the stage the moment the wire was connected,
    #: which is the failure the reduction guard exists to make impossible. The
    #: declared ``4`` was never the behaviour of anything.
    #:
    #: **What it controls, at both sites.** The population is ranked and cut
    #: into this many equal bins of width ``floor(n / bins)``, and the outermost
    #: two are compared. In ``a3_asset_channel.terms_pair`` the ranking is by
    #: ``γ``, which is the same ranking as centrality: ``γ = γ̄(1 + κ(1 − c))``
    #: is strictly monotone decreasing in ``c``, so ordering by terms and
    #: ordering by centrality are the same order and the field name is accurate.
    #: In ``a3c_load_bearing.terciles`` the ranking is on ``centrality``
    #: directly. Larger values mean narrower, more extreme groups.
    centrality_bins: int = 3

    #: ``T``. Holding period in the edge weight and in the counted stretch's
    #: amortisation, in rounds.
    #:
    #: This is the period over which a holding is actually held, so under arm E
    #: it must equal ``1 / turnover``. It was first set to ``40`` to match stage
    #: A4's generation length, which is a different quantity that happens to be
    #: a duration; the mismatch silently rescales ``δ`` and would have moved
    #: A3-4 by a factor of ``40/25`` with nothing in the run looking wrong. A
    #: configuration where the two disagree raises ``DesignDeviation``.
    holding_period: int = 25

    #: Which turnover arm. Both are registered and both are reported; their
    #: difference is the contribution of the liquidation channel, measured
    #: rather than assumed.
    arm: str = "exogenous"

    #: Tiers opened to every node regardless of terms, for A3-5.
    open_tiers: tuple[int, ...] = ()

    #: Rent per round, as a share of the low tier's current price, paid by
    #: production-layer nodes holding nothing to the nodes that hold units, in
    #: proportion to how many they hold.
    #:
    #: **Zero recovers the revaluation-only mechanism bitwise** and is the
    #: control. It is a switch rather than a fixture because the two settings
    #: answer different questions and the framework's own text does not
    #: obviously pick one:
    #:
    #: - ``0``: the gap between two agents comes from **the terms each is
    #:   charged when transacting**, compounding over round trips. Both parties
    #:   are in the market. Being outside is not a cost, it is an absence.
    #: - ``> 0``: holding **extracts** from not holding, every round, and the
    #:   amount scales with the price. Being outside costs, and what it costs
    #:   goes to those inside.
    #:
    #: The distinction is not academic. Measured at ``rent_rate = 0`` over three
    #: hundred rounds with prices up eighty-nine fold, production-layer nodes
    #: that never held anything ended **253% richer in claims** than in a run
    #: with no asset market at all, because they collect the opening rebate and
    #: the transaction premium and the price never touches them. A housing
    #: market that makes lifelong renters richer is not the mechanism the source
    #: framework describes.
    #:
    #: Five percent is a gross rental yield in the range US residential property
    #: actually shows, with a round read as a year.
    rent_rate: float = 0.05

    #: Which set the rent bill falls on. See ``RENT_BASES``. Default ``layer``
    #: reproduces every result recorded before 2026-08-13 bitwise, and the
    #: reproduction is asserted in ``tests/test_a3_rent_base.py`` rather than
    #: argued for here.
    rent_base: str = "layer"

    #: Most units one node may hold. ``0`` is no cap.
    #:
    #: A cap of one was the first implementation and it is kept available,
    #: because it is the cleanest reading of "who is inside and who is outside".
    #: It is not the default, and the reason is structural rather than a matter
    #: of taste: with a cap of one, every node that can afford anything already
    #: holds something within a few rounds, so an offered unit has no eligible
    #: buyer and three hundred rounds produce **zero** transactions. The
    #: cash-tier-cash cycle is then walked zero times and A3-3, A3-4 and A3-7
    #: have nothing to be evaluated on. The cap forbids the very thing the stage
    #: exists to measure, and the framework's own account — claims pile up at
    #: the top and the top bids for assets — is accumulation of more than one.
    #:
    #: **The zero-transaction claim above is scale-dependent, and it had never
    #: been run when it was written.** Measured 2026-08-15 by
    #: ``experiments/a5a_units_cap_probe.py`` at stage A5's price scale, three
    #: hundred rounds, five seeds, mean transactions at a cap of one:
    #:
    #: ===========  =====  =====  =====  =====  =====  =====
    #: rho_eff       0.25    0.5    1.0    2.0    4.0    8.0
    #: cap of one    12.6    4.2    0.0    0.0    0.0  117.6
    #: no cap       504.0  485.0  450.6  201.4  167.0  131.6
    #: ===========  =====  =====  =====  =====  =====  =====
    #:
    #: **It holds where stage A3 actually sits and not in general.** A3's
    #: registered parameters put its production layer at an effective
    #: reachability of about ``1.96``, inside the band where the cap does
    #: produce zero transactions, so the argument for the default is sound at
    #: the operating point it was written about. As a claim about the mechanism
    #: it is too strong: cheap enough and the opening does not clear every
    #: eligible buyer, dear enough and most of the stock never sells, and either
    #: way an offered unit finds a buyer.
    #:
    #: **The original sentence is left standing rather than corrected**, on the
    #: same rule that keeps ``MechanismParams``'s falsified docstring claim in
    #: place: a claim that turned out to be narrower than it was stated is a
    #: record, and rewriting it would remove the evidence that it was ever
    #: believed in the wider form. The default does not move on this account.
    max_units: int = 0

    #: ``s``. How far short of the acquisition cost a node may be and still
    #: enter, by paying everything it has. ``1`` is the hard gate and recovers
    #: the earlier behaviour bitwise.
    #:
    #: The boundary between inside and outside is soft in the world and was
    #: modelled hard because nothing seemed to turn on it. Something did: at
    #: ``s = 1`` the entire production layer is priced out of even the lowest
    #: tier and eighty of a hundred units have no buyer, which is not exclusion
    #: but the absence of a market. Measured on the production layer, ``s = 2``
    #: admits seven nodes of a hundred and eighty and ``s = 3`` admits
    #: twenty-three; ``s = 5`` admits eighty-eight, which is no longer
    #: stretching.
    stretch: float = 3.0

    #: What the shortfall costs.
    #:
    #: ``"uncounted"`` — health, family harmony, things consumed to get in that
    #: no ledger records. Recorded in ``A3Model.uncounted_cost`` and never
    #: entering the claim accounts, so ``net_worth`` overstates a stretcher's
    #: true position by exactly that amount and the model can print the amount
    #: instead of leaving a caveat. This is the framework's hole-versus-high-
    #: price distinction inside an A-track simulation: the price system records
    #: that they could afford it, and something real was consumed that the price
    #: system does not price.
    #:
    #: ``"counted"`` — medical expenses and the like. The shortfall is amortised
    #: over ``holding_period`` rounds as ordinary outgoings, **routed through the
    #: node's own adjacency row**. No new edge and no assumption about who
    #: receives: the graph already leaks upward from the production layer, so
    #: the stretcher financing somebody upstream for years afterward is derived
    #: rather than imposed.
    stretch_cost: str = "uncounted"

    # -- A3b: the opening construction ------------------------------------
    #
    # Every default below reproduces the pre-A3b behaviour bitwise. A
    # generalisation that cannot recover its own special case is not a
    # generalisation, the same discipline as ``elasticity = 0``.

    #: Which rule distributes the opening stock. ``docs/a3b_initial_
    #: construction.md`` §3.
    #:
    #: ``"auction"`` — highest tier first, richest first. Retained as the
    #: default and it is not fictional: it is the primary sale of new supply and
    #: the institutional purchase of distressed stock. It is simply not what the
    #: distribution of an **existing** stock looks like at the start.
    #:
    #: ``"occupancy"`` — sitting tenants receive the dwelling they occupy,
    #: ranked by residence rather than means. China 1998, Russia 1992, UK Right
    #: to Buy 1980.
    #:
    #: ``"continuous"`` — no opening event; ownership already tracks wealth
    #: without following the ranking strictly. The United States, which never
    #: ran an opening allocation.
    construction: str = "auction"

    #: Dwellings per node. ``0`` uses ``units`` verbatim and is the pre-A3b
    #: behaviour.
    #:
    #: The registered supply of ``(60, 30, 10)`` against two hundred nodes is
    #: **0.5 dwellings per node**, so half the population is without a dwelling
    #: before any mechanism runs and "the production layer holds nothing" is
    #: partly a statement about this number. Both large marketised economies sit
    #: in the same narrow place: the United States at 146.7M units over 132.7M
    #: households, or ``1.11``; urban China's 套户比 (dwelling-to-household
    #: ratio) at ``1.09``, up from ``0.8`` in 1978. A3b registers ``1.1`` with
    #: the tier ratio ``6 : 3 : 1`` left alone, so supply and tier structure
    #: cannot be confounded later.
    units_per_node: float = 0.0

    #: Share of nodes owning a dwelling at ``t = 0`` under ``occupancy`` and
    #: ``continuous``. Ignored under ``auction``, where ownership is an outcome.
    #:
    #: **This is not the axis.** ``occupancy`` at ``0.70`` and ``continuous`` at
    #: ``0.653`` are close on purpose: what separates them is *who* owns at the
    #: same rate, assigned by residence or sorted by claims. Any result that
    #: could be had by moving this number alone is mis-specified. §3.4.
    ownership_rate: float = 0.0

    #: Discount on the opening acquisition under ``occupancy``. The UK Right to
    #: Buy average was ``0.44``, from 33% at three years' tenure to 50% at
    #: twenty; Russia's transfer was effectively free, which is ``1.0``.
    #: Recorded in ``basis``, so it enters realised returns and therefore A3-4.
    opening_discount: float = 0.0

    #: Whether stock that finds no buyer keeps an owner. ``False`` is the
    #: pre-A3b behaviour and it is wrong: thirty-nine of a hundred units ended
    #: owned by nobody, so they never returned to the market (``_offers`` walks
    #: ``units > 0``) and never collected rent (``_collect_rent`` pays holders).
    #: **A dwelling that nobody owns does not exist in any economy.** The
    #: residual is stock still held by whoever held it before, which in a
    #: two-layer model is upstairs: the developer, the state, the incumbent.
    residual_owner: bool = False

    # -- a3_restated.md §4: gamma does double duty, so it is split -----------

    #: ``κ_gate``. Terms dispersion in the **admission threshold**, as against
    #: ``terms_spread`` which is now the dispersion in what is **paid**.
    #: ``None`` ties it to ``terms_spread`` and recovers the single-parameter
    #: behaviour bitwise.
    #:
    #: The split exists because one symbol was carrying two objects.
    #: ``H¹`` — the loop sum — lives in what is paid: the cochain sees prices
    #: and nothing else. ``H⁰`` — reachability — lives in who may enter: a
    #: restriction on the domain, a hole, outside the cochain by construction.
    #: Moving ``terms_spread`` alone moved both, so the one intervention that
    #: could show the holonomy is load-bearing was unavailable: `MEASUREMENT.md`
    #: rule 4, one switch changing two things.
    gate_spread: float | None = None

    #: Hold the cross-sectional **mean** acquisition cost fixed while the
    #: dispersion moves, at ``mean_cost_reference``. Off by default because it
    #: rescales the base terms and so is not bitwise for the registered run.
    #:
    #: Required for any comparison across ``terms_spread`` values. Without it
    #: the flat cell is also the cheap cell: nodes keep more claims, which is a
    #: level effect and not the dispersion effect under test.
    hold_mean_cost: bool = False

    #: The ``κ`` whose mean cost is held. Defaults to the registered
    #: ``terms_spread``, so the registered cell is the reference and the others
    #: are moved onto it rather than the other way round.
    mean_cost_reference: float = 1.0

    #: Where the opening proceeds go. ``"equal"`` is the pre-A3b split across
    #: all nodes, defended at the time as neutral because pro-rata would let the
    #: opening transaction itself concentrate claims. It is not neutral: the
    #: seller of a dwelling is its previous owner, and previous owners are not
    #: uniformly distributed, so an equal split performs one perfectly
    #: egalitarian redistribution at ``t = 0`` and then measures how a gap opens
    #: from there.
    proceeds: str = "equal"

    def units_for(self, n: int) -> tuple[int, ...]:
        """Tier supply for ``n`` nodes, from ``units_per_node`` if it is set.

        The tier **ratio** is taken from ``units`` and only the total is
        rescaled, so this cannot quietly change the tier structure. Rounding
        goes to the largest remainder and the low tier absorbs the residue, so
        the total is exact.
        """
        if self.units_per_node <= 0.0 or not self.units:
            return self.units
        total = int(round(self.units_per_node * n))
        base = sum(self.units)
        if base <= 0:
            return self.units
        exact = [total * u / base for u in self.units]
        out = [int(x) for x in exact]
        for i in sorted(
            range(len(out)), key=lambda i: exact[i] - out[i], reverse=True
        )[: total - sum(out)]:
            out[i] += 1
        return tuple(out)

    def __post_init__(self) -> None:
        if self.tiers < 0:
            raise ValueError("tiers must be non-negative")
        if len(self.units) != self.tiers:
            raise ValueError(
                f"units must have one entry per tier: {self.tiers} tiers, "
                f"{len(self.units)} entries"
            )
        if len(self.base_terms) != self.tiers:
            raise ValueError(
                f"base_terms must have one entry per tier: {self.tiers} tiers, "
                f"{len(self.base_terms)} entries"
            )
        if len(self.initial_price) != self.tiers:
            raise ValueError(
                f"initial_price must have one entry per tier: {self.tiers} "
                f"tiers, {len(self.initial_price)} entries"
            )
        if any(p <= 0.0 for p in self.initial_price):
            raise ValueError("initial_price must be positive")
        if any(u < 0 for u in self.units):
            raise ValueError("units must be non-negative")
        if any(g < 1.0 for g in self.base_terms):
            warnings.warn(
                "base_terms below one give a discount for being peripheral, "
                "which is the registered mechanism with its sign reversed. "
                "This runs, and it is a useful thing to run, because what "
                "happens under the reversed sign is a question the stage can "
                "answer. Any result taken from here must be labelled as the "
                "reversed-sign arm and not compared against the registered "
                "one without saying so.",
                DesignDeviation,
                stacklevel=2,
            )
        if self.elasticity < 0.0:
            raise ValueError("elasticity must be non-negative")
        if self.terms_spread < 0.0:
            raise ValueError("terms_spread must be non-negative")
        if not 0.0 <= self.turnover <= 1.0:
            raise ValueError("turnover must lie in [0, 1]")
        if not 0.0 <= self.forced_sale_floor <= 1.0:
            raise ValueError("forced_sale_floor must lie in [0, 1]")
        if self.centrality_bins < 1:
            raise ValueError("centrality_bins must be at least 1")
        if self.holding_period < 1:
            raise ValueError("holding_period must be at least 1")
        if self.arm not in TURNOVER_ARMS:
            raise ValueError(f"arm must be one of {TURNOVER_ARMS}, got {self.arm!r}")
        if any(not 0 <= q < self.tiers for q in self.open_tiers):
            raise ValueError("open_tiers must index existing tiers")
        if self.max_units < 0:
            raise ValueError("max_units must be non-negative; 0 means no cap")
        if not 0.0 <= self.rent_rate < 1.0:
            raise ValueError("rent_rate must lie in [0, 1)")
        if self.rent_base not in RENT_BASES:
            raise ValueError(
                f"rent_base must be one of {RENT_BASES}, got {self.rent_base!r}"
            )
        if self.stretch < 1.0:
            raise ValueError(
                "stretch must be at least one: below one it would exclude nodes "
                "that can pay the full cost, which is not a softer gate but a "
                "different one"
            )
        if self.stretch_cost not in STRETCH_COSTS:
            raise ValueError(
                f"stretch_cost must be one of {STRETCH_COSTS}, "
                f"got {self.stretch_cost!r}"
            )
        if self.construction not in CONSTRUCTIONS:
            raise ValueError(
                f"construction must be one of {CONSTRUCTIONS}, "
                f"got {self.construction!r}"
            )
        if self.proceeds not in PROCEEDS:
            raise ValueError(
                f"proceeds must be one of {PROCEEDS}, got {self.proceeds!r}"
            )
        if self.units_per_node < 0.0:
            raise ValueError("units_per_node must be non-negative; 0 uses units")
        if not 0.0 <= self.ownership_rate <= 1.0:
            raise ValueError("ownership_rate must lie in [0, 1]")
        if not 0.0 <= self.opening_discount <= 1.0:
            raise ValueError("opening_discount must lie in [0, 1]")
        if self.gate_spread is not None and self.gate_spread < 0.0:
            raise ValueError("gate_spread must be non-negative")
        if self.mean_cost_reference < 0.0:
            raise ValueError("mean_cost_reference must be non-negative")
        if (
            self.gate_spread is not None
            and self.gate_spread != self.terms_spread
            and not self.hold_mean_cost
        ):
            warnings.warn(
                "the payment and gate dispersions differ but the mean "
                "acquisition cost is not being held fixed, so the arms differ "
                "in level as well as in dispersion and the 2x2 of "
                "a3_restated.md §4.3 is not separable. This runs, because "
                "running it is how the size of the level effect is measured, "
                "but no cell comparison may be taken from it.",
                DesignDeviation,
                stacklevel=2,
            )
        if self.construction != "auction" and self.ownership_rate <= 0.0:
            raise ValueError(
                f"construction {self.construction!r} allocates by ownership "
                "rate and none was given; A3b §5 registers 0.70 for occupancy "
                "and 0.653 for continuous"
            )
        if self.construction == "auction" and self.ownership_rate > 0.0:
            warnings.warn(
                "ownership_rate is ignored under construction='auction', where "
                "ownership is an outcome rather than a parameter. Setting it "
                "here has no effect and suggests the wrong construction was "
                "selected.",
                DesignDeviation,
                stacklevel=2,
            )
        if self.construction != "occupancy" and self.opening_discount > 0.0:
            warnings.warn(
                "opening_discount is registered for the occupancy transfer, "
                "where a sitting tenant buys below market. Applying it to a "
                "market sale is a different mechanism and the run must be "
                "labelled as such.",
                DesignDeviation,
                stacklevel=2,
            )
        if self.construction != "auction" and not self.residual_owner:
            warnings.warn(
                "construction is not 'auction' but residual_owner is off, so "
                "unallocated stock is owned by nobody. That combination is "
                "coherent and runs, and it is the pre-A3b defect the new "
                "constructions exist to remove, so no number from it may be "
                "compared against a residual_owner run.",
                DesignDeviation,
                stacklevel=2,
            )

    @property
    def closed(self) -> bool:
        """Whether the asset layer is absent. The A3-1 control."""
        return self.tiers == 0


#: Section 4's registered robustness grid, **one parameter at a time off the
#: registered point**. It lives here rather than in either experiment because
#: both of them sweep it and a second copy would drift; it names fields of
#: :class:`AssetSpec`, so this is where a reader checks it against the thing it
#: varies.
#:
#: **One at a time, not a factorial, and the limitation is registered rather
#: than hidden.** The full grid is 4 x 3 x 3 x 4 x 3 = 432 cells, and section
#: 6.5's promise quantifies over one parameter at a time, which is what this
#: tests. What it does not test is interactions, and section 4's own table
#: registers ``initial_price`` as swept *with* ``stretch``, so at least one
#: pair is registered as joint and this grid does not deliver it.
#:
#: Two entries move a second field, and neither is an interaction.
#: ``forced_sale_floor`` does nothing under the exogenous arm, so sweeping it
#: alone would measure zero. ``holding_period`` is registered as tied to
#: ``turnover`` and this module enforces the tie with a ``DesignDeviation``
#: computed as ``round(1 / turnover)``; a mismatched ``T`` rescales the loop
#: sum, so A3-4 would move by that factor with nothing in the run looking
#: wrong. The first version of the turnover cells moved ``turnover`` alone and
#: the model said so.
SWEEP_CELLS: tuple[tuple[str, dict], ...] = (
    ("eta", {"elasticity": 0.0}),
    ("eta", {"elasticity": 0.5}),
    ("eta", {"elasticity": 1.5}),
    ("tau", {"turnover": 0.02, "holding_period": 50}),
    ("tau", {"turnover": 0.08, "holding_period": 12}),
    ("phi", {"forced_sale_floor": 0.05, "arm": "forced"}),
    ("phi", {"forced_sale_floor": 0.10, "arm": "forced"}),
    ("phi", {"forced_sale_floor": 0.20, "arm": "forced"}),
    ("s", {"stretch": 1.0}),
    ("s", {"stretch": 2.0}),
    ("s", {"stretch": 5.0}),
    ("bins", {"centrality_bins": 2}),
    ("bins", {"centrality_bins": 8}),
    ("stretch_cost", {"stretch_cost": "counted"}),
)


#: The registered configuration. ``CLOSED`` is the A3-1 control.
CLOSED = AssetSpec(tiers=0, units=(), base_terms=(), initial_price=())


def carrier_model(config: NetworkConfig, *, asset: bool = False) -> Network:
    """The model for one run, with or without A3's asset layer on top.

    **One place, because five stages need the same two lines and a copy in each
    is five chances to write them differently.** A2d, A10, A11, A13 and A14 all
    read concentration off a carrier with no asset revaluation on it, and
    revaluation is the channel the empirical work weights most heavily:
    Montecino and Epstein put an employment channel at about -0.5 points on the
    90/10 ratio against an equity channel at about +6.3 on the 95/10 ratio.

    **The returned object is the model and not the history**, because a caller
    may want the state after the run: A11 reads ``_alive`` to see who left. Call
    ``.run()`` on it.

    ``asset=False`` constructs a plain ``Network``, so the default path is the
    path those stages always took and reproduction is by construction.

    **What the asset layer changes is measured, not assumed.** A2d's four
    corners, 2026-08-24: the structural span on terminal top one percent wealth
    moves 0.156440 to 0.153907, essentially not at all, while sigma's span moves
    0.006645 to 0.015829, more than doubling. The ratio between them, which is
    that stage's headline, goes from 23.5 to 9.7. **The direction survives and
    the number does not**, and the mechanism is plain: sigma is a retention rate
    and retained claims can sit in an appreciating asset, so retention buys more
    when there is something to retain into.
    """
    if not asset:
        return Network(config)
    return A3Model(A3Config(asset=AssetSpec(), network=config))


@dataclass(frozen=True)
class A3Config:
    asset: AssetSpec = field(default_factory=lambda: CLOSED)
    network: NetworkConfig = field(default_factory=NetworkConfig)


# ---------------------------------------------------------------------------
# The terms function
# ---------------------------------------------------------------------------


def centrality(adjacency: np.ndarray) -> np.ndarray:
    """Normalised in-degree, in ``[0, 1]``, one entry per node.

    In-degree rather than any spectral measure, for two reasons. It is the
    statistic stage A2 already uses to set initial holdings and to pick the
    injection node, so A3 introduces no new notion of position. And it is
    computable by hand from the adjacency matrix, which the eigenvector measures
    are not, and this stage's whole defence is that a reader can check it.

    A graph with no edges returns zeros rather than dividing by zero: a node in
    an empty graph is not central, and it is not undefined either.
    """
    indeg = np.asarray(adjacency, dtype=float).sum(axis=0)
    peak = float(indeg.max()) if indeg.size else 0.0
    if peak <= 0.0:
        return np.zeros_like(indeg)
    return indeg / peak


def terms_matrix(
    centrality_values: np.ndarray,
    spec: AssetSpec,
    spread: float | None = None,
    hold_mean_at: float | None = None,
) -> np.ndarray:
    """``γ_{i,q}``, one row per node and one column per tier.

    ``γ_{i,q} = γ̄_q · (1 + κ (1 − c_i))``

    Monotone decreasing in centrality: the most central node pays the base
    terms, the most peripheral pays ``(1 + κ)`` times them. With ``κ = 0`` every
    row is identical and the four-cycle sums to zero.

    ``spread`` overrides ``κ``. ``a3_restated.md`` §4 splits ``γ`` into what is
    paid and what admits, and the two carry different ``κ``.

    ``hold_mean_at`` is the trap in §4.4, implemented rather than warned about.
    Lowering ``κ`` does not only flatten the terms, it lowers the **mean**
    acquisition cost, so the flat cell is also the cheap cell and the two cannot
    be told apart. Given a reference ``κ_ref``, the base is rescaled by

    ``(1 + κ_ref (1 − c̄)) / (1 + κ (1 − c̄))``

    which holds the cross-sectional mean of ``γ`` at its value under ``κ_ref``
    while leaving the dispersion to move. At ``κ = κ_ref`` the factor is one and
    the matrix is unchanged bitwise.
    """
    c = np.asarray(centrality_values, dtype=float)
    base = np.asarray(spec.base_terms, dtype=float)
    if base.size == 0:
        return np.zeros((c.size, 0))
    k = spec.terms_spread if spread is None else float(spread)
    if hold_mean_at is not None and c.size:
        gap = 1.0 - float(c.mean())
        base = base * ((1.0 + float(hold_mean_at) * gap) / (1.0 + k * gap))
    return base[None, :] * (1.0 + k * (1.0 - c)[:, None])


def gate_clears(
    claims: np.ndarray,
    terms: np.ndarray,
    price: np.ndarray,
    open_tiers: tuple[int, ...] = (),
) -> np.ndarray:
    """``(n, Q)`` boolean: can node ``i`` cover the acquisition cost of tier
    ``q``?

    The condition is ``claims_i ≥ γ_{i,q} · P_q``. One parameter carries both
    halves of the mechanism: worse terms mean paying more *and* being shut out
    sooner as the price rises. That is the framework's distinction between a
    hole and a high price, and keeping it in one parameter is what stops the two
    from being tuned against each other.

    ``open_tiers`` forces a tier open to every node regardless of claims. That
    is the A3-5 experiment and nothing else uses it.
    """
    claims = np.maximum(np.asarray(claims, dtype=float), 0.0)
    cost = np.asarray(terms, dtype=float) * np.asarray(price, dtype=float)[None, :]
    clears = claims[:, None] >= cost
    for q in open_tiers:
        clears[:, q] = True
    return clears


def soft_gate(
    claims: np.ndarray,
    terms: np.ndarray,
    price: np.ndarray,
    stretch: float = 1.0,
    open_tiers: tuple[int, ...] = (),
) -> tuple[np.ndarray, np.ndarray]:
    """``(admitted, stretched)``, both ``(n, Q)`` boolean.

    Three bands rather than two::

        claims ≥ γ·P            enters comfortably
        γ·P / s ≤ claims < γ·P  enters stretched, paying everything it has
        claims < γ·P / s        excluded

    ``stretch = 1`` collapses the middle band to nothing and returns the hard
    gate exactly, with ``stretched`` all false. That is the nested control, the
    same discipline as ``elasticity = 0`` and ``terms_spread = 0``.

    A node in an ``open_tiers`` tier is admitted and is never counted as
    stretched: the A3-5 experiment removes the gate rather than softening it,
    and conflating the two would make its result partly about the stretch
    parameter.
    """
    if stretch < 1.0:
        raise ValueError("stretch must be at least one")
    claims = np.maximum(np.asarray(claims, dtype=float), 0.0)
    cost = np.asarray(terms, dtype=float) * np.asarray(price, dtype=float)[None, :]
    comfortable = claims[:, None] >= cost
    admitted = claims[:, None] >= cost / stretch
    for q in open_tiers:
        admitted[:, q] = True
        comfortable[:, q] = True
    return admitted, admitted & ~comfortable


def bidder_pool(claims: np.ndarray, clears: np.ndarray) -> np.ndarray:
    """``(Q,)``: total claims held by the nodes clearing each tier's gate.

    ``B_q`` in the pricing rule. Claims, never net worth. Pricing off net worth
    would make the price a function of the price, and the widening this stage
    exists to measure would be an accounting identity rather than a result.

    **``clears`` must be evaluated at opening prices, not current ones.** The
    pre-registration wrote "nodes that clear tier q's gate at t", and taking
    that literally makes the rule oscillate rather than compound: a rising price
    thins the set that clears, which shrinks the pool, which lowers the price.
    Once the set empties the pool is zero and the price collapses to zero, after
    which everybody clears and it explodes. Measured over three hundred rounds
    that is a two-cycle, and the top tier sits in it.

    Evaluating the gate at opening prices removes the feedback from price into
    its own input while keeping what the mechanism is about: the pool is those
    who could have afforded the tier when it opened, and the price follows what
    *they* accumulate. Those who fall behind are excluded, and being excluded
    they do not moderate the price. That is the stretching effect as the source
    states it; the literal reading was a market that talks itself back down.
    """
    c = np.maximum(np.asarray(claims, dtype=float), 0.0)
    return (c[:, None] * np.asarray(clears, dtype=float)).sum(axis=0)


def price_at(
    initial_price: np.ndarray,
    pool: np.ndarray,
    pool_0: np.ndarray,
    elasticity: float,
) -> np.ndarray:
    """``P_q(t) = P_q(0) · (B_q(t) / B_q(0)) ^ η``.

    ``η = 0`` freezes prices exactly, which is the control that separates
    revaluation from ownership as such: if the A3-2 gap still opens there, it is
    produced by holding the asset rather than by the asset revaluing, and this
    stage's account of compounding is wrong.

    A tier whose opening pool was empty keeps its opening price. There is no
    ratio to take, and inventing one would put a number where the model has
    none.
    """
    p0 = np.asarray(initial_price, dtype=float)
    b = np.asarray(pool, dtype=float)
    b0 = np.asarray(pool_0, dtype=float)
    if elasticity == 0.0:
        return p0.copy()
    ratio = np.divide(b, b0, out=np.ones_like(p0), where=b0 > 0)
    return p0 * np.power(np.maximum(ratio, 0.0), elasticity)


def _apportion(count: int, weights: np.ndarray) -> np.ndarray:
    """Hand out ``count`` **whole** units across ``weights``.

    Largest remainder, ties broken by index so the result is deterministic
    across platforms and across runs. Dwellings do not divide, and rounding each
    share independently would either create or destroy units; the sum here is
    exactly ``count`` by construction and a test asserts it.
    """
    if count <= 0:
        return np.zeros_like(weights)
    exact = weights * count
    out = np.floor(exact)
    short = int(round(count - out.sum()))
    if short > 0:
        order = np.lexsort((np.arange(weights.size), -(exact - out)))
        out[order[:short]] += 1.0
    return out


def loop_sum(terms: np.ndarray, a: int, b: int, tier: int, periods: int) -> float:
    """Per-period holonomy of the four-cycle between two nodes at one tier.

    ``δ = log(γ_b / γ_a) / T``. The price does not appear because it cancels;
    see the module docstring. Positive when ``b`` faces worse terms than ``a``.

    This is the arithmetic only. The product-graph construction that this must
    agree with lives in ``product_graph.py``, and the two are kept apart on
    purpose: if the simulated exponent and the loop sum were computed by the
    same code, their agreement would be an identity and A3-4 would establish
    nothing. ``scripts/run_all.py`` asserts the two modules do not import each
    other.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    ga = float(terms[a, tier])
    gb = float(terms[b, tier])
    if ga <= 0.0 or gb <= 0.0:
        raise ValueError("terms must be positive")
    return float(np.log(gb / ga) / periods)


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


class A3Model(Network):
    """Stage A2's network with an asset layer attached.

    Only the closed channel is wired. A configuration with ``tiers > 0`` runs
    and warns: the ledger and the terms matrix are built and can be inspected,
    but no unit is ever acquired, so the dynamics are stage A2's exactly. That
    is a useful state to be able to run and hold, and it is recorded in
    ``deviations`` so that anything reported out of such a run has to say where
    it came from.
    """

    def __init__(self, config: A3Config) -> None:
        super().__init__(config.network)
        self.a3 = config
        spec = config.asset

        #: Every registered-design departure this run is operating under. Empty
        #: is the only value from which a headline number may be taken.
        self.deviations: list[str] = []

        #: Whether the asset channel is fully wired. The closed control counts,
        #: because a control with nothing in it is not a partial mechanism.
        self.channel_wired = True

        if not spec.closed and spec.turnover <= 0.0 and spec.arm != "forced":
            note = (
                "turnover is zero and forced sales are off, so no unit changes "
                "hands after the opening allocation. The cash-tier-cash cycle "
                "is walked zero times, the terms differential is never cashed, "
                "and A3-3, A3-4 and A3-7 have no realisation to be evaluated "
                "against. Any divergence in this run is revaluation with the "
                "loop sum playing no part."
            )
            self.channel_wired = False
            self.deviations.append(note)
            warnings.warn(note, DesignDeviation, stacklevel=2)

        if any(g < 1.0 for g in spec.base_terms):
            self.deviations.append("base_terms below one: reversed-sign arm")

        implied = round(1.0 / spec.turnover) if spec.turnover > 0 else 0
        mismatch = spec.holding_period != implied
        if spec.arm == "exogenous" and spec.turnover > 0 and mismatch:
            note = (
                f"holding_period {spec.holding_period} against turnover "
                f"{spec.turnover}, which implies a mean holding period of "
                f"{implied}. T in the edge weight is the period a unit is "
                "actually held, so a mismatch rescales the loop sum: A3-4 "
                "would move by that factor with nothing in the run looking "
                "wrong."
            )
            self.deviations.append(note)
            warnings.warn(note, DesignDeviation, stacklevel=2)

        #: Unit ledger, one row per node and one column per tier. Empty while
        #: the channel is closed, and carried here rather than in a later chunk
        #: so that ``net_worth`` means the same thing at every stage.
        self.units = np.zeros((self._n, spec.tiers))
        #: Tier supply actually used. Equal to ``spec.units`` unless A3b's
        #: ``units_per_node`` is set, in which case the total is rescaled to the
        #: node count with the tier ratio held fixed.
        self.supply = spec.units_for(self._n)
        self.price = np.asarray(spec.initial_price, dtype=float).copy()
        self.centrality = centrality(self.adjacency)
        ref = spec.mean_cost_reference if spec.hold_mean_cost else None
        #: What is paid. This is the field the product graph reads, so this is
        #: the matrix the holonomy is computed from. Named ``terms`` and not
        #: ``terms_pay`` because every existing caller means this one.
        self.terms = terms_matrix(self.centrality, spec, hold_mean_at=ref)
        #: What admits. Used only where entry is decided, never in a payment.
        #: Equal to ``terms`` unless ``gate_spread`` is set.
        self.terms_gate = (
            self.terms
            if spec.gate_spread is None
            else terms_matrix(
                self.centrality, spec, spread=spec.gate_spread, hold_mean_at=ref
            )
        )
        self.price_history: list[np.ndarray] = []
        #: Net worth per node per round. Needed because every A3 criterion is
        #: stated on net worth while the inherited history records claims.
        self.net_worth_history: list[np.ndarray] = []
        #: Claims per node per round, aligned with the two histories above.
        #: Stage A5's reachability measure has claims in its denominator and
        #: needs them on the same clock as the prices.
        self.claims_history: list[np.ndarray] = []
        self._pool_0 = np.zeros(spec.tiers)

        #: Who entered by stretching, and what it cost them.
        self.stretched = np.zeros(self._n, dtype=bool)
        #: Consumed to get in and never booked. ``net_worth`` overstates a
        #: stretcher's position by exactly this.
        self.uncounted_cost = np.zeros(self._n)
        #: Outstanding under the counted variant, amortised over
        #: ``holding_period`` rounds through the node's own adjacency row.
        self.stretch_debt = np.zeros(self._n)

        #: A stream of its own, so that turning turnover on does not shift the
        #: draws of anything already running. Without it a comparison between
        #: two arms would confound the arm with a change of random numbers.
        self._asset_rng = np.random.default_rng(config.network.seed + 517_003)

        #: Claims before the opening allocation. Arm F's trigger is relative to
        #: this rather than to post-allocation claims, because a stretcher ends
        #: the allocation at nearly zero and would otherwise be in forced sale
        #: on round one by construction.
        self._claims_0 = self.holdings.copy()

        #: Cumulative rent moved from those holding nothing to those holding.
        self.rent_collected = 0.0
        self.rent_history: list[float] = []

        #: Production-layer membership, for the tenancy channel.
        self._is_production = np.zeros(self._n, dtype=bool)
        self._is_production[config.network.spec.layer1_size :] = True

        #: Per-round record of what changed hands.
        self.sales: list[int] = []
        self.forced_sales: list[int] = []

        #: Cost basis of every unit held, keyed by ``(node, tier)``, oldest
        #: first. Needed because the loop sum is a per-transaction quantity: a
        #: round trip returns ``log(sale / (gamma * purchase))`` on **one
        #: unit**, while net worth moves by that only if the holder owns one
        #: unit. With portfolios the two differ by the portfolio's size, which
        #: is what made criterion A3-4 compare a per-trade number against a
        #: portfolio growth rate.
        self.basis: dict[tuple[int, int], list[float]] = {}

        #: Realised log return of every completed round trip, per node. This is
        #: the quantity the holonomy predicts, measured at the same grain.
        self.cycle_returns: dict[int, list[float]] = {}

        #: One row per completed round trip: ``(node, tier, entry_round,
        #: exit_round, paid, received, reference_price_at_entry)``.
        #:
        #: The reference price at entry is recorded rather than inferred. It
        #: could be recovered as ``paid / gamma``, but ``gamma`` is the quantity
        #: under test, and a measurement that divides by what it is trying to
        #: detect cannot fail.
        #:
        #: The dates are here because the four-cycle is stated at a **fixed**
        #: entry and exit: it compares two agents who bought on the same day and
        #: sold on the same day, and differ only in what they were charged.
        #: Comparing trades with different windows measures the holding period
        #: as well, and since prices rise the agent who trades less often books
        #: a larger return per trade purely for having held longer -- which
        #: reverses the sign of the effect the criterion is looking for. This is
        #: stage B2's structure exactly: fix the cell, then vary who.
        self.trades: list[tuple[int, int, int, int, float, float]] = []
        self._round = 0

        #: How many times each node has walked cash → tier → cash. This is the
        #: ``N`` in ``(γ_b/γ_a)^N``: one traversal buys a fixed ratio and only
        #: repetition compounds, so a node with ``cycles = 0`` carries no
        #: evidence about the loop sum however far its net worth has moved.
        self.cycles = np.zeros(self._n, dtype=int)

        if not spec.closed:
            self._allocate_initial()
            self._pool_0 = bidder_pool(self.holdings, self._admitted_at_opening())

    # -- the gate ----------------------------------------------------------

    def _clears(self) -> np.ndarray:
        """Who can afford each tier *now*. Used for acquisition."""
        return gate_clears(
            self.holdings, self.terms, self.price, self.a3.asset.open_tiers
        )

    def _admitted_at_opening(self) -> np.ndarray:
        """Who is in the market for each tier, at opening prices.

        The soft gate, not the hard one. A stretcher is in the market and its
        claims are chasing the asset; leaving it out would have the model say
        that a poor bidder's money does not count, which is the opposite of what
        the mechanism claims. With ``stretch = 1`` this is the hard gate exactly.
        """
        admitted, _ = soft_gate(
            self.holdings,
            self.terms,
            np.asarray(self.a3.asset.initial_price, dtype=float),
            self.a3.asset.stretch,
            self.a3.asset.open_tiers,
        )
        return admitted

    def _clears_at_opening(self) -> np.ndarray:
        """Who can afford each tier at its *opening* price. Used for pricing.

        Separate from ``_clears`` because the two answer different questions and
        conflating them is what made the price oscillate. Acquisition asks what
        a node can buy today. Pricing asks whose accumulation the tier tracks,
        and that has to be a set the price does not itself determine.
        """
        return gate_clears(
            self.holdings,
            self.terms_gate,
            np.asarray(self.a3.asset.initial_price, dtype=float),
            self.a3.asset.open_tiers,
        )

    def _allocation_order(self) -> np.ndarray:
        """The order the opening stock is walked down. A3b §3.

        This one function *is* the axis. All three constructions allocate the
        same stock by the same loop; they differ only in the sequence, and the
        sequence is exactly how strongly ownership at ``t = 0`` tracks claims at
        ``t = 0``.

        ``auction`` — descending claims. Perfect correlation. Retained as the
        default and reproduced bitwise.

        ``occupancy`` — a registered share of nodes drawn **without reference to
        claims** goes to the front, the rest follow in descending claims. Inside
        the drawn set the correlation with claims is zero, which is what
        "sitting tenants get the dwelling they occupy" means when residence is
        not itself modelled. The financial layer is not excluded from the draw:
        the transfer went to whoever lived there, and the point of the arm is
        that means did not decide it.

        **The drawn set bypasses the gate**, paying what it has. Leaving the
        gate in place put means back into a mechanism whose entire content is
        that means did not decide: with the gate on, a registered rate of `0.70`
        produced an ownership rate of `53%`, because the sitting tenants at the
        front of the queue were then filtered by what they could afford.
        Russia's transfer was free and the Chinese and British ones were
        discounted precisely so that tenure rather than income decided. The
        bypass is not a gift of claims — nothing is created, and claims are
        conserved exactly. Stock moves from the prior owner to the household at
        below market, which is what the transfer was.

        ``continuous`` — drawn with probability proportional to claims, so
        ownership rises with wealth without following the ranking strictly.
        Between the other two by construction, which is why the three are one
        axis and not three modes.

        Only the **order** changes. Every construction still faces the same
        gate, the same soft threshold and the same supply, so nothing here
        smuggles in a second difference. Whoever is early in the order still has
        to clear the gate to receive anything, which is why ``ownership_rate``
        is an input to the draw and not an outcome that can be read back off.
        """
        spec = self.a3.asset
        by_claims = np.argsort(-self.holdings, kind="stable")
        #: Nodes admitted at the opening regardless of claims. Only the
        #: occupancy transfer sets any of these; ``continuous`` is a market and
        #: faces the gate like ``auction``.
        self._opening_bypass = np.zeros(self._n, dtype=bool)
        if spec.construction == "auction":
            return by_claims

        # A stream of its own so that adding a construction does not shift the
        # draws of anything already running, the same reason turnover has one.
        rng = np.random.default_rng(
            (self.a3.network.seed or 0) * 1_000_003 + 90210
        )
        k = int(round(spec.ownership_rate * self._n))
        k = max(0, min(k, self._n))
        if spec.construction == "occupancy":
            weights = np.full(self._n, 1.0 / self._n)
        else:
            w = np.maximum(self.holdings, 0.0)
            total = float(w.sum())
            weights = (
                w / total if total > 0.0 else np.full(self._n, 1.0 / self._n)
            )
        front = rng.choice(self._n, size=k, replace=False, p=weights)
        chosen = np.zeros(self._n, dtype=bool)
        chosen[front] = True
        if spec.construction == "occupancy":
            self._opening_bypass = chosen.copy()
        # Within each block the order is still by claims, so the construction
        # decides *who is in the front block* and nothing else.
        return np.concatenate(
            [by_claims[chosen[by_claims]], by_claims[~chosen[by_claims]]]
        )

    def _allocate_initial(self) -> None:
        """Hand out the opening stock, highest tier first, in allocation order.

        A3-2 defines its two comparison groups by this ranking, so the rule is
        the one the criterion names and not a convenience. Under the default
        construction the order is descending claims; A3b §3 makes the order the
        registered axis and ``_allocation_order`` holds it.

        **One unit per node in the occupancy transfer, uncapped in the market
        pass.** The asset stands for a dwelling. A transfer of occupied public
        housing gives you the one you live in; a market is where holding more
        than one is the thing this stage measures. The cap was unconditional
        before A3b and the docstring said so; it is now the transfer's rule,
        recorded in `a3b_initial_construction.md` §9.1.

        **The buyer pays. Where the proceeds go is registered, not assumed.**
        Claims are conserved exactly either way, which keeps the stock-flow
        assertion live from round zero. `proceeds = "equal"` splits across all
        nodes and was defended as neutral, because pro-rata would let the
        opening transaction itself concentrate claims. A3b §1 withdraws that
        defence: the seller of a dwelling is its previous owner, so an equal
        split is one perfectly egalitarian redistribution at `t = 0` and then a
        measurement of how a gap opens from there. `"seller"` pays the prior
        owner. The default remains `"equal"` only so the pre-A3b runs are
        reproducible.
        """
        spec = self.a3.asset
        owned = np.zeros(self._n, dtype=int)
        order = self._allocation_order()
        paid_total = 0.0
        # Indexed by tier rather than appended, because the passes below skip
        # empty tiers and an append would then silently misalign the residual
        # with the tier it belongs to.
        left = [int(u) for u in self.supply]

        # Two passes, and only the occupancy transfer has a first one.
        #
        # **The transfer walks tiers low to high and gives each drawn node one
        # unit.** Both halves matter and neither is decoration. Walking high
        # first would let a hundred and forty bypassed nodes take the premium
        # stock before anyone else sees it, which is not what a transfer of
        # occupied public housing was; the sitting tenants were living in
        # ordinary dwellings. And one unit is what "the dwelling you occupy"
        # means — the uncapped rule is for a market, where accumulating more
        # than one is the thing the stage measures.
        #
        # This does not put means back in. The tier follows the layer, not the
        # claims, and the layer is the source manuscript's own structure rather
        # than a wealth test: §3.1 registers the occupancy arm as uncorrelated
        # with claims *within the production layer*.
        if self._opening_bypass.any():
            paid_total += self._walk_tiers(
                range(spec.tiers), order, owned, left, transfer=True
            )
        paid_total += self._walk_tiers(
            range(spec.tiers - 1, -1, -1), order, owned, left, transfer=False
        )
        unsold = list(left)
        self._settle_opening(paid_total, unsold)

    def _walk_tiers(
        self,
        tiers: range,
        order: np.ndarray,
        owned: np.ndarray,
        left: list[int],
        transfer: bool,
    ) -> float:
        """One pass of the opening allocation. Returns what was paid.

        ``left`` is mutated: it is the stock still unallocated, shared between
        the passes so the second cannot hand out a unit the first already gave
        away.

        ``transfer=True`` is the occupancy pass and is restricted to the drawn
        set, one unit each. ``transfer=False`` is the market pass and is the
        pre-A3b behaviour exactly.
        """
        spec = self.a3.asset
        cap = 1 if transfer else (spec.max_units or self._n)
        paid_total = 0.0
        for q in tiers:
            if left[q] <= 0:
                continue
            # The occupancy discount lowers the gate and the price paid with a
            # single number, which is what a Right-to-Buy discount did: it is
            # the reason a sitting tenant could afford the dwelling at all. It
            # also lands in ``basis``, so a discounted entry shows up in the
            # realised return, which is what a discount means.
            discount = 1.0 - spec.opening_discount
            cost_q = self.terms[:, q] * self.price[q] * discount
            # The gate and the payment are two different numbers now. Admission
            # is decided against ``terms_gate``; whoever is admitted then pays
            # against ``terms``. Where the two agree, which is the default, this
            # is the previous behaviour exactly.
            gate_q = self.terms_gate[:, q] * self.price[q] * discount
            forced_open = q in spec.open_tiers
            for i in order:
                if left[q] <= 0:
                    break
                if transfer and not self._opening_bypass[i]:
                    continue
                if owned[i] >= cap:
                    continue
                cost = float(cost_q[i])
                gate = float(gate_q[i])
                have = float(self.holdings[i])
                if forced_open or (transfer and self._opening_bypass[i]):
                    pay, short = min(cost, have), 0.0
                elif have >= gate:
                    # Admitted. It still has to find the money, and if the
                    # payment dispersion is wider than the gate's it may not
                    # have it, which is the stretch band by another route and
                    # is recorded the same way rather than being forbidden.
                    pay = min(cost, have)
                    short = cost - pay
                elif have >= gate / spec.stretch:
                    pay, short = min(cost, have), max(cost - have, 0.0)
                else:
                    continue
                self.holdings[i] -= pay
                paid_total += pay
                self.units[i, q] += 1.0
                self.basis.setdefault((i, q), []).append(
                    (max(pay, 1e-12), 0, float(self.price[q]))
                )
                owned[i] += 1
                left[q] -= 1
                if short > 0.0:
                    self.stretched[i] = True
                    if spec.stretch_cost == "uncounted":
                        self.uncounted_cost[i] += short
                    else:
                        self.stretch_debt[i] += short
        return paid_total

    # -- A3b: who sold, and who keeps what did not sell --------------------

    def _prior_owner_weights(self) -> np.ndarray:
        """The set that held the stock before the opening, and in what shares.

        **The financial layer, weighted by opening claims.** One rule used
        twice, for the residual and for the proceeds, so the two cannot drift
        apart. It is the same set under all three constructions and the reason
        differs only in the label: the developer of new supply, the state or
        work unit disposing of public housing, the incumbent owner of an
        existing stock. In a two-layer model all three are upstairs — the source
        manuscript's Volume I §3 puts Fed and PBC inside Layer 1 explicitly.

        Falls back to an equal split across the financial layer if opening
        claims there sum to zero, so the function has no undefined branch.
        """
        w = np.where(~self._is_production, np.maximum(self._claims_0, 0.0), 0.0)
        total = float(w.sum())
        if total > 0.0:
            return w / total
        upstairs = (~self._is_production).astype(float)
        n_up = float(upstairs.sum())
        return upstairs / n_up if n_up > 0 else np.full(self._n, 1.0 / self._n)

    def _settle_opening(self, paid_total: float, unsold: list[int]) -> None:
        """Route the opening proceeds, and give the residual stock an owner.

        Both halves default to the pre-A3b behaviour so the registered
        configuration is reproduced bitwise.

        **Residual stock carries no cost basis.** A prior owner did not buy its
        units inside this model, and writing one in would be inventing a
        purchase price that then feeds realised returns and therefore A3-4.
        Without a basis, selling residual stock moves a unit and moves claims
        but records no completed cycle, which is the same treatment
        ``terms_pair`` already gives an agent that never traded: it carries no
        evidence about the loop sum, so it contributes none.
        """
        spec = self.a3.asset

        if paid_total > 0.0:
            if spec.proceeds == "seller":
                self.holdings += paid_total * self._prior_owner_weights()
            else:
                self.holdings += paid_total / self._n

        if not spec.residual_owner:
            return
        weights = self._prior_owner_weights()
        for q, remaining in enumerate(unsold):
            if remaining <= 0:
                continue
            self.units[:, q] += _apportion(remaining, weights)

    # ----------------------------------------------------------------------

    # -- pricing -----------------------------------------------------------

    def _update_prices(self) -> None:
        """Re-mark every tier from the current bidder pool.

        The gate is evaluated against the price standing at the start of the
        round, so the pool that sets this round's price is the one that could
        have bid at last round's price. That avoids a fixed point, and it is the
        same lagged-information convention stage A0 already uses for issuance:
        no actor observes the round it is acting in.
        """
        pool = bidder_pool(self.holdings, self._admitted_at_opening())
        self.price = price_at(
            np.asarray(self.a3.asset.initial_price, dtype=float),
            pool,
            self._pool_0,
            self.a3.asset.elasticity,
        )

    def _service_stretch_debt(self) -> None:
        """Pay down one round of the counted stretch cost.

        Routed through the node's own adjacency row rather than to a nominated
        recipient. That keeps the destination out of the assumptions: the graph
        already leaks upward from the production layer, so a stretcher financing
        somebody upstream for years afterward comes out of the structure instead
        of being written into it. It also introduces no edge, so the potential
        support set is untouched.

        Claims are conserved because routing rows sum to one. A node that cannot
        pay this round pays what it has and the balance stays outstanding, in the
        same spirit as the wage channel, which narrows when its payers are
        illiquid rather than driving holdings negative.
        """
        owed = self.stretch_debt
        if not owed.any():
            return
        instalment = np.minimum(
            owed / float(self.a3.asset.holding_period),
            np.maximum(self.holdings, 0.0),
        )
        instalment = np.where(self._has_out, instalment, 0.0)
        if not instalment.any():
            return
        self.holdings = (
            self.holdings - instalment + (instalment[:, None] * self._route).sum(axis=0)
        )
        self.stretch_debt = np.maximum(owed - instalment, 0.0)

    # -- tenancy -----------------------------------------------------------

    def _collect_rent(self) -> None:
        """Move rent from production-layer non-holders to holders.

        The renter pays a share of the **low tier's current price**, which is
        the housing an ordinary agent would occupy, so the bill rises with the
        market whether or not the renter ever had a chance to buy into it. That
        is the whole content of the channel: the price is not a wall the
        excluded merely stand outside of, it is a meter that runs on them.

        Receipts go to holders **in proportion to units held**, which is what
        makes accumulating units an income and not only a mark-to-market.

        **The two sides are not keyed on the same kind of thing under the
        default**, and that is what ``rent_base`` exists to make visible. The
        receipt side has always been ``held > 0``, recomputed every round from
        the measured units. The payer side carries ``& _is_production``, a set
        fixed at construction. Under ``rent_base = "layer"`` that asymmetry is
        preserved exactly, because every result recorded before 2026-08-13 was
        produced under it. Under ``"holding"`` both sides read the same
        magnitude and a financial-layer node that holds nothing pays like any
        other non-holder.

        Neither setting is a claim about layer as position. It is a claim about
        who a rent bill is assessed on, and `MEASUREMENT.md` §8's rule is that
        a liability whose real counterpart is assessed on an observed magnitude
        has to be recomputed from that magnitude or registered as a modelling
        choice. This is the registration.

        A renter short of the rent pays what it has, in the same spirit as the
        wage channel, which narrows when its payers are illiquid rather than
        driving holdings negative. Claims are conserved exactly: this is a
        transfer and nothing is created.
        """
        spec = self.a3.asset
        if spec.rent_rate <= 0.0 or spec.closed:
            self.rent_history.append(0.0)
            return
        held = self.units.sum(axis=1)
        if spec.rent_base == "layer":
            renters = np.flatnonzero((held <= 0) & self._is_production)
        else:
            renters = np.flatnonzero(held <= 0)
        landlords = np.flatnonzero(held > 0)
        if renters.size == 0 or landlords.size == 0:
            self.rent_history.append(0.0)
            return

        due = spec.rent_rate * float(self.price[0])
        paid = np.minimum(due, np.maximum(self.holdings[renters], 0.0))
        total = float(paid.sum())
        if total <= 0.0:
            self.rent_history.append(0.0)
            return

        self.holdings[renters] -= paid
        share = held[landlords] / float(held[landlords].sum())
        self.holdings[landlords] += total * share
        self.rent_collected += total
        self.rent_history.append(total)

    # -- turnover ----------------------------------------------------------

    def _offers(self) -> list[tuple[int, int]]:
        """``(node, tier)`` pairs coming back onto the market this round.

        Arm E draws each held unit independently at rate ``τ``: people die,
        relocate, retire, and none of that is about the price. A Bernoulli per
        unit rather than a fixed count, so the rate is exact in expectation and
        no rounding rule has to be invented for a stock that changes size.

        Arm F adds units whose holder has fallen below ``φ`` of its opening
        claims and must liquidate. That is the source manuscript's two-sided
        squeeze: the drained production layer selling into a rising market. It
        overlaps stage A1 and takes only A1's trigger, never its cascade.
        """
        spec = self.a3.asset
        held = np.argwhere(self.units > 0)
        if held.size == 0:
            return []

        out: list[tuple[int, int]] = []
        if spec.turnover > 0.0:
            draw = self._asset_rng.random(len(held)) < spec.turnover
            out.extend(
                (int(i), int(q))
                for (i, q), take in zip(held, draw, strict=True)
                if take
            )

        if spec.arm == "forced":
            floor = spec.forced_sale_floor * self._claims_0
            distressed = self.holdings < floor
            already = {i for i, _ in out}
            forced = [
                (int(i), int(q))
                for i, q in held
                if distressed[i] and int(i) not in already
            ]
            self.forced_sales.append(len(forced))
            out.extend(forced)
        else:
            self.forced_sales.append(0)
        return out

    def _settle(self, offers: list[tuple[int, int]]) -> None:
        """Match each offered unit to the best available buyer.

        The seller receives the market price. The buyer pays ``γ · P``, so the
        premium ``(γ − 1) · P`` has to go somewhere or claims stop being
        conserved. It is **split equally across all nodes**, for the same reason
        the opening proceeds are: routing it to the financial layer is the
        realistic destination and it is also a second channel with the same sign
        as ``γ``, which would leave A3-4 unable to say whether the exponent it
        measured came from the terms differential or from the premium's
        destination. The realistic variant is a separate arm and is not run
        here.

        An offer with no buyer simply does not sell and the holder keeps it.
        Nothing is destroyed and no unit is left ownerless.

        **A seller may buy.** Excluding them emptied the market outright: one
        unit per node means the only agents with claims already hold something,
        so with sellers barred there is no eligible buyer anywhere and three
        hundred rounds produced zero transactions. It is also what a housing
        market mostly is — people selling one and buying another. Offers are
        settled in order, so a node that sells early can bid on what is offered
        after it.

        **Resale requires payment in full; the stretch applies only at the
        opening allocation.** At the opening there is no counterparty to
        shortchange: the proceeds are split equally and the shortfall is
        absorbed outside the ledger. A resale has a seller who must receive the
        market price, so a buyer short of it would have to be funded by
        something, and there is nothing to fund it with that does not break
        conservation.
        """
        if not offers:
            self.sales.append(0)
            return

        cap = self.a3.asset.max_units or self._n
        owned = self.units.sum(axis=1)
        sold = 0
        premium_pot = 0.0

        for seller, q in offers:
            price = float(self.price[q])
            cost = self.terms[:, q] * price
            eligible = (
                (owned < cap)
                & (self.holdings >= cost)
                & (np.arange(self._n) != seller)
            )
            if not eligible.any():
                continue
            # Whoever gets there first among those who qualify, not whoever is
            # richest. The price here is posted, not bid: it is the reference
            # price times the buyer's own terms, so there is no auction for a
            # highest bid to win and "richest wins" is a rationing rule rather
            # than a market.
            #
            # It was `argmax(holdings)` first, and that single line cancelled
            # criterion A3-4. One node outbids everyone every round, accumulates
            # most of the stock, and completes twenty to thirty cycles while the
            # badly-termed agents complete one. A3-4 compares two groups that
            # both walk the loop; the rationing rule guaranteed that only one of
            # them ever did.
            pool = np.flatnonzero(eligible)
            buyer = int(pool[self._asset_rng.integers(pool.size)])
            paid = float(cost[buyer])

            self.holdings[buyer] -= paid
            self.holdings[seller] += price
            premium_pot += paid - price
            self.units[seller, q] -= 1.0
            self.units[buyer, q] += 1.0
            owned[seller] -= 1
            owned[buyer] += 1

            # The seller closes a round trip: it entered at some cost and left
            # at the market price. That realised log return is the object the
            # holonomy predicts, and it is recorded per transaction rather than
            # inferred from the portfolio.
            held = self.basis.get((seller, q))
            if held:
                entry, bought_at, ref = held.pop(0)
                self.cycle_returns.setdefault(seller, []).append(
                    float(np.log(price / entry))
                )
                self.trades.append(
                    (
                        seller, q, int(bought_at), int(self._round),
                        entry, price, ref,
                    )
                )
                self.cycles[seller] += 1
            self.basis.setdefault((buyer, q), []).append(
                (max(paid, 1e-12), self._round, price)
            )
            sold += 1

        if premium_pot != 0.0:
            self.holdings += premium_pot / self._n
        self.sales.append(sold)

    def _post_round(self, t: int) -> None:
        if self.a3.asset.closed:
            return
        self._round = t
        self._collect_rent()
        self._service_stretch_debt()
        self._settle(self._offers())
        self._update_prices()
        self.price_history.append(self.price.copy())
        self.net_worth_history.append(self.net_worth())
        self.claims_history.append(self.holdings.copy())

    def net_worth(self) -> np.ndarray:
        """Claims plus the marked value of held units.

        Claims are conserved and the stock-flow assertion is on them. Net worth
        is not conserved, because revaluation changes what a held unit is worth
        with no transfer between parties. That is the point of the stage and it
        is the first quantity in this repository that does not conserve, so the
        two are named separately everywhere rather than folded into one total.

        With the channel closed this is the claim vector exactly, which is what
        makes stage A4's measures and stage A3's measures comparable across the
        boundary.
        """
        if self.a3.asset.closed:
            return self.holdings.copy()
        return self.holdings + self.units @ self.price

    def true_net_worth(self) -> np.ndarray:
        """Net worth less what was consumed to get in and never booked.

        Under the uncounted variant a stretcher gave up something the ledger
        does not record, so ``net_worth`` reports it better off than it is, by
        exactly ``uncounted_cost``. The gap is computable, so the model prints it
        rather than leaving a caveat in prose.

        This is the framework's own distinction made numerical inside the A
        track: the price system records that they could afford it, and something
        real was consumed that the price system does not price. Any welfare
        reading of ``net_worth`` is wrong by this vector.
        """
        return self.net_worth() - self.uncounted_cost


def run_a3_model(config: A3Config) -> A3Model:
    """Run and return the model itself, for callers that need ``deviations``.

    ``run_a3`` returns only the history, which cannot carry the deviation list.
    Anything that writes to ``results/`` uses this entry point instead, so a run
    that departed from the registered design cannot be written up as one that
    did not.
    """
    model = A3Model(config)
    model.run()
    return model


def run_a3(config: A3Config) -> NetworkHistory:
    """Run one A3 configuration.

    Returns the ordinary A2 history unchanged while the channel is closed. The
    asset-side record is added when the channel is implemented, so that this
    chunk's output is comparable to A2's without any translation.
    """
    return A3Model(config).run()
