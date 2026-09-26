# B101: a published productivity index read as an edge function

A superlative productivity index is a number attached to a pair of observations.
Attaching a number to a pair is a 1-cochain on the graph of comparisons that were
actually made, and the question a 1-cochain answers first is whether it is the
difference of something defined on the observations themselves. If it is not,
then no scalar productivity level reproduces the measured comparisons, and any
level that gets reported is a projection with a residual that was discarded on
the way.

B79 established the projection half of this: on a complete comparison graph the
GEKS parities are the least-squares projection of the log bilateral index onto
the exact cochains, and what the projection discards is the distance to that
subspace, a single path-independent number, of which chain drift along one route
is one reading. This station takes the same machinery to a productivity index in
a published empirical paper and reads it on the panel that paper's data source
has become.

## 1. The object

Griffith, Redding and Van Reenen (2004) write value added as `Y_ijt = A_ijt *
Phi_jt(L_ijt, K_ijt)` with `Phi` homogeneous of degree one, and read `A` two
ways. Their equation 9 reads its growth between adjacent years of one country
with a bilateral translog index. Their equations 10 and 11 read its level
against an industry-year geometric mean cell and then take the gap to the
frontier country. Both are the same edge function,

```
w(j,k) = ln(Y_k/Y_j) - s(j,k) ln(L_k/L_j) - (1 - s(j,k)) ln(K_k/K_j)
s(j,k) = (sigma_j + sigma_k) / 2
```

read on two different spanning structures: a path along the years of one country,
and a star from every cell to the mean cell. The midpoint weight is symmetric in
the endpoints, so `w` is antisymmetric and the object is a cochain. Measured on
this panel at `4.4e-16` over 7,951 adjacent pairs. The same construction with the
base-period share instead reads `1.5e-01`, which is the half of that check that
has to fail.

## 2. The closed form, and what is not in it

Around a closed path the value-added terms telescope to zero exactly. With two
factors whose shares sum to one, and using `x = ln(L/K)`, what remains is

```
holonomy(loop) = - (signed area of the closed polygon traced in (x, sigma))
```

evaluated by the trapezoid rule, which is the same arithmetic the index performs.
Two computations that share no step agree at `1.2e-15` at worst across window
lengths from two years to twenty-six, and the second never reads value added at
all. Rescaling every value-added figure by an arbitrary factor leaves the loop
sum unchanged at `1.8e-15`.

**So chain drift in a productivity index carries no information about output.**
It is a statement about factor accounting, and about nothing else.

The area vanishes when the sampled points are collinear in `(x, sigma)`, which is
to say when the share is affine in the log mix over the window being read. A
constant share is the flat special case; a share that moves and moves linearly
gives exactly zero too, and the numbers below are read against that null and not
against constancy.

**The direction runs one way.** A constant-returns translog production function
gives a share equation that is exactly affine in `ln(K/L)`, so translog implies
affine implies zero. The converse does not hold: a fitted affine relation is not
evidence that the underlying technology is translog, and nothing below is read
that way.

**And zero on one loop is a cancellation, not collinearity.** A crossed
quadrilateral encloses zero signed area with no three of its vertices in a line.
Collinear implies zero always; the converse needs every loop on a complete graph,
where every triangle vanishing forces it. The readings below are over all
non-degenerate windows of a series, which is the form that does constrain the
relation.

## 3. What this panel can and cannot answer

EU KLEMS & INTANProd growth accounts, 34 countries, 60 industries, 1995 to 2021,
1,057 (industry, country) series, 22,378 cells carrying all five series needed.

The quantity indices are based at 100 in 2015 in every series, so `ln(L/K)` reads
exactly zero in all 1,053 cells of 2015 and the file carries no cross-country
level at all. Writing `x = x* + c` with `c` fixed per series, the two
cross-country edges of a country-by-year square leave `(c_F - c_i) * (-1/2) *
(dsigma_i + dsigma_F)`, an arbitrary constant times a one-year share change,
which does not cancel. **Equations 10 and 11 cannot be built from this file**, and
criteria that depend on them are recorded as having no object rather than as
failing. Unblocking that half needs one cross-section, not a panel: 2015 labour
and capital levels by industry and country, comparable across countries.

Within a series every offset cancels, so the time half is readable with nothing
but the published figures: the chained index against the direct index over the
same window is a closed path.

## 4. The readings

