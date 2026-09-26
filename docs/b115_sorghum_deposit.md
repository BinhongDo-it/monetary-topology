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
