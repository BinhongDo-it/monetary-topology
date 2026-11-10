# B153: triangle deficits in the British rail fares database, by fare setter

Script `experiments/b153_rail_triangles.py`, record `results/b153_rail_triangles.json`, which carries the
configuration it ran under, every knob point and the three route brackets. Inputs: one full issue of the Rail
Settlement Plan fares database (issue 917, generated 13 October 2026), the timetable issued with it (issue 988)
and the routeing guide (issue 1095), read under the field layouts of the published interface specifications
RSPS5045, RSPS5046 and RSPS5047, and a retail check of fifteen fares read by hand on the National Rail journey
planner on 27 October 2026. The packages and the files unpacked from them stay on the machine that holds them;
the record carries counts, shares, quantiles and public station names only, never a fare table, and a single
triangle appears with a band of `delta`, not its value.

## 1. What is read

For a ticket type `t` and three stations `o`, `b`, `d` that one public train calls at in that order, with
passengers able to join at `o`, leave and join at `b`, and leave at `d`,

```
delta_t(o, b, d) = f_t(o, b) + f_t(b, d) - f_t(o, d)        (pence)
```

`delta < 0` means two tickets split at `b` cost less than the through ticket. National Rail Conditions of
Travel, condition 14, allows a journey on two or more tickets when the train calls at the station where the
tickets meet, so both purchases carry the same movement.

**Leg price.** `f_t(x, y)` is the lowest live fare of ticket `t` among the flows that serve the leg: the origin
code is `x`'s own location code, its fare group (location record field 14), or a station cluster holding
either; the destination likewise; a flow marked reversible serves both directions; the fare carries no
restriction code. The flow that supplies the price is kept with its usage code (`A`, a fare actually set on the
flow; `G`, a flow constructed by concatenating other flows) and its fare setter, the `TOC` field of the flow
record ("The Fare TOC code of the TOC setting the fares on the flow", RSPS5045 4.1.2). A triangle's setter
count `k` is the number of distinct setters among its three supplying flows, 1, 2 or 3.

**Routes compatible with the train (the default).** Each triangle is read on the first calling sequence, in
sorted order, that yields it, and each leg is priced on that train. A flow with any route code is admitted when
the route's include and exclude locations (route file, location records, RSPS5045 4.20.3) are met by the
stations the train calls at or passes between the leg's two ends. Routes without location records are admitted
only when they read `NOT VIA LONDON` and neither the ends nor the path touch the London fare group; routes
restricted to one operator's trains (descriptions reading `ONLY`) are not admitted; a flow marked as priced via
London is admitted only when an end or the path touches the London fare group. A flow on a route code that puts
no condition on the journey (`00000`, printed `ANY PERMITTED`, and `01000`, printed as an empty route) is
admitted on any train.

**Ticket.** `SDS` (Anytime Day Single, standard class) by default. Its fares, like those of `SOS` (Anytime
Single), are all multiples of 5 pence.

**Floor.** A rival that holds fares to be differences of a scalar defined on stations, each rounded to the
5 pence grid, allows `|delta| <= 1.5 x 5 = 7.5` pence. That is the floor; it is a published printing format,
so it is read off the file and not estimated.

**Knob points.** Each knob is moved alone from the default and every criterion is read on every point:
ticket `SOS`; the lower of `SDS` and `SOS` leg by leg; point-to-point flows taking precedence over cluster
flows when both serve a leg; floors of 5 and 15 pence; de-duplication by the triple of supplying flows instead
of by station triple; and three route readings that price each station pair once, whatever the train: the two
no-condition route codes (`route_anyperm`), route code `00000` alone, and the no-condition codes widened by the
`NOT VIA LONDON` route on pairs with neither end in the London fare group.

**Route brackets.** Three readings that admit fares a passenger on a given train might not hold are printed
beside the knob points and do not enter any verdict: every route code on all three legs; every route code on
the through leg alone; and the no-condition route codes with via-London flows removed on pairs with neither end
in London.

## 2. Coverage

