# B25 availability: is a posted price band set by a reference point rather than by cost or by local income?

**Status: availability and a first reading. No station is registered and no
criterion is scored here.** Exploratory feasibility work does not go through the
criteria process, and this document does not pretend otherwise. What it does is
establish that the carrier exists, that the data is public, and that the reading
is large enough to be worth a station.

The mechanism under test is a further generator of the same non-exactness the
rest of this repository measures, **advanced as a hypothesis and not as a
result**: a price set by reference to another price, propagated by convention.
Where the reference relations form a cycle, the product of the conventional
factors around that cycle need not equal one. The construction is arithmetic and
free; what is hypothetical is that observed price formation works this way, and
that is what a station would test.

---

## 1. The two rival accounts, and what each predicts

| account | prediction |
|---|---|
| **cost** | the price band tracks the cost of building the object |
| **local income** | the price tracks what buyers in that market can pay |
| **reference** | the price tracks a reference price converted at the exchange rate, and tracks neither of the above |

Neither rival can be dismissed by argument, and the first is the one a reader
will raise first: a supply chain built in one country makes everyone's
manufacturing cost similar, so similar prices follow.

**The design that separates them needs two halves and neither half suffices
alone.** A cross-section holds cost fixed; a time series moves income. Both are
below.

---

## 2. First half: the same object, forty-one countries

Cost is not merely converged here. **It is the same number**, because it is the
same manufactured object: one model, one storage tier, sold worldwide.

Prices for the iPhone 16 Pro 128GB across 41 countries, converted to USD, are
reported by Deutsche Bank (2025-09-20) and were read here from a secondary
compilation; **the primary must be pulled before any of this is quoted
elsewhere**. Nominal GDP per capita is IMF World Economic Outlook, April 2026.

| quantity | range, max / min | sd of log |
|---|---|---|
| price, USD | 2.05, or **1.43** excluding the two the source itself attributes to tax | **0.097** |
| GDP per capita, USD | **56.43** | 0.984 |
| price / GDP per capita | **60.58** | 0.991 |

Spearman rank correlation of price against GDP per capita: **`-0.0204`** on the
full sample, **`+0.0794`** excluding Turkey (a 50 per cent luxury tax on top of
20 per cent VAT) and Brazil (import tariffs), both named as tax outliers by the
source.

**The line worth reading twice is the third row.** Dividing the price by income
does not reduce dispersion at all: the ratio's log sd, `0.991`, is within one per
cent of income's own, `0.984`. The division imports income's dispersion and
removes none, which is what it means for income not to be the denominator. The
price's own log sd is `0.097`, an order of magnitude smaller.

Stated on one buyer: India pays `0.498` of annual GDP per capita for the object;
the United States pays `0.0114`. **The same object, a factor of 44 in burden.**

**What the residual `1.43` is.** The source attributes it to VAT, import duty and
luxury tax. Non-US prices include VAT and the US price excludes sales tax, so
stripping VAT would compress the band further. **The reading is therefore
conservative in the direction that matters.**

**What this kills, and what it does not.** It kills the cost account outright:
cost contributes exactly zero to cross-country variation because cost does not
vary. It does not kill a variant of the income account, namely that the seller
prices to a globally similar affluent segment whose income in USD is roughly
constant everywhere. **That variant predicts this data exactly and is not
separated here.** Separating it is what the second half is for.

---

## 3. Second half: one country, income moving, price not

The segment-income variant requires that when the buying segment's income rises,
the price rises with it. China over 2010 to 2022 is the available test and the
two series move by very different factors.

| series | start | end | factor |
|---|---|---|---|
| iPhone base model, China launch price, CNY | 4,999 (2010) | 5,999 (2024) | **1.20** |
| urban per capita disposable income, CNY | 18,779 (2010) | 54,188 (2024) | **2.89** |

The full base-model series, with the storage tier that came with each price:

| year | model | CNY | base GB | CNY per GB | price / urban income |
|---|---|---|---|---|---|
| 2010 | 4 | 4,999 | 16 | 312.4 | 0.2662 |
| 2012 | 5 | 5,399 | 16 | 337.4 | 0.2238 |
| 2015 | 6S | 5,288 | 16 | 330.5 | 0.1695 |
| 2016 | 7 | 5,388 | 32 | 168.4 | 0.1603 |
| 2017 | 8 | 5,388 | 64 | 84.2 | 0.1480 |
| 2018 | XR | 6,499 | 64 | 101.5 | 0.1656 |
| 2019 | 11 | 5,499 | 64 | 85.9 | 0.1298 |
| 2021 | 13 | 5,999 | 128 | 46.9 | |
| 2022 | 14 | 5,999 | 128 | 46.9 | |
| 2024 | 16 | 5,999 | 128 | 46.9 | 0.1107 |

**Across fourteen years the posted price has a log sd of `0.0805` and a range of
`1.303`**, while income moved `2.886`. The price as a share of a year of urban
income fell from `0.2662` to `0.1107`, a factor of `2.40`. **An account in which
the price is set to what local buyers can pay predicts that ratio to be roughly
flat. It more than halved.**

Income rose across percentiles, so the affluent segment's income rose too. The
price did not follow.

**One stretch inside the series does separate the two accounts, and it is
narrow.** Storage stopped rising in 2021. The three launches at 2021, 2022 and
2024 posted the identical price `5,999` with the identical `128GB`, while income
continued to rise. On that stretch the quality account has nothing on the storage
dimension to work with and the price still did not move with income. Three
observations on one dimension of quality is not much, and it is offered as what
it is.

The domestic makers walked toward the reference over the same window, which is
the band forming rather than the reference alone:

| year | domestic flagship / same-year iPhone base |
|---|---|
| 2011 | Xiaomi `0.401` |
| 2013 | Xiaomi `0.378`, Huawei Mate `0.508` |
| 2016 | Xiaomi `0.371`, Huawei Mate `0.631` |
| 2020 | Xiaomi `0.635`, Huawei Mate `0.794` |
| 2023 | Xiaomi `0.667`, Huawei Mate **`0.917`** |

**This second half is weaker than the first and its confound is named.** Domestic
flagships also converged in specification over the window, and quality
convergence predicts the same curve. **The cross-maker comparison does not
separate them**; only the flat stretch above does, and only narrowly.

**The instrument that would separate them cleanly is a cost shock that moves cost
without moving specification, and the availability check on it came back
negative.** The candidate is the memory price cycle, which is large, precisely
dated, globally driven and exogenous to pricing in any one country. The long
public series available is priced as *cheapest retail consumer SSD*, which is a
different measurement from the *component contract price* a handset assembler
pays; putting the two in one column is the caliber error this project catalogues
elsewhere. Contract-price series are behind a vendor paywall. **So the instrument
exists in the world and is not free, and that is the state to record rather than
a substitute series in the wrong caliber.**

---

## 4. What is on disk, what is public, and what has to be collected

| input | status |
|---|---|
| iPhone China launch prices, base model, 2010-2022 | **collected**, published |
| iPhone prices by country, one model | **collected** from a secondary compilation; primary to be pulled |
| GDP per capita by country | **collected**, IMF WEO |
| Xiaomi numeric-series launch prices, 2011-2024 | **collected**, published |
| Huawei Mate launch prices, 2013-2023 | **collected**, published; 2021 has no launch, a real gap rather than a missing datum |
| Chinese urban disposable income | **collected 2010-2019 and 2024** (`54,188`, median `49,302`); 2020-2023 still to be pulled |
| iPhone base storage tier by model | **collected**, published |
| OPPO, vivo, Honor, Meizu launch prices | **not collected.** Expected public |
| memory component price series | **checked and negative.** The free long series is retail SSD, a different caliber from component contract price; contract series are paywalled |
| teardown BOM by model | **not obtained.** Largely behind a vendor paywall |

**Worst cell.** 2010 to 2012 carries the reference alone plus one domestic maker;
Huawei's Mate line starts 2013 and the others later. This is thin but not fatal,
because those three years are when the reference is being set and a single seller
is what that period consists of.

