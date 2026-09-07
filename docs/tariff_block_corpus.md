# The counting law on the national tariff schedules of a global survey

**Read 2026-09-03.** Script `experiments/tariff_blocks_count.py`, record
`results/tariff_blocks_count.json`, input `data/raw/falling_short_layout.txt`.
Source: the residential annex of a published global survey of electricity tariff
design, giving per country the number of blocks in the residential schedule and the
charge on each.

**This is the counting law's third corpus and its first cross-country one.** The
first is a set of historical monetary decrees; the second is one commercial rating
plan in force. **This one is fifty-three national procedures at once, each
published, each stating both its blocks and its values.**

## Why a block tariff is the law's plainest object

The law says a published procedure that partitions a set produces as many values
as it writes **distinct** class values, and not as many blocks as it draws. **A
block tariff states both numbers itself.** The schedule declares how many blocks it
has and then prints a charge against each, so the two quantities the law separates
are printed side by side, in the same table, by the party.

**Nothing has to be inferred, estimated or modelled.** The reading is a count of
printed numbers.

## The reading

| | |
|---|---|
| country rows recovered | **64** |
| schedules with a block structure | **53** |
| rows dropped as unparsable | **0** |
| **blocks drawn** | **179** |
| **distinct values written** | **156** |
| collisions | **23**, 12.8 per cent of blocks |
| **schedules writing fewer values than blocks** | **15 of 53**, 28.3 per cent |

**The two distributions, and the second sits to the left of the first:**

| count | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **blocks** | 11 | 8 | 15 | 5 | 4 | 4 | 5 | **1** |
| **values** | **13** | 10 | 13 | 8 | 4 | 3 | 2 | **0** |

**Eleven countries draw one block and thirteen produce one value. One country draws
eight blocks and none produces eight values.**

## The parse is checked against the survey's own two counts, and hits both

**The survey states that it covers more than sixty countries**, and the annex parse
recovers **64 country rows**.

**The survey states that the mean number of blocks across its block-tariff countries
is four.** This parse gives **4.000** over the forty-two multi-block schedules, which
is 168 blocks over 42 schedules exactly. **A parse of a column-aligned table can be
silently wrong in a way that still produces plausible rows**, and these are the two
numbers in the document that catch that.

**On the same forty-two schedules the mean number of distinct values is 3.452**,
thirteen point seven per cent below the mean block count. **The block count is what the survey
reports and what the literature reports. The value count is not reported by
anyone.**

## The three largest gaps between blocks drawn and values written

**These are the three largest gaps, and they are not the three strongest readings.**
The section on what the printed resolution forces takes them apart, and two of the
three turn out to be exactly the cases the two-decimal grid explains on its own.

| country | | |
|---|---|---|
| **Philippines** | **8 blocks, 4 values** | the most elaborate structure in the corpus, and five of its eight blocks carry the identical charge |
| Ethiopia | **7 blocks, 3 values** | one charge appears four times |
| **Australia** | **3 blocks, 1 value** | typed in the source as a declining block tariff. **It does not decline** |

The other twelve: Bangladesh 6 to 4, Egypt 7 to 6, Iran 7 to 6, Lebanon 6 to 5,
Morocco 6 to 5, Bolivia 5 to 4, Honduras 5 to 4, Mozambique 4 to 3, Guinea 3 to 2,
Myanmar 3 to 2, Senegal 3 to 2, Greece 2 to 1.

## What this measures, and the limit is a resolution one

**The survey rounds charges to two decimals.** Five printed charges of the same
two-decimal number may be five different underlying rates. **So the twenty-three
collisions are an upper bound at the published resolution, not a measurement of
equality in the underlying schedules.**

**What it does measure exactly is what a reader of the published table can
distinguish**, which is the quantity the law is about when the published table is
the procedure. **Where the schedule is the published document, the published
resolution is the procedure's resolution.** Where it is a summary of a finer
document, it is not, and this corpus is the second case.

**The resolution can be removed as a limit** by taking the schedules from the
national regulators that publish them rather than from the survey, at four
significant figures instead of two. **That is a collection, not a re-reading, and
it has not been done.** The next section says which schedules that collection
should start from, and it is not the three above.

## How much of the collision count the printed resolution forces

