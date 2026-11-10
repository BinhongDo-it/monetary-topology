# B115: China's 2018 deposit on US sorghum and its end, read against Gulf corn

**RUN: 2026-09-17. Script `experiments/b115_sorghum_step.py`; record `results/b115_sorghum_step.json`, which
carries the configuration it ran under; the transcribed tables in `data/b115_sorghum_fob.json`, with sources
and caliber in `data/SOURCES.md`. The station's soybean branch is in [`b115_soy_tariff.md`](b115_soy_tariff.md).
Theorem 42 is in [`b104_action_footprint.md`](b104_action_footprint.md), Corollaries 43.1 and 43.6 in
[`b105_cutting_relations.md`](b105_cutting_relations.md).**

## 0. What the station reads

From 2018-04-18 importers of US sorghum (tariff line 10079000) paid a deposit of 178.6% of the value,
under the preliminary anti-dumping ruling of China's Ministry of Commerce. On 2018-05-18 the ministry
ended the anti-dumping and countervailing investigations and refunded the deposits. Both steps touch one
relation, from US sorghum at export to sorghum in China, and so does the investigation opened on
2018-02-04, which put no charge in force.

The comparison is Gulf corn. All three prices come from the US Grains Council's weekly FOB tables, in US
dollars a tonne FOB vessel, by delivery month:

| Position | Table | Column |
|---|---|---|
| NOLA sorghum | Sorghum FOB | #2 YGS, NOLA |
| Texas sorghum | Sorghum FOB | #2 YGS, Texas |
| Gulf corn | Yellow Corn FOB | #2 YC, Gulf |

The deposit weighed on both sorghum quotes at once, so the US sorghum export end is read as one
position quoted twice, and each quote is read against Gulf corn.

**What Corollary 43.6 says here.** With only the term of `e = (US sorghum → China)` moved, every potential
moves by `w_e Δ u`, where `u` is the potential of a unit current along `e`. By Theorem 42 `u` is smallest
at the US sorghum end, so every other position, Gulf corn among them, moves up against it:

| Step | Sorghum against Gulf corn |
|---|---|
| the deposit | at most 0 |
| its end | at least 0 |
| the two together | at least 0 |

The end put the charge in force back where it stood before the deposit (Corollary 43.1). The plateau
before the deposit lies inside the investigation, and an FOB quote is a price for delivery over the next
one to three months, so it can already carry part of the expected deposit, and the end takes that part away too.
The two steps together are therefore at least 0, and 0 when the quotes before the deposit carried none
of it.

**States.** A reading is one of **matches**, **does not match** and **not read**. A move predicted at
most 0 matches below minus its floor and does not match above its floor; a move predicted at least 0
matches above its floor and does not match below minus it; a move within its floor is not read. Four
settings of the plateaus are read, and a state counts only when all four give it.

## 1. The dated documents

| Date | Document | What it does |
|---|---|---|
| 2018-02-04 | Ministry of Commerce, anti-dumping investigation on US sorghum (the date as given in announcement 2018 No. 38) | opens the investigation; no charge in force |
| 2018-04-04 | Tariff Commission of the State Council, announcement [2018] No. 1 | 25% on 106 lines, 10059000 other corn and 10079000 other sorghum among them; the date to be announced |
| 2018-04-18 | Ministry of Commerce, announcement 2018 No. 38 | a deposit of 178.6% on imports of US sorghum from this day |
| 2018-05-18 | Ministry of Commerce, announcement 2018 No. 44 | both investigations end, and the deposits are refunded in full |
| 2018-05-19 | China-US joint statement on the trade consultations, dated Washington | the two sides agree to meaningfully increase US agricultural and energy exports |
| 2018-06-16 | Tariff Commission, announcement [2018] No. 5 | list one from 2018-07-06, corn and sorghum in it |
| 2018-07-06 | | list one in force |

The deposit and its end are the two steps read. The documents of 04-04, 05-19 and 06-16 cover corn,
sorghum and other goods at once, so Corollary 43.6 does not fix which way they move sorghum against corn,
and the path across them is printed without a state. The joint statement came a day after the end and no
plateau separates the two, so the reading of the end holds both. All seven dates are dated steps for the
floors.

