# B106: a labelled two-index price field, and the square it makes possible

## 1. Why this carrier and not the earlier one

B2A reads dispersion at a position: two loans in the same cell at different
rates, a within-cell share of `0.7831`. That is an `H0` statement. Its borrowers
carry no labels, so there is no "the same class at another position" to compare
against, and a square cannot be formed. This is the dispersion reading, with the cell as
the position; [`b0_claim_scope.md`](b0_claim_scope.md) §5 keeps it beside the square
reading, which takes the dwelling as the position under A1.

The labour accounts module of EU KLEMS labels them. At every position (country,
industry, year) it reports, for each of 3 education by 3 age by 2 gender cells,
that cell's share of employment and its share of the wage bill. Their ratio is
the class's pay relative to that position's average, and both shares sum to 100
at every position, so the position's own level is normalised away by
construction and what is left is the ladder.

That makes the field `p(position, class)` a labelled two-index object, and the
question the framework asks of any price field becomes askable:

    p(j, k) = a_j + b_k    <->    the ladder is one object everywhere

Additive separability is not an analogy for the field being a gradient, it is the
same statement: the additive subspace of a `J` by `K` table is the image of the
coboundary on the complete bipartite graph, and what is left carries `(J-1)(K-1)`
independent cycles. Each is a square: two positions, two classes, and the
difference in differences of log relative pay.

    13,843 positions, 99.5% carrying all 18 classes, 99.0% usable after a log
    20 NACE sections; five aggregates (M-N, MARKT, NMARKT, TOT, TOT_IND) excluded
        by name, 36,288 cells, because an aggregate beside its own parts enters
        the same workers twice while every count stays sensible
    621 country-year tables, 19 industries at the median, 306 cycles each
    527 industry-year tables, 33 countries at the median

## 2. Three floors, all measured

    no-structure floor   (J-1)(K-1)/(JK-1)      0.8974 at J = 19    pure counting
    sampling floor       1 - the year-to-year correlation   about 0.046
    counting floor       parameters / interaction dimensions   68/306 = 0.222

Two answers are read back before anything else: a separable field gives
`6.8e-32`, and a field with no structure gives its own degrees of freedom, worst
`z` of `1.50` against four standard errors of the exact Beta.

## 3. The reading

| orientation | tables | interaction share | no-structure floor | ratio |
|---|---|---|---|---|
| industries within a country-year | 621 | **0.4027** | 0.8974 | 0.450 |
| countries within an industry-year | 527 | **0.4353** | 0.9174 | 0.502 |

Both halves of that belong in any statement about it. The additive part is the
larger one: a common ladder accounts for about six tenths. And the reading it is
measured against is not that the interaction is small, it is that the interaction
is identically zero, so four tenths is a point prediction missing rather than a
matter of degree.

## 4. It is there every year, and that is the load-bearing part

A scalar price field on positions says the interaction is zero and what is seen
is survey error. Survey error does not repeat.

    year to year        +0.9544 and +0.9545 over 197,622 pairs
                        424 standard errors from the prediction of zero
    ten years apart     +0.6790 and +0.6684 over 85,050 pairs
    position pairing broken, every marginal kept    +0.0510 and +0.1537

The decade figure answers a compiler that interpolates between survey years: that
manufactures an adjacent-year correlation and cannot manufacture a decade of one.
The broken pairing answers the statistic itself. Neither is the source.

## 5. It is not small cells

Residual standard deviation by the class's own employment share, thinnest decile
to thickest: `0.6894, 0.3987, 0.3419, 0.3177, 0.2845, 0.2666, 0.2505, 0.2558,
0.2496, 0.2265`. A fall of `3.04` times across a span of at least `21.7` times in
share, where sampling error alone would fall about `5` times, and it stops
falling after the fifth decile. Thin cells carry noise; the `0.23` in the thick
ones is not noise.

## 6. Position characteristics do not absorb it

The reading that competes with this one does not deny the interaction. It says
the ladder differs because the positions differ: capital per hour, productivity,
size, how much of value added labour takes. That is a quantity.

Four characteristics, named before anything was fitted, each given its own
loading per class, which is that reading's own shape:

    generous scope, every country-year with its own loadings     33.4%
    what the same parameter count takes from an unrelated leftover  22.2%
    so the characteristics themselves                            about 10.8 points
    strict scope, one set of loadings for the panel, 68 parameters
        against 135,558 observations                              2.3%
    what would have to be reached, from section 4                 about 95%

Planted both ways: a leftover of exactly that reading's shape is absorbed at
`100.0000%`, and one unrelated to the characteristics at `22.6%` against the
`22.2%` the parameters take by counting alone.

## 7. Where in the class structure it lives

The 18 classes are a complete 3 by 3 by 2 grid, so the leftover splits
orthogonally into seven components: the position crossed with education, with
age, with gender, with each pair of those, and with all three. Their degrees of
freedom are 2, 2, 1, 4, 2, 2 and 4, summing to `K - 1 = 17`, so each has its own
floor, its own count over seventeen, and none is invented. They sum back to the
whole at `3.6e-16`, and a leftover planted to vary only with gender returns
entirely in the gender component at `2.2e-16`.

