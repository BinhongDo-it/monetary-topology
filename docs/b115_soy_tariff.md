# B115: China's 2018 tariff on US soybeans, read as a term moved in place

**RUN: 2026-09-17. Scripts `experiments/b115_soy_fetch.py` (fetch and file checks),
`experiments/b115_soy_describe.py` (the objects in the raw files) and `experiments/b115_soy_step.py`
(the reading); records `results/b115_soy_describe.json` and `results/b115_soy_step.json`, which carry
the configuration they ran under. Sources and caliber notes in `data/SOURCES.md`. Theorem 42 is in
[`b104_action_footprint.md`](b104_action_footprint.md), Theorem 43 and Corollary 43.6 in
[`b105_cutting_relations.md`](b105_cutting_relations.md).**

## 0. What the station reads

On 2018-07-06 China's additional tariff on US yellow soybeans (tariff line 12019010) went from nothing
to 25%, over a most-favoured-nation rate of 3%. The term of the relation from US soybeans at export to
soybeans in China moved by

```
Δ = ln(1.28 / 1.03) = 0.2173
```

and the rate on Brazilian soybeans stayed at 3%. Four series place the relation:

| Position | Series | Unit | Frequency |
|---|---|---|---|
| Gulf | AgTransport Grain Basis, soybeans, Gulf - Louisiana bid, 30 days to arrive | US$/bu | week |
| Dalian | Dalian Commodity Exchange No. 2 soybeans, settlement price on the days a contract traded | yuan/t | trading day |
| Paranaguá | CEPEA/ESALQ soybean indicator, Paranaguá | US$ per 60 kg bag | day |
| yuan | FRED `DEXCHUS` | yuan per US$ | business day |

The US export end is read as one position, at the Gulf: the AgTransport soybean series for the Pacific
Northwest starts on 2020-08-21. The No. 2 soybean contract is the exchange's contract on imported
soybeans. Its delivery rules changed from the 1805 contract on, so every contract read in 2018 trades
under one set of rules. Every file is checked against the SHA-256 in its manifest before it is read.

**What Corollary 43.6 says here.** With only the term of `e = (Gulf → Dalian)` moved, Dalian against the
Gulf moves by `h_e Δ`, and every potential moves by `w_e Δ u`, where `u` is the potential of a unit
current from the Gulf to Dalian. By Theorem 42, `u` at Paranaguá lies between its values at the two
ends. The tariff's part of each leg is therefore:

| Leg | The tariff's part |
|---|---|
| Dalian against the Gulf | `h_e Δ` |
| Paranaguá against the Gulf | between 0 and `h_e Δ` |
| Dalian against Paranaguá | at least 0 |

**The yuan's step.** The yuan moved in the same weeks, by +0.054 in logs between the plateaus of the
default setting (about 6.36 to 6.70 per dollar in weekly means), while Dalian's settlement in yuan rose
by about 1%. The same corollary bounds what a step in the yuan's own term does to any pair: at most its
size `s`, since a share never exceeds one. Two orientations fix its direction. Dalian is priced on the
yuan's side of the Gulf, and once the tariff binds, Paranaguá sits nearer China than the Gulf does. With
them the yuan's step can only push both legs down, and the tariff's part lies in these intervals:

| Leg | Low end | High end |
|---|---|---|
| Dalian against the Gulf | read at the market rate | read at the pre-plateau rate |
| Paranaguá against the Gulf | as read | as read plus `s` |
| Dalian against Paranaguá | Dalian at the market rate, less `s` | Dalian at the pre-plateau rate |

The same intervals with no orientation assumed, each end moved out by `s` (by `2s` for Dalian against
Paranaguá), are printed next to them.

**States.** A reading is one of **matches**, **does not match** and **not read**. An interval whose low
end is above its floor matches, one whose high end is below minus its floor does not match, and any other
is not read. Four settings of the plateaus are read, and a state counts only when all four give it.

## 1. The dated documents

| Date | Document | Soybeans |
|---|---|---|
| 2018-04-04 | Tariff Commission of the State Council, announcement [2018] No. 1 | 25% on 106 lines, the first two 12019010 and 12019020; the date to be announced |
| 2018-06-16 | announcement [2018] No. 5 | list one from 2018-07-06, 12019010 and 12019020 in it |
| 2019-08-23 | announcement [2019] No. 4 | 5% more on 12019010 from 2019-09-01 12:01, 33% in all |
| 2019-09-13 | notice relayed by the National Development and Reform Commission | purchases of US soybeans by firms to be excluded from the additional tariffs |
| 2019-12-06 | Ministry of Finance | exclusion of soybeans on applications by firms |
| 2020-02-06 | announcement [2020] No. 1 | the 5% becomes 2.5% from 2020-02-14 13:01 |
| 2020-02-17 | announcement [2020] No. 2 | market-based exclusion, applications from 2020-03-02, within the approved amount for one year |