The documents: No. 38, which also gives the date the investigation opened, in a copy on a Zhejiang government site
(zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web2757/site/attach/0/b7809a8f31bd4ecfa747b8bade41bd0d.pdf) and as relayed at m.guojiguoshu.com/article/3983; No. 44 at www.waizi.org.cn/doc/34910.html;
[2018] No. 1 with its list at gss.mof.gov.cn/gzdt/zhengcefabu/201804/P020180408316727037809.pdf; [2018] No. 5 at m.mof.gov.cn/czxw/201806/t20180616_2930325.htm, list one as posted
by the Fujian commerce department (swt.fujian.gov.cn/xxgk/ztzl/mymc/jsqd/201809/P020180918703451581078.pdf); the joint statement at www.gov.cn/xinwen/2018-05/20/content_5292160.htm.

## 2. The tables

Market Perspectives is the Council's weekly issue, dated on Thursdays. The Yellow Corn FOB table quotes
the Gulf and the Pacific Northwest, the Sorghum FOB table NOLA and Texas; each cell is a basis in US$/bu
over a CBOT corn futures month named by its letter and a flat price in US$/t. Corn and sorghum bushels
both weigh 56 lb, so a flat price is the futures price plus the basis, times 39.37.

`data/b115_sorghum_fob.json` holds 1,270 cells from 123 issues: 47 in 2016, 46 in 2017 and 30 in
2018, from January 4 to August 2. Every cell was read from the text layer of its issue's PDF, and the 231
cells from 2018-02-22 on were also read from the tables' images, with the same result in every cell.
Each PDF names its issue date in a Week Ending line, and all 123 match. No PDF was found for eight weeks
(2016-02-18, 06-09, 07-21 and 11-10; 2017-01-05, 03-16, 05-18 and 09-21), and four weeks had no issue
(2016-11-24, 2017-11-23, 2017-12-28, 2018-01-25).

**Two checks on the source**, both computed from the cells, flag 22 cells, which are printed and not used:

| Check | Cells flagged | What it asks of a cell |
|---|---|---|
| the pricing identity | 19 | the futures price its flat and basis imply lies within a cent a bushel of the median over the cells of its issue and futures month |
| the futures month | 3 | the futures month it hangs on does not end before its delivery month |

On 2017-08-24 the Gulf corn flats for August, September and October all imply one futures price, 3.42
$/bu, while the other cells of that issue quoted over the December contract imply 3.64. On 2018-05-10 the Gulf corn
cells for June and July miss by 1.5 cents, so that issue has no level at either port.

**Levels and the path.** A level is ln(sorghum flat) minus ln(Gulf corn flat) for one issue and one
delivery month, with the halves of a month averaged in logs. Levels are chained from issue to issue over
the delivery months both issues quote, which keeps the roll from one delivery month to the next out of
every move; two issues with no month in common start a new segment of the path. In 2018 each port's path
is one segment. Before 2018 NOLA's path breaks six times, NOLA having no quote through most of the summer
of 2016, and Texas's twice.

## 3. Plateaus and settings

| Setting | P0, before the deposit | P1, the deposit in force | P2, after the end |
|---|---|---|---|
| A (default) | 04-05 and 04-12 | 04-19 to 05-17, five issues | 05-24 to 06-14, four issues |
| B | 04-05 and 04-12 | 04-26 to 05-17, four | 05-24 to 06-14, four |
| C | 04-05 and 04-12 | 04-19 to 05-17, five | 05-31 to 06-14, three |
| D | 04-05 and 04-12 | 04-26 to 05-17, four | 05-31 to 06-14, three |

P0 lies after the list of 04-04 and before the deposit, P2 before list one. Settings B and D leave out
the first issue after the deposit was announced on 04-17, and C and D the first after its end. With
2018-05-10 carrying no level, P1 holds four levels in A and C and three in B and D. The deposit reads P0
against P1, its end P1 against P2, and the two together P0 against P2, each as the mean of the path over
one plateau against its mean over the other.

## 4. Floors

The floor of each move is the larger of two numbers. The quote grid adds the relative steps of the two
flat prices, 0.0008 for NOLA and 0.0010 for Texas against Gulf corn. The second is
the median absolute move of the same shape over every window on the Thursday grid from 2016-01-07 to
2018-02-01 whose span holds none of the seven dates, where each plateau has a level and the whole window
lies on one segment of the path. The median is the floor in every case below.