| | reading |
|---|---|
| Raw shares, chained against direct | non-zero in `99.8%` of 20,206 two-year windows, `99.8%` of 12,247 ten-year, `100.0%` of 445 twenty-six-year. Median `2.6e-04` to `9.5e-03` across those |
| Floor, measured | a relative shock of `1e-2` to every published figure moves the ten-year median by a factor `1.05`; the construction floor is `1.7e-16` |
| Scale | a twenty-six-year drift has a median of `0.0095` in log points against a median one-year growth reading of `0.0280`, about a third of a year of growth over twenty-six |
| **Shares put into the form the paper fits**, `sigma = a + b ln(K/L)` | **`0.0%` non-zero at every window length, medians `8.3e-17` to `2.2e-16`** |
| What that form keeps | within-series r-squared of the share on the log mix: median `0.212`, `79.0%` of series below a half |
| The slope, which is their own restriction and not their country term | cross-country spread against a floor built from each country's own two halves: median `0.91` over 55 industries, `1` of `55` above three |
| Second value-added concept, intangibles capitalised | `100.0%` non-zero at nine years over 16,992 windows, median `2.7e-03`. Reported apart, not merged |

## 5. What that adds up to

The smoothing is described as putting the shares into the form the index assumes.
What it does to this quantity is not to lower it. Raw shares drift in almost every
window; fitted ones drift in none, at machine precision, at every window length,
and the result does not depend on how the two coefficients are fitted: both are
constant within a series, so the fitted share is affine in the log mix along every
path inside it and the trapezoid sum telescopes.

This is the same operation the multilateral index performs by projection, done one
level earlier and on a different object. And it keeps about a fifth of the share's
own movement within a series. **The index becomes transitive because the share was
replaced, not because the replacement is close to what it replaced.**

**This is established for the time chain and not for the cross-country one.**
Inside a series both fitted coefficients are constant, which is what forces the
time drift to zero. Footnote 20 puts the country term on the intercept,
`sigma_ijt = alpha_ij + beta_j ln(K/L)`, and on a cross-country loop a slope that
is common inside the industry telescopes to zero while the intercept contributes
all of the holonomy. So the cross-country direction is exactly where a country
term can still leave one, and this panel cannot read it: the quantity indices are
based at 100 in the same year in every series, so a fit returns the slope
untouched and the intercept as `alpha - beta * e`. **The slope's blindness to the
index base is precisely why the intercept is not recoverable.** Their stated
restriction on the slope does hold here, `0.91` against a null of one, and that is
a reading about the slope and about nothing else.

## 6. The cross-country half

Section 3 recorded this half as having no object on the growth accounts module,
and the reason was specific rather than general. That module carries the factor
mix as a quantity index based at 100 in one year per series: 1,079 and 1,156 rows
read exactly 100 across 1,118 series, with 2015 the base for 1,053 of them. A
cross-section of such an index is the same number for every country, so the mix
has no spread there and nothing is swept.

The capital accounts module of the same release carries the capital stock as a
level in national currency, reading 100 in zero rows. Labour compensation is
already a level in the same currency. So the mix can be written as a flow over a
stock, and a cross-section exists: 25,886 cells with all four series, 1,485
(industry, year) cross-sections with three or more countries, 55 industries, 1995
to 2021, 6 to 32 countries each.

**This needs no purchasing power parity, and that is measured rather than
asserted.** Scaling one country's output, labour compensation, capital
compensation and capital stock by one factor is a change of currency. It moves
the edge function by `(1 - s - (1 - s))` times the log of that factor, which is
zero, and the reading moves by `3.6e-16`. The same factor on the capital stock
alone, which the share does not read, moves it by at least `0.0230`. The units of
the mix are load bearing and the currency is not. A quantity mix, which is what
the source paper uses, is a different definition rather than a better version of
this one, and it needs a module this station does not hold.

### The object is not a loop

Put the bilateral index on every edge of the complete graph over countries and
ask how far that edge field is from being a difference of node values:

    rho = || w - Pi w || / || w ||

with `Pi` the least-squares projection onto the image of the coboundary. `rho` is
zero exactly when one scalar per position reproduces every pairwise comparison,
which is the prediction that follows from treating productivity as a level
attached to a position. The projection is B79's, imported rather than rewritten.

Two answers are known before the run and are read back: an exact coboundary gives
`9.1e-16`, and a field with no structure gives `1 - 2/n` in expectation of `rho`
squared, matched to within `1.22` standard errors of the exact Beta at `n` of 4,
8, 16 and 24. The closed form is on `rho` squared; comparing the mean of `rho` to
the square root of `1 - 2/n` misses by `0.13` at `n = 4`.

### Two sources, and the second is most of it

A share that is linear in the mix gives exactly zero, because the trapezoid rule
is exact on a straight line. Read back at `2.3e-15` over 400 cross-sections. So a
non-zero reading has two sources and no others: curvature in how the share
depends on the mix, and the share not being a function of the mix at all.