These dates, and the effective dates they name (2018-07-06, 2019-09-01, 2020-02-14, 2020-03-02), are the
dated steps: no placebo window pair spans one. After 2018-07-06 the term moved by +0.0383 on 2019-09-01
and by −0.0190 on 2020-02-14, and from 2019 the exclusions set one rate for the approved purchases of
some firms and another for the rest. The later steps carry no reading here: `h_e Δ` is at most about
0.03 and 0.015, the size of the narrowest floors, and each step sits within days of other dated
documents.

The documents: [2018] No. 1 at gss.mof.gov.cn/gzdt/zhengcefabu/201804/t20180408_2862844.htm with its
list; [2018] No. 5 at m.mof.gov.cn/czxw/201806/t20180616_2930325.htm, list one as posted by the Fujian
commerce department (swt.fujian.gov.cn/xxgk/ztzl/mymc/jsqd/201809/P020180918703451581078.pdf);
[2019] No. 4 at gss.mof.gov.cn/gzdt/zhengcefabu/201908/t20190823_3372928.htm with its list one, and
the rates by line in USDA FAS GAIN report CH19051; 2019-09-13 at
ndrc.gov.cn/xwdt/xwfb/201909/t20190913_1181533_ext.html; 2019-12-06 at
mof.gov.cn/zhengwuxinxi/caizhengxinwen/201912/t20191206_3436960.htm; [2020] No. 1 and No. 2 at
gov.cn/zhengce/zhengceku/2020-02/06/content_5475214.htm and 2020-02/18/content_5480381.htm. The
exchange's rule change for the 1805 contract was announced on 2017-05-23. The first case of African
swine fever in China was confirmed on 2018-08-03 (Xinhua, relaying the Ministry of Agriculture and
Rural Affairs).

## 2. Plateaus and settings

Each relative level is averaged over a plateau of weeks before the step and a plateau after it. A week
ends on a Friday and opens on the Saturday before it; an AgTransport week dated on a Wednesday, a
Thursday or a Saturday belongs to the nearest Friday. The Gulf enters once a week. Paranaguá, the yuan
and Dalian enter as means over the days of the plateau that carry a value: Dalian over the days its
contract traded, and Dalian in dollars over those of them that also carry a yuan rate. The contract read
is the one that traded in both plateaus with the largest volume over the two.

| Setting | Pre plateau | Post plateau | Weeks between |
|---|---|---|---|
| A (default) | 13 weeks, 2018-01-05 to 03-30 | 4 weeks, 2018-07-06 to 07-27 | 13 |
| B | 13 weeks, 2018-01-05 to 03-30 | 6 weeks, 2018-06-22 to 07-27 | 11 |
| C | 6 weeks, 2018-05-04 to 06-08 | 4 weeks, 2018-07-06 to 07-27 | 3 |
| D | 6 weeks, 2018-05-04 to 06-08 | 6 weeks, 2018-06-22 to 07-27 | 1 |

The pre plateaus of A and B end before the first dated document, and those of C and D before the one
that gave the date. The post plateaus of B and D open with the week that holds 2018-06-16. Every post
plateau ends before 2018-08-03. In all four settings the contract read is b1809, and every week of both
plateaus carries a Gulf bid, a Paranaguá day, a yuan day and a day b1809 traded.

## 3. Floors

The floor of each move is the larger of two numbers. The quote grid adds the relative quote steps of
the series in the move: a cent on a Gulf bid (median 9.79 dollars over 2016 to 2020), a cent on a
Paranaguá bag (median 22.24), one yuan on a Dalian settlement (median 3,245) and a ten-thousandth on a
yuan rate (median 6.79), from 0.00001 for the yuan to 0.0015 for Paranaguá against the Gulf. The second
number is the median absolute move of the same quantity over every window pair of the same shape
between 2016-01-08 and 2021-01-01 whose span holds no dated step, where each plateau carries a Gulf
week and a day of each daily series. The median is the floor in every case below.

| Setting | Pairs kept | Spanning a dated step | Apart | Short a Gulf week |
|---|---|---|---|---|
| A | 131 | 101 | 5 | 25 |
| B | 131 | 101 | 5 | 27 |
| C | 182 | 67 | 16 | 32 |
| D | 182 | 67 | 16 | 38 |

"Apart" counts pairs that share no week, taken in time order: the floors of A and B rest on five
separate stretches of the five years, those of C and D on sixteen. Dalian's legs have fewer pairs,
since in some of them no contract traded in both plateaus: 115 and 117 in A and B, 169 and 173 in C and D, with 14 and 15
apart in C and D.