**Windows kept, and in brackets how many share no week:**

| Port and move | A | B | C | D | Windows without a level, A |
|---|---|---|---|---|---|
| NOLA, the deposit | 63 (11) | 60 (11) | 63 (11) | 60 (11) | 40 |
| NOLA, its end | 56 (9) | 59 (10) | 53 (9) | 56 (10) | 45 |
| NOLA, the two together | 43 (7) | 43 (7) | 40 (6) | 40 (6) | 56 |
| Texas, the deposit | 92 (14) | 92 (14) | 92 (14) | 92 (14) | 11 |
| Texas, its end | 86 (10) | 89 (13) | 86 (10) | 89 (13) | 15 |
| Texas, the two together | 80 (9) | 80 (9) | 80 (9) | 80 (9) | 19 |

No window spans a dated step: the grid ends on 2018-02-01.

## 5. Readings

**Moves, with the floor and how many placebo windows moved at least as far:**

| Move | Port | A | B | C | D |
|---|---|---|---|---|---|
| The deposit, P0 to P1 | NOLA | −0.0679 (0.0186; 1 of 63) | −0.0710 (0.0213; 1 of 60) | −0.0679 (0.0186; 1 of 63) | −0.0710 (0.0213; 1 of 60) |
|  | Texas | −0.0473 (0.0206; 9 of 92) | −0.0464 (0.0239; 14 of 92) | −0.0473 (0.0206; 9 of 92) | −0.0464 (0.0239; 14 of 92) |
| Its end, P1 to P2 | NOLA | +0.0617 (0.0207; 2 of 56) | +0.0647 (0.0201; 2 of 59) | +0.0875 (0.0250; 0 of 53) | +0.0906 (0.0242; 0 of 56) |
|  | Texas | +0.0715 (0.0241; 0 of 86) | +0.0706 (0.0217; 0 of 89) | +0.1004 (0.0264; 0 of 86) | +0.0995 (0.0252; 0 of 89) |
| The two together, P0 to P2 | NOLA | −0.0063 (0.0336; 35 of 43) | −0.0063 (0.0336; 35 of 43) | +0.0196 (0.0316; 25 of 40) | +0.0196 (0.0316; 25 of 40) |
|  | Texas | +0.0242 (0.0350; 47 of 80) | +0.0242 (0.0350; 47 of 80) | +0.0530 (0.0336; 22 of 80) | +0.0530 (0.0336; 22 of 80) |

**States:**

| Move | Port | State |
|---|---|---|
| The deposit, P0 to P1 | NOLA | matches in all four |
|  | Texas | matches in all four |
| Its end, P1 to P2 | NOLA | matches in all four |
|  | Texas | matches in all four |
| The two together, P0 to P2 | NOLA | not read in all four |
|  | Texas | A not read; B not read; C matches; D matches: the settings disagree, not read |

Of the eight readings of the two steps together, 0 lie below minus their floor and 2 above it.

**Known answer.** Hansen, Marchant, Zhang and Grant (Choices 33(2), 2018), citing the International
Grains Council, report that the US Gulf sorghum export price fell by about 4% after the announcement of
18 April. The NOLA flat price from the 04-12 issue to the 04-19 issue, over the May and June delivery
months both quote, moved by −0.0433 in logs against ln 0.96 = −0.0408, a ratio of 1.06.

**The path**, in logs, from the record:

| Issue | NOLA | Texas |
|---|---|---|
| 02-01 | +0.2496 | +0.2138 |
| 02-08 | +0.2382 | +0.2118 |
| 03-08 | +0.0732 | +0.0143 |
| 04-05 | +0.0572 | +0.0022 |
| 04-12 | +0.0448 | +0.0001 |
| 04-19 | −0.0077 | −0.0489 |
| 04-26 | +0.0036 | −0.0373 |
| 05-03 | −0.0280 | −0.0483 |
| 05-17 | −0.0356 | −0.0502 |
| 05-24 | −0.0328 | −0.0613 |
| 05-31 | +0.0606 | +0.0504 |
| 06-07 | +0.0640 | +0.0527 |
| 06-14 | +0.0871 | +0.0594 |
| 06-21 | +0.1148 | +0.0980 |
| 07-05 | +0.1272 | +0.1095 |
| 07-12 | +0.1226 | +0.1042 |
| 08-02 | +0.0807 | +0.0578 |

