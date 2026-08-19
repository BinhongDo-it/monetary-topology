# B6-C availability: the Havana order book, and the two assumptions it can retire

**Written 2026-08-19.** This is an availability check and nothing else. No
criterion is registered here and no reading is computed. `PROJECT_PLAN.md`
§14.6 listed this source as a candidate on 2026-08-12 with the note that it
**ends 2025-02 and cannot reach B6's window**; §9 of `b6b_eltoque_prereg.md`
registered it as not contained in B6-B.

**Why a source that cannot reach the window is worth a check at all.** The four
things it can do are properties of the **instrument**, not statistics of the
window. An instrument property measured over 1,321 days outside the window is
evidence about the instrument inside it, subject to the instrument not having
changed, and that is checkable rather than assumed: elTOQUE's methodology page
dates its own revisions.

---

## 1. What it is

García Figal, Lage-Castellanos and Mulet, *Looking into informal currency
markets as Limit Order Books: impact of market makers*, arXiv `2503.03858`.
Repository: `github.com/lolfig/Looking-into-Informal-Currency-Markets-as-Limit-Order-Books`,
291 MB, 1,325 files, cloned and inspected 2026-08-19.

**It is not an independent referee and this document does not treat it as one.**
The orders are scraped from elTOQUE's own sources, so it is the same population
the TRMI is computed from. What it supplies is the **inside** of a statistic this
project can otherwise only see the outside of.

## 2. What is in the repository

| file | size | content |
|---|---|---|
| `data/analytics/all_orders.json` | 62 MB | `{date: [{sign, price, volume}]}` |
| `data/daily_info.pickle` | 80 MB | `{date: DailyInfo}`, the reconstructed book |
| `data/analytics/lob_data.pickle` | 100 MB | the book's state series |
| `data/messages/YYYY-MM-DD.parquet` | 1,321 files | the raw scraped messages |

`DailyInfo` is a plain dataclass and so is `Order`. Neither defines `__reduce__`
and neither has a side effect, so **unpickling executes nothing beyond two
dataclass definitions from the cloned repository**, which was checked by reading
`services/limit_order_book/tools/types.py` before anything was loaded.

`DailyInfo` carries, per day, **all of them as event-level lists rather than
daily scalars**, appended as the book processes each order:

```
bid_price   ask_price   bid_ask_spread   mid_price
rate_distance   bid_rate_distance   ask_rate_distance
limit_orders_buy   limit_orders_sell
market_orders_buy  market_orders_sell  executed_orders
delta_p  market_order_volumes  old_buy_orders  old_sell_orders
```

`Order` carries `sign`, `price`, `volume`, **`time_stamp`** and `date`.

## 3. Coverage, counted rather than quoted

**1,321 days, 2021-07-23 to 2025-03-04. 790,705 orders.**

| | |
|---|---|
| days with at least five orders on **each** side | **1,321 of 1,321** |
| buy orders per day | median 145, min 6, max 1,424 |
| sell orders per day | median 285, min 11, max 1,486 |
| `vendo` | 421,395, 53.3% |
| `compro` | 199,453, 25.2% |
| unsigned, `''` | 156,164, **19.7%** |
| other tokens, about 350 distinct | roughly 1.8% |

## 4. Four things it can do, and how far each reaches

**1. Retire assumption A1, on the dollar leg.** `b6b_eltoque_prereg.md` §3.3
assumes `bid <= m <= ask` and says the Applied Economics paper is where it could
be settled; that paper is behind a paywall and returns 403. This dataset settles
it by measurement, from `bid_price` and `ask_price`, which are per-day series of
the book's best quotes.

**`bid_rate_distance` and `ask_rate_distance` are not what their names suggest
and are not used.** The first draft of this section read them as the published
rate's distance from each side of the book. The code says otherwise:

```python
rate_distance = (self.buy_orders[0].price - order.price) / self.buy_orders[0].price
```

`buy_orders[0]` is the best bid and `order` is the **incoming** order, so the
quantity is a new arrival's distance from the touch. **"Rate" there means the
order's own price and has nothing to do with the TRMI.** Recorded because a field
name read without its code is exactly the shape of error `MEASUREMENT.md` failure
mode 7 is about, and because this one was written into this document before the
code was read.

**2. ~~Retire B6-13's offer ratio `r`.~~ Not possible from this source.
Closed 2026-08-19.**

