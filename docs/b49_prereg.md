# B49 pre-registration: a class square on the two carriers that cannot be resold

The rival account of prices this repository tests is that the terms attached to a
position are the difference of a scalar over positions. It predicts that every
closed loop of such terms sums to exactly zero, whatever the terms themselves
are, and it has no free parameter with which to accommodate a non-zero one.

The smallest such loop is a square. This one is built from four published
prices, two carriers by two customer classes:

```
S = [ log P(household, electricity) - log P(household, gas) ]
  - [ log P(industry,  electricity) - log P(industry,  gas) ]
```

**Why these two carriers and not the other six.** The IEA end-use series carries
eight products. Four of them (gasoline, automotive diesel, and the two grades of
fuel oil where the series is a transport series) are quoted for one sector only,
so no square can be written at all. Two more move in tankers and drums and can
be resold across the class line, which collapses the two classes into one
position. **Electricity and piped natural gas arrive through a metered network:
a household cannot resell to an industrial buyer, the split is written into the
tariff by someone other than the two parties, and both classes are quoted
annually from national official sources.** The product grid is printed in the
record so this selection can be checked rather than taken.

## 1. Criteria

| | asks | kind | FAIL |
|---|---|---|---|
| **B49-1** | the locked panel is complete: four series, three years, every country kept | `instrument` | a leg is missing without being named |
| **B49-2** | the roster is never shorter than the records it names, gap reported per product | `bookkeeping` | a product's roster is shorter than its record count |
| **B49-3** | the square does not move with the currency the prices are quoted in | `instrument` | the residual exceeds what one shared scalar can leave behind |
| **B49-4** | every square stands above the measured floor | `instrument` | a cell falls to or below it, in which case it is unreadable and carries no verdict |
| **B49-5** | no cell sits at the rival's point prediction of exactly zero | `rival` | **a cell reads exactly zero** |

Three states: readable and scored, readable and at the rival's prediction, and
below the floor and unscored. **The third has to exist.** A continuous quantity
read at a threshold cannot be reported as a zero because the instrument stops
there.

## 2. The four numbers before the run

**No estimator, no band, no power.** The prediction is a point at exactly zero,
so there is no sampling distribution and nothing on which to draw a line. The
gate that replaces both is a resolution floor, measured and not declared: the
same square computed from prices quoted in a second unit must return the same
number up to what one shared scalar per country and year can leave behind, and
the largest such residual is the floor.

Only the national-currency quotation is admitted for that floor. The
purchasing-power unit is not a single scalar per country and year, so a residual
against it carries structure of its own.

**Independent count.** Four positions, four edges, `b_1 = 4 - 4 + 1 = 1` per
country-year cell.

**Degeneracy, asked before the square is built.** A square sum has three parts,
and only all three vanishing makes it degenerate. Both classes buy both carriers
in every kept country, so this is a first-cohomology object and not a
reachability statement; the two classes face separate published tariffs, so the
first part is not zero by construction; the two transfer wedges are not
observed, and for the whole sum to vanish they would have to cancel the measured
part in every single cell.

## 3. Carrier and basis

`https://api.iea.org/prices`, the public read endpoint behind the End-Use Prices
Data Explorer, no key, CC BY 4.0. Fourteen aggregate names are dropped so no
aggregate is read as a country. **Prices include VAT in every sector in this
series**, which is load-bearing: were household prices quoted with tax and
industrial prices without, this square would be measuring the tax convention.
The units are checked in the script rather than assumed, since the square
divides one carrier by the other.

**Depth is the binding limit.** Electricity and gas by sector carry three years
only: 2000, 2010 and 2025. The products with a full annual series back to the
1960s are the transport fuels, which have one class. **Depth and shape run
opposite in this source**, which is why the panel is thirteen countries by three
years and not more.

The record `results/b49_energy_class_square.json` carries the criteria wording,
the configuration this run used, and every quantity it produced.