The 2018-05-10 issue carries no level. From 02-08 to 03-08, with none of the seven dates between, sorghum
moved against Gulf corn by −0.165 at NOLA and −0.197 at Texas; the end showed in the second issue after it,
05-24 to 05-31.

**Across each document**, from the last issue before it to the first after:

| Date | Document | Issues | NOLA | Texas |
|---|---|---|---|---|
| 2018-02-04 | the investigation opens | 02-01 to 02-08 | −0.0114 | −0.0020 |
| 2018-04-04 | the list naming corn and sorghum | 03-29 to 04-05 | −0.0163 | −0.0269 |
| 2018-04-18 | the deposit | 04-12 to 04-19 | −0.0525 | −0.0490 |
| 2018-05-18 | its end | 05-17 to 05-24 | +0.0027 | −0.0111 |
| 2018-05-19 | the joint statement | 05-17 to 05-24 | +0.0027 | −0.0111 |
| 2018-06-16 | list one | 06-14 to 06-21 | +0.0277 | +0.0386 |
| 2018-07-06 | list one in force | 07-05 to 07-12 | −0.0046 | −0.0053 |

## 6. Structural checks

| | Kind | What it checks | Run |
|---|---|---|---|
| PASS `B115-8` | `instrument` | every issue from 2018-01-04 to 2018-08-02 has cells in both tables, and every plateau week of every setting is such an issue | 30 issues, 11 plateau weeks |
| PASS `B115-9` | `instrument` | no placebo window kept spans a dated sorghum document, and every port, setting and move has placebo windows | section 4 |
| PASS `B115-10` | `own_reading` | NOLA: the deposit moved sorghum down against Gulf corn | matches in all four settings |
| PASS `B115-11` | `own_reading` | Texas: the deposit moved sorghum down against Gulf corn | matches in all four settings |
| PASS `B115-12` | `own_reading` | NOLA: the end moved sorghum back up against Gulf corn | matches in all four settings |
| PASS `B115-13` | `own_reading` | Texas: the end moved sorghum back up against Gulf corn | matches in all four settings |
| no verdict `B115-14` | `own_reading` | NOLA: the two steps together moved sorghum against Gulf corn by at least 0 | within the floor in all four settings |
| no verdict `B115-15` | `own_reading` | Texas: the two steps together moved sorghum against Gulf corn by at least 0 | within the floor in A and B, above it in C and D |
| PASS `B115-16` | `known_answer` | the NOLA flat price across the deposit's week has the sign of the reported fall of about 4% and lies within one order of magnitude of it | −0.0433 against −0.0408 |

An `instrument` check asks whether the tables and the windows are what the reading needs, an
`own_reading` is this station's reading of Corollaries 43.1 and 43.6, and the `known_answer` sets the
first week of the deposit against an independent report.

The selftest runs the whole reading on synthetic worlds whose sorghum levels carry a month offset and exact
steps, and checks the moves, the weeks between the plateaus, the floors and the known answer. It plants a
failure under each criterion: an issue dropped from a plateau, an issue outside the plateaus, a plateau
week with no issue, an issue without its sorghum table, a placebo window across a dated document, a move
with no placebo window, sorghum rising at the deposit, an end that falls short of the deposit, and a fall
twenty times the known answer. It checks both source checks on planted cells, that a flagged cell is kept
out of the reading, the halves of a month, the chaining over shared months and the breaks between
segments, the reading at each floor, every row of the state mapping, and that settings that disagree give
no verdict. Thirty-eight deliberate faults in the implementation were each caught by the selftest.

## 7. What more data would read

1. **A weekly price for sorghum landed in China, or for Argentine or Australian sorghum FOB**, would read
   the share of each step, as the soybean branch reads it with Dalian and Paranaguá.
2. **The tables for the eight weeks with no PDF** would close gaps in the NOLA path and add placebo windows.

## 8. The flows on the same relation

**RUN: 2026-10-13. Script `experiments/b115_sorghum_flows.py`; record `results/b115_sorghum_flows.json`, which
carries the configuration it ran under; the data in `data/b115_sorghum_esr.json`, with sources and caliber in
`data/SOURCES.md`.**