**This is arithmetic on the numbers already parsed and it cost nothing.**

A schedule whose own printed charges span three cents cannot write one value per
block if it draws eight blocks, because a two-decimal grid holds four points inside
three cents. **That part of the collision count is forced and carries nothing.** The
rest is not forced: those blocks had grid points available and still printed the
same number.

**Ceiling** is the count of two-decimal grid points inside the schedule's own printed
span. **Forced** is `blocks - ceiling` where that is positive. **Excess** is the
collisions the ceiling does not account for.

| | |
|---|---|
| collisions | **23** |
| **forced by the two-decimal grid** | **11** |
| **not forced** | **12** |

| country | blocks | values | span | ceiling | collisions | forced | excess | top charge |
|---|---|---|---|---|---|---|---|---|
| **Bangladesh** | 6 | 4 | 0.08 | 9 | 2 | 0 | **2** | 0.12 |
| Bolivia | 5 | 4 | 0.09 | 10 | 1 | 0 | **1** | 0.09 |
| Egypt | 7 | 6 | 0.09 | 10 | 1 | 0 | **1** | 0.10 |
| Guinea | 3 | 2 | 0.02 | 3 | 1 | 0 | **1** | 0.03 |
| Honduras | 5 | 4 | 0.09 | 10 | 1 | 0 | **1** | 0.16 |
| Iran | 7 | 6 | 0.11 | 12 | 1 | 0 | **1** | 0.13 |
| Lebanon | 6 | 5 | 0.11 | 12 | 1 | 0 | **1** | 0.13 |
| Morocco | 6 | 5 | 0.07 | 8 | 1 | 0 | **1** | 0.18 |
| Mozambique | 4 | 3 | 0.09 | 10 | 1 | 0 | **1** | 0.12 |
| Myanmar | 3 | 2 | 0.02 | 3 | 1 | 0 | **1** | 0.06 |
| Senegal | 3 | 2 | 0.02 | 3 | 1 | 0 | **1** | 0.23 |
| **Ethiopia** | 7 | 3 | 0.02 | 3 | 4 | **4** | 0 | 0.03 |
| **Philippines** | 8 | 4 | 0.03 | 4 | 4 | **4** | 0 | 0.21 |
| Australia | 3 | 1 | 0.00 | 1 | 2 | 2 | 0 | 0.26 |
| Greece | 2 | 1 | 0.00 | 1 | 1 | 1 | 0 | 0.14 |

**The two largest gaps in the corpus are the two the grid explains in full.**
Ethiopia prints its whole residential schedule between one and three cents, so
three values is every value a two-decimal grid can hold there, and seven blocks
cannot produce more than three however the underlying rates fall. The Philippines
prints eight blocks inside a three-cent span. **Neither collision is evidence about
the schedule. Both are evidence about the reporting precision.**

**The ceiling is read off the schedule's own printed span, so for a schedule that
prints every block at the same charge it is one by construction.** Australia and
Greece are that case, and the two rows are flagged in the record. **The grid is not
explaining them, it is being handed the answer.** What is independent about those
two is the level: Australia prints at 0.26, the highest in the table, so a declining
block tariff that actually declined would have to decline by under half a cent on a
twenty-six cent rate to hide inside the rounding. **That makes Australia the
strongest of the fifteen, and the survey types it as declining.**

**So the collection order inverts.** Australia and Greece first, because their claim
is the sharpest and the grid does not touch it. Then the eleven schedules carrying
the twelve unforced collisions, highest charge first, since the grid is finest
relative to the level there: Senegal, Morocco, Honduras, Iran, Lebanon, Bangladesh,
Mozambique, Egypt, Bolivia, Myanmar, Guinea. **Ethiopia and the Philippines last**,
because the printed answer there is already determined and collection would only
replace a forced number with a free one.

**A second check ran with it.** Distinct values counted on the printed strings and on
the rounded floats must agree, or a schedule printing `0.1` in one cell and `0.10` in
another would be split into two values by the string count. **Rows disagreeing: zero.**

## The collection was started at Australia, and it returned three facts about the survey instead

**Started 2026-09-03 on the schedule the section above puts first.** It did not reach a
national schedule, and the reason it did not is itself the reading.

