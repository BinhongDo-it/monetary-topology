# B83: the space-and-time square on the ICP, which is the number the World Bank sets by hand

**RUN: 2026-09-13. Checks in `experiments/b83_icp_square.py`, record
`results/b83_icp_square.json`, which carries the configuration it ran under. Two
published benchmark rounds and two published price indices; nothing is estimated.**

## 0. The question this station answers

B79 showed that a comparison across periods and regions is a product graph and that
its square part has dimension `(|V_G| - 1)(|V_H| - 1)`, and registered a question:
is there a published space-and-time comparison whose links are dense enough to
identify that square part on its own? There is. The International Comparison Program
publishes a benchmark parity for each economy in each round, and the World Bank
extrapolates between rounds with a price index. Two rounds and two years close the
loop, and the square part is identified with one degree of freedom per economy.

**A scalar price field predicts every one of those loops is exactly zero.** If the
number attached to each (economy, year) is the difference of a potential, then
carrying an old benchmark forward by relative inflation returns the new benchmark
exactly, for every economy, with nothing free to fit. That is a point prediction and
it is not ours.

## 1. The loop

Positions are (economy, year). Four legs:

```
(a, t0) --- parity in round 0 ---> (base, t0)
(base, t0) --- base's price index t0 to t1 ---> (base, t1)
(base, t1) --- parity in round 1 ---> (a, t1)
(a, t1) --- a's price index t1 to t0 ---> (a, t0)
```

In logs the loop sum is

```
loop(a) = log P1(a) - log [ P0(a) * rel(a) ],
rel(a)  = ( I(a,t1) / I(a,t0) ) / ( I(base,t1) / I(base,t0) )
```

which is the log ratio of the new benchmark to the value the old one extrapolates to.
The base economy's own loop is zero by construction and is used as a short circuit.

**The two benchmarks have to come from the two rounds as each published them.** The
World Bank serves them as separate sources with separate update stamps, `ICP 2017`
last updated 2020-10-21 and `ICP 2021` last updated 2024-08-04, so the earlier
figures predate the later round and are not its back-revisions. The filled annual
series is not usable here: its 2017 value sits on the 2021 basis, which closes part
of the loop by construction.

## 2. The floor, measured

**Counting printed digits is not a measurement of the instrument.** In one source the
base economy prints `1` and China prints `4.18381118774414`; a floor read off those
digits differs by five orders of magnitude for two figures of the same provenance.
Round-tripping all 2,333 published values through float32 puts the worst of them
`5.94e-08` from a representable value, below half a float32 unit, so every figure is
a float32 printed long and the storage granularity is uniform. Over the loop's six
legs that is `7.14e-07`, and it does not bind.

**What binds is the choice of index.** The square is computed twice, once
extrapolating with the GDP deflator and once with the consumer price index, both of
which anyone would defend. The gap between the two readings is the floor. It does not
involve the benchmarks at all:

```
loop_deflator - loop_cpi = log( rel_cpi / rel_deflator )
```

so it is a property of the two indices and the two years. Across the carrier it runs
to `0.6484` with a median of `0.0344`, about 48,000 times storage. Fifteen economies
have no consumer price index over both years, take no measured floor, and carry no
verdict rather than being scored on storage alone.

A third component is not measured here and is registered: the deflator's own revision
between vintages, which needs two vintages of it.

## 3. What the readings are

181 economies carry all four legs. 38 more are named with the reason each is short,
which together is the 219 the three inputs mention.

| cell | count | verdict |
|---|---|---|
| clears its own measured floor | **77** | counts against the point prediction |
| does not clear it | 87 | no verdict |
| no measured floor | 15 | no verdict |
| the two rounds quote different currencies | 2 | no verdict |

Among the 77 the median square is `0.0824` in logs at a median of 4.2 floors, the
largest is Zimbabwe at `-4.1460` and 11 floors, and the deepest relative to its own
floor is 142 floors. **60 of the 77 are negative**: the new benchmark comes in below
what the old one extrapolates to, more often than not.

Zimbabwe is the extreme and it is the mechanism in the open. Its two benchmarks are
`0.5112` and `0.5414`, almost the same, while its relative inflation over the window
is 66.9, so the extrapolation predicts `34.21` and the round reports `0.5414`. Under
a hyperinflation the index and the benchmark stop being two views of one thing.

