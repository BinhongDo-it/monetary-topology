# B146: filing stops, closures and cut edges on the mandi panel

A market town has two edges to everywhere else. Goods move on one. A price quoted
elsewhere arrives on the other. This station asks whether the daily mandi panel
(Agmarknet arrivals and prices, the same files B60 and B61 read) holds any market
for which a dated document cuts both edges at once, and sorts every candidate into
one of seven cells.

Scripts: `experiments/b146_stop_census.py` (the census of stops) and
`experiments/b146_double_cut.py` (event table, cells, readings, self-test).
Records: `results/b146_double_cut_lentil.json`, `results/b146_double_cut_cowpea.json`,
`results/b146_double_cut_white.json`, and the census of stops set against the event
documents in `results/b146_stop_census_lentil.json`, `results/b146_stop_census_cowpea.json`,
`results/b146_stop_census_white.json`, each carrying the configuration it ran under.
No data was collected for this station.

## 1. What a missing row is

A market files a row on a day it trades and its committee uploads. A missing row is
one of four different things, and the row count cannot tell them apart:

| the market | what is missing |
|---|---|
| traded, nothing uploaded | the record. The price formed |
| did not trade (holiday, strike, curfew, no means of settlement) | the price itself |
| could not move goods in or out | the transport edge |
| could not hear a price from elsewhere | the inbound information edge |

Only the last two describe the market's edges. A row leaving the market is an
outbound edge; whether a price from elsewhere can arrive is an inbound one, and the
panel is silent on it. So in this station the dates of an information cut come only
from named documents (orders to carriers, reports of an outage), and a filing stop
is one column of the panel.

One consequence follows from how the panel is built. The panel exists only where
markets file. A market that stopped filing leaves the two filings on either side of
the stop and nothing between. A reading inside a window can come only from a market
whose inbound edge was cut by a document while it went on filing.

## 2. The event table

Ten candidate events between January 2008 and June 2017. Six were checked against
press reports and a public tracker of shutdown orders; four were not checked and
carry no cell. The sources are listed with each row in the script and in the records.

An event is not one date. Each has several restrictions, each with its own start and
end, so every reading is indexed by the set of restrictions in force on a day. The
Manipur row, day by day:

```
2016-11-01 .. 2016-12-17    47 days   transport
2016-12-18                   1 day    transport, mobile data, curfew
2016-12-19 .. 2016-12-30    12 days   transport, mobile data
2016-12-31 .. 2017-03-19    79 days   transport
```

| event | transport document | information document and what it stopped | closure documents |
|---|---|---|---|
| Manipur highway blockade | 1 Nov 2016 to 19 Mar 2017, whole state | mobile data, 18 to 30 Dec 2016, two Imphal districts | curfew in the two districts, documented for 18 Dec |
| Madhya Pradesh farmers' strike | none with dates | mobile data, 6 to 11 Jun 2017, six districts | strike 1 to 10 Jun, statewide; curfew in Mandsaur 6 to 10 Jun |
| Lower Assam flood | highway under water 22 to 25 Sep 2014 (the last dated report; a lower bound), two districts | none found | none |
| Eastern Rajasthan rail and road blockade | 21 to 28 May 2015, five districts | none found | none |
| Darjeeling hills shutdown | from 15 Jun 2017, still on when the panel ends on 22 Jun | mobile data from 18 Jun, every internet service from 20 Jun, in the hills | none |
| Madhya Pradesh, November 2016 | none | none | markets shut for want of cash after large notes were withdrawn on 8 Nov; reports give five days to a fortnight |

The last row is the largest cluster of stops on the whole panel. No document cuts
either edge there. What went missing was the means of settlement, so no price formed.

## 3. The cells

A unit is a (market, event) pair in which the market filed at least five times in the
30 days before the event's first date. The mapping, printed by the script as it runs:

```
unverified             an edge document of the event is not checked           no verdict
ordinary               neither edge document covers the market                counted
T_cut_I_open           transport cut; no full information cut                 printed (B146-8)
T_open_I_cut           full information cut; no transport cut                 printed
object_absent          a closure covers it and it filed nothing in its        no verdict
                       window, or every filing there has zero arrivals
both_cut_read_inside   both documents cover it and it filed inside            read (B146-6)
both_cut_edges_only    both documents cover it and it filed nothing inside    read (B146-7)
```

