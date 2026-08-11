# A3b: the opening construction as an axis, not a convenience

Pre-registration. **Written before any code for it exists.** Everything below is
fixed here; §5 is the parameter table and nothing outside it is free.

This document exists because A3's opening allocation was discovered to be one
arbitrary choice out of several that real economies actually ran, and the choice
was silently carrying results. It is not a correction of a bug — though it fixes
one — it is the promotion of a hidden constant to a registered axis.

---

## 1. What was wrong

Three findings, in ascending order of depth.

**One, units could be ownerless.** `_allocate_initial` sells an opening stock
that belongs to nobody: the proceeds are split equally across all nodes and any
unit that does not sell is held by no node at all. Thirty-nine of a hundred
units ended in that state. They never re-enter the market, because `_offers`
iterates over `units > 0`; they never collect rent, because `_collect_rent` pays
holders. **A dwelling that nobody owns does not exist in any economy.** The
residual is not dead inventory, it is stock still held by whoever held it
before.

**Two, the equal split of proceeds is a counterfactual.** It was recorded as the
neutral choice — pro-rata would let the opening transaction itself concentrate
claims. But the seller of a dwelling is its previous owner, and previous owners
are not uniformly distributed. Splitting equally performs one perfectly
egalitarian redistribution at `t = 0` and then measures how a gap opens from
there. Neutral in the code is not neutral in the model.

**Three, and this is the axis: allocation by claims ranking is one construction
of several, and it is the one least like how housing stock is actually
distributed at the start.** §3 sets out the alternatives with sources.

---

## 2. Supply comes first, because it dominates the other two

The registered supply is `(60, 30, 10)` units against `200` nodes: **0.5
dwellings per node**. Half the population is structurally without a dwelling
before any mechanism runs, so "the production layer holds nothing" is partly a
statement about this number rather than about access.

Both large marketised economies sit in the same narrow place:

| | dwellings per household | source year |
|---|---|---|
| United States | 146.7M units / 132.7M households = **1.11** | 2024 |
| Urban China | 套户比 **1.09** (0.8 in 1978) | 2020 |

**Registered: `units_per_node = 1.1`**, tier shape unchanged at `6 : 3 : 1`, so
`units = (132, 66, 22)`. One number changes, not four. The tier ratio is left
alone precisely so that the supply change and any tier-structure change cannot
be confounded later.

The surplus over one per node is vacancy and multiple holding, which is what the
`1.1` is: US vacancy runs about `10.3%` of inventory.

---

## 3. The axis: how strongly does opening ownership track opening claims

The three constructions below are not three unrelated modes. They are three
sourced points on one axis — **the correlation between who owns at `t = 0` and
who has claims at `t = 0`** — and that is the only thing that differs between
them. Stating it as one axis rather than three modes is what makes the
comparison a test rather than a menu.

### 3.1 `occupancy` — ownership assigned by residence

The stock is held by the state, the work unit or the municipality, and is
transferred to **sitting tenants**, ranked by occupancy and tenure rather than
by means.

- **China, 1998.** The State Council ended in-kind allocation of housing;
  public housing was sold to its existing occupants at deep discounts. By 2019
  about **70%** of urban residents lived in owner-occupied housing, about 20%
  rented.
- **Russia, 1992.** Transfer to sitting tenants, effectively free. Individual
  ownership of the stock went from **26.4% in 1990 to 58.2% by 2000**.