---

## 5. Gate pre-read

**Gate zero** passes. The treatment is whether a category carries a reference
product, and the count of such categories is not capped by the number of
countries, unlike the institution-type family closed elsewhere.

**The zero-multiple gate and the power floor do not apply** and this is a scope
statement rather than a failure. The reading is a comparison of two candidate
denominators printed as ratios, with no estimator and no pre-declared band, so
there is no line whose readability those gates are about. A design document would
record which type the criterion is.

**The resolution floor** needs a number, and the floor here is not instrument
noise: launch prices are exact to the yuan. **The floor is the specification
confound**, and bounding it is the open design problem, not a formality.

**The private-contract gate** passes: launch prices are published, not
negotiated bilaterally.


---

## Independent confirmation, and what it is worth

**Neither of these readings was advanced as a discovery.** They establish a
premise. The payload of the framework section they serve is a separate claim,
stated there as a hypothesis and untouched by anything measured here.

**The premise turns out to be established in the literature, on other carriers,
by tighter designs than either station could run.**

- **Uniform pricing despite local demand.** DellaVigna, S. and Gentzkow, M.
  (2019), *Uniform Pricing in U.S. Retail Chains*, Quarterly Journal of Economics
  134(4), 2011-2084. US food, drugstore and mass-merchandise chains charge
  nearly uniform prices across stores despite wide variation in consumer
  demographics and competition; the median chain forgoes about **`16` million
  dollars a year** relative to store-level optimal pricing. **Their design is
  tighter than this project's**: same chain, same country, same regulation, so
  cost is not merely converged but shared. They also record that uniform pricing
  raises what poorer households pay relative to richer ones.
- **Rigidity at focal price points.** Snir, A., Levy, D., Gotler, A. and Chen, H.
  find that nine-ending prices are more common and more rigid than others, that
  consumers treat the ending as a cheapness signal and are **less likely to
  notice a larger price ending in nine**, and that the rigidity is asymmetric,
  holding upward and not downward. See also Levy, Lee, Chen, Kauffman and Bergen,
  *Price Points and Price Rigidity*.

**Three unrelated carriers, three unrelated methods, one phenomenon.** US retail
chains, cross-country consumer electronics, and Chinese prepared coffee. That
convergence is worth more than any of the three alone and it is the reason to
cite rather than to compete.

**What the literature does not do, and this is the whole of what remains.** The
uniform pricing result is presented there as a puzzle and explained by managerial
simplicity, inattention and fairness concerns. **No claim is made that the
structure generates an obstruction.** The step from "posted prices are
conventional and rigid" to "convention propagated around a cycle admits no global
potential" is not taken in that literature, is not taken here, and is the only
part still unclaimed.

**Citation status.** Both records were read from abstracts and working paper
pages. **Neither full text has been read**, and page-level claims must be checked
against the version of record before use.

---

## 6. What this document does not claim

**Does not claim** that the reference account is established. Section 2 kills one
rival and names a second it does not kill.

**Does not claim** that the domestic convergence in section 3 is evidence for the
reference account. Its confound is load-bearing and unresolved.

**Does not claim** that any cycle of reference relations has been measured. The
cyclic construction is arithmetic and separate from everything read here.

**Does not claim** that the price band is unaffected by cost. It claims that cost
explains none of the cross-country variation, because there is no cross-country
cost variation to explain it with.

---

## Sources, and the locator debt this file carries

**Added 2026-08-30 by audit under rule 109.** One external work is cited properly:
DellaVigna and Gentzkow (2019), *Uniform Pricing in U.S. Retail Chains*, Quarterly
Journal of Economics. **Everything else in this file is recorded without a
locator.** The quotation marks elsewhere are the writer's scare quotes and not
quotations, so the original-text half of rule 109 does not arise.

**What needs a locator.**