An order that stops mobile data and leaves voice and fixed lines up makes the
inbound edge thinner. A price can still arrive by a phone call. It is recorded and
does not count as a cut. The count under the wider reading, where stopping every
data service counts as a cut with voice still up, is reported next to it.

`object_absent` exists so that a closed market is never read as an isolated one. A
strike that keeps produce away from the yard removes the price. It says nothing
about either edge.

## 4. Readings

Criteria come in kinds. `instrument` and `known_answer` ask about the tool,
`bookkeeping` about the record, `premise` about a fact the later criteria depend on,
and `own_reading` about a reading registered by this station. A `premise` that does
not hold leaves the criteria that depend on it without an object, and they carry no
verdict. This station registers no prediction of a rival account.

Lentil, 115,905 rows, 388 markets, 19 states:

| criterion | kind | state | reading |
|---|---|---|---|
| B146-1 | instrument | PASS | 10 files, 115,905 rows, none dropped |
| B146-2 | known_answer | PASS | on three fixed closure days the count of filing markets is 0.219 of the median of the 14 neighbouring days, below in 28 of 28 cells; on calendars shifted by -40, -20, -10, 10, 20 and 40 days the ratio is 0.867, 0.936, 1.035, 0.795, 0.904, 0.900 and the cells below number 7 to 18 of 27 or 28 |
| B146-3 | bookkeeping | PASS | 10 event rows, 6 checked, every field present; no unit of an unchecked row sits in a cell that reads |
| B146-4 | premise | FAIL | units under a checked transport document and a checked full information cut: 0. Counting a stop of every data service with voice up: 0. Counting any information order: 2 |
| B146-5 | own_reading | PASS | 199 units, one cell each: ordinary 127, T_cut_I_open 7, object_absent 65, both-cut 0, unverified 0. With the same documents moved back a week at a time, the two closures' shares of object_absent (0.347 and 0.448) are reached in none of 403 and 377 windows (medians 0.077 and 0.061) |
| B146-6 | own_reading | not read | no unit in the cell |
| B146-7 | own_reading | not read | no unit in the cell |
| B146-8 | own_reading | PASS | 7 units in 3 events; the Manipur tables are below |
| B146-9 | instrument | PASS | 12 of 12 knob points; both-cut units are 0 at every point; 4 units change cell, all between object_absent and ordinary |
| B146-10 | bookkeeping | PASS | 6 events with units, 199 units |

Cowpea (28,236 rows) has 2 units, both ordinary. White Peas (3,337 rows) has 5:
3 object_absent, 1 ordinary, 1 unverified. B146-4 is false on both and B146-8 has
no unit to print.

### 4.1 Where each event stops

| event | where it stops | count |
|---|---|---|
| Manipur 2016 | the information edge was thinned, not cut: mobile data only, two districts, 13 days. The four valley markets filed on 93, 92, 89 and 87 of the 139 blockade days, and Imphal resumed filing on 23 Dec while the order ran to 30 Dec | 4 units, all T_cut_I_open |
| Darjeeling 2017 | no market in scope. This is the one order among the ten that stopped every data service, and it overlaps the transport document. The panel has one market in the district, Siliguri, in the plains, and the orders name the hills. The two documents overlap on three days, and the panel has rows at scale on the first of them only | 7 active in the state, 1 in both documents by district, 0 in the hills |
| Madhya Pradesh 2017 | the price was absent. In the six districts under the order, all 9 active markets filed their last row between 22 and 31 May, before the order of 6 Jun. The stops line up with the strike that began on 1 Jun | 9 of 9 object_absent; 35 of 101 statewide |
| Assam 2014 | no document of an information cut | 2 units, T_cut_I_open |
| Rajasthan 2015 | no document of an information cut | 1 unit, T_cut_I_open |
| Madhya Pradesh 2016 | neither edge document exists; closure for want of cash | 30 of 67 object_absent |
| four unchecked candidates | no market active before the event on lentil or cowpea | 1 unit on white peas, unverified |

