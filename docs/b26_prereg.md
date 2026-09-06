# B26 preregistration: one headline number against every margin around it

**The hypothesis is out of sample.** It was written from a micro argument about
posted prices before any of this carrier's data was pulled, and is recorded in
the project's framework document. The readings collected so far are in
[`b26_focal_price_availability.md`](b26_focal_price_availability.md).

**This file replaces an earlier design that could not be run.** That design
contrasted focal against non-focal prices across a menu, and the availability
work established that no unified menu state exists to classify: the offer's terms
vary by store, by period and by customer, and are set automatically. **The
criterion below therefore reads the headline number and the margins around it,
and never needs a menu.**

**B-track rules apply**: fixed before the run, added to but not rewritten after.

---

## 1. Criteria

Four arms. No arm draws a line on an estimator. Each has three states.

**B26-1  the headline scalar.** Count the changes to the announced focal number
over the window, from its national launch to the end of the cost shock.

- the number changes → **the hypothesis fails on this carrier**
- the number is unchanged and the offer remains in force → the number is rigid
- **the number is unchanged while its scope is emptied or the offer withdrawn** →
  rigid in the number, abandoned in substance

The third state is not a fallback. It is a distinct prediction of the hypothesis
and must be reported as itself rather than merged into either neighbour.

**B26-2  the margin count.** The offer has four fields, and **they are the
seller's own, not the analyst's**: the price, the eligible drinks, the
participating stores, and the frequency. That enumeration is taken from the
seller's own statement of what it may adjust, and fixing it here is what keeps
this criterion from choosing its own answer.

Count how many of the four moved over the window while the price field did not.

- three or four moved → adjustment happened behind the number
- one or none moved → the whole offer was rigid and this reading says nothing
  about the price field specifically
- two → undecided, reported as undecided

**B26-3  the shock is large enough to have forced something.** Compute the unit
cost increase as the bean price move times the raw material share of unit cost,
both from published figures.

- unit cost rises by more than `20` per cent → a cost-passthrough account
  predicts the price field moves, and its not moving is a reading
- less than `10` per cent → the shock is too small to force anything and **the
  station reads nothing, whatever the other arms say**
- between → the station reports the number and does not resolve

**B26-4  positive control.** Count posted prices at this seller, outside the
focal offer, observed to have moved in the same window.

- two or more moved → the seller's price system is not globally rigid, so
  rigidity at the focal number is a property of that number
- none moved → **no power, and the other arms are void**

**Placement.** Against a cost-passthrough account, B26-1 combined with B26-3 is
**distinguishing**. Against an account in which all posted prices are sticky in
the short run, B26-4 is what separates them, and if B26-4 fails the station has
not beaten that opponent. B26-2's four-field count is **a quantity no competing
account has a reason to assemble**.

---

## 2. Gate arithmetic

**Type of criterion: counts and an exhaustive outcome mapping, with no estimator
and no pre-declared band.** The zero-multiple gate and the power floor therefore
do not apply, which is scope and not failure.

| gate | number |
|---|---|
| cost shocks in the window | **one.** Identification is within-shock across margins, not across shocks. Any claim about the shock's own effect inherits that and must not be made |
| margins available to count | **four**, fixed in §1 from the seller's own statement |
| resolution floor | the headline number is announced and exact. **The floor is whether a margin moved at all**, which is a yes or no from dated public statements, not an estimate |
| private bilateral contract | passes. The offer is publicly announced |
| sources checked | six classes, enumerated in the availability file. Four carry something |

---

## 3. Reachability

**Every state in §1 is reachable and this must be true or the station is worth
nothing.** The price field changing was available: a competitor ran the same kind
of offer at a different number in the same market and period, so a change of
number was an ordinary move and not a forbidden one. The margins not moving was
available: they could have been held and the number cut instead. The control
failing was available: had no posted price at this seller moved, that outcome
would be observed and would void the station.

**What is not reachable, and is excluded here.** Any statement about which
individual menu items sat at the focal number on a given date. No unified menu
state exists to be read, and the earlier design that required one is superseded
rather than postponed.

---

## 4. Carrier and caliber

One seller, one market, one product category, over the window from the offer's
national launch through the commodity shock. Cost from exchange-traded futures.
Unit cost composition from a published decomposition for a comparable operator in
the same market, **which is a different firm and is used only for the raw
material share, not for a level**. Realized average price per cup from cups
disclosed on earnings calls against net revenue from the corresponding release.
Margin movements from dated public statements by the seller and its staff, which
are the weakest caliber used here and are labelled as such wherever they carry a
count.