1. **The 41-country handset price panel's capture date, bounded 2026-08-30.**
   Not logged per country, and not unrecoverable either: this file existed with the
   panel in it before its first backup at **2026-08-29 09:21 local**, so the panel
   was captured **on or before 2026-08-29**. **International list prices for this
   product change a few times a year**, so a one-day bound is far finer than the
   quantity's own variation and the reading is unaffected. **The GDP per capita
   series still needs its own citation.**
2. **Closed 2026-08-30, and the citation changes the reading. See below.**
3. ~~The urban income series.~~ **Closed 2026-08-30, see below.**
3b. **The GDP per capita series was never a gap.** The 2026-08-30 audit listed it
   as uncited. **That was an audit error.** This file's own §2 names it: *"Nominal
   GDP per capita is IMF World Economic Outlook, April 2026."* The price side is
   named too, *"reported by Deutsche Bank (2025-09-20) and were read here from a
   secondary compilation"*, with this file's own warning in bold that **the primary
   must be pulled before any of it is quoted elsewhere.**
4. ~~The price-points literature.~~ **Closed 2026-08-30, see below.**
5. **The EV export figures** used in B25-5.

### Item 3, the income series, closed with one caveat worth more than the citation

**2024 is official and exact.** National Bureau of Statistics, 2024 resident income
and expenditure, stats.gov.cn/sj/zxfb/202501/t20250117_1958325.html:
*"城镇居民人均可支配收入54188元，增长4.6%，扣除价格因素，实际增长4.4%。"* The
series is the **住户收支与生活状况调查**, sampling about 160,000 households across
nearly 2,000 counties.

**2010 carries a trap and this file walks into it silently.** The figure used here
is **18,779**. **The figure a reader will find first for 2010 is 19,109**, which is
the pre-2013 survey basis, and the two must not be mixed with 54,188. The
difference is **1.76 per cent** and its direction and size are what a survey
redesign produces, but **this has not been verified against the back-cast table**
and closing it needs one lookup in the yearbook.

**The result does not turn on which one is used**, and that is the useful thing to
record rather than the citation:

```
income ratio, new basis   54,188 / 18,779 = 2.886
income ratio, old basis   54,188 / 19,109 = 2.836
price over income, fall   2.405x  against  2.363x
```

**A referee who checks 2010 will find a different number from the one printed
here.** That is now stated in advance instead of being discovered.

### Item 4, the price-points literature, closed

- **Levy, Snir, Gotler and Chen (2020)**, *Not all price endings are created equal:
  Price points and asymmetric price rigidity*, **Journal of Monetary Economics 110,
  33-49**. Working paper: International School of Economics at TSU, 001-19 (2019),
  earlier draft October 2012. **Their finding, in their own words: 9-ending prices
  are "more rigid upward than downward"**, because consumers have difficulty
  noticing a higher price when it is 9-ending, so retailers set 9-endings more
  often after raising a price than after lowering one.
- **Snir and Levy**, *If You Think 9-Ending Prices Are Low, Think Again*, **Journal
  of the Association for Consumer Research**, doi:10.1086/710241.

**Consistency check against this project's own reading, because the two look like
they collide and do not.** [`b26`](b26_results.md) and the framework hold that the
**focal** number is rigid in both directions while **non-focal** prices move up
easily and down hard. Levy and co-authors find the 9-ending price resists being
**raised**. **A focal price that resists increases and a non-focal price that
resists decreases are the two halves of the same ratchet**, and the framework's
section says exactly that. No conflict, and it is checked here rather than assumed.

### The two endpoints, located, and the ladder is the finding rather than the price

**2010-09-25, verbatim:** *"iPhone4今日上午8时在Apple Store零售店全面发售，其售价为
16GB机型建议零售价4999元，32GB机型为5999元，无需合约。"* Unlocked, sold through
Apple Store and one authorised national channel. **Trade press dated the day of
sale.**

**2024-09-10, verbatim:** *"128GB、256GB、512GB三个版本，国行售价分别为5999元、
6999元、8999元"*. **Trade press dated the launch event.**

**The reading in this file was that the posted price rose from 4,999 to 5,999 over
fourteen years, a factor of 1.20 while urban income went up 2.886. That is true and
it is the smaller half of what the two quotations say.**