Sections 0 to 6 read the two steps in prices at the US end. This section reads them in the weekly tonnage
on the relation itself and on the relations beside it.

**The source.** The Export Sales Reporting and Query System of the USDA Foreign Agricultural Service gives US
grain sorghum (commodity 701, marketing year September to August) by destination and week, in tonnes. A
week runs Friday to Thursday and is named by its Thursday, the grid of sections 2 to 5. Six marketing years
are read, 2013/14 to 2018/19: 313 Thursdays, 2,722 destination rows, 25 destinations. The report has eight
columns: Gross New Sales, Net Sales, Weekly Exports, Outstanding Sales, Accumulated Exports and Total
Commitment for the marketing year of the block, and Net Sales and Outstanding Sales for the next one. It has
no column of cancellations by destination. `R` = Gross New Sales − Net Sales is printed under that name: by
the source's definition of Net Sales it nets buy-backs and cancellations with changes of destination out of
and into the row, and it can be negative. A week can hold two marketing-year blocks (new-crop sales, and
the first week of September); flows are summed over the blocks of a week.

**Three series.** `e` is the relation from US sorghum to China (destination 5700). Beside it stand the
destination the source reports as unknown (9990), a reporting category, and the other named destinations
taken together.

**The charge in force on `e`**, counted from three documents (section 1), by week as
`ω = ln(1 + rate in force)` averaged over the week's seven days:

| Weeks ending | In force | `ω` |
|---|---|---|
| to 04-12 | nothing | 0 |
| 04-19 | the deposit from Wednesday 04-18, two days of seven | 0.2927 |
| 04-26 to 05-17 | the 178.6% deposit, four whole weeks | 1.0246 |
| 05-24 to 07-05 | nothing | 0 |
| from 07-12 | 25% under list one | 0.2231 |

**What Corollary 43.6 says of the flows.** With only the term of `e` moved by `Δ`, the residual on `e` becomes
`r_e + (1 − h_e)Δ`: what a deal along `e` pays beyond the gap between its two ends rises with the deposit and
falls with its end. So shipments and new business on `e` move by at most 0 at the deposit and by at least 0
at its end, and what travelled along `e` lands on the relations still open, so the other named destinations
move by at least 0 at the deposit. No direction is fixed for the move from before the deposit to after its
end, for the step of 07-06 (the same list moved corn and other relations), for the unknown destination, or
for the size of any move. Those are printed with their floors and carry no state.

**Moves, floors and states.** A move is the mean weekly tonnage over one plateau minus the mean over another,
in levels, since weekly values are often zero. The plateaus and the four settings are those of section 3,
and P3 is the four weeks 07-12 to 08-02. Each move is set against the same move over every window of the
same shape on a Thursday grid that ends on 2018-02-01 and so holds none of the seven dates. Two grids are
read, from 2016-01-07 (the grid of section 4) and from 2013-09-05. The floor is the larger of the reporting
grid, 0.1 t over each plateau's weeks, and the median absolute placebo move; the median is the floor in
every case. A cell matches, does not match or is not read as in section 0, and a criterion has a verdict
only when all eight cells, four settings by two grids, give one state.

### 8.1 The weeks around the two steps

China's row, with the other named destinations, in tonnes:

| Week ending | `ω` | Gross new sales | Net sales | Exports | Outstanding | `R` | Others, gross new sales | Others, exports |
|---|---|---|---|---|---|---|---|---|
| 03-29 | 0 | 5,048 | 71,048 | 173,100 | 510,484 | −66,000 | 0 | 0 |
| 04-05 | 0 | 9,202 | 127,678 | 185,989 | 452,173 | −118,476 | 997 | 10,997 |
| 04-12 | 0 | 6,000 | 61,201 | 120,334 | 393,040 | −55,201 | 20,000 | 21 |
| 04-19 | 0.2927 | 1,424 | −8,446 | 57,979 | 326,615 | 9,870 | 39,474 | 954 |
| 04-26 | 1.0246 | 0 | −53,051 | 2,037 | 271,527 | 53,051 | 82,210 | 87,260 |
| 05-03 | 1.0246 | 3,181 | 3,040 | 58,706 | 215,861 | 141 | 209,592 | 133,049 |
| 05-10 | 1.0246 | 0 | −132 | 0 | 215,729 | 132 | 156,480 | 65,941 |
| 05-17 | 1.0246 | 0 | 0 | 0 | 215,729 | 0 | 762 | 11,138 |
| 05-24 | 0 | 2,831 | −163,819 | 51,707 | 203 | 166,650 | 105 | 26,166 |
| 05-31 | 0 | 958 | 958 | 23 | 1,138 | 0 | 12 | 4,402 |
| 06-07 | 0 | 0 | 0 | 180 | 958 | 0 | 5 | 4,574 |
| 06-14 | 0 | 0 | 0 | 0 | 958 | 0 | 0 | 1,050 |