§4.3 converts an hour-against-day dispersion into the full-day estimator's scale
by dividing by `sqrt(r - 1)`, and `r` is not observed, which is why B6-13 reports
a critical value of 44%. This section originally said `Order.time_stamp` gives
the intraday arrival distribution. **It does not. It is a sequence counter.**

```
date          orders   ts min   ts max   span   span/orders
2021-10-31        74    15154    15227     73          0.99
2022-12-05       614   197077   197690    613          1.00
2024-01-09       459   432705   433163    458          1.00
2025-02-12       336   669911   670246    335          1.00
```

The span of a day equals that day's order count, and the last stamp of one day
and the first of the next differ by **1**. It indexes the message stream. The raw
`data/messages/*.parquet` carry three columns, `messages`,
`processed_messages` and `orders`, and **no timestamp either**: the only time in
the artefact is the date in the filename.

**B6-13 keeps its critical-ratio sensitivity and there is no route here to
replace it.**

> **Twice in this document a field was read by its name.** `bid_rate_distance`
> was written up as the published rate's distance from the book before the code
> was read, and `time_stamp` as a clock before the values were. Both were wrong
> and both are corrected in place. `MEASUREMENT.md` failure mode 7 covers the
> shape; what this pair adds is that **an availability check is exactly where it
> happens**, because that is the document written fastest and with the least of
> the artefact opened.

**3. Put a measured distribution behind B6-15's critical spread.** B6-15(b)
reports that the standing gap survives an informal round trip of up to 5.07% and
cites elTOQUE's own 2022 microstructure note, 0.93% normal and 1.8% stressed, as
context. `bid_ask_spread` is computed per day for 1,321 days, which replaces a
published figure with a distribution.

**4. Validate the TRMI's construction.** Recompute the twenty-four hour median
with the two-standard-deviation filter from the raw orders and compare against
the published value. This is what §14.6 registered the source for, and it is also
the only available check on the failure mode `b5_orphan_prereg.md` §7.4 was
written against: a series quietly frozen is visible in the order flow.

## 5. What it cannot do

**It is dollars only.** `data/` ships the USD run and nothing else. The code
takes `CURRENCY` in `{"USD", "EUR"}`, so the euro leg is reachable **only by
re-running their scraper**, which needs their pipeline and live access to the
sources. So:

- A1 is retired on the dollar leg and stays an assumption on the euro, MLC and
  tether legs.
- **B6-13 is the criterion that needs the euro**, and its `r` would be a dollar
  measurement carried across on a new assumption that arrival patterns do not
  differ by instrument. That assumption is weaker than the one it replaces but it
  is not nothing, and it would be registered rather than absorbed.

**It stops at 2025-03-04**, before B6-A's window opens on 2025-12-19. Everything
above is about the instrument. Nothing here is a statistic of the window.

**A fifth of the orders carry no side.** 19.7% have an empty `sign` and about
1.8% carry a token that is neither verb, so the classification covers **78.5%**.
The unsigned fifth is **not missing at random**: a message whose verb the
extractor missed may be systematically different from one it caught, and no
correction for that is available from inside the dataset.

**The shipped file is 790,705 orders and the paper reports 814,233**, a gap of
2.9%. The published artefact is therefore a filter stage rather than the headline
count, and any recomputation should reproduce the file rather than the paper.

**The licence is stated in the README as MIT and there is no `LICENSE` file.**
The underlying offers are scraped from elTOQUE, whose own terms forbid resale and
redistribution, so the derived data would be treated the way the TRMI series
already is: kept out of the repository, cited, and reported in aggregate.

## 6. Verdict

**Open, on the dollar leg, for three of the four instrument-level questions.**
The offer ratio is closed: the artefact carries no wall-clock time anywhere. The retrieval is one
`git clone`; the book's best quotes and its spread are inside
`daily_info.pickle` and need an aggregation from event level to daily, which is
a registered choice rather than a read.

**What is not settled here is whether it becomes a registered arm.** Reading
`bid_rate_distance` and calling A1 retired is a criterion, and a criterion
belongs in a pre-registration written before the file is opened. The three shapes
available are: fold it into `b6b_eltoque_prereg.md` as criteria B6-16 and B6-17,
open it as its own stage B6-C, or record it here as available and not done.