- **United Kingdom, 1980.** Right to Buy sold **1.9 million** council homes in
  England to their tenants at an average discount of **44%** (33% at three
  years' tenure rising to 50% at twenty), raising owner-occupation by roughly
  15 percentage points.

**In the model**: ownership at `t = 0` is uncorrelated with claims within the
production layer. A registered share of nodes each receive one unit by draw
rather than by rank; the stock above one per node goes to the financial layer.

### 3.2 `continuous` — no opening event, ownership already tracks wealth

The United States never ran an opening allocation. The stock has always had
owners and the ownership rate moves through flows: **43.6% in 1940, 61.9% in
1960, a peak of 69.2% in 2004, a trough of 63.4% in 2016, about 65.3% now.** The
1940–1960 climb was produced by FHA, VA and the GI Bill — **access opened by
policy, not price falling** — which is the same object as the source
manuscript's Volume I §15 reading of the New Deal as punching through the
thermocline.

**In the model**: ownership at `t = 0` rises with claims but does not follow the
ranking strictly. Ordinary nodes own; the financial layer owns more.

### 3.3 `auction` — allocation by claims ranking

What the code does today: highest tier first, richest first. This is retained,
both so existing runs stay comparable and because it is not fictional — it is
what the **primary sale of new supply** and the **institutional purchase of
distressed stock after a crisis** look like. It is simply not what the
distribution of an existing stock looks like at the start.

### 3.4 The ownership rate is not the axis

`occupancy` at ~70% and `continuous` at ~65% are close. **The rate is not what
distinguishes them** and no result may be attributed to it. What distinguishes
them is *who* the owners are at the same rate: assigned by residence, or sorted
by claims. Any criterion below that could be satisfied by moving the rate alone
is mis-specified.

**A definitional trap, recorded so it is not walked into.** Chinese sources give
an urban "住房拥有率" of **96%**, but that counts a household as owning if it
owns housing *anywhere*, including a parent's dwelling in another city. The
occupancy-relevant number is the ~70% who live in owner-occupied housing. Using
96% would import a definitional artefact as a fact.

---

## 4. What the grid is for

Two axes, crossed:

- **Construction**: `occupancy`, `continuous`, `auction`.
- **Flow mechanism**: rent on/off, turnover exogenous/endogenous, price live/frozen.

The question is not which construction is right. It is:

> **Which results survive a change of construction?**

Those are properties of the flow topology. The rest were properties of the
opening. This is the source manuscript's own second correspondence standard —
拓展性, that the meta-level survives a change of parameters — made executable
for the first time in this repository, rather than asserted.

The one result currently waiting on this is the **one-way exit**: under the
present calibration 21 production-layer nodes hold a unit at the opening and
none holds one by round 100, and none ever returns. Under `auction` that is a
marginal population created by the soft threshold. Under `occupancy` the
production layer starts as the **majority** of owners, so the same measurement
becomes the thing the source manuscript actually claims — not that ordinary
people can never get in, but that **they got in and it was taken back** — and it
acquires a calibration target that exists in the world: the US ownership rate
falling 69.2% → 65.3%, and Chinese urban ownership concentrating into fewer
households at an unchanged stock.

**If the one-way exit appears under all three constructions**, it is the flow.
**If it appears only under `auction`**, the result reported so far was the
opening allocation talking, and that will be recorded as such.

---

## 5. Registered parameters

| name | value | fixed by |
|---|---|---|
| `units_per_node` | `1.1` | US 1.11, urban China 1.09 |
| tier shape | `6 : 3 : 1` unchanged | not a free parameter here |
| `construction` | `occupancy` \| `continuous` \| `auction` | §3 |
| `ownership_rate` under `occupancy` | `0.70` | China, share living in owner-occupied urban housing |
| `ownership_rate` under `continuous` | `0.653` | US 2024 |
| `ownership_rate` under `auction` | outcome, not a parameter | — |
| opening discount under `occupancy` | `0.44` | UK Right to Buy average |
| residual stock | held by the prior owner set, never ownerless | §1 |
| sale proceeds | to the seller, in proportion to units sold | §1 |
| new construction | **none**. Supply is fixed | user's ruling: short-run flow is small against the stock outside an infrastructure boom |

`construction = auction`, `ownership_rate` ignored, residual-ownership off and
equal-split proceeds on must reproduce the current results **bitwise**. A
generalisation that cannot recover its own special case is not a
generalisation — the same discipline as `elasticity = 0`.

---

## 6. What this does to A3's existing criteria

- **A3-1** unaffected. The channel closed means no asset, so no construction.
- **A3-2** *not* redefined, but **re-based**. The entry pair still compares
  either side of a boundary; under `occupancy` the boundary is between those who
  keep a unit and those who lose one, because it is not the case that everyone
  owns — about 30% do not, at the registered rate, and that is the point.
- **A3-4** expected to be **unaffected**, and this is a free robustness test.
  The holonomy is `log(γ_b/γ_a)`, which contains no initial condition at all. If
  A3-4's agreement moves when the construction changes, something is wrong that
  the current runs cannot see.
- **A3-5** stays failed and stays diagnosed in `a3_asset_channel.md` §9.14. The
  construction does not repair it; `open_tiers` not reaching resale is separate.
- **A3-6** expected to move a lot, because it asks whether a stock survives and
  under `occupancy` most nodes have one.

---

## 7. Known limits, stated before any result

**The model cannot capture what actually differs between these economies.**
Chinese households' preference for housing as the savings vehicle, the political
economy of land finance, the difference between a discount granted to a sitting
tenant and one granted to a voter — none of that is in here and none of it will
be inferred from these runs. What is being compared is the **shape of the
opening topology** and nothing else. The three constructions are an inspiration
drawn from history, not a claim to model those histories.

**Any finding that depends on the ownership rate rather than on the
correlation** is a finding about §3.4's non-axis and is void.

---

## 8. Tier-differential appreciation: measured, already present, not added

Raised as a question rather than a request: a good dwelling appreciates even
sitting idle, a poor one may not, in a growth era everything rises, and a rise
slower than the price level is a fall. Does that belong in the simulation?

**No, and the reason is that it is already there, endogenously.** Measured at
the registered parameters, seed 0, three hundred rounds:

| round | low | mid | high | total claim stock |
|---|---|---|---|---|
| 50 | 20.9× | 25.3× | 33.1× | 18.1× |
| 100 | 40.4× | 49.1× | 64.3× | 35.1× |
| 299 | 120.1× | 146.0× | **191.1×** | 104.3× |

Nothing in the code says a high tier appreciates faster. `price_at` marks each
tier from its own bidder pool, `P_q(t)/P_q(0) = (pool_q(t)/pool_q(0))^η`, and a
high tier's pool is the rich, whose claims grow fastest. Quality-differential
appreciation is a consequence of the gate plus issuance, not an input.

**"A rise slower than the price level is a fall" has an in-model form that is
not a deflator.** There is no consumption price level here and inventing a
conversion rate is the operation `PROJECT_PLAN.md` §11.7 prohibits. But the
total claim stock is a second quantity the model already carries, so the ratio
of one to the other invents nothing:

| round | low | mid | high |
|---|---|---|---|
| 50 | 1.1514 | 1.3975 | 1.8244 |
| 100 | 1.1513 | 1.3988 | 1.8313 |
| 200 | 1.1514 | 1.3989 | 1.8315 |
| 299 | 1.1514 | 1.3989 | **1.8315** |

**Not a digit moves after round 50.** The tier spread is a **one-off
repricing**, not a per-period wedge: in real terms all three tiers then grow at
the rate of the claim stock and none outruns another. This is the distinction
A3-7 was registered to enforce, showing up on the price side rather than the
net-worth side.

**Why it is nonetheless irrelevant to what A3 tests.** The loop sum is
`log(γ_b/γ_a)` and **the price cancels out of it entirely** (`a3_asset_channel.md`
§2). Tier appreciation, one-off or compounding, does not enter A3-4. It acts on
`H⁰` — who can get in and who is pushed out — and A3's load-bearing criterion is
`H¹`.

**The growth era and the cycle stay out.** A general upward trend or a regime
switch is a parameter that takes values by epoch, and §13.4 forbids registering
those until `σ(t) = f(observable graph features)` exists with `f` fixed across
epochs. With epoch-varying parameters the model fits anything and the fourth
correspondence standard, predictive power, goes to zero.

Recorded with the numbers rather than as a decision, because a later session
will otherwise "discover" that tier appreciation is missing and add a rule for
something the model already produces.

---

## 9. Changelog

### 9.1 The occupancy transfer bypasses the gate, and walks tiers low to high

**Decided after seeing that the gate was filtering the transfer.** §3.1 as
registered left the acquisition gate in place for the drawn set, and a
registered `ownership_rate` of `0.70` then produced an opening ownership rate of
**53%**: the sitting tenants at the front of the queue were filtered by what
they could afford. That put means back into a mechanism whose entire content is
that means did not decide. Russia's transfer was free; the Chinese and British
ones were discounted precisely so that tenure rather than income decided.

The drawn set is now admitted regardless of claims and pays what it has. With
the bypass, the registered `0.70` produces **72.0%**, the excess being financial
-layer nodes that also buy in the market pass.

**Two consequences had to be handled together, and neither is decoration.**

*The transfer walks tiers low to high.* The market pass walks high first, and
with the bypass on that let a hundred and forty admitted nodes take the premium
stock before anyone else saw it. Transferred public housing was not premium
stock; the sitting tenants were living in ordinary dwellings.

*The transfer gives one unit per node.* "The dwelling you occupy" is one. The
uncapped rule belongs to the market pass, where accumulating more than one is
the thing the stage measures. Measured: 124 production-layer holders holding
exactly 124 units.

**This does not reintroduce means.** The tier follows the layer, not the claims,
and the layer is the source manuscript's own structure. §3.1 registers the arm
as uncorrelated with claims *within the production layer*, which is what it is.

### 9.2 First cross-construction result: the one-way exit is the flow

Seed 0, three hundred rounds, `units_per_node = 1.1`, residual owned, proceeds
to the seller. **Production-layer holders, of 180:**

| round | `auction` | `continuous` | `occupancy` |
|---|---|---|---|
| 1 | 21 | 21 | **124** |
| 25 | 10 | 10 | 46 |
| 50 | 3 | 3 | 19 |
| 100 | 0 | 0 | 3 |
| 200 | 0 | 0 | **0** |

Overall ownership rate, same runs: `auction` and `continuous` go `20.5% → 9.0%`;
`occupancy` goes **`72.0% → 9.5%`**.

**The exit survives every construction, and so does its endpoint.** Starting
ownership between 20% and 72% — the latter sitting on the historical anchors,
the US peak of 69.2% and post-Right-to-Buy Britain — and the terminal rate is
`9%` either way. The initial distribution sets how long the drain takes, not
where it ends. By §4's registered reading this makes the one-way exit a property
of the flow topology and not of the opening, which is the answer to the question
this document was written to ask.

The earlier worry that "21 in, 21 out" was an artefact of the soft threshold is
therefore dead: put 124 of 180 production-layer nodes in on day one, each owning
outright, and two hundred rounds later none of them owns anything and none has
returned.

### 9.3 The middle of the axis collapsed onto an endpoint

**`continuous` is bitwise identical to `auction` at this calibration**, in every
row above. The claims-weighted draw selects the rich, and the rich were already
at the front of the claims ranking, so the treatment has nothing to move.

**So the axis currently has two points, not three, and no run may be described
as "all three constructions tested".** Whether `continuous` can be made distinct
— by drawing on a flatter function of claims than proportionality, which is what
"ownership rises with wealth but does not follow the ranking" was meant to say —
is open and is not fixed here.

### 9.4 Not yet established

Every number in §9.2 is **one seed**. Nothing above may be reported until it is
run across seeds, which is `experiments/a3b_construction.py` and does not exist
yet.

---

## 10. Result at the registered run, and what may be said from it

Five seeds, three hundred rounds, `units_per_node = 1.1`, residual owned,
proceeds to the seller. Means across seeds. §9.4's "one seed only" restriction
is discharged by this section.

**Ownership rate — share of all nodes holding any unit**

| round | `auction` | `continuous` | `occupancy` | `auction`, pre-A3b |
|---|---|---|---|---|
| 1 | 21.3% | 21.3% | **72.0%** | 21.2% |
| 25 | 14.0% | 14.0% | 33.8% | 13.7% |
| 50 | 10.8% | 10.8% | 18.7% | 10.1% |
| 100 | 8.4% | 8.4% | 10.1% | 7.7% |
| 200 | 8.0% | 8.0% | 8.7% | 7.5% |
| 300 | **8.6%** | **8.6%** | **8.8%** | 7.6% |

**Production-layer holders, of 180**

| round | `auction` | `continuous` | `occupancy` |
|---|---|---|---|
| 1 | 22.6 | 22.6 | **124.0** |
| 25 | 8.6 | 8.6 | 49.2 |
| 50 | 2.4 | 2.4 | 19.4 |
| 100 | 0.0 | 0.0 | 2.4 |
| 200 | **0.0** | **0.0** | **0.0** |

Units are never created and never orphaned: worst discrepancy `0.0` across every
arm and seed. No arm reported a `DesignDeviation`.

### 10.1 One invariant, one variant, one collapse

**Invariant — the endpoint.** Opening ownership of 21.3% and of 72.0% both end
at **8.6% and 8.8%**, and the production layer reaches **zero** holders in every
arm. The opening distribution does not survive the flow.

**Variant — the duration.** `auction` empties the production layer by round 100;
`occupancy` takes twice as long, still holding 2.4 nodes at 100 and reaching zero
by 200. Starting broad buys time and nothing else.

By §4's registered reading, the one-way exit is therefore a property of the flow
topology rather than of the opening. The earlier concern that "21 in, 21 out"
was an artefact of the soft threshold is settled: put 124 of 180 production-layer
nodes in on day one, each owning outright, and two hundred rounds later none of
them owns anything and none has returned.

**Collapse — `continuous` is not a third point.** It is identical to `auction`
to the last digit on all three reported measures at all six checkpoints, though
terminal net worth differs. The two arms move claims around without moving who
holds anything, which for a stage about access is a collapse. **The axis has two
points and no run may be described as testing three constructions.** Whether a
genuine middle point exists — a draw on a flatter function of claims than
proportionality — is open and is not settled here.

### 10.2 Scope: the three constructions are an inspiration, not an analysis

**The three economies supplied the constructions. They are not what is being
studied.** The purpose of drawing on China 1998, Russia 1992, the UK 1980 and
the United States is to obtain opening topologies that are *actually different
from each other and actually occurred*, so that the invariance in §10.1 is a
robustness statement rather than a statement about one arbitrary starting point.

This model cannot analyse those economies and no sentence here should be read as
attempting it. It has two hundred nodes, one asset in three tiers, no land
finance, no mortgage market, no migration, no household formation, no policy
actor, and no representation of the difference between a discount granted to a
sitting tenant and one granted to a voter. Chinese households' preference for
housing as the savings vehicle — the single most cited driver of the outcome
there — is absent entirely. **The object of comparison is the shape of the
opening topology and nothing else.**

### 10.3 What may nonetheless be conjectured, and in what form

Given the scope statement, connecting the model's behaviour to the observed
ownership and concentration series is admissible as **conjecture about what to
look for**, not as explanation of what happened. Stated in the distinguishing
form `PROJECT_PLAN.md` §1.4 requires — what this mechanism predicts that a rival
does not:

**One. The observable is concentration, not the ownership rate.** In the model
the terminal state is reached by units moving to holders who already hold, and
the ownership *rate* is a lagging and compressible summary of that. An economy
in which the mechanism were operative could therefore hold its ownership rate
roughly flat while the same stock came to be held by fewer households. Urban
China is the case that discriminates: the stock per household has been
approximately unchanged at `1.09`, headline ownership has not fallen, and the
multiple-holding distribution has moved — 31.0% of urban households holding two
dwellings and 10.5% three or more as of 2019. A rival account in which
affordability alone drives outcomes predicts movement in the rate; this one
predicts movement in the distribution at an unchanged rate.

**Two. A broad start delays rather than prevents.** The model's `occupancy` arm
begins at 72% and converges to the same place as an arm beginning at 21%, taking
about twice as long. If that carried over, the prediction for post-transfer
economies is not that they avoid concentration but that their concentration
arrives later and from a higher base, and that the informative series is the
*rate of change* rather than the level. The US drift from 69.2% in 2004 to 65.3%
now, and the UK's post-Right-to-Buy trajectory, are the series this would be
tested against — **not confirmed by, tested against**, since neither has been
fitted here and neither could be with this model.

**Three. What opened access historically was not price.** The 1940–1960 US climb
from 43.6% to 61.9% came from FHA, VA and the GI Bill, and the 1980 and 1992 and
1998 transfers came from statute. In the model, nothing internal ever reverses
the drain; the arms differ only in where they start. That the model has no
mechanism capable of producing a *rise* in ownership, and that every historical
rise in these four economies came from outside the price system, is a
correspondence worth recording — and it is also exactly the kind of
correspondence that is cheap to over-read, since a model containing no policy
actor cannot fail to lack one.

### 10.4 The level does not transfer

Terminal ownership of `8.6%` is far below anything any of these economies has
exhibited. **What is claimed to transfer is the invariance and the direction,
not the level**, on the same footing as A6's `R* = 6%` being a comparison rather
than a tax rate. A reading of this section that quotes the terminal percentage
as a forecast has misread it.
