# B137: the borrowed price, one formula, its slope in the unpublished price, and the least correction the rival's premise requires

**RUN: 2026-09-27; rerun 2026-10-06 (every reading stored before is unchanged; the FISIM amounts are now
read from the published cells as well). Statement and proof below. Checks in
`experiments/b137_borrowed_price.py`, record
`results/b137_borrowed_price.json`, which carries the configuration it ran under. Nothing fetched: the
raw data are those already on disk for B131 to B134, read through those stations' own loaders.**

## 0. The question this station answers

A price statistic needs a value in every class-by-position cell. Where one class has no published price,
the cell is filled with another class's value: the rent tenants pay stands in for owner-occupiers
(imputed rent), the interbank rate stands in for every sector as the reference rate of FISIM, the urban
price stands in for rural households in the ICP. B131, B132, B133 and B134 each measured one instance.

**The question is whether they are one quantity, and what can be said when the own class's price is
never published.** They are one quantity. When the own price is not published the error is a line in
it with a known slope, a "without the borrowed item" reading formed by dropping the item and renormalising
is one named point on that line, and the rival's own premise gives a least correction that needs no own
price at all.

## 1. Setup

One position, classes `a` with values `P_a` and stocks or weights `x_a ≥ 0`. The cells of a set `E` of
classes are filled with the value of a donor class `b ∉ E`. For an index, `p_a` is a class's price
relative between two periods and `w_a` its base-period value share.

## 2. Theorem 45

**(1) Level.** Published less true is `Σ_{a∈E} (P_b − P_a) x_a`.

**(2) Growth.** A chained Laspeyres period's growth is off by `Σ_{a∈E} w_a (p_b − p_a)`. A Törnqvist
period, at the published index's mean shares, is off by `Σ_{a∈E} s̄_a (ln p_b − ln p_a)`; the rest of its
gap is the shares' own move.