## 4. Two ratios that are conversions, not readings

Printing the squares as objects rather than counting them put two conversions at the
top of the list. Mauritania reads `-2.3579` and Croatia `-2.0712`, and neither is a
revision: the ouguiya was redenominated ten new for one old from 1 January 2018, and
the kuna was replaced by the euro at the fixed 7.53450, both between the two rounds.
The two rounds quote different units, so the ratio is a conversion factor and nothing
about the world has to have happened for it to be large.

**Net of the changeover they come back ordinary**, `-0.0553` and `-0.0517` against a
median square of `0.0643`, which is the check: a ratio blamed on units has to stop
being large once the units are taken out. Both are held out of the counted set and
carry no verdict, since correcting a parity is not reading one. Any other ratio
sitting near a conversion has to be named the same way or the criterion fails, so a
third changeover cannot be quietly counted as an obstruction.

## 5. The count, and a second route to it

With two benchmark years and 181 economies the closed form gives 180 independent
squares. The graph the published legs actually leave, built from the legs and not
from the rows that survived filtering, has 387 nodes, 566 edges and one component, so
its first Betti number is 180 as well. Building it from the legs is what lets the two
part company: an economy dropped by the row filter but still carrying its edges would
show up as a difference rather than agree by construction.

`rank(incidence) = 386` against `V - c = 386` is an implementation check and not a
second route, since the two are equal by a theorem.

## 6. Criteria

| | | |
|---|---|---|
| `B83-1` `instrument` | coverage closes | 181 carry all four legs, 38 named with a reason, 219 in the universe, none dropped silently and none counted twice |
| `B83-2` `premise` | the two benchmarks are two rounds, not one round back-revised | separate sources, stamps 2020-10-21 and 2024-08-04 |
| `B83-3` `instrument` | the floor is measured | storage `7.14e-07` over six legs from 2,333 values; index spread to `0.6484`, median `0.0344` |
| `B83-4` `rival` | a scalar potential predicts every square exactly zero | 77 of 164 countable squares stand at two floors or more; PASS means the point prediction is wrong here |
| `B83-5` `own_reading` | the independent count is `(T-1)(R-1)` | closed form 180, graph 180 |
| `B83-6` `own_reading` | the squares as objects | every square printed with its floor and its multiple |
| `B83-7` `instrument` | the degenerate square reads zero | base against itself, `0.00e+00` |
| `B83-9` `instrument` | a conversion is not a reading | 2 of 166 ratios sit near one, both named, both ordinary net of it |
| `B83-8` `bookkeeping` | the record carries what the others say it does | 181 rows at 12 fields, 38 reasons, 2 stamps |

**What each kind of failure would mean is not the same across the table**, so the
counts are not added: only `B83-4` is about a theory.

## 7. Scope

Two benchmark years and one series, gross domestic product at the global
purchasing-power-parity classification. Nothing here says which parity a statistical
office should publish, and nothing here is an error in the ICP: the square is the
quantity that has to be decided when two independently benchmarked rounds are spliced
into one series, and this station measures it rather than proposing a rule for it.
The 87 squares that do not clear their own floor are not zeros; they are readings the
choice of price index cannot be separated from.

**And the object measured is the published index, which is what the prediction is
about.** The number attached to each (economy, year) is an aggregate, and aggregation
can break transitivity on its own: a Fisher or Tornqvist index over commodities whose
underlying prices did come from one potential need not compose to zero around a loop.
**So a non-zero loop here refutes a potential on the published figures and does not by
itself place the non-exactness in the underlying per-commodity prices.** This station's
own binding floor is the choice of index, `0` to `0.6484` between the deflator and the
consumer price index, which is that same effect measured: **it is the reason the scope
line is load-bearing rather than decoration.** Whether the disaggregated field is exact
is a separate reading and no station has made it.

**One narrower point on the storage floor.** Round-tripping the published values through
float32 shows the granularity at which the figures are stored and printed. **It does not
show the accuracy of what was measured**, which could be coarser; the floor it gives,
`7.14e-07` over six legs, is therefore a lower bound on the noise and is used only as
one, and the binding floor is four orders of magnitude above it.
