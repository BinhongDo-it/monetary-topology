# B25 preregistration: a posted price band against cost, against local income, and against a reference

**The hypothesis is out of sample.** It was written down from a micro argument
about one product category before any price series was pulled, and the readings
listed in [`b25_price_band_availability.md`](b25_price_band_availability.md) were
taken afterwards. That is what carries evidential weight here and it is stated
plainly.

What this file fixes is which of those readings the station is scored on, in what
form, and which branches it is not permitted to claim. **Criterion shape is not a
degree of freedom in this project and its timing is not disclosed**; what would
be disclosed, and is not the case here, is a reading having chosen which quantity
gets scored.

**B-track rules apply**: fixed before the run, added to but not rewritten
afterwards. A result that overturns one is recorded in the results file, not here.

---

## 1. Criteria

Four arms. **No arm draws a line on an estimator.** Each prints an object with a
reading rule fixed here, and each rule has three states.

**B25-1  cross-section, cost held identical.** One model, one storage tier,
every country the source covers. Print the price in USD, GDP per capita, their
ratio, and the rank correlation of price against income, with and without the
countries the source itself attributes to tax.

- `|rho| < 0.20` → the price does not track local income
- `rho > 0.40` → it does, and the reference account fails on this carrier
- otherwise → **undecided at this coverage**, report and do not resolve

**B25-2  time series, income moving.** One country, base model, launch price and
urban per capita disposable income by year. Print both, their ratio, and the log
sd of the price.

- price/income falls by more than `1.5` over the window → the price is not set to
  what local buyers can pay
- the ratio is flat within `1.2` → it is
- otherwise → undecided

**B25-3  the flat stretch.** Launches where the posted price and the base storage
tier are both unchanged while income rises. Print price, tier, income, count.

- three or more such launches with the price unchanged → the quality account has
  nothing on that dimension and does not explain the constancy
- fewer than three → **insufficient, and reported as insufficient rather than as
  a null**

**B25-4  the band forming.** Each domestic maker's flagship over the reference
price, same year. Print the ratio series per maker.

- every maker's ratio rises monotonically to within one reversal → the makers
  converge on the reference and the dispersion between classes falls
- any maker's ratio falls over the window → convergence is not general
- otherwise → undecided

**B25-5  the residual is edge cost, not income.** *(Added 2026-08-29. It reads
the dispersion B25-1 leaves behind, which B25-1 did not attempt, rather than
recutting B25-1.)* B25-1 finds the price uncorrelated with income and a residual
band of `1.43` after removing the two the source attributes to tax. **That
residual is the object here.** Regress or, preferably, tabulate the residual
against measurable costs of the arbitrage edge: import duty, value added tax,
shipping, warranty portability, and carrier or regional locking.

- the residual is accounted for by edge costs and the income term adds nothing →
  **price separation is sustained by the cost of the connecting edge**, which is a
  statement about connectivity rather than about willingness to pay
- edge costs account for none of it → the residual is unexplained and is reported
  as unexplained
- otherwise → undecided

**This arm is where the hypothesis stops being compatible with "prices are
arbitrary".** An arbitrary posted price would leave a residual unrelated to
anything. **The prediction is that it is related to one specific thing and not to
the obvious other one.**

**Primary carrier for this arm, and it is not the one the rest of the station
uses.** Vehicle exports from one country into a bloc that levies a published,
firm-specific import duty. **The edge cost is a posted number, it varies across
firms, and it changed discretely on a dated day.** Combined with the bloc's
standing tariff the total runs from `17.8` to `45.3` per cent depending on the
exporter.

**The identifying comparison is within one firm across two models**, where the
edge cost is not merely controlled but **identical by construction**: same
exporter, same duty rate, same route, same destination. Two models of one exporter
show destination-to-home price ratios of `2.267` and `1.584`, a difference of
`1.43`, **against an edge cost multiplier of at most `1.38` that is the same
number for both.**

- the ratio differs across models sharing one edge cost → **edge cost cannot be
  the whole account**, and what differs is the destination segment
- the ratios agree within the precision of the edge cost estimate → edge cost
  suffices and the reference reading fails on this carrier