## 4. Readings

**Moves between the plateaus, with the floor and how many placebo pairs moved at least as far:**

| Move | A | B | C | D |
|---|---|---|---|---|
| Paranaguá against the Gulf | +0.1376 (0.0406; 13 of 131) | +0.1171 (0.0415; 15 of 131) | +0.1370 (0.0223; 6 of 182) | +0.1164 (0.0197; 7 of 182) |
| Dalian against the Gulf, market rate | +0.1030 (0.0310; 13 of 115) | +0.1030 (0.0295; 11 of 117) | +0.1107 (0.0220; 1 of 169) | +0.1107 (0.0201; 1 of 173) |
| Dalian against the Gulf, pre-plateau rate | +0.1592 (0.0475; 1 of 115) | +0.1510 (0.0521; 2 of 117) | +0.1620 (0.0242; 0 of 169) | +0.1537 (0.0268; 1 of 173) |
| Dalian against Paranaguá, market rate | −0.0346 (0.0760; 76 of 115) | −0.0141 (0.0777; 102 of 117) | −0.0263 (0.0295; 92 of 169) | −0.0057 (0.0268; 141 of 173) |
| Dalian against Paranaguá, pre-plateau rate | +0.0216 (0.0833; 93 of 115) | +0.0340 (0.0793; 85 of 117) | +0.0250 (0.0342; 96 of 169) | +0.0373 (0.0323; 80 of 173) |
| log yuan per US$ | +0.0541 (0.0281; 9 of 131) | +0.0451 (0.0262; 11 of 131) | +0.0507 (0.0121; 0 of 182) | +0.0417 (0.0109; 0 of 182) |

**The tariff's part, and the states:**

| Leg | A | B | C | D | State |
|---|---|---|---|---|---|
| Paranaguá against the Gulf | [+0.138, +0.192] | [+0.117, +0.162] | [+0.137, +0.188] | [+0.116, +0.158] | matches in all four |
| same, no orientation | [+0.083, +0.192] | [+0.072, +0.162] | [+0.086, +0.188] | [+0.075, +0.158] | matches in all four |
| Dalian against Paranaguá | [−0.089, +0.022] | [−0.059, +0.034] | [−0.077, +0.025] | [−0.047, +0.037] | not read in all four, within the floor |
| same, no orientation | [−0.143, +0.074] | [−0.104, +0.076] | [−0.128, +0.075] | [−0.089, +0.078] | not read in all four, within the floor |
| Dalian against the Gulf | [+0.103, +0.159] | [+0.103, +0.151] | [+0.111, +0.162] | [+0.111, +0.154] | printed |

**The share `h_e`**, the tariff's part of Dalian against the Gulf over `Δ`: from below, the larger of
Paranaguá against the Gulf and Dalian at the market rate; from above, Dalian at the pre-plateau rate.

| | A | B | C | D |
|---|---|---|---|---|
| `h_e` | 0.633 to 0.733 | 0.539 to 0.695 | 0.630 to 0.745 | 0.536 to 0.708 |
| no orientation | 0.384 to 0.723 | 0.331 to 0.682 | 0.397 to 0.743 | 0.344 to 0.701 |

In every setting the low end comes from Paranaguá, the leg that does not pass through the yuan. Over
setting A the Gulf fell by about 15% in weekly means and Paranaguá by about 1%. The settings whose post
plateau opens on 2018-06-22 read Paranaguá against the Gulf about 0.02 lower than those opening on
07-06: their two extra weeks are the weeks right after the announcement that gave the date.

**Known answer.** Adjemian, Smith and He (2021, Food Policy 105, 102152) estimate that, against no
tariff, the Gulf export price was about $0.74/bu lower and the Brazilian price about $0.97/bu higher
from late June to late November 2018. Paranaguá minus the Gulf, in dollars a bushel, averaged
+0.038 over the pre plateau of A (13 weeks) and
+1.629 over the Fridays 2018-06-29 to 11-30 (22 weeks with a
Gulf bid): +1.591 against their +1.71, a ratio of 0.93.

**The path**, weekly from the record (tonne prices as weekly means; relative levels in logs):