From January to 04-12 China took 93% to 100% of each week's exports. In the weeks ending 04-26 to 05-17 the
other named destinations' new sales were Spain 182,551, Japan 117,698, Mexico 115,334 and Colombia 25,207,
with smaller lots to Taiwan, Vietnam and South Africa. Through March and early April China's net sales ran above its
gross new sales (a negative `R`) by about what left the unknown destination in the same weeks: sales first
reported without a destination being assigned to China. In the week ending 05-24, the first whole week after the
end, China's outstanding sales fell from 215,729 to 203, with exports of 51,707 and net sales of −163,819,
and net sales to the unknown destination were −132,000. From 05-31 to 08-09 China's weekly exports were at
most 957. The record holds all 35 weeks from 01-04 to 08-30, with every destination.

Plateau means, tonnes a week, setting A (setting B's P1 and setting C's P2 in brackets):

| Series | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| China, exports | 153,162 | 23,744 (15,186) | 12,978 (68) | 0 |
| China, gross new sales | 7,601 | 921 (795) | 947 (319) | 0 |
| China, net sales | 94,440 | −11,718 (−12,536) | −40,715 (319) | 0 |
| China, `R` | −86,838 | 12,639 (13,331) | 41,662 (0) | 0 |
| Others, gross new sales | 10,498 | 97,704 (112,261) | 30 (6) | 516 |
| Others, exports | 5,509 | 59,668 (74,347) | 9,048 (3,342) | 16,539 |
| Unknown, net sales | −84,750 | −11,519 (2,101) | −16,520 (21,974) | −10,230 |

### 8.2 Readings

Moves in tonnes a week; in brackets the floor and how many placebo windows moved at least as far, first on
the grid from 2016 and then on the grid from 2013.

| Move | A | B | C | D |
|---|---|---|---|---|
| The deposit, China's exports | −129,417 (35,626, 0 of 103; 38,536, 5 of 225) | −137,976 (39,500, 0 of 103; 42,835, 4 of 225) | as A | as B |
| The deposit, China's gross new sales | −6,680 (29,938, 91 of 103; 40,138, 203 of 225) | −6,806 (36,148, 91 of 103; 47,722, 202 of 225) | as A | as B |
| The end, China's exports | −10,767 (24,945, 81 of 101; 31,399, 181 of 223) | −2,208 (27,667, 95 of 102; 34,410, 209 of 224) | −23,677 (25,350, 52 of 101; 34,335, 134 of 223) | −15,118 (26,714, 66 of 102; 36,509, 164 of 224) |
| The end, China's gross new sales | +26 (33,716; 39,886) | +152 (28,498; 41,306) | −602 (34,682; 42,812) | −476 (35,594; 41,604) |
| The deposit, others' gross new sales | +87,205 (6,516, 0 of 103; 7,256, 0 of 225) | +101,762 (8,740, 0 of 103; 8,490, 0 of 225) | as A | as B |
| The deposit, others' exports | +54,159 (6,220, 0 of 103; 4,671, 0 of 225) | +68,838 (6,551, 0 of 103; 5,084, 0 of 225) | as A | as B |