- otherwise → undecided

**The competing account to name is margin recovery**, that the exporter prices
high abroad to recover margin lost in a price war at home. **The two-model
comparison separates it**: a margin target predicts a common markup, not two
markups differing by `1.43`, unless the target is set per segment, which is the
reference account restated.

**Caliber, and it is the weakest used anywhere in this station.** The price
figures are trade-press dollar conversions from one period. **They are to be
recomputed from both markets' own configurators on a matched specification before
any of this reaches a manuscript**, and the duty rates from the implementing
regulation rather than from a law firm summary.

**Not in scope for this arm, and recorded so it is not smuggled in.** Whether a
market entrant adopts the destination's price level rather than exporting its own
is a claim about how an anchor forms on entry. **That belongs to the framework's
hero-product section as a prediction and is not tested here**, because this arm
reads a residual and that claim reads a formation.

**Placement, fixed here so it is not chosen after the fact.** Against a
competitive account, which predicts a price equal to marginal cost plus a normal
margin and therefore near-constant across countries, B25-1 is a **shared
explanation and carries no distinction**. Against third-degree price
discrimination, which predicts pricing to local willingness to pay, B25-1 is
**distinguishing**, and that is the opponent to name. B25-4's falling
between-class dispersion is a **quantity no competing account has a reason to
compute**.

---

## 2. Gate arithmetic

**Type of criterion: exhaustive outcome mapping and sign, with no estimator and
no pre-declared band.** The zero-multiple gate and the power floor therefore **do
not apply, which is a scope statement and not a failure**. There is no line whose
readability those gates are about.

| gate | number |
|---|---|
| treatment values in the world | categories carrying a reference product; **not capped by the number of countries**, unlike the institution-type family closed elsewhere. Passes |
| independent cycles in the reference graph | **`b1 = 0`.** See §3 |
| resolution floor | **not instrument noise.** Launch prices are exact to the yuan and the price series' own log sd is `0.0805`. **The floor is the specification confound**, and B25-3 is the only arm that bounds it, on one dimension, with three observations |
| private bilateral contract | passes. Launch prices are published |

---

## 3. Reachability, and the branch this station may not claim

Every branch of §1 is reachable on the collected data except one, and that one is
excluded here rather than left to be discovered.

**The convention-holonomy branch is unreachable on this carrier, by construction
and not for want of data.** Non-zero holonomy requires a cycle in the graph of
reference relations. The structure here is every seller referring to one
reference product, which is a **star**; a star is a tree; its first Betti number
is zero; and with no independent cycle there is no loop for a holonomy to be
non-zero around. **No quantity of price data changes this.**

This is the same shape the A-track already met: a star-shaped position graph
gives `b1(G) = 0`, hence all obstruction is square, hence a channel's holonomy
share is predicted to be exactly zero. **The judgment there and here is the same
judgment.**

**Consequence, and it is the load-bearing sentence of this file.** The station
carries the claim that reference pricing manufactures homogeneity, which is the
degenerate locus, and B25-4 measures that homogeneity arriving. **It does not
carry the claim that pricing convention generates non-zero holonomy, and a
closing document must say so in those words.** "Not measured here because the
reference structure has no cycle" and "measured and found absent" are opposite
signals to the next reader: the first sends them to look for a carrier with a
cycle, the second sends them to retry this one.

**Forward gate for any station aimed at that claim: count the independent cycles
in the reference graph before anything else.** Reference relations are
hierarchical by default, every seller looking up at one leader, and that is a
star. A carrier where sellers refer to each other in a closed ring is the
requirement, and its scarcity is a property of how reference works rather than a
gap in the data.

---

## 4. Carrier and caliber

Posted launch prices, one product category, one reference product and the
domestic sellers priced against it, against two denominators: the reference price
converted at the spot exchange rate, and per capita disposable income. Non-US
prices include VAT and the US price excludes sales tax, which widens the observed
band and therefore makes the reading conservative. The cross-country figures were
read from a secondary compilation and **the primary is to be pulled before any
figure here is quoted outside this repository**.