| quantity | count |
|---|---|
| flow records / fare records in the flow file | 723,590 / 7,780,689 (equal to the header's 8,504,279) |
| flows live on the generation date; flows starting after it | 695,296; 28,294 (none has ended) |
| live `SDS` fares indexed (usage `A` / `G`) | 378,134 (290,636 / 87,498) |
| `SDS` fares skipped for a restriction code | 86 |
| live locations, station clusters | 4,970, 2,473 |
| fare-setter records in the setter file; setter codes on the triangles read | 63; 28 on the default point |
| live routes; with include or exclude locations; reading `ONLY` | 1,387; 625; 169 |
| timetable schedules; not cancelled; closed by a terminating record | 516,498; 427,719; 427,719 |
| distinct public calling sequences | 17,520 |
| stations reached through the timetable's station file | 3,131 (no CRS code without a location record) |
| triangles (station triples on one train) | 877,680 |
| triangles with all three legs priced; of which all three legs supplied by `A` flows | 697,308; 696,531 |
| legs admitted after a check of the train's path; of which on a route code naming a route; flows turned away by the path | 572,294; 492,350; 138,228 |
| the same two counts on the `route_anyperm` reading | 487,377; 486,873 |

On the `route_anyperm` reading 70,210 of the 99,263 station pairs the triangles need are priced. The 29,053
left unpriced fall into four groups: `SDS` fares only on flows whose route code names a route, 20,671; `SOS`
fares and no `SDS`, 6,288; other ticket types only, 382; no live fare on any station, fare-group or cluster
code of either end, 1,712.

## 3. Criteria

Criteria come in kinds. `instrument` and `bookkeeping` ask about the tool and the record; `known_answer` is
a check whose outcome is fixed by a published rule; `own_reading` is a reading this station registers; `rival`
scores the scalar-potential point prediction and passes when that prediction fails.

| | criterion | reading |
|---|---|---|
| PASS | B153-1 `instrument` **files whole** | 52 unpacked members hashed, 0 differ from the package manifest; flow, ticket-type, setter and cluster files hold 8,504,279, 4,203, 149 and 43,751 records, each equal to its header and each ending on the end-of-file line; 427,719 open schedules, 427,719 closed |
| PASS | B153-2 `instrument` **retail check of five station triples** | 15 legs read on the retail journey planner: 14 Anytime Day Single prices equal the default-point price; on the fifteenth (Nottingham to Elsecar, through) the planner offers only an Anytime Single valid via Sheffield, and the fares database holds that fare on a flow with route `VIA SHEFFIELD` and ticket `SOS`, which the lower of `SDS` and `SOS` on the same train returns |
| FAIL | B153-3 `known_answer` **a `G` flow's fare is a sum of `SDS` flow fares** | 87,498 live `G` fares: an exact two-leg sum 22,386; 17,575 sit below the cheapest chain of two or more `SDS` flows of any length in the file; the rest are not met at two legs and reach at least the cheapest chain. A seeded sample of 2,000 of these was searched at three legs: 1,500 exact three-leg sums, 352 with none, 148 cut by the search's time cap. The 17,575 are read into classes in section 4 |
| PASS | B153-4 `rival` **scalar-potential prediction, delta = 0 within the floor, on triangles supplied by `A` flows** | 696,531 triangles; 693,464 beyond the floor (0.995597); 3,059 exactly zero; share beyond the floor from 0.987192 to 0.998783 over ten knob points |
| PASS | B153-5 `own_reading` **both signs clear the floor inside one setter's own table** | all priced triangles: 104,219 below -7.5, 3,077 within the floor, 590,012 above +7.5; on one-setter triangles supplied by `A` flows 75,680 below and 486,052 above |
| PASS | B153-6 `own_reading` **share below the floor is lower when one setter writes all three legs** | share of delta below -7.5 among `A`-flow triangles, `k = 1` against `k >= 2`: 0.134203 against 0.213720 on the default point, and lower on all ten knob points (table in section 4) |
| no verdict | B153-7 `known_answer` **railcard arm** | not run in this pass |
| PASS | B153-8 `bookkeeping` **config block and coverage table in the record** | both present |

## 4. Readings

**Against the scalar potential.** The prediction `delta = 0` holds on 3,067 of 696,531 triangles supplied by
`A` flows and fails on the other 693,464. Over the ten knob points the share beyond the floor runs from
0.987192 at the 15 pence floor to 0.998783 on `SOS`. The rival's premise, a scalar `phi` on stations with
`f(x, y) = phi(y) - phi(x)`, entails `f(o, d) = f(o, b) + f(b, d)` on every triangle; the published table does
not have that form.

**Sign and size.** Most triangles are positive: the through fare is lower than the two legs together, the
tapering a mileage-based scale produces. A minority are negative, which is the split-ticket saving. Inside one
setter's own table (`k = 1`) both signs clear the floor, so none of three one-sided readings holds there: a
table kept subadditive by arbitrage (`delta >= 0`), a scale tapering with distance (`delta >= 0`), and a through
ticket priced up for its wider rights (`delta <= 0`). On the default point the `A`-flow triangles split 104,021
below -7.5, 3,067 within and 589,443 above; delta quantiles in pence are 1% -1,600, 5% -500, 25% 140, 50% 280,
75% 410, 95% 890, 99% 1,600; of 37,744 through flows, 7,047 have their most negative split below the floor.

**By setter count.** The share of triangles below the floor rises with the number of setters on every knob
point:

| knob point | `A`-flow triangles | share below floor, `k = 1` | share below floor, `k >= 2` |
|---|---|---|---|
| default (routes compatible with the train) | 696,531 | 0.134203 | 0.213720 |
| ticket `SOS` | 19,726 | 0.293286 | 0.330954 |
| lower of `SDS`, `SOS` | 773,156 | 0.144961 | 0.262090 |
| point-to-point first | 695,673 | 0.134240 | 0.215363 |
| floor 5 pence | 696,531 | 0.134203 | 0.213720 |
| floor 15 pence | 696,531 | 0.130619 | 0.207770 |
| de-duplicated by supplying flows | 528,175 | 0.103889 | 0.194554 |
| no-condition route codes, every pair | 486,873 | 0.108482 | 0.177040 |
| route `00000` only | 66,981 | 0.120269 | 0.363104 |
| no-condition codes widened by `NOT VIA LONDON` | 537,157 | 0.112396 | 0.186902 |

The three route brackets point the same way: every route code on all legs 0.130419 against 0.250084; every
route code on the through leg alone 0.101929 against 0.132520; via-London flows removed off London 0.100566
against 0.161349.

Setter codes that the setter file ties to no carrier (31 of its 63 fare-setter records; `ATO`, `PGM`, `PSY`,
`PTW`, `PWM` and `PWY` appear on the triangles read) were dropped as a control: on the default point the two
shares become 0.148077 and 0.301985.

Exactly-zero triangles by setter count on the default point: 2,191 at `k = 1`, 829 at `k = 2`, 39 at `k = 3`,
against 563,923, 125,547 and 7,061 triangles.

**Inside one through flow.** On the default point 8,496 through flows have split points of both kinds.
Comparing, flow by flow, the share below the floor among its one-setter splits with the share among its
several-setter splits, the latter is higher on 1,429 flows, lower on 1,793 and equal on 5,274; pooled over
these flows the shares are 0.227655 (`k = 1`) and 0.195342 (`k >= 2`). Route `00000` alone (0.209499 against
0.249122), ticket `SOS` (0.200939 against 0.334630) and the every-route bracket read the other way, so the sign
inside one through flow moves with the settings and is not read. What holds on every knob point is the
cross-section above.

**Retail check.** Five triangles were drawn from the default point, each with all three leg prices equal to the
lowest `SDS` fare over every route code: Didcot Parkway, Swindon, Llanelli; Brockholes, Denby Dale, Barnsley;
Didcot Parkway, Bath Spa, Taunton; Nottingham, Chapeltown, Elsecar; Didcot Parkway, Bristol Temple Meads, Neath.
The fifteen legs were priced on the National Rail journey planner (single, one adult, no railcard, standard
class, travel date 28 October 2026, morning peak). The flag is computed from those stored readings against the
fares the station resolves on each leg's train. Fourteen Anytime Day Single prices are equal. On the
Nottingham to Elsecar through leg the planner shows an Anytime Single valid only via Sheffield and no Anytime
Day Single; the fares database carries that fare on a cluster-to-cluster flow with route code `00079`
(`VIA SHEFFIELD`, include location Sheffield) and ticket `SOS`. The train passes Sheffield, so the leg on that
train at the lower of `SDS` and `SOS` returns the price the planner shows. The draw compared each leg with the
lowest `SDS` fare only; where an `SOS` fare on a compatible route is lower, the planner sells that one, and the
`lower of SDS, SOS` knob point is the reading that prices it. On the Northern legs the planner listed cheaper
Advance fares first; their Anytime Day Single prices are the ones compared.

**Concatenated flows.** The fares database marks 174,662 flows `G`, constructed by concatenating two or more
other flows; 87,498 carry a live `SDS` fare. 22,386 of them meet an exact sum of two `SDS` flow fares at a
junction (a match counts when any pair of fares at the junction gives the sum, so this is an upper count). Of
the 47,535 not met at two legs whose fare reaches at least the cheapest chain, a seeded sample of 2,000 was
searched at three legs, and 1,500 meet an exact sum of three. 17,575 sit below the cheapest chain of two or
more `SDS` flows of any length the file holds between the same ends.

Those 17,575 were read into classes. Each class widens the set of fares the two-leg search may use by one
thing; a flow takes the first class that yields an exact two-leg sum. Beside each count is the number of exact
hits when every fare is raised by one 5 pence step, the level at which exact sums occur by coincidence on the
same index.

| widened by | exact two-leg sums | at fare + 5 pence | cheapest chain reaches the fare | flows classed |
|---|---|---|---|---|
| flows starting after the generation date (the next pricing round) | 40 | 120 | 1,038 | 40 |
| `SOS` fares as well as `SDS` | 1 | 0 | 463 | 1 |
| `SDS` fares carrying a restriction code | 0 | 0 | 12 | 0 |
| every standard-class single ticket (1,632 ticket codes) | 6,380 | 1,133 | 14,454 | 6,360 |
| none: the fare sits below every sum the file offers | | | | 11,174 |

The next-round fares give fewer exact sums than their own coincidence level, so the gap is not a matter of the
`G` fare having been set on the coming round's component fares. The standard-class singles give more than five
times theirs, and the tickets on those sums are mostly one leg of Bus Day Single (`BDS`) with an Anytime Day
Single, a Bus Day Single with a Family Single, a `NOT FOR TRAVEL` (`ZZY`) leg, ScotRail group fares and a child
flat fare. These are through fares to bus-linked destinations (Heathrow by bus, East Midlands Designer Outlet,
the Glasgow Airport express, MIRA Technology Park among them) that join a rail leg to a leg of another ticket.
The other 11,174 sit below every sum: 863 by up to 50 pence, 4,877 by 50 to 200, 4,843 by 200 to 500 and 591 by
more; the median `G` fare is 0.915 of its cheapest chain. 19 of them have no two-leg junction in the file at
all. 2,804 have a station cluster at an end, and the most frequent setters are `GWR` (2,624), `SWT` (1,858),
`NSE` (1,107) and `NTH` (1,011). The record names the first five flows of each class with their setter, route
code and a band of the gap. These flows stay outside the `A`-flow readings above.

## 5. Not covered here

The railcard arm (whether a proportional railcard discount closes every class-by-flow square outside the
exceptions the minimum-fare, non-standard-discount and status-discount files name) is not run in this pass.
Routes restricted to one operator's trains are not matched to the train's operator, and routes without
location records other than `NOT VIA LONDON` are not admitted on the compatible-route reading. The classes of
the concatenated flows are read at two legs; widened three-leg searches are not run.