**The survey states its own scope**: tariffs are taken for **the largest electric
utility by customer base serving the largest business city**. For Australia that is
Sydney, inside one distribution zone, served by a competitive retail market. **So the
row is one retailer's published offer, and the survey does not print which retailer.**

**Two Sydney residential three-step schedules were read for structure**, both from the
period:

| schedule | step boundaries as written | direction | printed precision |
|---|---|---|---|
| one retailer's Ausgrid-zone standing offer, effective 1 July 2015 | first `10.9589` kWh/day, next `10.9589` kWh/day, remainder | **each step costs more than the one before** | cents/kWh, two decimals, GST-exclusive and GST-inclusive columns |
| the regulated residential price the regulator published for the Ausgrid-zone incumbent | first 1,000 kWh per quarter, next 1,000 kWh per quarter, remainder | **later steps cost more** | cents/kWh, **four decimals** |

**Neither matches the boundaries the survey prints.** `10.9589` kWh/day annualises to
4,000 kWh and monthly to **333.3**, which is the survey's first boundary to the digit.
Both schedules put the second boundary at twice the first, monthly **667**, and the
survey prints **583**. So the survey's row is a third schedule, cumulative boundaries
1,000 and 1,750 kWh per quarter, and which retailer published it is not stated.

**Three facts came out of this, and all three are about the instrument.**

1. **The unit is wrong by two orders of magnitude.** These schedules print
   cents/kWh to two and four decimals. The survey prints USD to two decimals, near
   0.26. **A schedule separating its steps in the fourth decimal of a cent cannot
   survive that rounding**, and both schedules read do separate their steps.
2. **Both schedules read are increasing, and the survey types Australia declining.**
3. **The same type label appears on Australia in the commercial annex, where the row
   carries three time-of-use charges and no demand charge.** A label reading
   "declining block" sits on a row printing three time-of-use prices. **So that column
   is not being read off the schedule for this country, in either annex.**

**What this does to the reading at the top.** The Australia collision is
**most likely a rounding artefact**, and the sharpest sentence in this document, that
a schedule typed as declining does not decline, **is superseded**: the type label is
not a reading of that schedule. The collision count of 23 and the eleven-forced split
are unchanged, because both are counts of what the survey prints.

**The queue moves to Greece.** Greece prints two blocks at 0.14 with the boundary at
6.4 times average consumption, so it is degenerate on both readings, **and its carrier
is a single national schedule published by one utility rather than one offer chosen out
of a competitive retail market**. The identification problem above does not arise there.

## Greece, the second station, and it closes the collection

**Read 2026-09-03.** Greece is the case the identification problem above does not
touch: one national residential tariff, published by one utility, on its own page.
**Three readings, and the third needs no collection at all.**

**One. The two blocks do not carry the same rate.** The utility's own published G1
schedule prints a competitive energy charge per block, to five decimals in euros:

| effective | 0 to 2000 kWh | above 2000 kWh | ratio |
|---|---|---|---|
| the utility's published schedule, 1 January 2021 | `0.11058` | `0.11936` | 1.079 |
| an undated teaching copy of an earlier vintage | `0.0946` | `0.10252` | 1.084 |

**Two independent copies, two vintages, and the second block is about eight per cent
dearer in both.** The survey prints both blocks at `0.14` USD. **Eight per cent at
that level is roughly one cent, which is one step of the survey's grid**, so the
collision is what the rounding does to a schedule that separates its blocks in the
third decimal of a euro.

**Two. The block boundary is not monthly.** The published schedule defines 2000 kWh
as the **four-month** total consumption, in its own words the
`συνολικό ύψος της 4μηνιαίας κατανάλωσης`. The survey divides that boundary by a
**monthly** average consumption of 310.6 kWh and obtains 6.44. **On a common period
the boundary is 500 kWh a month against 310.6, which is 1.61.** Greece still does not
put its first block below average consumption, **but it moves from a structure that
does nothing to a first block a little above average**, which is an ordinary design.

**Three, and this one is free.** The survey types Greece **IBT**, and its own text
says what an IBT is for: a discounted first block paid for by surcharges on the
largest consumers. **A schedule whose blocks all carry one price does not run that
mechanism.** So the row types itself as something the numbers on the same row cannot
be. **The contradiction is inside one row of one table and needs no collection.**