Replacing the share by its own quadratic on the mix and touching nothing else
measures the first. It is a median `0.0209` against an observed median of
`0.1045`, a ratio of `4.84`, and it accounts for a median `4.3%` of `rho` squared.
No cross-section out of 1,485 sits at or below it, and 1,338 sit above twice it.

### What the published smoothing does here

The paper's own smoothing puts the country on the intercept and the industry on
the slope. Fitted on a mix with no index base, the intercept is that country term
itself rather than the country term less the slope times an unknown offset, which
is what a based index returns. Slope median `+0.0991`; within R squared `0.096`.

The area that country term sweeps is the closed form for this half, because the
slope term integrates to zero around any closed path. Evaluated directly on the
loop that visits countries in the mix's own order, so that no ordering is chosen,
it is a median `0.0587` against `0.0712` for the raw share: a ratio of `0.824`.
Read again with no loop at all, through `rho`, it is `0.0857` against `0.1044`: a
ratio of `0.839`. Two routes that share no step, `0.015` apart. The smoothing
halves the reading in 66 cross-sections out of 1,485.

Planting the answer confirms what carries it: one country term shared by every
country sweeps `4.4e-16`, and a term that moves across countries, on the same mix
and the same loop, sweeps at least `0.1711`.

### The line this station ends on

The same smoothing does opposite things on the two chains. Inside one
country-industry it sets the drift to exactly zero, at a median of `8.3e-17`.
Across countries it keeps between `82%` and `84%` of it. The algebra says why in
one line: within a series the country term is a constant, and a constant sweeps
no area; across countries it moves, and the area it sweeps is the whole reading.

So a published index is transitive along one chain because of its smoothing, and
transitive along the other because the multilateral form projects the obstruction
away. Those are two different mechanisms, and reporting them as one statement
about transitivity loses the part that matters.

## 7. The quantity mix, and the parity that turns out not to matter

The mix above is currency invariant. The one the source paper uses is not: hours
are physically comparable across countries, a capital stock is a national
currency amount, so the quantity mix carries an unknown per country term. The
third module of the same release supplies hours in levels, and under D11 this is
a second definition, reported beside the first rather than merged into it.

The two are exactly one measured quantity apart. Their difference is the log
hourly labour cost, `ln(LAB/H)`, to `8.9e-16`, so nothing unknown separates them.

**Both give the same verdict and a different ordering.** Every one of the 1,485
cross-sections sits above its own curvature floor under both definitions: none
under neither, none disagreeing. The rank correlation between the two readings is
`+0.006`. Which mix is chosen does not change what is concluded, and does change
which cross-sections look large. Both halves belong in any statement about it.

    quantity mix    rho median 0.0745    floor 0.0173    ratio 4.32    0 of 1485 at the floor
    value mix       rho median 0.1045    floor 0.0209    ratio 4.84    0 of 1485 at the floor

### The missing parity, answered by a minimum rather than a sensitivity

Write a per country conversion `e` on the log of a factor. The edge function moves
by `sbar` times `(e_b - e_a)`, which is linear in `e`. So the smallest reading any
conversion can produce is the value of a least squares problem: not a plausible
conversion, not a sampled one, the minimum over all of them.

That question is empty until the conversion is tied down. One free per
cross-section drives the reading below `1e-10` in 300 of 300, and the conversion
it takes is minus the mix, which makes the mix the same number in every country.
Substituting that directly reads `1.2e-15`. It is deleting the variable rather
than converting it.

A parity is one number per country, the same across every industry. Solved once
over every cross-section at the same time, that is 32 numbers globally or 864 per
year against 210,324 dimensions of non-gradient field:

| definition, scope | before | after the best parity | cut | reaches the floor |
|---|---|---|---|---|
| quantity, global | `0.0745` | `0.0569` | `26.4%` | `161 / 1485` |
| quantity, per year | `0.0745` | `0.0555` | `26.5%` | `169 / 1485` |
| value, global | `0.1045` | `0.0584` | `40.0%` | `157 / 1485` |
| value, per year | `0.1045` | `0.0569` | `44.3%` | `197 / 1485` |

The claim on the other side is that one parity puts every cross-section back on
one level per position, so what is read against it is the share left above the
floor: at worst `86.7%` remain. The cross-sections a parity does close are the
narrow ones, a median of 15 countries against 19 for those it does not, which is
the same parameters spread over fewer pairs.

Neither overstatement survives this. A parity is not irrelevant, since it removes
up to `44%` of the reading. And no parity rescues the position-scalar reading,
since that claim is about every cross-section and it fails on nearly nine in ten.