| component | share | its floor | ratio |
|---|---|---|---|
| education | `21.0%` | `11.8%` | **`1.78`** |
| age | `14.9%` | `11.8%` | **`1.27`** |
| gender | `6.7%` | `5.9%` | **`1.13`** |
| education by gender | `10.2%` | `11.8%` | `0.87` |
| education by age | `20.3%` | `23.5%` | `0.86` |
| age by gender | `9.3%` | `11.8%` | `0.79` |
| all three | `17.7%` | `23.5%` | `0.75` |

Shares and floors each sum to one, so a component above its floor forces another
below it. What is read is the order: all three single attributes above, all four
of their crossings below. The position-specific part of the ladder moves along
one attribute at a time rather than along combinations of them.

Each component repeats on its own, year to year over 10,979 pairs: education
`+0.9694`, age `+0.9598`, gender `+0.9578`, and the four crossings between
`+0.9445` and `+0.9512`. The competing reading puts every one of these at zero,
because it puts the whole leftover at zero.

Education is the largest, and it is the component a large existing literature
already works on, so that part is a cell both accounts read the same way rather
than a result for either. Age and gender sit above their floors and repeat just
as strongly, and are not organised as one object with education in that
literature. This framework predicts an obstruction without naming an attribute,
so the three are read together; it does not predict that education premia vary by
position and is not a claim to have done so.

### One alternative that closes here

Education and age are each compressed to three levels, so part of the leftover
could be composition inside a coarse class differing by position rather than pay
differing by position. Gender is not compressed: two levels, with nothing inside
them to shift. Its component sits above its floor and repeats at `+0.9578`, so
compression is not the source.

The finer education and age codes the module also ships cannot answer this. They
cover 26 positions, all on one industry code in one country, and a table needs
two positions carrying the same classes, so none can be built from them. That is
registered rather than attempted.

## 8. The squares themselves

Sections 3 to 6 report a share of the field and whether it repeats. Neither is a
square. A square here is two positions by two classes,

    s = [p(j,k) - p(j,k')] - [p(j',k) - p(j',k')]

the difference in differences of log relative pay, and it is the quantity the
competing reading puts at exactly zero. Only `(J-1)(K-1)` are independent, so the
basis is every industry against one reference industry and every class against
one reference class: 306 per country-year, 188,054 in all.

Read back before anything else: a separable field gives every square zero at
`8.9e-16`, and an arbitrary square rebuilt from four basis squares matches the
direct calculation at `4.4e-16`, so the basis spans and nothing is double
counted.

**The floor is measured from this panel's own year-to-year movement.** If a
square were a standing feature and the survey added independent error each year,
the change in the same square from one year to the next is pure noise of size
`sqrt(2)` times a single reading's error. Half that spread is the floor:
`0.1766` log points over 176,715 pairs.

That construction bends both ways and both are stated. Treating the square as
fixed makes any real drift count as noise, which raises the floor and works
against this reading. Survey error correlated between adjacent years would lower
it. A longer lag carries more drift, so its floor is an upper bound on the noise:

    lag 1 year    floor 0.1766    74.3% clear it
    lag 2 years   floor 0.2346    66.9%
    lag 5 years   floor 0.3470    54.4%

Against a floor that has absorbed five years of drift, more than half the squares
still stand above it, so the reading does not rest on how the floor was built.

    |square|   median 0.3925   p90 1.3444   max 6.9888
    above the floor          139,811 of 188,054   (74.3%)
    above twice the floor    101,142              (53.8%)
    median square            2.22 times the floor

The competing reading is that a class's pay at a position is a scalar on the
position times a factor for the class, which in logs is additive and puts every
one of these at exactly zero. This is the same reading section 4 scores; what
differs is the object. Section 4 asks whether the leftover repeats, and this asks
how large it is.

## 9. What is open



The finer class codes, education `11..15` and age `11..17`, are present for a
handful of positions only and are not read; they are a different granularity and
would be reported separately rather than merged.

Whether the employment share counts hours or persons is settled, and it is
settled by the panel rather than by a document. It does not cancel out of the
ratio: on the hours reading the field is relative hourly pay, on the persons
reading it is relative annual earnings and part of the interaction could be
part-time composition varying by industry and gender.

The published methods note says only "the shares of employment and labour
compensation by type of worker", which is the ambiguous word itself, and the
module's own naming points one way while the construction the release is built
on points the other. So the documentation does not decide it.

The labour accounts exist to build the labour services index published in the
growth accounts, and that index is a Tornqvist over these same classes:
`dln L = dln T + sum_k vbar_k dln S_k`. Putting the total `T` at hours and then
at persons and asking which reproduces the published index is a known answer
check against a series this station did not construct.

    7,161 adjacent-year steps within one section and country

    T = hours     rmse 0.00108    correlation +0.9998    within 1e-3: 6,972
    T = persons   rmse 0.03284    correlation +0.8370    within 1e-3:   479
    dropping the class term       0.02033 and 0.03765

Hours, by a factor of thirty in root mean square error. The two totals are
genuinely different objects, so the verdict carries weight: their difference is
the change in hours per worker, with a standard deviation of `0.0325` against
`0.0569` for hours and `0.0441` for persons.

So the field is relative hourly pay, and part-time composition is not an
alternative for any part of the interaction.

## References

Bontadini, F., C. Corrado, J. Haskel, M. Iommi and C. Jona-Lasinio (2023),
EUKLEMS & INTANProd database. Cite when using the data.