### The two collisions that are total, and the thirteen that are partial

**This split is the useful one, and it was not visible before the two stations.**

| | schedules | collisions | what the row's own type label says |
|---|---|---|---|
| **all blocks at one price** | Australia, Greece | 3 | **contradicted by the row itself.** A declining or increasing block tariff with one price is neither |
| **some blocks share a price** | the other thirteen | 20 | **not contradicted.** An increasing block tariff is non-decreasing, and a flat step inside it is allowed |

**Both totals were taken to the source and both are rounding.** Greece separates its
two blocks by eight per cent; the two Sydney schedules read for Australia both
increase. **Neither carrier prints the equality the survey prints.**

### What this makes the corpus a reading of

**The survey is not the procedure. It is a two-decimal transcription of fifty-three
procedures**, and the two cases taken to source both show the transcription creating
an equality the source does not have. **So the twenty-three collisions are a property
of the transcription.**

**That does not empty the reading, it relocates it.** The transcription is itself a
published procedure: it is cited, it is served by a public database, and a reader
computing from it gets what it prints. **It draws 179 blocks and writes 156 values,
and 156 is what any reader of it can distinguish.** The counting law's claim is that
those are two different numbers and that the second is smaller, and on this object
that is exactly what is measured. **What the corpus cannot do is carry that reading
back onto the fifty-three national schedules**, and the resolution paragraph above
said so before either station was run. **It is now measured rather than stated.**

### The eleven unforced collisions are registered, not collected

**They are not being taken to source, and the reason is arithmetic rather than
interest.** Thirteen schedules, each needing its own regulator or utility page, in as
many languages. **What comes back is eleven binary answers**, and the two already
taken both came back the same way, from the same cause, which is one instrument
rounding every row identically. **The prior that the eleven agree with them is not
something the eleven can move much.**

**Registered for anyone who wants them**, highest charge first: Senegal, Morocco,
Honduras, Iran, Lebanon, Bangladesh, Mozambique, Egypt, Bolivia, Myanmar, Guinea.
**The one that would change the reading is a schedule printing two blocks at an
identical rate in its own currency at full precision.** Greece and Australia were the
two candidates for that and neither is one.

## A second reading off the same table, and it cost nothing

**The survey states design principles alongside the survey**, among them that the
first block should fall **well below** average consumption, so that a majority of
customers do not sit inside it. **The same annex prints both quantities**, the
first block size and the average monthly consumption, so whether a schedule
satisfies the principle is a division.

| reading of "well below" | satisfies | does not |
|---|---|---|
| the loosest, first block below average | **25 of 42**, 60 per cent | 17 |
| **taking "well below" at half** | **14 of 42**, 33 per cent | 28 |

**Ratio from 0.12 to 6.44, median 0.74.** The largest are Greece at 6.44, Yemen at
3.11, Cameroon at 3.05 and Myanmar at 2.54.

**The largest of those is a period mismatch, and the others are unchecked for the same
thing.** Greece's boundary is a four-month total and the consumption it is divided by
is monthly, so 6.44 is a ratio of two different periods and the like-for-like figure
is 1.61. **The survey converts some boundaries to a monthly basis and not others**:
Australia's printed 333 is already an annual 4,000 divided down, while Greece's 2000
is the raw four-month figure. **So a large ratio is a flag to check that country's
billing period before it is read as a structure that does nothing**, and the four
above Greece's are unchecked.

**Greece was read as degenerate on both readings at once**, two blocks priced
identically at 0.14 and a boundary 6.4 times average consumption. **Both halves are
superseded by the Greece section above**: the source schedule separates its two blocks
by eight per cent, and the boundary is a four-month total, giving 1.61 rather than
6.44. **The degeneracy was the instrument in both halves, and it took one published
schedule to see it.**

### What this reading is, and it is weaker than it first looks

**The principle is stated by the surveying body in the survey itself.** There is no
evidence here that the countries were told to follow it, or that they saw it. **So
this measures how often published schedules satisfy a principle a multilateral body
states, and not whether a rule reached its receivers.**

### The lookup that would have promoted it was done, and it closes the arm

