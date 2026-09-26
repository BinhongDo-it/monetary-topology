"""A47: housing rules on top of A3's asset channel.

What this adds
--------------
Switches that change the rules of the housing market A3 already runs, and nothing else.
Every switch defaults off, and with all of them off every overridden method hands the
call to ``A3Model`` unchanged, so a run is A3's registered run bit for bit. A47-1 checks
that by running both.

Block 1: ownership and who holds the rental stock
-------------------------------------------------
``residence_bound``. Ownership is tied to residence: a node holds at most one unit and
the unit it holds is the one it lives in, so no node collects rent. Requires
``AssetSpec.max_units == 1``, which A3 already enforces in the opening allocation and in
resale. Stock the opening allocation does not place goes to the landlord, not to the
financial layer's nodes.

``landlord``. Who holds the rental stock under ``residence_bound``, by behaviour and by
where the money goes, not by legal form.

- ``"public"``: a pool outside the graph. Rent paid into it leaves the renters' accounts;
  each round ``pool_pass_rate`` of the pool comes back to the production layer, equally
  per live node, as construction wages. What stays in the pool still exists and is
  counted in the conservation check.
- ``"listed"``: a listed company owned by the financial layer, weighted by opening claims
  (the same weights A3 uses for the prior owners). ``dividend_exit`` of its rent receipts
  leaves the graph as cash dividends to owners outside it and does not come back; the rest
  goes to the financial layer. Its stock is part of the financial layer's net worth.

``liquidation``. A resident drawn by turnover (death, moving away) must sell.

- ``"market"``: offered at the market price; if no eligible household buys, the landlord
  buys at the market price.
- ``"cost"``: sold to the landlord at the cost price, the opening price times the wage
  index (this round's wage bill paid over the first round's). Households buy from the
  landlord at the cost price too, so no unit changes hands at a market price and a
  resident's unit is marked at cost in net worth.

In both arms the landlord offers ``turnover`` of its stock each round to households
without a unit, at the arm's price.

``bidders_exclude_owners`` (default True, read only under ``residence_bound``). A3 prices
each tier off the claims of those who could afford it at opening. Under residence
binding an owner cannot buy a second unit, so it is not a bidder, and the rule is carried
through to the price: the pool counts only nodes with no unit. The opening pool is taken
on the same basis, so the price starts where A3's does.

Block 2: tenancy by unit, and new supply
----------------------------------------
``tenant_tier``. A3's rent is not tied to a dwelling: every renter pays a share of the
low tier's price and receipts are split across all holders by units held. With this on,
a renter occupies a rental unit and pays ``rent_rate`` times that unit's tier price to
that unit's owner. Rental units are what owners hold beyond the one they live in (their
highest tier) or, under ``residence_bound``, the landlord's stock. Matching each round:
tiers cheapest first, owners in index order within a tier, renters in one fixed random
order drawn at the start, so tenancies persist while nothing changes. Renters beyond
the rental stock are unhoused and pay nothing; their count is recorded.

``new_supply_rate``. Units built per round as a share of the opening supply, apportioned
across tiers in the opening ratio. The builder pays the cost price (opening price times
the wage index) as construction wages to the live production layer, equally per node:
the financial layer pays pro rata to its claims and receives the units in the same shares
without ``residence_bound``, the landlord pays and holds them with it. A round builds only
what the builder can pay for in full. **A3's price rule reads bidders' claims and not the
stock, so new supply does not lower the price in this carrier**; that is A3's mechanism
and is left alone. Every built unit carries a "new" flag (``new_units``,
``landlord_new``), which block 3's rent cap reads to exempt new building. On a sale the
flag moves with the unit: exactly under ``residence_bound``, where this module settles
sales; pro rata within each tier otherwise, where A3 settles them and does not say which
unit went to whom.

Block 3: the carrier, the price floor, and rent caps
----------------------------------------------------
``levy_rate``. A9's transfer arm, so the production layer is not drained (A47 results
§R3): each round ``levy_rate`` of every financial-layer node's non-negative holdings, split
equally across the production layer. The arithmetic is ``A6Model._apply_levy`` with
``as_edge = False``, applied at the start of ``_post_round``, before rent and sales. With
the asset channel closed the run is ``A6Model``'s bit for bit, which A47-5 checks.

``cost_floor``. The price of a tier does not fall below its cost price (opening price times
the wage index). Without it, residence binding with ample supply leaves no bidder and A3's
price rule gives zero (A47 results §R2); with it, nobody sells below what it costs to
build again.

``rent_cap``. From round ``cap_start`` on, the rent on a regulated unit is at most:

- ``"wage"``: ``cap_wage_share`` times the median wage plus ``cap_maintenance`` times the
  unit's maintenance cost, ``maintenance_rate`` times its cost price. The median wage is
  the median of what each wage receiver was paid in the round, read off the wage channel.
- ``"berlin"``: the tier's rent at ``cap_start`` times the wage index since then. B129's
  law in this carrier's terms: an earlier rent level carried forward by wages.

``cap_exempt_new`` (default True): units built under ``new_supply_rate`` are not capped,
as Berlin exempted building from 2014. Under ``tenant_tier`` a tenant's rent is the
expected rent over its lessor's units in that tier, the new share at market and the rest
capped, since the model tracks how many of a lessor's units are new but not which one a
tenant lives in. ``rent_cap`` requires ``tenant_tier``: A3's own rent is not attached to
any unit, so nothing could be exempt under it.

Every round under a cap records, by class, what regulated and exempt units paid and how
many there were, for B129's square (A47-6).

Block 4: public housing that keeps itself, with the state behind it
--------------------------------------------------------------------
The rule, ruled 2026-09-23: rent on public housing pays for its upkeep first, a surplus
stays with the project and pays for new building, and a gap is met by the state out of
the levy. One rule in two steps, so the two funding sources are its order, not two
alternatives.

``public_build_rate``. Public units built per round, as a share of the opening supply,
held by the public landlord (the pool). They exist with or without ``residence_bound``:
without it, public rental stock sits beside private landlords' spare units and is
offered to renters first, which is how building at a set rate widens the renters'
choice. Public units are never sold.

``public_rent_cost``. Rent on a public unit is ``rent_rate`` times the unit's cost price
instead of its market price. Paid into the pool, outside the graph.

``public_maintenance``. Each round the pool pays ``maintenance_rate`` times the cost price
of every public unit, as wages to the live production layer.

``state_topup``. What the pool cannot pay, for maintenance and then for the round's
building, is drawn from this round's levy before the rest of the levy is paid out. What
the levy cannot cover either is recorded as unfunded maintenance, or leaves the round's
building to carry over. The levy the production layer receives is smaller by exactly the
top-up, so claims are conserved.

Self-maintaining public housing is ``pool_pass_rate = 0`` (a surplus stays in the pool),
``public_maintenance``, ``state_topup`` and ``public_rent_cost``. Every field defaults off,
and with them off blocks 1 to 3 reproduce.

A48: a core location, and staying put when leaving means not getting back
------------------------------------------------------------------------
``core_premium``. The top tier is the core location. After every other rule has set the
price, the top tier's is multiplied by ``core_R0 * (1 + core_g) ** t``: an opening
location premium and a relative rise per round, the core being finite and not extended.
New building, private and public, goes to the other tiers only.

``optional_move_rate`` (``tau_o``). A3's turnover ``tau`` is split: a unit drawn below
``tau - tau_o`` must be sold, as before; one drawn in ``[tau - tau_o, tau)`` is an optional
move. An optional mover in the core tier sells only if it could come back: selling at the
core price, buying a low-tier unit on its own terms, and buying the core again after
``holding_period`` rounds at the core price carried forward by the premium's growth,

    gap = terms[i, core] * P_core * (1 + g) ** T - P_core + terms[i, low] * P_low,

and a gap above its claims keeps it where it is, recorded as a lock. A budget, not a
preference. The same one uniform draw per held unit as A3's decides both, so with
``tau_o = 0`` the random stream and the offers are A3's. A mover who does come back later
is a new buyer: the model keeps no record of who lived where. Requires
``residence_bound``: without it a mover keeps the unit and lets it, and nothing is sold.

A49: a loan secured on a commitment to stay, and those who stay only briefly
-----------------------------------------------------------------------------
``commit_loan``. A node that can commit to staying at least ``holding_period`` rounds (its
must-move rate is at most ``1 / holding_period``) and owns no unit may buy with a down
payment of ``loan_down`` times the cost; the lender pays the rest to the seller and the
node owes it, repaid in ``holding_period`` equal instalments plus ``loan_rate`` on the
balance each round. ``loan_lender``: ``"public"`` lends from the public pool and is repaid
into it; ``"bank"`` is the financial layer, lending and repaid by opening-claim weights.
A lender lends only what it has. A node that pays short for ``loan_arrears_k`` rounds in a
row loses the unit: to the landlord under ``residence_bound`` (at the trade price, paid to
the lender first), to the lender otherwise (the public pool, or the financial node with the
largest opening-claim weight), credited against the debt. What the unit does not cover is
written off as the lender's loss; no claim moves on a write-off. A borrower that sells
repays from the proceeds first.

``short_stay_share``. That share of the production layer, drawn once from its own stream,
must move at ``short_stay_rate`` per round instead of the carrier's turnover, so it can make
no commitment and gets no loan. The same single uniform draw per held unit decides it.

A49 block 2: a provident fund as the third lender
-------------------------------------------------
``loan_lender = "provident"``, with ``provident_rate`` ``c``. Each round every wage
receiver pays ``c`` of the wage it received this round into its own account, and the wage
payers pay as much again, taken from them in proportion to their claims and credited to
the receivers in proportion to their wages; what a side cannot pay is not paid. The
contributions sit in the fund as cash (``pf_cash``), outside the circulating holdings,
while each account is its owner's claim on the fund and counts in its owner's net worth.
The fund lends only to nodes that have contributed, from its cash; a member spends its
account first, then its holdings, on a purchase, a down payment and its instalments. The
fund pays no interest on accounts; what it earns on loans and loses on write-offs is its
own, reported as ``pf_surplus``. China's housing provident fund is this shape: employer
and employee each pay at least 5 % of the prior year's average monthly wage into the
employee's account, and the pool lends to contributors below commercial rates.

A50: which side pays, and where the money goes
----------------------------------------------
``provident_employee`` and ``provident_employer`` switch each side of the contribution;
``provident_park`` off pays the employer side straight to the receivers' holdings in the
same round (``pf_returned``), which is a wage rise of ``c``, instead of into their accounts.
An employee side paid back to its own payer is the identity, so parking off requires the
employee side off. ``provident_visible`` has the authority count what is paid into the
accounts each round as layer-2 inflow, so it does not issue against it (``pf_visible_cut``).
``provident_in_target`` has the authority's target count the account balances: the
baseline inflow it steers to is lowered by the balances times the carrier's inflow per unit
of circulating claims at baseline (the first round's layer-2 inflow over the initial
claims), so it accepts circulation lower by what the accounts hold (``pf_target_cut``). Like
``provident_visible`` it is exact on the rule ``max(0, gain x gap)``.
``provident_release`` ``L`` pays each round's parked money back to its owner's holdings
``L`` rounds later, as far as the account still holds it (``pf_released``).
A51: ``core_tier`` puts A48's core on a tier other than the top one (the carrier then splits
the low tier into a plain and a core tier of one size and price, so the core differs from the
low tier by location alone). ``location_s`` is location demand: a renter outside the core pays
``location_s`` times its wage this round in commuting, a renter with no wage pays nothing, and
each renter in the fixed order takes the unit that minimises rent plus commuting among those it
can pay (``_tenancy_rent_located``).
``lease_rounds`` ``L`` keeps a renter on the unit it chose for ``L`` rounds (tier and lessor; a
unit the lessor no longer has ends the lease, counted in ``lease_evictions``); renters on a lease
take their units before anyone chooses. ``lease_rent_lock`` holds the rent at what was signed. ``location_history`` records the core's tenants, how many
earn a wage, the location rent a cost-renting public landlord leaves with its tenants and the
location rent a market landlord collects.
``provident_spendable`` off keeps parked money in the accounts for
good: it counts in net worth and is never spent on a dwelling. All four default on, which is
A49 block 2's fund.

A49 block 3: the treasury behind the public lender
--------------------------------------------------
``treasury_backing`` (read with ``loan_lender = "public"``). The state lends ahead of its
revenue: when the pool is short for a loan, it may go below zero by up to this round's
levy, and at the start of the next round the levy first brings the pool back to zero, the
rest being paid out as before. The state borrows against the next round's tax, which is
the shape of a housing board funded from the budget. The overdraft is counted in the pool,
so the conservation check sees it. Upkeep, building and landlord purchases draw only on
the pool's positive balance; with the pool never below zero that is what they always did.

Conservation
------------
The base network checks stock and flow inside the round; ``_post_round`` moves claims
after that check. So this module keeps its own: holdings plus the pool plus what has
exited must not change across ``_post_round``, asserted every round (18b).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .asset import A3Config, A3Model, _apportion, bidder_pool, price_at

RENT_CAPS: tuple[str | None, ...] = (None, "wage", "berlin")
LIQUIDATIONS: tuple[str, ...] = ("market", "cost")
LANDLORDS: tuple[str, ...] = ("public", "listed")
LANDLORD = -1          # seller or lessor index for the landlord
TOL = 1e-9


@dataclass(frozen=True)
class HousingRules:
    residence_bound: bool = False
    liquidation: str = "market"
    landlord: str = "public"
    #: Share of the listed landlord's rent receipts paid out as cash dividends to owners
    #: outside the graph. Vonovia fiscal 2024: cash dividend / rental Adjusted EBITDA
    #: = 0.271; all dividends / rental Adjusted EBITDA = 0.421 (A47 design, decisions).
    dividend_exit: float = 0.0
    #: Share of the public pool passed back to the production layer each round.
    pool_pass_rate: float = 1.0
    bidders_exclude_owners: bool = True
    tenant_tier: bool = False
    new_supply_rate: float = 0.0
    #: Block 3.
    levy_rate: float = 0.0
    cost_floor: bool = False
    rent_cap: str | None = None
    cap_start: int = 0
    #: HUD's affordability line: rent above 30 % of income is a cost burden.
    cap_wage_share: float = 0.30
    cap_maintenance: float = 1.0
    #: Vonovia 2024: maintenance 764.7 m EUR on a portfolio of about 82.3 bn EUR, 0.0093.
    maintenance_rate: float = 0.0093
    cap_exempt_new: bool = True
    #: Block 4.
    public_build_rate: float = 0.0
    public_rent_cost: bool = False
    public_maintenance: bool = False
    state_topup: bool = False
    #: A48.
    core_premium: bool = False
    core_R0: float = 1.0
    core_g: float = 0.0
    optional_move_rate: float = 0.0
    #: A49.
    commit_loan: bool = False
    loan_down: float = 0.1
    loan_lender: str = "public"
    loan_rate: float = 0.0
    loan_arrears_k: int = 3
    short_stay_share: float = 0.0
    short_stay_rate: float = 0.25
    #: A49 block 2.
    provident_rate: float = 0.0
    #: A49 block 3.
    treasury_backing: bool = False
    #: A50: which side contributes, and whether the money is parked.
    provident_employee: bool = True
    provident_employer: bool = True
    provident_park: bool = True
    provident_spendable: bool = True
    #: A50 block 4: the authority counts what is paid into accounts as arrived inflow.
    provident_visible: bool = False
    #: A50 block 5: the authority's target counts the account balances.
    provident_in_target: bool = False
    #: A50 block 6: parked money goes back to its owner's holdings after this many rounds
    #: (0: never).
    provident_release: int = 0
    #: A51: which tier is the core (-1: the top tier, A48's), and location demand: a renter's
    #: commuting cost outside the core, as a share of its wage this round.
    core_tier: int = -1
    location_s: float = 0.0
    #: A51 block 2: a renter keeps its unit for this many rounds (0 and 1: it chooses again
    #: every round), and optionally at the rent it signed for.
    lease_rounds: int = 0
    lease_rent_lock: bool = False

    def __post_init__(self) -> None:
        if self.lease_rounds < 0:
            raise ValueError("lease_rounds must be non-negative")
        if (self.lease_rounds > 1 or self.lease_rent_lock) and self.location_s <= 0.0:
            raise ValueError("leases are defined on the located matching only")
        if self.location_s < 0.0:
            raise ValueError("location_s must be non-negative")
        if self.location_s > 0.0 and not (self.tenant_tier and self.core_premium):
            raise ValueError("location demand needs tenancy by unit and a core")
        if self.location_s > 0.0 and self.rent_cap is not None:
            raise ValueError("location demand is not defined under a rent cap")
        if self.location_s > 0.0 and (self.commit_loan or self.short_stay_share > 0.0):
            raise ValueError("location demand is not combined with A49's loans or short stays")
        if self.core_tier < -1:
            raise ValueError("core_tier is a tier index or -1 for the top tier")
        if self.provident_in_target and not (self.provident_park and self.provident_rate > 0.0):
            raise ValueError("provident_in_target needs a parked contribution")
        if self.provident_release < 0:
            raise ValueError("provident_release must be non-negative")
        if self.provident_release and not (self.provident_park and self.provident_rate > 0.0):
            raise ValueError("provident_release needs a parked contribution")
        if self.provident_release and self.commit_loan:
            raise ValueError("provident_release is not defined with lending")
        if self.provident_visible and not (self.provident_park and self.provident_rate > 0.0):
            raise ValueError("provident_visible needs a parked contribution")
        if not self.provident_spendable and not self.provident_park:
            raise ValueError("an account that cannot be spent needs the contributions parked")
        if not self.provident_spendable and self.loan_lender == "provident" and self.commit_loan:
            raise ValueError("a provident lender needs accounts its members can spend")
        if not (self.provident_employee or self.provident_employer):
            raise ValueError("at least one side must contribute")
        if not self.provident_park and self.provident_employee:
            raise ValueError("an employee contribution returned at once is the identity; "
                             "use provident_employee=False")
        if not self.provident_park and self.loan_lender == "provident" and self.commit_loan:
            raise ValueError("a provident lender needs the contributions parked")
        if self.treasury_backing and (self.loan_lender != "public" or self.levy_rate <= 0.0):
            raise ValueError("treasury_backing needs loan_lender='public' and a levy")
        if self.loan_lender not in ("public", "bank", "provident"):
            raise ValueError("loan_lender must be 'public', 'bank' or 'provident'")
        if not 0.0 <= self.provident_rate < 0.5:
            raise ValueError("provident_rate must lie in [0, 0.5)")
        if self.loan_lender == "provident" and self.provident_rate <= 0.0 and self.commit_loan:
            raise ValueError("a provident lender needs provident_rate > 0")
        if not 0.0 <= self.loan_down <= 1.0 or self.loan_rate < 0.0 or self.loan_arrears_k < 1:
            raise ValueError("loan_down in [0, 1], loan_rate >= 0, loan_arrears_k >= 1")
        if not 0.0 <= self.short_stay_share <= 1.0 or not 0.0 <= self.short_stay_rate <= 1.0:
            raise ValueError("short_stay_share and short_stay_rate must lie in [0, 1]")
        if self.optional_move_rate < 0.0:
            raise ValueError("optional_move_rate must be non-negative")
        if self.optional_move_rate > 0.0 and not self.residence_bound:
            raise ValueError("optional_move_rate requires residence_bound")
        if self.core_R0 <= 0.0 or self.core_g <= -1.0:
            raise ValueError("core_R0 must be positive and core_g above -1")
        if self.public_build_rate < 0.0:
            raise ValueError("public_build_rate must be non-negative")
        if (self.public_build_rate > 0.0 or self.public_maintenance or self.state_topup
                or self.public_rent_cost) and self.landlord != "public":
            raise ValueError("block 4's public housing needs landlord='public'")
        if self.rent_cap not in RENT_CAPS:
            raise ValueError(f"rent_cap must be one of {RENT_CAPS}")
        if not 0.0 <= self.levy_rate < 1.0:
            raise ValueError("levy_rate must lie in [0, 1)")
        if self.cap_start < 0:
            raise ValueError("cap_start must be non-negative")
        if self.rent_cap is not None and not self.tenant_tier:
            raise ValueError("rent_cap requires tenant_tier")
        if self.liquidation not in LIQUIDATIONS:
            raise ValueError(f"liquidation must be one of {LIQUIDATIONS}")
        if self.landlord not in LANDLORDS:
            raise ValueError(f"landlord must be one of {LANDLORDS}")
        if not 0.0 <= self.dividend_exit <= 1.0:
            raise ValueError("dividend_exit must lie in [0, 1]")
        if not 0.0 <= self.pool_pass_rate <= 1.0:
            raise ValueError("pool_pass_rate must lie in [0, 1]")
        if self.new_supply_rate < 0.0:
            raise ValueError("new_supply_rate must be non-negative")

    @property
    def off(self) -> bool:
        return not (self.residence_bound or self.tenant_tier or self.new_supply_rate > 0.0
                    or self.levy_rate > 0.0 or self.cost_floor or self.rent_cap is not None
                    or self.public_build_rate > 0.0 or self.public_maintenance
                    or self.state_topup or self.public_rent_cost
                    or self.core_premium or self.optional_move_rate > 0.0
                    or self.commit_loan or self.short_stay_share > 0.0
                    or self.provident_rate > 0.0 or self.treasury_backing)

    @property
    def public_housing(self) -> bool:
        """Public rental stock can exist outside residence binding."""
        return self.public_build_rate > 0.0


@dataclass(frozen=True)
class A47Config:
    a3: A3Config = field(default_factory=A3Config)
    rules: HousingRules = field(default_factory=HousingRules)


class A47Model(A3Model):
    """A3's model with A47's housing rules. All rules off is A3 exactly."""

    def __init__(self, config: A47Config) -> None:
        # Set before A3's constructor, which runs the opening allocation and so
        # calls the overridden ``_settle_opening``.
        self.rules = config.rules
        tiers = config.a3.asset.tiers
        #: Units held by the landlord, per tier, and how many of them are new.
        self.landlord_units = np.zeros(tiers)
        self.landlord_new = np.zeros(tiers)
        #: Claims in the public pool, outside the graph.
        self.pool = 0.0
        #: Claims that have left the graph for good (listed dividends).
        self.exited = 0.0
        self.passed_down = 0.0
        self.landlord_rent = 0.0
        self._wage0: float | None = None
        if config.rules.residence_bound and config.a3.asset.max_units != 1:
            raise ValueError("residence_bound requires AssetSpec.max_units == 1")
        super().__init__(config.a3)
        self.liquidation_shortfall = np.zeros(self._n)
        self.liquidations: list[int] = []
        self.landlord_sales: list[int] = []
        self.pool_history: list[float] = []
        self.exited_history: list[float] = []
        #: Block 2.
        self.new_units = np.zeros_like(self.units)
        self.built = np.zeros(tiers)
        self.build_paid = 0.0
        self._build_acc = 0.0
        self.tenancy = np.full(self._n, -1)          # tier occupied as a renter, -1 none
        self.lessor = np.full(self._n, -2)           # owner of that unit; LANDLORD = -1
        self.unhoused_history: list[int] = []
        self.housed_history: list[np.ndarray] = []
        #: Block 3. One row per tenancy round: round, cap in force, regulated rent paid,
        #: regulated units occupied, exempt rent paid, exempt units occupied, what the
        #: regulated units would have paid uncapped, and the sum of their caps (+inf with no
        #: cap). "Exempt" means new building, counted whether or not a cap is in force, so the
        #: two classes can be compared before and after it (B129's square).
        self.rent_class_history: list[tuple] = []
        self.cost_price_history: list[np.ndarray] = []
        self.levied = 0.0
        self._cap_ref: tuple[np.ndarray, float] | None = None
        #: Block 4.
        self.public_built = np.zeros(tiers)
        self._public_acc = 0.0
        self._levy_held = 0.0
        self.topup_total = 0.0
        self.maintenance_paid = 0.0
        self.maintenance_unfunded = 0.0
        self.public_build_paid = 0.0
        self.public_tenants_history: list[int] = []
        #: A48; A51 may move the core off the top tier.
        if config.rules.core_tier >= tiers:
            raise ValueError("core_tier must index an existing tier")
        self._core_q = tiers - 1 if config.rules.core_tier < 0 else config.rules.core_tier
        #: A51: per round (core tenants, of whom wage receivers, location rent the landlord left
        #: uncollected, location rent collected), and per round the renters' tier choices.
        self.location_history: list[tuple[int, int, float, float]] = []
        self.location_choices: list[tuple[int, int, int, float, float]] = []
        #: A51 block 2: each renter's lease (last round it holds, tier, lessor, signed rent),
        #: the renters kept on a lease each round, and leases ended because the unit was gone.
        self.lease_until = np.full(self._n, -1)
        self.lease_q = np.full(self._n, -1)
        self.lease_who = np.full(self._n, -2)
        self.lease_rent = np.zeros(self._n)
        self.lease_log: list[tuple[int, int, int, int, float]] = []   # round, node, tier, lessor, rent paid due
        self.lease_evictions = 0
        self.raw_core_price_history: list[float] = []
        self.lock_events: list[tuple[int, int, float, float]] = []   # round, node, gap, claims
        self.optional_core_draws = 0
        self.optional_core_moved = 0
        self.optional_other_moved = 0
        self.core_buys: list[tuple[int, int, bool]] = []            # round, buyer, production
        #: Per round under ``core_premium``: core units held by households over all core
        #: units, and the core's tenants (count, how many in the production layer).
        self.core_household_history: list[float] = []
        self.core_tenant_history: list[tuple[int, int]] = []
        #: A49.
        n = self._n
        self.debt = np.zeros(n)
        self.instalment = np.zeros(n)
        self.arrears = np.zeros(n, dtype=int)
        #: round, node, loan, down payment, holdings before, short-stayer
        self.loan_log: list[tuple[int, int, float, float, float, bool]] = []
        self.repaid_principal = 0.0
        self.interest_paid = 0.0
        self.written_off = 0.0
        self.foreclosure_credit = 0.0
        self.foreclosures: list[tuple[int, int, float, float]] = []   # round, node, debt, credited
        self.cleared_nodes: set[int] = set()
        self.cleared_history: list[int] = []
        #: renters, of whom short-stayers, below the down payment, other
        self.renter_mix_history: list[tuple[int, int, int, int]] = []
        #: A49 block 2: the provident fund.
        self.account = np.zeros(n)
        self.pf_cash = 0.0
        self.contributed = np.zeros(n)
        self.pf_contrib_employee = 0.0
        self.pf_contrib_employer = 0.0
        self.pf_spent_from_accounts = 0.0
        #: A50: employer contributions paid straight to the receivers' holdings.
        self.pf_returned = 0.0
        #: A50 block 4: issuance withheld because the authority saw the accounts.
        self.pf_visible_cut = 0.0
        #: A50 block 5: issuance withheld because the target counts the accounts; the
        #: inflow per unit of circulating claims at baseline, read once.
        self.pf_target_cut = 0.0
        self.pf_velocity: float | None = None
        #: A50 block 6: what each round parked, per node, oldest first; and what went back.
        self._pf_vintages: list[np.ndarray] = []
        self.pf_released = 0.0
        if (config.rules.provident_visible or config.rules.provident_in_target) and (
                config.a3.network.withdraw.active or config.a3.network.authority.rule != "endogenous"
                                               or config.a3.network.writeoff.refill):
            raise ValueError("provident_visible and provident_in_target read the endogenous authority "
                             "without the refill or withdrawal clauses")
        #: A49 block 3: the treasury's overdraft of the pool.
        self._treasury_cap = 0.0
        self.treasury_repaid = 0.0
        self.pool_min = 0.0
        self.pool_min_over_cap: float | None = None
        self.pf_in = 0.0        # paid to the fund as lender: repayments, interest, foreclosure credit
        self.pf_out = 0.0       # paid by the fund as lender: loans, foreclosure surplus
        self.short_stay = np.zeros(n, dtype=bool)
        if config.rules.short_stay_share > 0.0:
            prod = np.flatnonzero(self._is_production)
            k = int(round(config.rules.short_stay_share * prod.size))
            rng = np.random.default_rng((config.a3.network.seed or 0) * 1_000_003 + 49_001)
            self.short_stay[rng.choice(prod, size=k, replace=False)] = True
        if config.rules.optional_move_rate > config.a3.asset.turnover + 1e-12:
            raise ValueError("optional_move_rate cannot exceed the turnover it splits")
        self._renter_order = np.random.default_rng(
            (config.a3.network.seed or 0) * 1_000_003 + 47_202).permutation(self._n)
        if self.rules.residence_bound and self.rules.bidders_exclude_owners \
                and not self.a3.asset.closed:
            self._pool_0 = bidder_pool(self.holdings, self._bidders())

    # -- helpers -------------------------------------------------------------

    def _bidders(self) -> np.ndarray:
        clears = self._admitted_at_opening()
        if not (self.rules.residence_bound and self.rules.bidders_exclude_owners):
            return clears
        return clears & (self.units.sum(axis=1) <= 0)[:, None]

    def _wage_index(self) -> float:
        paid = float(getattr(self, "_last_bill_paid", 0.0) or 0.0)
        if self._wage0 is None and paid > 0.0:
            self._wage0 = paid
        return paid / self._wage0 if self._wage0 else 1.0

    def cost_price(self) -> np.ndarray:
        return np.asarray(self.a3.asset.initial_price, dtype=float) * self._wage_index()

    def median_wage(self) -> float:
        """Median of what each wage receiver was paid this round."""
        paid = float(getattr(self, "_last_bill_paid", 0.0) or 0.0)
        receivers = self._wage_receivers
        if paid <= 0.0 or receivers.size == 0:
            return 0.0
        if self._wage_weights is None:
            return paid / receivers.size
        return float(np.median(paid * np.asarray(self._wage_weights, dtype=float)))

    def _cap_active(self) -> bool:
        return self.rules.rent_cap is not None and self._round >= self.rules.cap_start

    def rent_caps(self) -> np.ndarray:
        """Per-unit rent cap by tier this round; +inf where no cap is in force."""
        tiers = self.a3.asset.tiers
        r = self.rules
        if not self._cap_active():
            return np.full(tiers, np.inf)
        if r.rent_cap == "wage":
            maint = r.maintenance_rate * self.cost_price()
            return r.cap_wage_share * self.median_wage() + r.cap_maintenance * maint
        if self._cap_ref is None:
            self._cap_ref = (self.a3.asset.rent_rate * self.price.copy(), self._wage_index())
        ref_rent, ref_wage = self._cap_ref
        return ref_rent * (self._wage_index() / ref_wage if ref_wage else 1.0)

    def _new_share(self, who: int, q: int) -> float:
        if not self.rules.cap_exempt_new:
            return 0.0
        if who == LANDLORD:
            return float(self.landlord_new[q] / self.landlord_units[q]) if self.landlord_units[q] else 0.0
        return float(self.new_units[who, q] / self.units[who, q]) if self.units[who, q] else 0.0

    def _apply_levy(self) -> None:
        """A6Model._apply_levy with as_edge False, arithmetic unchanged."""
        rate = self.rules.levy_rate
        if rate <= 0.0:
            return
        l1 = np.asarray(self._l1, dtype=int)
        l2 = np.asarray(self._l2, dtype=int)
        levy = rate * np.maximum(self.holdings[l1], 0.0)
        total = float(levy.sum())
        if total <= 0.0:
            return
        self.holdings[l1] -= levy
        self.levied += total
        if self.rules.treasury_backing:
            self._treasury_cap = total
            if self.pool < 0.0:
                top = min(-self.pool, total)
                self.pool += top
                total -= top
                self.treasury_repaid += top
                if total <= 0.0:
                    return
        if self.rules.state_topup:
            # Held for the public project's first call; the rest goes out in
            # ``_release_levy`` exactly as A6 pays it.
            self._levy_held = total
            return
        self.holdings[l2] += total / l2.size

    def _release_levy(self) -> None:
        if self._levy_held > 0.0:
            l2 = np.asarray(self._l2, dtype=int)
            self.holdings[l2] += self._levy_held / l2.size
            self._levy_held = 0.0

    def _public_pays(self, amount: float) -> float:
        """The public project pays: its pool first, then the state out of the held levy."""
        if amount <= 0.0:
            return 0.0
        from_pool = min(amount, max(self.pool, 0.0))
        self.pool -= from_pool
        from_state = 0.0
        if self.rules.state_topup:
            from_state = min(amount - from_pool, self._levy_held)
            self._levy_held -= from_state
            self.topup_total += from_state
        return from_pool + from_state

    def _public_round(self) -> None:
        """Upkeep first, then this round's public building."""
        r = self.rules
        cost = self.cost_price()
        if r.public_maintenance and self.landlord_units.sum() > 0.0:
            due = r.maintenance_rate * float(self.landlord_units @ cost)
            paid = self._public_pays(due)
            self._pay_production(paid)
            self.maintenance_paid += paid
            self.maintenance_unfunded += due - paid
        if r.public_build_rate > 0.0:
            supply = np.asarray(self.supply, dtype=float)
            self._public_acc += r.public_build_rate * float(supply.sum())
            k = int(np.floor(self._public_acc + 1e-12))
            if k > 0:
                per_tier = _apportion(k, self._build_weights(supply))
                want = float(per_tier @ cost)
                funds = max(self.pool, 0.0) + (self._levy_held if r.state_topup else 0.0)
                if funds + 1e-12 >= want:
                    self._public_acc -= k
                    paid = self._public_pays(want)
                    self._pay_production(paid)
                    self.public_build_paid += paid
                    self.landlord_units += per_tier
                    self.landlord_new += per_tier
                    self.public_built += per_tier

    def _trade_price(self, q: int) -> float:
        if self.rules.liquidation == "cost":
            return float(self.cost_price()[q])
        return float(self.price[q])

    def _credit_landlord(self, amount: float) -> None:
        """Money paid to the landlord: rent or sale proceeds."""
        if amount <= 0.0:
            return
        if self.rules.landlord == "public":
            self.pool += amount
            return
        out = self.rules.dividend_exit * amount
        self.exited += out
        self.holdings += (amount - out) * self._prior_owner_weights()

    def _landlord_pays(self, amount: float) -> float:
        """The landlord pays. Returns what it could pay."""
        if self.rules.landlord == "public":
            paid = min(amount, max(self.pool, 0.0))
            self.pool -= paid
            return paid
        w = self._prior_owner_weights()
        take = np.minimum(amount * w, np.maximum(self.holdings, 0.0))
        self.holdings -= take
        return float(take.sum())

    def _landlord_funds(self) -> float:
        if self.rules.landlord == "public":
            return max(self.pool, 0.0)
        w = self._prior_owner_weights()
        live = w > 0
        if not live.any():
            return 0.0
        # the most it can pay in full at its own weights
        return float(np.min(np.maximum(self.holdings[live], 0.0) / w[live]))

    def _pay_production(self, amount: float) -> None:
        live = np.flatnonzero(self._is_production & self._alive)
        if amount > 0.0 and live.size:
            self.holdings[live] += amount / live.size

    def _total(self) -> float:
        return (float(self.holdings.sum()) + self.pool + self.exited + self._levy_held
                + getattr(self, "pf_cash", 0.0))

    def _move_new(self, frm: int, to: int, q: int) -> None:
        """Move the new-flag share of one unit of tier q with the unit."""
        if frm == LANDLORD:
            share = self.landlord_new[q] / self.landlord_units[q] if self.landlord_units[q] else 0.0
            self.landlord_new[q] -= share
        else:
            share = self.new_units[frm, q] / self.units[frm, q] if self.units[frm, q] else 0.0
            self.new_units[frm, q] -= share
        if to == LANDLORD:
            self.landlord_new[q] += share
        else:
            self.new_units[to, q] += share

    # -- block 2: new supply --------------------------------------------------

    def _build(self) -> None:
        rate = self.rules.new_supply_rate
        if rate <= 0.0 or self.a3.asset.closed:
            return
        supply = np.asarray(self.supply, dtype=float)
        self._build_acc += rate * float(supply.sum())
        k = int(np.floor(self._build_acc + 1e-12))
        if k <= 0:
            return
        per_tier = _apportion(k, self._build_weights(supply))
        cost = self.cost_price()
        want = float(per_tier @ cost)
        if self.rules.residence_bound:
            funds = self._landlord_funds()
        else:
            fin = ~self._is_production
            funds = float(np.maximum(self.holdings[fin], 0.0).sum())
        if funds + 1e-12 < want:
            return            # build only what can be paid in full; the count carries over
        self._build_acc -= k
        if self.rules.residence_bound:
            paid = self._landlord_pays(want)
            self.landlord_units += per_tier
            self.landlord_new += per_tier
        else:
            fin = ~self._is_production
            h = np.where(fin, np.maximum(self.holdings, 0.0), 0.0)
            shares = h / h.sum()
            take = want * shares
            self.holdings -= take
            paid = float(take.sum())
            for q in range(per_tier.size):
                got = _apportion(int(per_tier[q]), shares)
                self.units[:, q] += got
                self.new_units[:, q] += got
        self._pay_production(paid)
        self.built += per_tier
        self.build_paid += paid

    # -- block 2: tenancy -----------------------------------------------------

    def _rental_slots(self) -> list[tuple[int, int, int]]:
        """(tier, lessor, count) of rentable units, cheapest tier first."""
        slots = []
        tiers = self.a3.asset.tiers
        if self.rules.residence_bound:
            for q in range(tiers):
                c = int(round(self.landlord_units[q]))
                if c > 0:
                    slots.append((q, LANDLORD, c))
            return slots
        # Public rental stock, where there is any outside residence binding, is offered
        # first: it is the cheaper option the building exists to add.
        if self.rules.public_housing or self.landlord_units.sum() > 0.0:
            for q in range(tiers):
                c = int(round(self.landlord_units[q]))
                if c > 0:
                    slots.append((q, LANDLORD, c))
        held = self.units.sum(axis=1)
        own_q = np.where(held > 0, tiers - 1 - np.argmax(self.units[:, ::-1] > 0, axis=1), -1)
        for q in range(tiers):
            spare = self.units[:, q] - (own_q == q)
            for i in np.flatnonzero(spare > 0):
                slots.append((q, int(i), int(round(spare[i]))))
        return slots

    def _commute_cost(self) -> np.ndarray:
        """A51: each node's commuting cost this round if it lives outside the core."""
        out = np.zeros(self._n)
        paid = float(getattr(self, "_last_bill_paid", 0.0) or 0.0)
        rec = np.asarray(self._wage_receivers, dtype=int)
        if paid <= 0.0 or rec.size == 0:
            return out
        w = (np.full(rec.size, 1.0 / rec.size) if self._wage_weights is None
             else np.asarray(self._wage_weights, dtype=float))
        out[rec] = self.rules.location_s * paid * w
        return out

    def _tenancy_rent_located(self) -> None:
        """Tenancy by unit with location demand (A51). Renters in the fixed order each take the
        rental unit that minimises rent plus commuting cost among those whose rent they can pay,
        the cheapest rent if they can pay none; ties go to the lower tier. No rent cap."""
        spec = self.a3.asset
        held = self.units.sum(axis=1)
        if spec.rent_base == "layer":
            is_renter = (held <= 0) & self._is_production
        else:
            is_renter = held <= 0
        renters = [int(i) for i in self._renter_order if is_renter[i]]
        self.tenancy[:] = -1
        self.lessor[:] = -2
        housed = np.zeros(spec.tiers, dtype=int)
        total = 0.0
        public_tenants = 0
        slots = self._rental_slots()
        self.match_state = {
            "renters": len(renters),
            "slots_by_tier": [sum(c for q_, _, c in slots if q_ == q) for q in range(spec.tiers)],
            "held_at_match": held.copy(),
            "is_renter": is_renter.copy(),
        }
        queue: dict[int, list[int]] = {}
        for q, who, c in slots:
            queue.setdefault(q, []).extend([who] * c)
        commute = self._commute_cost()
        core = self._core_q
        n_core = n_core_emp = 0
        left_with_tenants = collected = 0.0
        k = 0
        t_now = int(self._round)
        L = self.rules.lease_rounds
        kept: list[int] = []
        if L > 1:
            for i in renters:
                if self.lease_until[i] < t_now:
                    continue
                q, who = int(self.lease_q[i]), int(self.lease_who[i])
                if who in queue.get(q, []):
                    queue[q].remove(who)
                    kept.append(i)
                else:
                    self.lease_evictions += 1
                    self.lease_until[i] = -1
        kept_set = set(kept)
        order = kept + [i for i in renters if i not in kept_set]
        for i in order:
            have = max(float(self.holdings[i]), 0.0)
            if i in kept_set:
                q, who = int(self.lease_q[i]), int(self.lease_who[i])
                if self.rules.lease_rent_lock:
                    due = float(self.lease_rent[i])
                elif who == LANDLORD and self.rules.public_rent_cost:
                    due = spec.rent_rate * float(self.cost_price()[q])
                else:
                    due = spec.rent_rate * float(self.price[q])
                rent = {q: due}
                self.lease_log.append((t_now, i, q, who, due))
                k += 1
            else:
                open_q = [q for q in sorted(queue) if queue[q]]
                if not open_q:
                    break
                k += 1
                rent = {}
                for q in open_q:
                    who = queue[q][0]
                    if who == LANDLORD and self.rules.public_rent_cost:
                        rent[q] = spec.rent_rate * float(self.cost_price()[q])
                    else:
                        rent[q] = spec.rent_rate * float(self.price[q])
                cost = {q: rent[q] + (0.0 if q == core else float(commute[i])) for q in open_q}
                ok = [q for q in open_q if rent[q] <= have]
                if ok:
                    q = min(ok, key=lambda x: (cost[x], x))
                else:
                    q = min(open_q, key=lambda x: (rent[x], x))
                self.location_choices.append((t_now, i, q, cost[q], min(cost[x] for x in ok) if ok else cost[q]))
                who = queue[q].pop(0)
                if L > 1:
                    self.lease_until[i] = t_now + L - 1
                    self.lease_q[i] = q
                    self.lease_who[i] = who
                    self.lease_rent[i] = rent[q]
            self.tenancy[i] = q
            self.lessor[i] = who
            housed[q] += 1
            if who == LANDLORD:
                public_tenants += 1
            if q == core:
                n_core += 1
                n_core_emp += int(commute[i] > 0.0)
                location = spec.rent_rate * float(self.price[q]) * (1.0 - 1.0 / self.core_factor())
                if who == LANDLORD and self.rules.public_rent_cost:
                    left_with_tenants += spec.rent_rate * float(self.price[q]) - rent[q]
                elif i in kept_set and self.rules.lease_rent_lock:
                    # a locked rent: what the landlord charges above the plain tier's rent now,
                    # and what the lock leaves with the tenant
                    market_now = spec.rent_rate * float(self.price[q])
                    collected += max(0.0, rent[q] - market_now / self.core_factor())
                    left_with_tenants += market_now - rent[q]
                else:
                    collected += location
            if spec.rent_rate <= 0.0:
                continue
            pay = min(rent[q], have)
            self.holdings[i] -= pay
            total += pay
            if who == LANDLORD:
                self._credit_landlord(pay)
                self.landlord_rent += pay
            else:
                self.holdings[who] += pay
        self.location_history.append((n_core, n_core_emp, left_with_tenants, collected))
        self.unhoused_history.append(len(renters) - k)
        self.housed_history.append(housed)
        self.public_tenants_history.append(public_tenants)
        self.rent_class_history.append((int(self._round), False, 0.0, 0.0, 0.0, 0.0, 0.0, float("inf")))
        self.rent_collected += total
        self.rent_history.append(total)

    def _tenancy_rent(self) -> None:
        if self.rules.location_s > 0.0:
            return self._tenancy_rent_located()
        spec = self.a3.asset
        held = self.units.sum(axis=1)
        if spec.rent_base == "layer":
            is_renter = (held <= 0) & self._is_production
        else:
            is_renter = held <= 0
        renters = [int(i) for i in self._renter_order if is_renter[i]]
        if self.rules.commit_loan or self.rules.short_stay_share > 0.0:
            gate = self.rules.loan_down * self.terms[:, 0] * float(self.price[0])
            r_idx = np.asarray(renters, dtype=int)
            n_short = int(self.short_stay[r_idx].sum()) if r_idx.size else 0
            below = int((~self.short_stay[r_idx] & (self.holdings[r_idx] < gate[r_idx])).sum()) if r_idx.size else 0
            self.renter_mix_history.append((len(renters), n_short, below, len(renters) - n_short - below))
        self.tenancy[:] = -1
        self.lessor[:] = -2
        k = 0
        housed = np.zeros(spec.tiers, dtype=int)
        total = 0.0
        caps = self.rent_caps()
        capped = self._cap_active()
        reg_paid = reg_units = ex_paid = ex_units = reg_uncapped = reg_cap_sum = 0.0
        public_tenants = 0
        slots = self._rental_slots()
        #: The state the round's matching saw. Sales later in the round change the stock,
        #: so a check on tenancy reads this, not the end of the round.
        self.match_state = {
            "renters": len(renters),
            "slots_by_tier": [sum(c for q_, _, c in slots if q_ == q) for q in range(spec.tiers)],
            "held_at_match": held.copy(),
            "is_renter": is_renter.copy(),
        }
        for q, who, c in slots:
            for _ in range(c):
                if k >= len(renters):
                    break
                i = renters[k]
                k += 1
                self.tenancy[i] = q
                self.lessor[i] = who
                housed[q] += 1
                if spec.rent_rate <= 0.0:
                    continue
                if who == LANDLORD and self.rules.public_rent_cost:
                    market = spec.rent_rate * float(self.cost_price()[q])
                else:
                    market = spec.rent_rate * float(self.price[q])
                if who == LANDLORD:
                    public_tenants += 1
                f = self._new_share(who, q)
                regulated = min(market, float(caps[q])) if capped else market
                # Uncapped, the blend would equal ``market`` only up to the last bit.
                due = f * market + (1.0 - f) * regulated if capped else market
                pay = min(due, max(float(self.holdings[i]), 0.0))
                reg_units += 1.0 - f
                ex_units += f
                reg_uncapped += (1.0 - f) * market
                if capped:
                    reg_cap_sum += (1.0 - f) * float(caps[q])
                if due > 0.0:
                    scale = pay / due
                    reg_paid += (1.0 - f) * regulated * scale
                    ex_paid += f * market * scale
                self.holdings[i] -= pay
                total += pay
                if who == LANDLORD:
                    self._credit_landlord(pay)
                    self.landlord_rent += pay
                else:
                    self.holdings[who] += pay
        self.unhoused_history.append(len(renters) - k)
        self.housed_history.append(housed)
        self.public_tenants_history.append(public_tenants)
        self.rent_class_history.append(
            (int(self._round), bool(capped), reg_paid, reg_units, ex_paid, ex_units,
             reg_uncapped, reg_cap_sum if capped else float("inf")))
        self.rent_collected += total
        self.rent_history.append(total)

    # -- overrides -----------------------------------------------------------

    def _settle_opening(self, paid_total: float, unsold: list[int]) -> None:
        if not self.rules.residence_bound:
            return super()._settle_opening(paid_total, unsold)
        spec = self.a3.asset
        if paid_total > 0.0:
            if spec.proceeds == "seller":
                self.holdings += paid_total * self._prior_owner_weights()
            else:
                self.holdings += paid_total / self._n
        self.landlord_units += np.asarray(unsold, dtype=float)

    def _update_prices(self) -> None:
        if not self.rules.residence_bound:
            super()._update_prices()
        else:
            pool = bidder_pool(self.holdings, self._bidders())
            self.price = price_at(np.asarray(self.a3.asset.initial_price, dtype=float),
                                  pool, self._pool_0, self.a3.asset.elasticity)
        if self.rules.cost_floor:
            self.price = np.maximum(self.price, self.cost_price())
        if self.rules.core_premium:
            q = self._core_q
            self.raw_core_price_history.append(float(self.price[q]))
            self.price[q] = self.price[q] * self.core_factor()

    def _collect_rent(self) -> None:
        if self.rules.tenant_tier:
            self._tenancy_rent()
        elif not self.rules.residence_bound:
            return super()._collect_rent()
        else:
            spec = self.a3.asset
            held = self.units.sum(axis=1)
            if spec.rent_rate <= 0.0 or self.landlord_units.sum() <= 0.0:
                self.rent_history.append(0.0)
            else:
                if spec.rent_base == "layer":
                    renters = np.flatnonzero((held <= 0) & self._is_production)
                else:
                    renters = np.flatnonzero(held <= 0)
                due = spec.rent_rate * float(self.price[0])
                paid = np.minimum(due, np.maximum(self.holdings[renters], 0.0))
                total = float(paid.sum())
                self.holdings[renters] -= paid
                self._credit_landlord(total)
                self.rent_collected += total
                self.landlord_rent += total
                self.rent_history.append(total)
        if (self.rules.residence_bound or self.rules.public_housing) \
                and self.rules.landlord == "public" and self.pool > 0.0:
            live = np.flatnonzero(self._is_production & self._alive)
            if live.size:
                amount = self.rules.pool_pass_rate * self.pool
                self.pool -= amount
                self.holdings[live] += amount / live.size
                self.passed_down += amount

    def core_factor(self) -> float:
        r = self.rules
        return r.core_R0 * (1.0 + r.core_g) ** int(self._round)

    def _build_weights(self, supply: np.ndarray) -> np.ndarray:
        w = supply.astype(float).copy()
        if self.rules.core_premium:
            w[self._core_q] = 0.0     # the core is not extended
        return w / w.sum()

    def lock_gap(self, i: int) -> float:
        spec = self.a3.asset
        q, low = self._core_q, 0
        grow = (1.0 + self.rules.core_g) ** spec.holding_period if self.rules.core_premium else 1.0
        p_core, p_low = float(self.price[q]), float(self.price[low])
        return float(self.terms[i, q]) * p_core * grow - p_core + float(self.terms[i, low]) * p_low

    # -- A49: the loan book ----------------------------------------------------

    def _can_commit(self) -> np.ndarray:
        """Nodes whose must-move rate is at most 1 / holding_period."""
        spec = self.a3.asset
        ok = spec.turnover <= 1.0 / spec.holding_period + 1e-12
        return ~self.short_stay & ok

    def _pf(self) -> bool:
        return self.rules.provident_rate > 0.0

    def _spendable(self) -> np.ndarray:
        if self._pf() and self.rules.provident_spendable:
            return self.holdings + self.account
        return self.holdings

    def _spend(self, i: int, amount: float) -> None:
        """Pay ``amount`` for node ``i``: its fund account first when there is one."""
        if not (self._pf() and self.rules.provident_spendable):
            self.holdings[i] -= amount
            return
        from_acc = min(amount, self.account[i])
        self.account[i] -= from_acc
        self.pf_cash -= from_acc
        self.pf_spent_from_accounts += from_acc
        self.holdings[i] += from_acc - amount

    def _contribute(self) -> None:
        """Employee and employer contributions on this round's wages.

        With ``provident_visible`` the authority counts this round's parked contributions as
        layer-2 inflow. Its rule is ``max(0, gain x (baseline - inflow))``, set for the next
        round before this runs; counting ``x`` more inflow gives ``max(0, pending - gain x x)``
        exactly, since a positive pending is ``gain x`` a positive gap.
        """
        r = self.rules
        if not (r.provident_visible or r.provident_in_target or r.provident_release):
            self._contribute_sides()
            return
        acc0 = self.account.copy()
        before = self.pf_cash
        self._contribute_sides()
        gain = self.config.authority.gain
        if r.provident_visible:
            withheld = min(gain * (self.pf_cash - before), self._pending_issuance)
            self._pending_issuance -= withheld
            self.pf_visible_cut += withheld
        if r.provident_release:
            self._release(self.account - acc0)
        if r.provident_in_target:
            if self.pf_velocity is None:
                self.pf_velocity = float(self._baseline_active) / float(self.config.initial_claims)
            withheld = min(gain * self.pf_velocity * float(self.account.sum()), self._pending_issuance)
            self._pending_issuance -= withheld
            self.pf_target_cut += withheld

    def _release(self, parked_now: np.ndarray) -> None:
        """Pay back what was parked ``provident_release`` rounds ago, as far as it is still there."""
        self._pf_vintages.append(parked_now)
        if len(self._pf_vintages) <= self.rules.provident_release:
            return
        due = np.minimum(self._pf_vintages.pop(0), np.maximum(self.account, 0.0))
        self.account -= due
        self.holdings += due
        got = float(due.sum())
        self.pf_cash -= got
        self.pf_released += got

    def _contribute_sides(self) -> None:
        c = self.rules.provident_rate
        if c <= 0.0:
            return
        paid = float(getattr(self, "_last_bill_paid", 0.0) or 0.0)
        rec = np.asarray(self._wage_receivers, dtype=int)
        if paid <= 0.0 or rec.size == 0:
            return
        w = (np.full(rec.size, 1.0 / rec.size) if self._wage_weights is None
             else np.asarray(self._wage_weights, dtype=float))
        wage = paid * w
        if self.rules.provident_employee:
            emp = np.minimum(c * wage, np.maximum(self.holdings[rec], 0.0))
            self.holdings[rec] -= emp
            self.account[rec] += emp
            self.contributed[rec] += emp
            self.pf_cash += float(emp.sum())
            self.pf_contrib_employee += float(emp.sum())
        if not self.rules.provident_employer:
            return
        payers = np.asarray(self._wage_payers, dtype=int)
        want = c * paid
        have = np.maximum(self.holdings[payers], 0.0)
        if have.sum() <= 0.0:
            return
        take = np.minimum(want * have / have.sum(), have)
        got = float(take.sum())
        self.holdings[payers] -= take
        share = wage / wage.sum()
        if self.rules.provident_park:
            self.account[rec] += got * share
            self.contributed[rec] += got * share
            self.pf_cash += got
        else:
            self.holdings[rec] += got * share
            self.pf_returned += got
        self.pf_contrib_employer += got

    def pf_surplus(self) -> float:
        """Fund cash plus loans it holds, less what it owes its members."""
        lent = float(self.debt.sum()) if self.rules.loan_lender == "provident" else 0.0
        return self.pf_cash + lent - float(self.account.sum())

    def _lender_funds(self) -> float:
        if self.rules.loan_lender == "provident":
            return self.pf_cash
        if self.rules.loan_lender == "public":
            if self.rules.treasury_backing:
                return self.pool + self._treasury_cap
            return self.pool
        w = self._prior_owner_weights()
        live = w > 0
        return float(np.min(np.maximum(self.holdings[live], 0.0) / w[live])) if live.any() else 0.0

    def _lender_pays(self, amount: float) -> None:
        if self.rules.loan_lender == "provident":
            self.pf_cash -= amount
            self.pf_out += amount
        elif self.rules.loan_lender == "public":
            self.pool -= amount
        else:
            self.holdings -= amount * self._prior_owner_weights()

    def _lender_receives(self, amount: float) -> None:
        if amount <= 0.0:
            return
        if self.rules.loan_lender == "provident":
            self.pf_cash += amount
            self.pf_in += amount
        elif self.rules.loan_lender == "public":
            self.pool += amount
        else:
            self.holdings += amount * self._prior_owner_weights()

    def _loan_ok(self, cost: np.ndarray, owned: np.ndarray, cash_ok: np.ndarray) -> np.ndarray:
        if not self.rules.commit_loan:
            return np.zeros(self._n, dtype=bool)
        d = self.rules.loan_down
        funds = self._lender_funds()
        ok = (self._can_commit() & (owned <= 0) & ~cash_ok
              & (self._spendable() >= d * cost) & ((1.0 - d) * cost <= funds + 1e-12))
        if self.rules.loan_lender == "provident":
            ok &= self.contributed > 0.0
        return ok

    def _originate(self, buyer: int, cost: float) -> None:
        down = self.rules.loan_down * cost
        loan = cost - down
        before = float(self._spendable()[buyer])
        self._spend(buyer, down)
        self._lender_pays(loan)
        self.debt[buyer] += loan
        self.instalment[buyer] = self.debt[buyer] / self.a3.asset.holding_period
        self.arrears[buyer] = 0
        self.loan_log.append((int(self._round), buyer, loan, down, before, bool(self.short_stay[buyer])))

    def _repay_from(self, i: int) -> None:
        """A seller with a loan repays from what it holds, up to the balance."""
        if self.debt[i] <= 0.0:
            return
        pay = min(self.debt[i], max(float(self.holdings[i]), 0.0))
        self.holdings[i] -= pay
        self._lender_receives(pay)
        self.debt[i] -= pay
        self.repaid_principal += pay
        if self.debt[i] <= 1e-15:
            self.debt[i] = 0.0
            self.instalment[i] = 0.0
            self.arrears[i] = 0

    def _foreclose(self, i: int) -> None:
        q_held = np.flatnonzero(self.units[i] > 0)
        debt = float(self.debt[i])
        credited = 0.0
        if q_held.size:
            q = int(q_held[0])
            price = self._trade_price(q)
            if self.rules.residence_bound:
                got = self._landlord_pays(price)
                self._move_new(i, LANDLORD, q)
                self.landlord_units[q] += 1.0
                self.holdings[i] += got
                credited = min(got, debt)
                self.holdings[i] -= credited
                self._lender_receives(credited)
            else:
                credited = min(price, debt)
                surplus = price - credited
                if surplus > 0.0:
                    self._lender_pays(surplus)
                    self.holdings[i] += surplus
                if self.rules.loan_lender in ("public", "provident"):
                    self._move_new(i, LANDLORD, q)
                    self.landlord_units[q] += 1.0
                else:
                    j = int(np.argmax(self._prior_owner_weights()))
                    self._move_new(i, j, q)
                    self.units[j, q] += 1.0
            self.units[i, q] -= 1.0
            self._close_cycle(i, q, price)
        self.foreclosure_credit += credited
        self.written_off += debt - credited
        self.foreclosures.append((int(self._round), i, debt, credited))
        self.debt[i] = 0.0
        self.instalment[i] = 0.0
        self.arrears[i] = 0

    def _service_loans(self) -> None:
        if not self.rules.commit_loan:
            return
        for i in np.flatnonzero(self.debt > 0.0):
            i = int(i)
            interest = self.rules.loan_rate * self.debt[i]
            principal = min(self.instalment[i], self.debt[i])
            due = interest + principal
            pay = min(due, max(float(self._spendable()[i]), 0.0))
            self._spend(i, pay)
            self._lender_receives(pay)
            to_interest = min(pay, interest)
            self.interest_paid += to_interest
            to_principal = pay - to_interest
            self.debt[i] -= to_principal
            self.repaid_principal += to_principal
            self.arrears[i] = self.arrears[i] + 1 if pay + 1e-15 < due else 0
            if self.debt[i] <= 1e-15:
                self.debt[i] = 0.0
                self.instalment[i] = 0.0
                self.arrears[i] = 0
            elif self.arrears[i] >= self.rules.loan_arrears_k:
                self._foreclose(i)
        cleared = np.flatnonzero((self.debt > 0.0) & (self._spendable() <= 1e-12))
        self.cleared_nodes.update(int(c) for c in cleared)
        self.cleared_history.append(int(cleared.size))

    def _household_offers(self) -> list[tuple[int, int]]:
        if self.rules.optional_move_rate <= 0.0 and self.rules.short_stay_share <= 0.0:
            return super()._offers()
        # A3's ``_offers`` with its one draw per held unit split in two.
        spec = self.a3.asset
        held = np.argwhere(self.units > 0)
        if held.size == 0:
            return []
        out: list[tuple[int, int]] = []
        forced_cut = spec.turnover - self.rules.optional_move_rate
        if spec.turnover > 0.0 or self.rules.short_stay_share > 0.0:
            draw = self._asset_rng.random(len(held))
            for (i, q), x in zip(held, draw, strict=True):
                i, q = int(i), int(q)
                if self.short_stay[i]:
                    if x < self.rules.short_stay_rate:
                        out.append((i, q))
                    continue
                if x < forced_cut:
                    out.append((i, q))
                elif x < spec.turnover:
                    if q == self._core_q:
                        self.optional_core_draws += 1
                        gap = self.lock_gap(i)
                        have = max(float(self.holdings[i]), 0.0)
                        if gap > have:
                            self.lock_events.append((int(self._round), i, gap, have))
                            continue
                        self.optional_core_moved += 1
                    else:
                        self.optional_other_moved += 1
                    out.append((i, q))
        if spec.arm == "forced":
            floor = spec.forced_sale_floor * self._claims_0
            distressed = self.holdings < floor
            already = {i for i, _ in out}
            forced = [(int(i), int(q)) for i, q in held if distressed[i] and int(i) not in already]
            self.forced_sales.append(len(forced))
            out.extend(forced)
        else:
            self.forced_sales.append(0)
        return out

    def _offers(self) -> list[tuple[int, int]]:
        out = self._household_offers()
        if not self.rules.residence_bound:
            return out
        spec = self.a3.asset
        for q in range(spec.tiers):
            k = int(self.landlord_units[q])
            if k and spec.turnover > 0.0:
                n_offer = int((self._asset_rng.random(k) < spec.turnover).sum())
                out.extend([(LANDLORD, q)] * n_offer)
        return out

    def _settle(self, offers: list[tuple[int, int]]) -> None:
        if not self.rules.residence_bound and self.rules.commit_loan:
            before = self.units.copy()
            self._settle_unbound_with_loans(offers)
            if self.rules.new_supply_rate > 0.0:
                self._carry_new_pro_rata(before)
            return
        if not self.rules.residence_bound:
            if self.rules.new_supply_rate <= 0.0:
                return super()._settle(offers)
            before = self.units.copy()
            super()._settle(offers)
            self._carry_new_pro_rata(before)
            return
        owned = self.units.sum(axis=1)
        sold = liq = ll_sold = 0
        premium_pot = 0.0
        for seller, q in offers:
            if seller != LANDLORD and self.units[seller, q] <= 0:
                continue
            if seller == LANDLORD and self.landlord_units[q] < 1.0:
                continue
            price = self._trade_price(q)
            cost = self.terms[:, q] * price
            cash_ok = self._spendable() >= cost
            loan_ok = self._loan_ok(cost, owned, cash_ok)
            eligible = ((owned <= 0) & cash_ok) | loan_ok
            if seller != LANDLORD:
                eligible &= np.arange(self._n) != seller
            if eligible.any():
                pool_ = np.flatnonzero(eligible)
                buyer = int(pool_[self._asset_rng.integers(pool_.size)])
                paid = float(cost[buyer])
                if loan_ok[buyer]:
                    self._originate(buyer, paid)
                else:
                    self._spend(buyer, paid)
                premium_pot += paid - price
                if self.rules.core_premium and q == self._core_q:
                    self.core_buys.append((int(self._round), buyer, bool(self._is_production[buyer])))
                self._move_new(seller, buyer, q)
                if seller == LANDLORD:
                    self.landlord_units[q] -= 1.0
                    self._credit_landlord(price)
                    ll_sold += 1
                else:
                    self.holdings[seller] += price
                    self.units[seller, q] -= 1.0
                    owned[seller] -= 1
                    self._close_cycle(seller, q, price)
                    self._repay_from(seller)
                self.units[buyer, q] += 1.0
                owned[buyer] += 1
                self.basis.setdefault((buyer, q), []).append(
                    (max(paid, 1e-12), self._round, price))
                sold += 1
            elif seller != LANDLORD:
                # Leaving is compulsory: the landlord takes the unit.
                got = self._landlord_pays(price)
                self.holdings[seller] += got
                self.liquidation_shortfall[seller] += price - got
                self._move_new(seller, LANDLORD, q)
                self.units[seller, q] -= 1.0
                owned[seller] -= 1
                self.landlord_units[q] += 1.0
                self._close_cycle(seller, q, got)
                self._repay_from(seller)
                liq += 1
        if premium_pot != 0.0:
            self.holdings += premium_pot / self._n
        self.sales.append(sold)
        self.liquidations.append(liq)
        self.landlord_sales.append(ll_sold)

    def _settle_unbound_with_loans(self, offers: list[tuple[int, int]]) -> None:
        """A3's ``_settle`` line for line, with the commitment loan as a second way in."""
        if not offers:
            self.sales.append(0)
            return
        cap = self.a3.asset.max_units or self._n
        owned = self.units.sum(axis=1)
        sold = 0
        premium_pot = 0.0
        for seller, q in offers:
            if self.units[seller, q] <= 0:
                continue
            price = float(self.price[q])
            cost = self.terms[:, q] * price
            cash_ok = self._spendable() >= cost
            loan_ok = self._loan_ok(cost, owned, cash_ok)
            eligible = (((owned < cap) & cash_ok) | loan_ok) & (np.arange(self._n) != seller)
            if not eligible.any():
                continue
            pool = np.flatnonzero(eligible)
            buyer = int(pool[self._asset_rng.integers(pool.size)])
            paid = float(cost[buyer])
            if loan_ok[buyer]:
                self._originate(buyer, paid)
            else:
                self._spend(buyer, paid)
            self.holdings[seller] += price
            premium_pot += paid - price
            self.units[seller, q] -= 1.0
            self.units[buyer, q] += 1.0
            owned[seller] -= 1
            owned[buyer] += 1
            held = self.basis.get((seller, q))
            if held:
                entry, bought_at, ref = held.pop(0)
                self.cycle_returns.setdefault(seller, []).append(float(np.log(price / entry)))
                self.trades.append((seller, q, int(bought_at), int(self._round), entry, price, ref))
                self.cycles[seller] += 1
            self.basis.setdefault((buyer, q), []).append((max(paid, 1e-12), self._round, price))
            self._repay_from(seller)
            sold += 1
        if premium_pot != 0.0:
            self.holdings += premium_pot / self._n
        self.sales.append(sold)

    def _carry_new_pro_rata(self, before: np.ndarray) -> None:
        """A3 settled the round's sales; move the new flags within each tier pro rata."""
        for q in range(before.shape[1]):
            lost = np.maximum(before[:, q] - self.units[:, q], 0.0)
            gained = np.maximum(self.units[:, q] - before[:, q], 0.0)
            if not lost.any():
                continue
            share = np.divide(self.new_units[:, q], before[:, q],
                              out=np.zeros(self._n), where=before[:, q] > 0)
            moved = lost * share
            self.new_units[:, q] -= moved
            if gained.sum() > 0:
                self.new_units[:, q] += moved.sum() * gained / gained.sum()

    def _close_cycle(self, seller: int, q: int, received: float) -> None:
        held = self.basis.get((seller, q))
        if held:
            entry, bought_at, ref = held.pop(0)
            self.cycle_returns.setdefault(seller, []).append(
                float(np.log(max(received, 1e-12) / entry)))
            self.trades.append((seller, q, int(bought_at), int(self._round),
                                entry, received, ref))
            self.cycles[seller] += 1

    def _post_round(self, t: int) -> None:
        if self.rules.off:
            return super()._post_round(t)
        self._wage_index()
        before = self._total()
        self._round = t
        self._apply_levy()
        if self.a3.asset.closed:
            self._release_levy()
            super()._post_round(t)
            return
        self._public_round()
        self._release_levy()
        self._build()
        self._contribute()
        self._service_loans()
        super()._post_round(t)
        after = self._total()
        if abs(after - before) > TOL * max(1.0, abs(before)):
            raise AssertionError(
                f"A47 stock-flow inconsistency at round {t}: {before!r} -> {after!r}")
        self.pool_history.append(self.pool)
        self.exited_history.append(self.exited)
        if self.rules.treasury_backing:
            self.pool_min = min(self.pool_min, self.pool)
            if self.pool < 0.0 and self._treasury_cap > 0.0:
                ratio = -self.pool / self._treasury_cap
                self.pool_min_over_cap = max(self.pool_min_over_cap or 0.0, ratio)
        self.cost_price_history.append(self.cost_price())
        if self.rules.core_premium:
            q = self._core_q
            hh = float(self.units[:, q].sum())
            total = hh + float(self.landlord_units[q])
            self.core_household_history.append(hh / total if total > 0 else float("nan"))
            in_core = self.tenancy == q
            self.core_tenant_history.append(
                (int(in_core.sum()), int((in_core & self._is_production).sum())))

    def net_worth(self) -> np.ndarray:
        nw = self._net_worth_before_debt()
        if self._pf():
            nw = nw + self.account
        if self.rules.commit_loan and not self.a3.asset.closed:
            nw = nw - self.debt
            if self.rules.loan_lender == "bank":
                nw = nw + float(self.debt.sum()) * self._prior_owner_weights()
        return nw

    def _net_worth_before_debt(self) -> np.ndarray:
        if not self.rules.residence_bound or self.a3.asset.closed:
            return super().net_worth()
        marks = self.cost_price() if self.rules.liquidation == "cost" else self.price
        nw = self.holdings + self.units @ marks
        if self.rules.landlord == "listed":
            nw = nw + float(self.landlord_units @ marks) * self._prior_owner_weights()
        return nw


def run_a47_model(config: A47Config) -> A47Model:
    model = A47Model(config)
    model.run()
    return model