### One carrier checked and set aside

The national accounts module separates employees from all employed in both
headcount and hours, and the growth accounts' labour compensation is the wider
concept, so two labour classes sit at every position with their own terms. That
is this framework's own object, and whether it carries anything is arithmetic:
the implied self-employed hourly wage divided by the employee wage is exactly one
in `71.42%` of 24,828 cells and negative in `4.09%`; of 32 countries, 9 impute at
the employee wage in every cell and 2 in none. The class difference is imputed
away in most of the panel and differs by compiler elsewhere. So the split is a
convention here rather than a reading, and this station records that it was
checked and set aside.

## 7b. What this frame does say about that slope, and a first test of it that
came out on the wrong side

**B101-11 records that the rival's restriction holds here and is not scored,
because a slope of a factor share on a factor ratio is not this frame's object.**
That is right as far as it goes, and it leaves a sharper question unanswered:
does the frame say nothing at all about the slope, or does it say the slope is
not a primitive?

**It says the second, and the step is short.** If the price a class is paid at a
position is class-dependent, the labour share at that position is a
composition-weighted average rather than a scalar property of the position. A
slope fitted on that share is then a functional of the class mixture: bounded by
the class-specific slopes, and placed inside that range by the mixture. **So
there is a range, and where a country sits inside it is set by a state that
moves slowly rather than by a technology constant.** The labour accounts put a
number on how slowly: a country-industry's class composition correlates +0.95
with itself one year on and +0.68 ten years on.

**That has a consequence this panel can read.** Across the countries of one
industry, the spread of the fitted slope should be wider where the countries
staff that industry with more different mixtures. The rival's slope is a
technology parameter and carries no such term, so under it the relation is flat.

**Built from two files already here, nothing retrieved.** Both axes take the
same shape, spread across countries over a floor from each country's own two
halves, so a panel with no cross-country component reads one on either axis.
The fitting routine is imported from the arm that registered it. Both axes are
computed on the same matched countries: taking the floor over every country in
the industry while the spread runs on the matched ones puts two sides of one
ratio on two populations, and the ratio still prints, so it was worth fixing
before reading anything. It moved the reading from -0.37 to -0.45.

| criterion | reading | |
|---|---|---|
| **B101-36** *(instrument)* the two files join and every industry carries the minimum countries on both sides, with the matched count printed per industry | 19 industries joined, fewest matched countries in any of them 20 | PASS |
| **B101-37** *(own reading)* the relation between how differently the countries of an industry staff it and how far apart their fitted slopes are, printed against the rank correlation's own scale with no line drawn | **rank correlation -0.4456 across 19 industries, its own scale about 0.236** | PASS |
| **B101-38** *(bookkeeping)* every industry named with both axes and both floors | 19 carried in full | PASS |

**The sign is the opposite of the one the step above predicts, and that is the
reading.** Leaving each industry out in turn keeps it negative every time, from
-0.37 to -0.52, so it is not one industry. Nineteen industries put the rank
correlation's own scale at about 0.236, so the reading sits near twice it and
this is not a decisive measurement either way.

**Two confounds are worth naming because both push the other way.** An industry
whose composition is stable within countries gets a large composition ratio
through a small floor, and a stable composition is also one on which the slope
is better determined, which enlarges the slope ratio too. An industry noisy on
both axes shrinks both ratios. Each of those couples the two axes positively,
and the measurement is negative against them.

**What it does not settle.** The step above predicts that the slope is a
mixture average; the spread relation is a consequence of that and not the claim
itself. The direct test compares a slope fitted on the actual mixture with one
fitted on a mixture held fixed, and the class-level wage shares needed for it
are in the same labour file. That is registered here and not done.

## 8. What is registered and not done

Nothing on this station now waits on data. What remains open is a different
carrier for the two-class reading, since the one this panel offers is imputed.

## References

Griffith, R., S. Redding and J. Van Reenen (2004), "Mapping the Two Faces of R&D:
Productivity Growth in a Panel of OECD Industries", *Review of Economics and
Statistics* 86(4), 883-895.

Bontadini, F., C. Corrado, J. Haskel, M. Iommi and C. Jona-Lasinio (2023),
EUKLEMS & INTANProd database. Cite when using the data; the database is the
successor to the OECD sectoral source the 2004 paper used.

Ivancic, L., W. E. Diewert and K. J. Fox (2011), "Scanner Data, Time Aggregation
and the Construction of Price Indexes", *Journal of Econometrics* 161(1), 24-35,
for the GEKS product formula whose least-squares reading B79 records.