**To make it a propagation reading the principle has to appear in a document
addressed to those countries and dated before their schedules.** That lookup was
done on 2026-09-03 across three classes of source, and the arm closes.

| class of source | what is there |
|---|---|
| the citation attached to the statement itself | **none.** The rule is the surveying body's own normative sentence, carrying no reference |
| the survey's literature review and bibliography | the underlying critique has an earlier source, a 2005 multilateral monograph and two papers, **all published to the world** |
| country-by-country tariff studies | they exist, but the ones reachable are contemporaneous or later, 2015 and 2020, **and cannot be the source of the 2015-16 schedules** |

**The second row is what closes it, and it closes it before any collection cost.**
A published source has no non-receivers. **Every country could read it, so the
treatment takes one value and there is no second side to compare against.** This is
the first gate in its propagation form: the question there is not how many values a
cross-sectional treatment takes in the world, it is **how many receivers did not get
the document**, and here the answer is zero by construction.

**A second reason stands on its own.** A design rule that follows from the mechanism
does not need a transmitter. Anyone who wants a discounted first block that most
customers exceed will draw it below average consumption, **because that is what
drawing it there means**. So conformance is over-determined: the mechanism supplies
it for free, and transmission would supply the same thing, and the two predictions
coincide on this reading. **Separating them needs a signature the mechanism cannot
produce, and that signature is identical printed values across countries**, which
is the collision count at the top of this document.

**So the compliance reading stands as what it is.** Forty-two published schedules,
a stated principle, and a count of how often the two agree. **It is not a
propagation reading and cannot be turned into one on this source.**

## Limits

1. **Sixty-four country rows recovered, fifty-three carrying a block structure.**
   The other eleven are schedules that are not block tariffs, or that state a block
   count without printing charges. **Nothing is dropped as unparsable.**
2. **One year, 2015 to 2016, and a cross-section.** No schedule is observed twice.
3. **Residential only.** The survey's other four annexes carry demand and
   time-of-use charges and have no blocks.
4. **Every row's carrier identity is inferred from the survey's scope rule, not
   printed.** The rule is the largest utility by customer base serving the largest
   business city. **Where a country has one national schedule that names a unique
   document; where it has a competitive retail market it does not**, and the survey
   prints neither the retailer nor the offer. Australia is the case where this was
   tested and the schedule could not be identified.
5. **The compliance reading uses forty-two schedules**, the multi-block ones printing
   both a first block size and an average consumption, and treats the survey's own
   wording as its threshold. **The wording is qualitative and the two readings
   above bracket it rather than resolve it.**
6. **The survey's own summary of that ratio cannot serve as a parse check, because
   it is inconsistent as printed.** It gives a central value of 50 per cent against
   a stated range whose minimum is 60 per cent, and a central value cannot lie below
   the minimum of its own range. **The block-count mean and the country count can
   serve as parse checks and do. Whether a printed statistic can be used that way has
   to be asked of each statistic, and is not inherited from the document it sits in.**

## Correction, 2026-09-03, and the numbers before it

**The first reading of this corpus was made with a parser carrying two bugs, and
both were found by printing the parsed country names rather than the row count.**

**Bug one, the wrapped country name.** A country whose name wraps to a second line
in the annex has that second line begin in column zero, exactly as a new row does.
The parser started a new row on it, **splitting six countries in half and inventing
six rows carrying the back half of their fields**. Two of the six carried data in
other columns on the wrap line, so testing for an otherwise-empty line catches only
four. **The test that works is the structure column**: every schedule states a
structure type on its own first line, and a line beginning in column zero without one
is a wrapped name.

**Bug two, the footnote marker.** The last charge in a row is followed by the page's
footnote marker with only a space between them, so the cell reads `0.13 34` and the
whole charge failed to parse. **Four schedules were being dropped for a declared
block count that disagreed with a charge list the parser had truncated.** Taking the
first whitespace token of each comma field cuts the marker, and it cannot invent a
charge, because the resulting count still has to equal the declared block count.

**The numbers before the correction, kept as required:**