`object_absent` is a count by rule: a closure document covers the market, it filed
nothing in its window, and a stop of at least eight days lies over the closure. A
market that falls silent for a fortnight with no document anywhere meets the same
rule. So the count is set against the same documents moved back a week at a time to
the start of the panel, leaving out windows that overlap a closure document of the
state and windows with fewer than ten active markets:

| event | object_absent on the event's dates | shifted windows | median share | 90th percentile | highest | windows at or above the event's share |
|---|---|---|---|---|---|---|
| Madhya Pradesh 2017 (strike) | 35 of 101 (0.347) | 403 | 0.077 | 0.171 | 0.333 | 0 |
| Madhya Pradesh 2016 (no cash) | 30 of 67 (0.448) | 377 | 0.061 | 0.152 | 0.304 | 0 |

No shifted window reaches either event's share. At the median share about 12 of the
65 units (7.8 and 4.1) would sit in the cell in any window. The last filing before
the closure's first day: for November 2016, 19 of the 30 units last filed on 7 or 8
Nov and 11 between 20 Oct and 5 Nov; for the strike, 21 of the 35 last filed on 30
or 31 May and 14 between 18 and 27 May. For the 40 units whose last filing is within
two days of the closure, the stop and the closure begin together. The other 25 were
already silent when it began.

Stops come in clusters on this panel: on lentil, 191 clusters of at least three
markets of one state whose last filings fall within three days of each other
(stops of 8 days or more, markets with 10 filings in the 30 days before). Eight of
them fall on the documents of a checked event:

| rank by size | state | markets, of those active | first last filing | documents of the event it falls on | the cluster's markets in the districts each document names |
|---|---|---|---|---|---|
| 1 | Madhya Pradesh | 39 of 97 | 6 Nov 2016 | closure (no cash) | closure 39 of 39 |
| 12 | Madhya Pradesh | 8 of 119 | 31 May 2017 | closure (strike), mobile-data order | closure 8 of 8, order 2 of 8 |
| 30 | Madhya Pradesh | 6 of 96 | 2 Nov 2016 | closure (no cash) | closure 6 of 6 |
| 32 | Madhya Pradesh | 6 of 117 | 27 May 2017 | closure (strike), mobile-data order | closure 6 of 6, order 2 of 6 |
| 58 | Madhya Pradesh | 5 of 120 | 5 Jun 2017 | closure (strike), mobile-data order | closure 5 of 5, order 0 of 5 |
| 141 | Assam | 3 of 13 | 25 Sep 2014 | transport only | transport 1 of 3 |
| 181 | Manipur | 3 of 4 | 15 Dec 2016 | transport, mobile-data order, curfew | transport 3 of 3, order 2 of 3, curfew 2 of 3 |
| 191 | Madhya Pradesh | 3 of 120 | 10 Jun 2017 | closure (strike), mobile-data order | closure 3 of 3, order 0 of 3 |

A cluster is matched to an event by state and dates; the last column counts its
markets in the districts each document names. Seven of the eight have a closure
document that covers their markets. The Assam cluster has a transport document that
covers one of its three markets, and that market filed on each of the four days of
the document's window and stopped the day after. The cluster ranked 191 begins on
the day the strike ended. No cluster has a market under a document that cuts
communication outright. The other 183 clusters were set against no document; the
largest of them is 21 of 91 markets in Madhya Pradesh from 24 Mar 2015. With stops
of 15 days or more there are 31 clusters, and the three set against a document all
have a closure covering their markets.

Two statements follow, and their scope differs. The date a market stops filing does
not read the inbound edge: that holds by construction on any panel built from
filings. That a stop reads whether a price formed rests on the eight clusters set
against documents, seven of them closures, which is 8 of 191; for the other 183 the
panel cannot tell a closed market from one that traded and uploaded nothing.

Communication can also go down physically. Four storms and floods inside the
panel's span (Odisha 2013, north Andhra 2014, Chennai 2015 and 2016) were screened
on activity alone: none of the three commodities has a market with five filings in
the 30 days before any of them.