**(3) Change.** Between two periods the bias changes by `Σ Δ(P_b − P_a) · x̄_a + Σ (P_b − P_a)‾ · Δx_a`
(Bennet's symmetric split): the gap moving and the stock moving. A scalar `s` placed between an own
class below it (`lo`, stock `x_lo`) and one above it (`hi`, stock `x_hi`) splits
`(s − P_lo) x_lo + (P_hi − s) x_hi = P_hi x_hi − P_lo x_lo + s (x_lo − x_hi)`: **it moves the total only
through the stock difference**, and with equal stocks it moves only the split.

**(4) The own price unpublished.** If `P_a ∈ [L_a, U_a]`, the bias lies in
`[Σ (P_b − U_a) x_a, Σ (P_b − L_a) x_a]` and both ends are attained. **The bias is a line in the
unpublished price with slope `−x_a`** (`−w_a` for growth).

**(5) The least correction.** A rival whose premise is that one scalar is acceptable to every class puts
that scalar in `F = ∩_c [lo_c, hi_c]`. If the borrowed value `P_b` lies outside `F`, every
premise-consistent scalar is at least `d = dist(P_b, F)` from it, so a cell filled with `P_b` must move by
at least `d` times that cell's stock. **The bound needs no own-class price.** If `F` is empty the premise
itself fails. The statement is about cells filled from one scalar. Where the published cells imply
different scalars it holds cell by cell, each cell with the scalar it implies; a scalar averaged over the
cells gives the least correction on a baseline rebuilt from that average, which is no bound on the moves of
the published cells.

**(6) The "without" reading.** Dropping `E` and renormalising the rest equals (2) with every own relative
set to the rest of the basket's, for a Laspeyres index and for a geometric index at the whole index's
frozen mean shares, the rest's weights being `(s₀ᵢ + s₁ᵢ) / (A₀ + A₁)` with `A` the rest's share in each
period. **A "without the borrowed item" figure formed this way is the point of the line in (4) at own
relative = rest of the basket.** The Törnqvist index of the rest itself renormalises each period's shares
first, with weights `(s₀ᵢ / A₀ + s₁ᵢ / A₁) / 2`; it is another operation and differs by a weight term, and
so does a Fisher index of the rest.

**Proof.** (1) The published aggregate differs from the true one only in the cells of `E`, by
`(P_b − P_a) x_a` each. (2) Laspeyres growth is `Σ w_a p_a`; replacing `p_a` by `p_b` on `E` changes it by
`Σ_E w_a (p_b − p_a)`. The Törnqvist statement is the same substitution in `Σ s̄ ln p` with the shares held.
(3) `g₁x₁ − g₀x₀ = (g₁ − g₀)(x₀ + x₁)/2 + (g₀ + g₁)/2 · (x₁ − x₀)`, term by term; the bracketed total is
linear in `s` with that coefficient. (4) The bias is affine in each `P_a` with coefficient `−x_a`, so over a
box it is extreme at the corners named. (5) `F` is an interval, the nearest point of an interval to `P_b`
is its nearer end or `P_b` itself, and the side's value moves by the scalar's move times its stock.
(6) With `W_E = Σ_E w_a` and `p_rest = Σ_{a∉E} w_a p_a / (1 − W_E)`, setting `p_a = p_rest` on `E` gives
`Σ_{a∉E} w_a p_a + W_E p_rest = p_rest`; in logs the same holds at frozen mean shares. ∎

(1), (2), (3) and (6) are index-number identities and are cited; (4) and (5) are what the framework adds:
the published statistic's error is a line in the one quantity the statistic does not observe, with the
own class's weight as its slope, and the rival's premise alone gives a floor under the correction.

## 3. What the checks read

| | check | reading |
|---|---|---|
| PASS | B137-1 `instrument` **level and growth** | 2,000 synthetic fields of 2 to 12 classes: largest gap `9.0e-15`. Planted: the gap's sign, current-period shares; both caught |
| PASS | B137-2 `instrument` **the change and the bracketed scalar** | 2,000 pairs of periods: `5.3e-15`. Planted: base-period values on both terms, which leaves the cross term; caught |
| PASS | B137-3 `instrument` **the interval** | Random own values in their intervals never leave the bounds; the ends are attained exactly. Planted: the ends swapped; caught |
| PASS | B137-4 `instrument` **the least correction** | 2,000 interval sets against a search of the intersection, no gap beyond half the search step; empty intersections reported. Planted: distance to the midpoint; caught |
| PASS | B137-5 `instrument` **the "without" reading** | 2,000 fields, the Laspeyres identity and the one at frozen mean shares: `4.4e-16`. On three items (prices 1, 1, 1 to 2, 1, 1.1; quantities 1, 1, 1 to 2, 1, 1; the first dropped) the rest rises `4.961967%` at frozen mean shares and `4.999955%` as its own Törnqvist index. Planted: the dropped weight forgotten, the rest's own Törnqvist taken for the frozen-share index; caught |
| PASS | B137-6 `known_answer` **the "without" readings from the raw data** | Through the bias formula with the own relative set to the rest's: France 2023 `7.048` and `4.938`, as B132 printed; B132's 2020–2024 "without both" in 31 areas, no gap at two places. B133's 1973–2014 borrowed share by its two operators: `0.1623` by the contributions construct, `0.1528` by the Fisher removal |
| PASS | B137-7 `known_answer` **B131's reference scalar is (1) inverted** | 187 member years; the scalar each side implies from the published FISIM, its own rate and its mean stock matches B131's exactly; median spread of the four `0.5824` and 95 years with one of them outside the band, as B131 printed. Planted: year-end stocks; caught |
| PASS | B137-8 `own_reading` **FISIM, what the premise requires of the published cells** | 187 member years; a cell's implied scalar outside the band in 95, as B131 counted; the cell-by-cell bound lies under the fit with one common scalar in every year, no cell is negative at a scalar in the band, and every negative cell's bound is at least its amount; the mean of the four outside the band in 56. Planted: the mean's projection taken for the cell-by-cell bound; caught |
| PASS | B137-9 `own_reading` **deflators, the slope** | 1,011 EU area-years, 96 US years, B134's three rounds |

Three deliberate breaks of the block-two code (notice deposits left out of the stock, the US share taken
from the current year, FISIM left in the rest) were each caught.

## 4. What the carriers read

**FISIM: what the premise requires of the four published cells.** The four cells (households' and
non-financial corporations' deposits and loans) each imply a scalar, and the four differ, by a median of
`0.58` points. So (5) is read cell by cell. A deposit cell whose scalar lies below the band, or a loan cell
whose scalar lies above it, must rise by at least the distance times its own stock; in the opposite cases
it must fall. This holds for every scalar in the band and uses no baseline.

In 95 of the 187 member years at least one cell lies outside the band. Cells that must rise appear in 67
years: the least rise has a median of `0.30%` of GDP and a maximum of `4.5%`. Cells that must fall appear in
80 years, median `0.44%`, maximum `4.7%`. With one common scalar for the four cells, the least sum of
increases over the 95 years has a median of `0.19%` of GDP and the least sum of absolute moves `0.69%`,
maximum `9.2%`. France 2023 and 2024 are the largest in euros: all four implied scalars sit above the band
(`1.61` to `1.95`, `1.98` to `2.22`), the two loan cells must rise by at least 56 and 55 billion euros
(`2.0%` and `1.9%` of GDP) and the two deposit cells fall by at least 46 and 47 billion. In the Netherlands
2012 to 2016 all four sit below the band: the deposit cells must rise by at least 3.7 to 5.9 billion and
the loan cells fall by at least 16 to 20 billion. **A negative cell is published in 49 years, 73 cells in
all, and every one of them has a bound at least as large as its negative amount**; no scalar in the band
leaves a cell negative.

**The mean of the four as the office's one scalar.** B131 takes the office's scalar as the mean of the four
implied ones. It lies outside the common intersection of the two sectors' intervals in 56 years, 45 below
and 11 above; in 29 of them it is outside both sectors' own intervals and in 27 outside one. Its distance
to the band times the understated side's stock has a median of `0.55%` of GDP and a maximum of `4.2%`,
51 billion euros for France 2023. That amount is the least correction on a baseline rebuilt from the mean.
The published cells differ from that baseline, so it does not bound their moves: in 34 of the 56 years it
exceeds the least sum of increases from the published cells (Netherlands 2012: 10.3 billion against 5.9),
and it never exceeds the least sum of absolute moves. It is at least the published negative amount in 37 of
the 45 years that have one; added cell by cell to the published cells it still leaves a negative cell in 10
of those 37. The total moves only through the stock difference (3): the median imbalance
`|D − L| / (D + L)` is `0.15`.

**Deflators: the slope.** In the euro area's consumption deflator the two borrowed items together weigh
`0.13` to `0.16`, so each point of the owner-occupiers' and depositors' own price relative that the
statistic does not observe moves the published deflator by that much; across 1,011 area-years the slope
has a median of `0.137` (range `0.056` to `0.260`). B132's 2023 figure is one point on that line: at own
relative = rest of the basket, the published `6.29%` becomes `5.33%`, a bias of `+0.96`: FISIM, at weight
`0.022` and a relative of `+62%`, contributes `+1.24`, and imputed rent, at weight `0.120` and a relative of
`+2.9%` against the rest's `+5.3%`, contributes `−0.29`. In the US PCE the borrowed items' base share has
a median of `0.116` over 1930 to 2025. The PCE price index is a Fisher index, and the US "own" and "rest"
relatives here are a construct: BEA's Fisher contributions of the two items over their previous-year share,
and what is left over the rest's share. Inside the construct the line and its slope are exact, and B133's
`0.1623` of the 1973–2014 divergence is its point at own relative = rest. By B133's other operator, the
Fisher removal, the share is `0.1528`; year by year the two "without" changes differ by a median of
`−0.001` points (`−0.044` to `+0.026`). B133-6 calibrates both on a removal BEA publishes.

**B134 is the cell where the own price is published**, so the bias is read directly: China's national
price is `21.7%`, `18.6%` and `17.2%` above the rural one in the 2011, 2017 and 2021 rounds, at `0.76` to
`0.79` of the way from rural to urban.

## 5. The borrowed price read as an economy

A statistic that holds one price per position cannot hold two classes' terms at that position. Where the
classes' values sit together the borrowing is invisible; where they separate, as when a policy rate
passes through one class's terms and not another's, the separation is written into the statistic as a
service with a negative price, a deflator moving faster than the goods in it, or a rural real income that
is too low. **The size of each is the class-value gap times the own class's stock**, and when the own
class's value is not published the statistic's error is a line in that value whose slope is the own
class's weight. The "without" figures that statistical offices and their critics publish choose one point
on the line (own = rest of the basket) without saying so. The premise that one rate is acceptable to every
sector, taken at its word and applied to the cells as published, already requires cells to rise by up to
four and a half percent of GDP.

## 6. Placement

**A.** The level and growth identities and the "without" reading are index-number theory; the symmetric
split is Bennet's; FISIM's allocation is ESA 2010 chapter 14 (14.01, 14.09).

**D.** That imputed rent, FISIM's reference rate and the ICP's urban price are one quantity, the class-value
gap times the own stock; that when the own value is not published the error is a line in it whose slope is
the own class's weight, and each published "without" figure is a named point on it; and that the rival's
premise of one acceptable scalar gives a least correction with no own price: read cell by cell on the
euro-area data, a least rise with a median of `0.30%` of GDP in the 67 years a cell must rise, covering
every published negative cell.

**C is empty**: no point prediction of another account is scored here; B131-3 scored the rival's
non-negativity premise and is not scored again.

## 7. Scope

The formula is exact for linear aggregates and for chained Laspeyres; for Törnqvist it holds at the
published index's shares, and (6) at frozen mean shares; the US readings are on the contributions construct
of a Fisher index. The cell-by-cell bounds take the own rates and mean stocks B131 measures as given. The
projection takes the office's scalar as the mean of the four scalars the four cells imply, as B131 does;
with any one of the four instead, the count of years outside the band is B131's 95. Locked equity valued at the closing price, the fifth instance the reading names, is not read
here. Nothing here says what any class's own price was.

## References

- Bennet, T. L. (1920). The theory of measurement of changes in cost of living. *Journal of the Royal
  Statistical Society* 83(3): 455–462.
- Eurostat (2013). *European System of Accounts: ESA 2010*, chapter 14. Publications Office of the European Union.