| | Kind | Reading | State |
|---|---|---|---|
| PASS `B115-21` | `own_reading` | the deposit: China's weekly exports moved by at most 0 | matches in all eight cells |
| no verdict `B115-22` | `own_reading` | the deposit: China's gross new sales moved by at most 0 | not read in all eight: new sales to China were already 7,601 t a week before the deposit, about a fifth of the floor, so a fall beyond the floor is out of reach and a cell can only be not read or not match |
| no verdict `B115-23` | `own_reading` | the end: China's weekly exports moved by at least 0 | not read in all eight: within the floor. Exports are never below zero and stood at 15,186 to 23,744 t a week under the deposit, under every floor (24,945 to 36,509), so a cell can only match or be not read; the level after the end, 68 to 12,978 t a week, is in the table of 8.1 |
| no verdict `B115-24` | `own_reading` | the end: China's gross new sales moved by at least 0 | not read in all eight: within the floor. New sales stood at 795 to 921 t a week under the deposit, so here too a cell can only match or be not read |
| PASS `B115-25` | `own_reading` | the deposit: gross new sales to the other named destinations moved by at least 0 | matches in all eight cells |
| PASS `B115-26` | `own_reading` | the deposit: exports to the other named destinations moved by at least 0 | matches in all eight cells |

The same weeks of the three marketing years before, printed beside the floors and not part of them:
China's exports over the deposit's plateaus moved by −80,549, −7,845 and −56,523 t a week in 2014/15, 2015/16
and 2016/17 (setting A), the season's decline, against −129,417 in 2018; the others' gross new sales moved
by +31, −28,206 and −17,311 against +87,205.

The floors are taken over windows of every season, and the season's decline alone passed them in 2014/15
and 2016/17. With the largest of the three earlier years taken off (2014/15: −80,549, and −89,438 without
the mixed week), the move of China's exports in 2018 is −48,868 (settings A and C) and −48,537 (B and D),
still beyond both floors in all eight cells, at 1.13 to 1.37 times the floor against 3.2 to 3.6 times
before. As a ratio, the deposit's plateau stood at 0.155 of the plateau before it in 2018 (0.099 without
the mixed week) against 0.693, 0.934 and 0.566 over the same weeks of the three earlier years. For the
other named destinations no earlier year passed a floor, and with the largest taken off the moves stay at
11.6 to 13.4 times the floor for gross new sales and 8.0 to 13.8 times for exports.

**Printed without a state**, setting A, with the floor on the grid from 2016:

| Move | Tonnes a week | Floor | Placebo windows as large |
|---|---|---|---|
| China's exports, P0 to P2 | −140,184 | 41,071 | 2 of 99 |
| China's exports, P2 to P3 | −12,978 | 37,060 | 78 of 99 |
| China's `R`, the deposit | +99,477 | 17,801 | 0 of 103 |
| China's `R`, the end | +29,024 | 15,586 | 21 of 101 |
| China's net sales, the deposit | −106,157 | 47,227 | 15 of 103 |
| Others' gross new sales, the end | −97,673 | 8,701 | 0 of 101 |
| Others' exports, the end | −50,620 | 6,450 | 0 of 101 |
| Unknown, net sales, the deposit | +73,231 | 36,650 | 18 of 103 |

China's `R` stands at −86,838 t a week before the deposit, the sales moved from the unknown destination to
China's row (8.1), and at +12,639 under it: 63,194 t over the five weeks 04-19 to 05-17, of which 53,051 in
the week ending 04-26. Of the move of +99,477, 86,838 is that reassignment stopping. The largest `R` on
China's row, 166,650, is in the first whole week after the end.

**Sold and shipped in one row.** Over the deposit's plateau three rows of the other named destinations carry
the same tonnage as gross new sales and as exports of the same week: Spain 49,502 and Colombia 25,207 in
the week ending 04-26, and Spain 133,049 in the week ending 05-03, together 207,758 t. That is 0.696 of
the others' exports over the plateau (298,342 t) and 0.425 of their gross new sales (488,518 t). Without
those three rows the move of the others' exports is +12,608 t a week (+16,898 without the mixed week),
still above every floor, with 18 of 103 and 49 of 225 placebo windows as large. `B115-25` and `B115-26`
therefore share most of their tonnage: the deposit's step reads as two things, shipments along `e` down
and business on the other relations up. The eight columns do not tell a cargo re-routed at sea from one
sold and loaded within the week; China's accumulated exports chain without a break, so nothing already
counted as exported to China was taken back.

**The charge as a dose.** Over these weeks the charge on `e` is piecewise constant, and the criteria read
the plateau under each level. China's weekly exports by level: 153,162 t at `ω = 0` before the deposit;
15,186 at `ω = 1.0246` (the four whole weeks; 23,744 with the mixed week); 68 to 12,978 at `ω = 0` after
the end; 0 at `ω = 0.2231` under list one. The flow did not return when `ω` returned to 0.