The conditional registered for the both-cut cell is: if both edges of a market are
cut by named documents and it still forms a price, the dispersion of prices across
such markets does not fall back and grows. Its antecedent does not occur on this
panel, so the conditional was not tested here.

### 4.2 Transport cut, information open: Manipur, 139 days

The reference is the median log modal price on the day over every series outside
the state: 8.572 in the 60 days before the blockade, 8.423 inside it, 8.287 in the
60 days after. Valley prices are printed on a grid of 1,000 rupees, about 0.091 in
logs. `h` is the local log price less the reference. The reference's own move from
one day to the next inside the window has a median of 0.027 and a 90th percentile of
0.357, because the set of series behind the daily median changes; the readings below
use weekly means and medians over the window, never a pair of single days.

| market | filings inside | median price before / inside / after | h before | h inside | h after | median arrivals before, inside |
|---|---|---|---|---|---|---|
| Bishenpur | 93 | 12,500 / 11,500 / 10,500 | 0.824 | 0.912 | 0.992 | 0.4, 0.4 |
| Lamlong Bazaar | 92 | 9,500 / 10,500 / 10,500 | 0.602 | 0.808 | 0.910 | 0.25, 0.2 |
| Imphal | 89 | 10,500 / 10,500 / 9,500 | 0.670 | 0.833 | 0.887 | 5.8, 3.0 |
| Thoubal | 87 | 11,500 / 11,500 / 10,500 | 0.722 | 0.911 | 0.970 | 0.6, 0.5 |

- Over the 139 days the reference fell by 0.149. Two valley prices did not move, one
  rose one grid step and one fell one.
- In the 60 days after the blockade was lifted, three of the four fell one grid step.
- Arrivals at Imphal, the only market of the four whose arrivals per filing exceed one unit,
  halved between the filings of 29 and 30 Nov 2016, 29 days into the blockade
  (5.5 and 2.8 on those two days; medians of 5.7 before the split and 2.9 after),
  and had not come back when the window closed. In the 60 days after the blockade
  was lifted the median is 3.9.
- The weekly dispersion across the four (median absolute deviation of log prices)
  has a median of 0.087 before and 0.042 inside. Both are under one grid step.

The reference is a choice, so the change in `h` inside the window is computed once
per definition: all varieties pooled, and each variety with at least 500 outside
rows in the window. The fixed-composition column holds the set of series fixed
(series with ten filings in each of the three segments; the median of their own
changes). A change is read only where every definition gives one sign and every
one exceeds the price grid of 0.091, with at least two definitions and a window of
at least 30 days; the Assam and Rajasthan units (windows of 4 and 8 days, one
definition) are printed and not read. The segment before the window runs in whole
weeks from the Monday of the week that holds the sixtieth day before it.

| reference | outside rows come from | move inside | fixed composition (series) | Bishenpur | Lamlong Bazaar | Imphal | Thoubal |
|---|---|---|---|---|---|---|---|
| all varieties | every other state | -0.149 | -0.167 (100) | +0.088 | +0.205 | +0.163 | +0.189 |
| Other | Madhya Pradesh, Uttar Pradesh, West Bengal, Rajasthan, Maharashtra and four more | -0.162 | -0.174 (64) | +0.096 | +0.209 | +0.178 | +0.189 |
| Masoor Gola | Uttar Pradesh, Madhya Pradesh, Chhattisgarh | -0.109 | -0.169 (18) | +0.037 | +0.175 | +0.133 | +0.158 |
| Masur Dal | Assam, West Bengal, Jharkhand, Kerala | -0.051 | -0.032 (13) | -0.020 | +0.096 | +0.069 | +0.066 |
| state | | | | unread (sign changes) | **read** | unread (under the grid once) | unread (under the grid once) |

The four valley series are labelled Other. Their level sits next to the Masur Dal
series of the eastern states (`h` of 0.08 to 0.30 before the window against that
reference, 0.65 to 0.87 against Other).

Windows of the same 139 days that end before the blockade begins, one starting every
30 days, give the same table with nothing cut:

| market | windows | outside moved a grid step or more | of those, local median price within one of its own steps | of those, unmoved | arrivals ratio in the blockade | lowest ratio in a placebo window | placebo windows at or below the blockade's ratio |
|---|---|---|---|---|---|---|---|
| Bishenpur | 7 | 5 | 4 | 2 | 1.000 | 0.429 | 4 |
| Lamlong Bazaar | 10 | 6 | 5 | 4 | 0.800 | 0.500 | 1 |
| Imphal | 21 | 11 | 9 | 7 | 0.517 | 0.949 | 0 |
| Thoubal | 8 | 5 | 5 | 2 | 0.833 | 0.643 | 4 |

The windows overlap. Five of Imphal's 21 do not overlap one another, and their
ratios are 1.231, 1.056, 0.949, 1.018, 1.018.

- On the quantity side Imphal stands apart from its own history: its arrivals ratio
  of 0.517 is reached in none of 21 windows before the blockade.
- On the price side it does not. A local price that stays within one step while the
  outside moves by a grid step is what these four series do in most windows with
  nothing cut, and a price printed in steps of 1,000 rupees is the direct reason.
- The change in `h` is read in one market of four, Lamlong Bazaar, +0.096 to +0.209.

The placebo windows all end before the blockade, so none of them holds 8 Nov 2016,
when large notes were withdrawn nationwide, seven days into the blockade's window.
The same calendar window at every market outside the state (ten filings on each
side) gives the cross-section, with the same window a year earlier next to it:

| window | markets outside the state | median arrivals ratio | at or below Imphal's 0.517 | where |
|---|---|---|---|---|
| 1 Nov 2016 to 19 Mar 2017 | 103 | 1.000 | 12 (11.7%) | Madhya Pradesh 9 of 55, Uttar Pradesh 3 of 24; none of the 24 markets of six other states, Assam (9) and West Bengal (7) among them |
| the same window a year earlier | 78 | 1.092 | 6 (7.7%) | Madhya Pradesh 2 of 33, Uttar Pradesh 4 of 17 |

The halving at Imphal lies outside its own two years of history, and about one
market in nine elsewhere shows as large a fall over the same window, all of them in
two states far from Manipur. The split falls 29 days into the blockade and 22 days
after the withdrawal of notes, on no start or end date of a restriction. The
blockade and the withdrawal are not separated on this panel.

The two sides are recorded apart. With the transport edge cut and information open,
the quantity on that edge falls and stays down while the cut lasts; Imphal reads in
that direction, as one event and one market, with the withdrawal of notes inside the
same window. On the price side no direction is registered, and the tables are
printed.

### 4.3 The knob sweep

Activity floor 5, 10, 15 filings; stop floor 8, 15 days; cluster window 3, 7 days.
The number of both-cut units is 0 at all 12 points. Raising the stop floor to 15
days moves four Madhya Pradesh units from object_absent to ordinary, because their
stops are shorter than 15 days. The size of the November 2016 cluster runs from 8
to 59 markets across the sweep (49 at the default point), which is why it is
reported as a table and not as one number.

## 5. Scope

- The independent unit is the event. Six events carry units on lentil. Nothing here
  is pooled into an estimate.
- Sources for the event dates are press reports and a public tracker. Where two
  reports give different dates both are noted in the event row.
- The end of the Assam transport window is the last dated report of the closure.
  The Darjeeling row leaves Siliguri out by hand, because the panel resolves to the
  district and the orders name the hills.
- The both-cut cell needs a carrier this panel does not have: a place whose trade
  and communication were both cut by dated documents and which went on forming a
  price that someone recorded.

## 6. Self-test

`python experiments/b146_double_cut.py --selftest` runs a fixture with a known
answer (a closed and silent market reads back as object_absent, a filing market
under both documents as read-inside, a silent one with no closure as edges-only),
then hands each criterion an input that must fail it: an empty directory, a shifted
calendar, a checked row with no source, an event with its information document
removed, a classifier blind to closures, identical prices, two markets, a reference
that does not move, a missing market, a sweep one point short, an event count above
the unit count. The reference table, the fixed-composition reference, the placebo
windows, the cross-section, the shifted closure windows, the reference's daily move
and the marking of clusters by district each have a fixture with a planted answer.
Planted changes to the implementation were run in three rounds; each change the
fixtures first let through was given a fixture of its own, and all are now caught.