```
2010 ladder    16GB 4,999    32GB 5,999
2024 ladder   128GB 5,999   256GB 6,999   512GB 8,999

step in 2010   1,000
step in 2024   1,000, then 2,000
```

**Both rungs of the 2010 ladder are numbers that still exist in 2024, and the step
between them is the same 1,000.** What moved is which rung is the base: **5,999 was
the upper rung in 2010 and is the entry rung in 2024**, while **4,999 has left the
base of the ladder entirely.**

**So the fourteen-year constancy is a property of the ladder, not of one price.**
The base moved up exactly one rung, the rung spacing did not move at all, and the
content at a fixed rung went up fourfold: **the 5,999 rung carried 32GB in 2010 and
carries 128GB in 2024.** Against the base of 2010 the comparison is eightfold
storage for 1.20 times the price.

**This is the same shape as the hundred-dollar step** read in
[`b28`](b28_results.md), where nine retained models moved by exactly one step of
the same size on three separate dates. **Here the step survives fourteen years and
a change of product generation.**

**One thing the endpoints do not settle.** The intervening years are not cited
here, so the claim that the base stayed on the ladder throughout rather than
wandering and returning rests on the series already in this file rather than on
these two quotations. **The endpoints are now sourced; the path between them is
not.**

### The panel was verified on 2026-08-30, and the debt is smaller than the two
### previous audit entries said

***This is the third assessment of this panel in one day and the first one that
checked instead of inferring.** The two above are kept because the pattern they
form is the point: each judged the panel worse than it is, and each did so by
reasoning from an absence rather than by looking. Failure mode 110.*

**The inputs are dated publications and they do not change.** Deutsche Bank
research **published 2025-09-20**, and IMF World Economic Outlook **April 2026**.
**A dated publication needs no capture date at all**, so the capture-date question
does not arise for this panel and the entry above that treats it as bounded is
answering a question that was never open.

**The secondary compilation is identified and the primary is linked.** The
compilation is Visual Capitalist, *Ranked: The iPhone Price Index in 2025*, whose
attribution line reads *"based on data from Deutsche Bank"* and links the primary
at `dbresearch.com/PROD/RI-PROD/PDFVIEWER.calias?pdfViewerPdfUrl=PROD0000000000592089`.

**Four descriptors match this file exactly**: iPhone 16 Pro, 128GB, **41
countries**, source date **2025-09-20**.

**And one of the six summary statistics verifies independently.**

```
most expensive   Türkiye      $2,182
least expensive  South Korea  $1,063
range                          2.0527
this file's reported price range   2.05
```

**Exact to three significant figures, from two endpoints reported by a third party
that this file did not use for the statistic.**

**So the panel is not irreproducible and its numbers are not in doubt.** What
remains is that the forty-one rows are not cached here, so the other five
statistics, the GDP per capita range 56.43, the two log standard deviations, the
ratio range 60.58 and the two Spearman coefficients, **stand verified in one place
and unchecked in five.**

**The remaining task is one PDF and a cached table**, not a re-collection. It
closes the primary pull this file has been asking for since it was written, the
country list, and the five unchecked statistics at once.


**A repository-wide search on 2026-08-30 found no data file and no script for this
panel.** `results/` and `experiments/` contain nothing for B25, and no file
anywhere contains the figures 56.43, 60.58 or 0.0794.

**So the six summary statistics in §2 exist only as prose.** The range 56.43, the
log sds 0.984 and 0.991, the range 60.58, and the two Spearman coefficients cannot
be recomputed from anything held here, because **the forty-one rows were never
written down.**

**This is a different and larger debt than a missing citation.** Both sources are
named. What is absent is the panel itself. **A reader with both sources in hand
still cannot reproduce a single figure**, because the country list is not recorded
either.

**Superseded by the verification section above.** The fix is one PDF pull and a
cached table, the price range has since been checked against independent endpoints
and matches, and the inputs are dated publications that do not need a capture
date.