| Friday | Gulf US$/t | Paranaguá US$/t | Dalian b1809 yuan/t | yuan | ln Paranaguá/Gulf | ln Dalian/Gulf, market rate | ln Dalian/Gulf, pre-plateau rate |
|---|---|---|---|---|---|---|---|
| 03-30 | 397.6 | 403.5 | 3,547.8 | 6.2803 | +0.0149 | +0.3513 | +0.3398 |
| 04-06 | 403.1 | 414.0 | 3,636.1 | 6.2960 | +0.0268 | +0.3605 | +0.3506 |
| 05-18 | 385.8 | 387.3 | 3,380.6 | 6.3648 | +0.0039 | +0.3197 | +0.3215 |
| 06-08 | 375.9 | 382.5 | 3,379.6 | 6.3972 | +0.0174 | +0.3404 | +0.3473 |
| 06-15 | 352.4 | 370.5 | 3,310.2 | 6.4059 | +0.0502 | +0.3829 | +0.3911 |
| 06-22 | 348.7 | 370.4 | 3,407.1 | 6.4764 | +0.0604 | +0.4098 | +0.4305 |
| 06-29 | 335.1 | 369.7 | 3,441.9 | 6.5903 | +0.0983 | +0.4437 | +0.4804 |
| 07-06 | 342.8 | 373.3 | 3,478.1 | 6.6434 | +0.0852 | +0.4236 | +0.4681 |
| 07-13 | 320.0 | 381.1 | 3,398.2 | 6.6542 | +0.1745 | +0.4673 | +0.5136 |
| 07-20 | 330.7 | 387.6 | 3,380.3 | 6.7280 | +0.1587 | +0.4183 | +0.4756 |
| 07-27 | 339.1 | 392.5 | 3,429.6 | 6.7892 | +0.1461 | +0.3984 | +0.4648 |
| 08-03 | 341.7 | 393.7 | 3,394.4 | 6.8197 | +0.1415 | +0.3761 | +0.4470 |

## 5. Structural checks

| | Kind | What it checks | Run |
|---|---|---|---|
| PASS `B115-1` | `instrument` | every week of both plateaus, in every setting, has a Gulf bid, a Paranaguá day, a yuan day and a day the chosen No. 2 soybean contract traded | four settings, b1809, no week missing |
| PASS `B115-2` | `instrument` | no placebo window pair spans a dated soybean tariff document, and in every setting placebo pairs read Paranaguá against the Gulf and Dalian against the Gulf | 131, 131, 182 and 182 pairs kept, none spanning a dated step |
| PASS `B115-3` | `own_reading` | the six moves are printed in every setting against their placebo floors | section 4 |
| PASS `B115-4` | `own_reading` | the tariff moved Paranaguá up against the Gulf | matches in all four settings, with and without the orientations |
| no verdict `B115-5` | `own_reading` | the tariff's part of Dalian against Paranaguá is at least 0 | not read in all four settings, within the floor |
| PASS `B115-6` | `own_reading` | the interval for `h_e` is printed in every setting, with and without the orientations | section 4 |
| PASS `B115-7` | `known_answer` | Paranaguá minus the Gulf, late June to late November 2018 against the pre plateau, has the sign of the published +1.71 $/bu and lies within one order of magnitude of it | +1.591 $/bu, ratio 0.93 |

An `instrument` check asks whether the inputs and the windows are what the reading needs, an
`own_reading` is this station's reading of Corollary 43.6, and the `known_answer` sets one leg against
an independent published estimate.

The selftest runs the whole reading on synthetic worlds with exact steps and checks the six moves,
the intervals, the share, the known-answer spread and the number of weeks between plateaus. It plants a
failure under each criterion: a Gulf week dropped from a plateau, a week in which the contract did not
trade, a placebo pair across a dated step, a setting with no placebo pair for Dalian, a missing move, a
missing interval, Paranaguá falling against the Gulf, a spread two orders of magnitude off the known
answer. It checks every row of the state mapping, that an interval straddling zero and settings that
disagree give no verdict, the contract chosen on a tie and on a volume, and that a traded day without a
yuan rate stays out of the dollar reading. Thirty-one deliberate faults in the implementation were each
caught by the selftest.

## 6. What more data would read

1. **A 2018 US Pacific Northwest soybean bid** would read the US export end as two positions, the Gulf
   and the port most tied to China, with the package clause of Corollary 43.6 across the two.
2. **A dollar import price in China for US and for Brazilian cargoes** would read the Dalian legs without
   the yuan's step, and with it Dalian against Paranaguá.
3. **The AgTransport soybean series from 2007 and Dalian's No. 2 soybean files before 2016** would give
   settings A and B more separate placebo stretches than five.
4. **Sorghum** carries a cut on the same kind of relation (a 178.6% deposit from 2018-04-18) and its
   end (the investigation closed on 2018-05-18). The station's other branch reads their directions against
   Gulf corn in [`b115_sorghum_deposit.md`](b115_sorghum_deposit.md); with no weekly price for sorghum in
   China, the share of either step is not read there.