| | before | after |
|---|---|---|
| rows recovered | 60, then 70 | **64** |
| schedules | 43 | **53** |
| dropped as unparsable | 4 | **0** |
| blocks | 144 | **179** |
| distinct values | 124 | **156** |
| collisions | 20 | **23** |
| schedules with a collision | 12 | **15** |
| mean blocks, multi-block schedules | 3.97 | **4.000** |
| compliance reading, below average | 24 of 41 | **25 of 42** |
| compliance reading, below half | 13 of 41 | **14 of 42** |
| ratio range | 0.12 to 8.28 | **0.12 to 6.44** |

**The direction of the change is the same on every line and the qualitative reading
does not move**: values still sit to the left of blocks, the same three schedules
carry the largest gaps, and the same two schedules are degenerate at the top of the
grid table. **Egypt, Iran and Myanmar enter the collision list, all three with one
collision, and all three in the unforced column.** The maximum ratio falls because
the 8.28 belonged to a row assembled out of two halves of different countries.

**What caught it was the known-answer check moving to exact.** The mean block count
read 3.97, then 3.92, and only 4.000 against the survey's stated four once both bugs
were out. **A check that is close is not a check that passes**, and the two runs that
read 3.97 and 3.92 were both being called a pass.


## A third arm on the same document, and it needed no collection

The residential annex is the only one of the five that draws blocks, which is
why the first arm stopped there. The other four carry a time-of-use column
instead, and that column states a charge per period. A schedule that writes four
periods and prints `0.06, 0.14, 0.22, 0.24` has written four values; one that
writes three and prints `0.18, 0.32, 0.32` has written two. That is the same
object the block arm counts, under another name, and the text of all five
annexes was already on disk.

Three annexes carry the column. The public annex carries a demand charge and no
time-of-use column, so it is out of this arm, named here rather than dropped
quietly.

**The reading.** Across the three, 125 rows, of which **42 carry a time-of-use
column**. They write **112 periods** and **105 distinct values**, so **7
collisions**.

**Seven collisions, and two of them are exact.** Every collision in the block arm
is bounded above by the survey rounding charges to two decimals, and is reported
that way. Two collisions here are not: India prints `0, 0, 0.01, 0.02` for both
its commercial and its industrial schedule, and two periods printed as zero are
two periods charged nothing. No pair of distinct positive charges rounds to two
zeros. Those two are one country writing one rule into two tables rather than two
independent readings, and they are counted as one country in the record.

| criterion | reading | |
|---|---|---|
| **TB-14** the same column splitter on the residential annex, against the counts already on disk | 53 schedules, `179` blocks, `156` distinct values, `23` collisions, reproduced digit for digit | PASS |
| **TB-15** periods against distinct values, per annex and per colliding schedule | commercial `44 -> 42`, industrial `54 -> 49`, agricultural `14 -> 14`; every colliding schedule printed with its charges | PASS |
| **TB-16** collisions split by whether rounding could have produced them | 7 total, **2 exact**, 5 resolution-limited | PASS |
| **TB-17** the survey's structure column against its time-of-use column, both directions named row by row | 7 name time-of-use and print no charges; 4 print charges and do not name it | PASS |
| **TB-18** periods per customer class for countries in more than one annex | 12 countries, 8 write the same period count in every annex they appear in | PASS |

**What TB-17 found in the document itself.** Eleven of the forty-two schedules
disagree with the survey's own description of them. Australia's commercial
schedule is typed `DBT` and prints three time-of-use charges; Armenia's
industrial one is typed `kV-dependent` and prints two. Seven go the other way,
naming time-of-use in the structure column with the charge column empty. The rows
are named rather than counted, because the count alone does not say whether the
disagreement is in the typing or in the collection.

**A parse error worth recording, and why the known-answer check did not catch
it.** The first version identified each annex by its column labels. The
industrial and agricultural annexes both print `Low to high TOU` and `Monthly`,
so the industrial pages matched the agricultural pattern as well and were parsed
a second time with the wrong column edges. The agricultural annex then reported
66 rows where it has 17, and India's agricultural cell, which reads `-. -` in the
document, came back carrying four numbers from the industrial row above it.
**TB-14 passed throughout**, because it checks the residential annex and nothing
else. A known-answer check covers the part it checks. Identifying each page by
the `Annex 1X` title, which is printed once per annex, assigns every page to
exactly one.
