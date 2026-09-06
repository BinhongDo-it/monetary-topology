# B35 pre-registration: one animal, two outputs, and the two anchors sit in different countries

The framework says a price lives on an edge, and that the edge which carries it
runs to whatever the local substitution graph anchors against. A joint
production process makes a clean test of that, because it puts two outputs into
the world at the same instant from the same input, and their substitution
graphs can sit in different countries.

Slaughter is such a process. Muscle cuts have a thick substitute class in the
producing country and in the importing one. Parts that the producing country
does not eat have no substitute class at origin, and a thick one at the
destination. If the price of a good is set where its substitutes are, the two
outputs of one animal must respond to shocks in different countries.

A cost account of prices says otherwise: both outputs come off the same carcass,
so a shock to the cost of raising it moves both, and a shock at the destination
moves neither beyond ordinary demand.

## 1. Criteria

The station registers two load-bearing arms pointing in opposite directions and
one structural arm that runs before them.

| arm | shock | cost account predicts | anchor account predicts | FAIL |
|---|---|---|---|---|
| **B35-5** (load-bearing) | a dated move at the destination | neither output moves | the no-substitute part moves, the substitutable one moves far less | both move by a similar factor, or the no-substitute part does not move |
| **B35-6** (load-bearing, reversed) | a dated move at origin | both move together | the substitutable part moves, the no-substitute one moves far less | both move by a similar factor |
| **B35-7** (structural, runs first) | none | | check part by part whether origin has a substitute class, with a citable source | a part whose origin substitute class is thick leaves the station |

Three states: pass, FAIL, and **undecidable** (the reading falls inside the
band below, or a month fails the minimum-volume floor).

**B35-5 and B35-6 point in opposite directions, and that is where the station's
force is.** Either one alone admits other explanations. Both together separate
the cost account from the anchor account.

Two further arms are registered and scored separately:

| arm | question |
|---|---|
| **B35-4** | the same good sold to a self-sufficient destination and to an import-dependent one should track origin conditions less in the first |
| **B35-8** | one part sold to two or more destinations with different local substitution graphs: read the cross-destination dispersion |

**Scale fixed in advance**: log changes. Levels are printed beside them; the
verdict reads the logs, because the two series differ by an order of magnitude
in base and a common inflation would manufacture a difference in levels.

**Ratio band**: if the two log responses fall within a factor of 1.5 of each
other, B35-6 is FAIL. The anchor account asks for a difference in magnitude,
not a difference in sign, so a reading of "both rose and one rose a bit more"
must not be read as a pass.

The pre-registration design is the ordinary one: the criteria are written into
the script that produces the record, the record carries the criterion text, and
every quantity a run produced is reported.

## 2. Gate arithmetic

**This station has an estimator and a band, so gate two (`D14`) and gate three
(`D17`) both apply.** They are computed, not asserted.

| gate | how it is met |
|---|---|
| `D14` gate two | `1.645 x se(difference of the two slopes)` against the band half-width `log 1.5 = 0.4055` |
| `D17` gate three | power at the registered effect, floor 0.50, which is the same inequality as gate two |
| `D24` gate six | the measured resolution floor, from pairs the theory says should not differ |
| `D22` | the number of independent steps among the adjacent monthly changes, measured rather than assumed |
| `D18` gate zero | how many destinations the part actually has |

Critical value `1.645` throughout, the same constant used elsewhere in this
work. Undecidable band `1.4 < |t| <= 1.9`.

## 3. Reachability

| branch | reachable | why |
|---|---|---|
| both outputs move together | yes | that is what the cost account looks like when it holds |
| the no-substitute part does not move | yes | if the shock did not reach that line |
| a part leaves on the structural arm | yes | offal goes into pet food and industrial uses, which is a substitute class at origin |
| undecidable | yes | unit value is a composite quantity |
| gate zero closes the arm | yes | a part may have only one destination |

All branches are reachable.

## 4. Carrier and definitions

```
carrier      US export unit values by ten-digit code, by month, by destination
             value and quantity both pulled, unit value = value / quantity
             one source, one query, so the two series share a definition

poultry      0207140045 paws         no substitute class at origin
             0207140010 leg quarters thick substitute class at origin
             destination China, window 2020-01 to 2023-11

origin leg   USDA AMS wholesale broiler composite, monthly
             history begins 2022 for parts, which is why the composite is used

pork         0206490010/20/30/40/50/90, six ten-digit codes
             four named single parts used for same-level comparison:
             tongues, hearts, feet, head meat
             0206490090 NESOI excluded, a mixed basket, composition not
             comparable across destinations
             0206490050 skins excluded, only sixteen months of that window
             (2022 full year, China leg has four months, the two figures agree)

floors       minimum monthly volume 25,000 kg, registered before any unit value
             was read
             unit values pile up on whole and half cents per pound, so the
             resolution grid of any unit-value reading is 0.011 to 0.022 $/kg

destinations region aggregates must be stripped: keep country codes that are
             four digits and do not begin with 00
```

**Mixing risk is real, not defensive.** Within one heading the unit value runs
from $0.79 to $2.42, a factor of three, so a heading whose composition can shift
cannot carry a price reading. This is why the comparison is run at ten digits
and why the residual code is excluded.

## 5. Superseded registrations

The station changed carrier twice, and both moves are on record.

| original | question | now asked by |
|---|---|---|
| B35-1 | destination-side shock, bovine carrier | B35-5 |
| B35-2 | origin-side shock, bovine carrier | B35-6 |
| B35-3 | which parts have no substitute class at origin | B35-7 |

The first move was forced at step zero: the heading for edible offal is not
bovine, and on the China leg it is 99.8 per cent swine by value, because that
market was shut to US beef for fourteen years. The second move followed the
shock: African swine fever is a swine shock, and the original design had paired
it with a bovine carrier. Both are recorded in the results document, together
with the readings they produced.