The other named destinations' new sales and exports fell back at the end by about as much as they had risen at
the deposit. The end holds the joint statement of 05-19 as in section 1, and P2 stands after the list of
04-04 had named sorghum for a 25% charge not yet dated.

**Known answer.** Hansen, Marchant, Zhang and Grant (Choices 33(2), 2018) write that cargoes at sea in April
were sent on to Saudi Arabia, Spain, Vietnam and Japan. In the weeks ending 04-19 to 05-31 the source shows
gross new sales of 182,551 t to Spain, 117,698 to Japan and 1,760 to Vietnam, and exports of 182,551, 96,674
and 1,058. Saudi Arabia has no row in any week of the six marketing years, so `B115-28` lists it. Over the
calendar years 2014 to 2017 China's share of the weekly exports was 0.951, 0.958, 0.899 and 0.894, against
the 86% the same article gives from customs statistics.

### 8.3 Structural checks

| | Kind | What it checks | Run |
|---|---|---|---|
| PASS `B115-17` | `instrument` | each of the six files is one page, carries the dates asked for and the commodity; every Thursday from 2013-09-05 to 2019-08-29 has a Total row; every plateau week is there | 6 files, 313 of 313 Thursdays, 15 plateau weeks |
| PASS `B115-18` | `instrument` | Total Commitment is Outstanding Sales plus Accumulated Exports in every row; the Total row is the sum of the destinations in all eight columns; China's outstanding and accumulated chain week to week through net sales and exports from 01-04 to 08-30, within 0.15 t | 2,722 rows, 35 links, no break; no chain break elsewhere either |
| PASS `B115-19` | `instrument` | no placebo window kept spans a dated document, and every series, move, setting and grid has windows | 99 to 103 windows on the grid from 2016 (9 to 15 sharing no week), 221 to 225 from 2013 (21 to 33) |
| PASS `B115-20` | `own_reading` | the weekly table of 8.1 in full, the same weeks of 2016/17 and 2018/19, and China's calendar-year shares are in the record | 35 weeks |
| PASS `B115-27` | `own_reading` | the 22 moves with no predicted direction are printed, each with both floors and none with a state; beside the criteria, the states each cell can reach, the same weeks of earlier years against each move, and the tonnage sold and shipped in one row and week | the tables and paragraphs of 8.2 |
| FAIL `B115-28` | `known_answer` | each of the four destinations Hansen and co-authors name has gross new sales or exports above zero in the weeks ending 04-19 to 05-31 | Spain, Japan and Vietnam do; Saudi Arabia has no row |
| PASS `B115-29` | `bookkeeping` | the record carries its configuration, a kind on every criterion, the mapping from states to verdicts, and the hash and URL of each file | 6 files |

The selftest reads a synthetic world with exact plateau values, a seasonal path and noise through the whole
pipeline and checks the moves, the gaps between plateaus, both floors, the twin windows and the table. It
checks the parser on a week with two marketing-year blocks, on destination names with commas, ampersands
and brackets, and on negative numbers, and that it stops on columns in another order, a row a number short
and a destination without a code. It plants a failure under each criterion: a plateau week removed, a file
of two pages, a header a day off, a file of another commodity, a tonne added to one cell, a row removed, a
Total row changed, a placebo window across a dated document, a grid too short for a window, an empty table,
China rising at the deposit and falling after the end, the others falling at the deposit, China counted
among the others, one setting moving the other way, a verdict placed on a printed move, a floor removed, a
named destination without rows, and a record without its configuration. It checks every row of the state
mapping and that cells that disagree give no verdict. It also checks that China without a row is named when
the Total row still agrees, the weeks of P3 and the ends of both grids, that plateau means follow their own
setting, and which columns the Total row's share, the outstanding path and the calendar-year shares read.
For what is printed beside the criteria it checks, on worlds built for it, which states a cell can reach
when the level before a move is above or under its floor or the floor is missing, which earlier year is
taken off and what remains over each floor, which rows count as sold and shipped alike and over which
weeks, and that the placebo windows set against the move without those rows are those of the same series,
shape and grid as the floor's; and that `B115-27` fails when any of the three is absent for a cell or a
setting.
